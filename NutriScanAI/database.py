# database.py
# NutriScan AI — SQLite Persistence Layer
#
# Manages two tables:
#   users       — registered accounts (email, name, hashed password, avatar)
#   scan_history — per-user scan results (max 50 stored, 5 shown in sidebar)
#
# The DB file is created automatically at first run.
# Default location: nutriscan.db next to this file.
# Change DB_PATH below to move it (e.g. into a data/ subfolder).
#
# No external packages needed — sqlite3 is part of Python's stdlib.

import sqlite3
import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta
from contextlib import contextmanager

# ── Config ────────────────────────────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(__file__), "nutriscan.db")

# Max scan entries stored per user in the DB
MAX_HISTORY_PER_USER = 50

# Max entries loaded into session_state for the sidebar
SIDEBAR_HISTORY_LIMIT = 5


# ── Connection helper ─────────────────────────────────────────────────────────

@contextmanager
def _get_conn():
    """Thread-safe SQLite connection with WAL mode for concurrent Streamlit sessions."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row          # lets us access columns by name
    conn.execute("PRAGMA journal_mode=WAL") # safer for multi-session access
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ── Schema init ───────────────────────────────────────────────────────────────

def init_db():
    """
    Create tables if they don't exist.
    Safe to call on every app startup — it's a no-op if the DB is already set up.
    """
    with _get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                email         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
                name          TEXT    NOT NULL,
                password_hash TEXT,           -- NULL for Google SSO users
                avatar_url    TEXT    DEFAULT '',
                created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
                last_login    TEXT
            );

            CREATE TABLE IF NOT EXISTS scan_history (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email   TEXT    NOT NULL COLLATE NOCASE,
                product_name TEXT    NOT NULL,
                score        REAL,
                frequency    TEXT    DEFAULT '',
                barcode      TEXT    DEFAULT '',
                llm_estimated INTEGER DEFAULT 0,  -- boolean: 0/1
                report_json  TEXT    DEFAULT '{}', -- full report_data as JSON
                scanned_at   TEXT    NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (user_email) REFERENCES users(email)
                    ON DELETE CASCADE ON UPDATE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_scan_history_user
                ON scan_history(user_email, scanned_at DESC);

            CREATE TABLE IF NOT EXISTS reset_tokens (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                email      TEXT NOT NULL COLLATE NOCASE,
                token      TEXT NOT NULL UNIQUE,
                expires_at TEXT NOT NULL,
                used       INTEGER DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_reset_tokens_token
                ON reset_tokens(token);
        """)

    # Seed demo user if not already present
    _seed_demo_user()


def _seed_demo_user():
    """Insert the demo account if it doesn't exist yet."""
    create_user(
        email    = "demo@nutriscan.ai",
        name     = "Demo User",
        password = "demo1234",
    )


# ═════════════════════════════════════════════════════════════════════════════
#  USER CRUD
# ═════════════════════════════════════════════════════════════════════════════

def _hash(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def get_user(email: str) -> dict | None:
    """
    Return user dict or None.
    Keys: id, email, name, password_hash, avatar_url, created_at, last_login
    """
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE email = ?", (email.strip().lower(),)
        ).fetchone()
    return dict(row) if row else None


def create_user(email: str, name: str,
                password: str | None = None,
                avatar_url: str = "") -> bool:
    """
    Insert a new user. Returns True on success, False if email already exists.
    Pass password=None for Google SSO users (no password stored).
    """
    pw_hash = _hash(password) if password else None
    try:
        with _get_conn() as conn:
            conn.execute(
                """INSERT INTO users (email, name, password_hash, avatar_url)
                   VALUES (?, ?, ?, ?)""",
                (email.strip().lower(), name, pw_hash, avatar_url),
            )
        return True
    except sqlite3.IntegrityError:
        # email already exists — that's fine, not an error
        return False


def verify_password(email: str, password: str) -> bool:
    """Return True if the password matches the stored hash."""
    user = get_user(email)
    if not user or not user["password_hash"]:
        return False
    return user["password_hash"] == _hash(password)


def update_last_login(email: str):
    """Stamp the last_login timestamp for a user."""
    with _get_conn() as conn:
        conn.execute(
            "UPDATE users SET last_login = datetime('now') WHERE email = ?",
            (email.strip().lower(),),
        )


def update_avatar(email: str, avatar_url: str):
    """Store an avatar URL (or base64 string) for a user."""
    with _get_conn() as conn:
        conn.execute(
            "UPDATE users SET avatar_url = ? WHERE email = ?",
            (avatar_url, email.strip().lower()),
        )


# ═════════════════════════════════════════════════════════════════════════════
#  PASSWORD RESET TOKENS
# ═════════════════════════════════════════════════════════════════════════════

def create_reset_token(email: str) -> str | None:
    """
    Generate a secure reset token for the given email.
    Returns the token string, or None if the email is not registered.
    Token expires in 30 minutes.
    """
    if not get_user(email):
        return None  # email not registered — don't reveal this to the caller

    token      = secrets.token_urlsafe(32)
    expires_at = (datetime.now() + timedelta(minutes=30)).isoformat()

    with _get_conn() as conn:
        # Invalidate any existing unused tokens for this email
        conn.execute(
            "UPDATE reset_tokens SET used = 1 WHERE email = ? AND used = 0",
            (email.lower(),)
        )
        conn.execute(
            "INSERT INTO reset_tokens (email, token, expires_at) VALUES (?, ?, ?)",
            (email.lower(), token, expires_at)
        )
    return token


def verify_reset_token(token: str) -> str | None:
    """
    Verify a reset token. Returns the email address if valid, None otherwise.
    A token is valid if: it exists, hasn't been used, and hasn't expired.
    """
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT email, expires_at, used FROM reset_tokens WHERE token = ?",
            (token,)
        ).fetchone()

    if not row:
        return None
    if row["used"]:
        return None
    if datetime.fromisoformat(row["expires_at"]) < datetime.now():
        return None
    return row["email"]


def consume_reset_token(token: str, new_password: str) -> bool:
    """
    Verify the token and update the user's password in one atomic step.
    Returns True on success, False if the token is invalid/expired.
    """
    email = verify_reset_token(token)
    if not email:
        return False

    with _get_conn() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE email = ?",
            (_hash(new_password), email)
        )
        conn.execute(
            "UPDATE reset_tokens SET used = 1 WHERE token = ?",
            (token,)
        )
    return True


def update_password(email: str, new_password: str):
    """Directly update a user's password (used from profile edit page)."""""
    with _get_conn() as conn:
        conn.execute(
            "UPDATE users SET password_hash = ? WHERE email = ?",
            (_hash(new_password), email.lower())
        )


def update_profile(email: str, name: str, avatar_url: str = None):
    """Update a user's display name and optionally their avatar."""""
    if avatar_url is not None:
        with _get_conn() as conn:
            conn.execute(
                "UPDATE users SET name = ?, avatar_url = ? WHERE email = ?",
                (name, avatar_url, email.lower())
            )
    else:
        with _get_conn() as conn:
            conn.execute(
                "UPDATE users SET name = ? WHERE email = ?",
                (name, email.lower())
            )


# ═════════════════════════════════════════════════════════════════════════════
#  SCAN HISTORY CRUD
# ═════════════════════════════════════════════════════════════════════════════

def save_scan(email: str, report_data: dict):
    """
    Persist one scan result for a user.
    Automatically prunes old entries so the DB doesn't grow forever.

    report_data is the same dict that app.py already builds — no changes needed.
    """
    email = email.strip().lower()

    # Avoid duplicate consecutive scans of the same barcode
    recent = load_scans(email, limit=1)
    barcode = report_data.get("barcode", "")
    if recent and barcode and recent[0].get("barcode") == barcode:
        return

    with _get_conn() as conn:
        conn.execute(
            """INSERT INTO scan_history
               (user_email, product_name, score, frequency,
                barcode, llm_estimated, report_json, scanned_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))""",
            (
                email,
                report_data.get("product_name", "Unknown Product"),
                report_data.get("display_score"),
                report_data.get("consumption_frequency", ""),
                barcode,
                1 if report_data.get("llm_estimated") else 0,
                json.dumps(report_data),   # full report stored for future use
            ),
        )

        # Prune: keep only the most recent MAX_HISTORY_PER_USER rows
        conn.execute(
            """DELETE FROM scan_history
               WHERE user_email = ?
               AND id NOT IN (
                   SELECT id FROM scan_history
                   WHERE user_email = ?
                   ORDER BY scanned_at DESC
                   LIMIT ?
               )""",
            (email, email, MAX_HISTORY_PER_USER),
        )


def load_scans(email: str, limit: int = SIDEBAR_HISTORY_LIMIT) -> list[dict]:
    """
    Return the most recent `limit` scans for a user as a list of dicts.
    Each dict has the same keys that app.py's session_state.scan_history uses,
    plus a `report_data` key with the full JSON for future detail views.
    """
    with _get_conn() as conn:
        rows = conn.execute(
            """SELECT product_name, score, frequency, barcode,
                      llm_estimated, scanned_at, report_json
               FROM scan_history
               WHERE user_email = ?
               ORDER BY scanned_at DESC
               LIMIT ?""",
            (email.strip().lower(), limit),
        ).fetchall()

    results = []
    for row in rows:
        # Parse the stored datetime and reformat to HH:MM for the sidebar
        try:
            dt = datetime.fromisoformat(row["scanned_at"])
            time_str = dt.strftime("%H:%M")
            date_str = dt.strftime("%d %b")
        except Exception:
            time_str = row["scanned_at"][:5]
            date_str = ""

        results.append({
            "product_name":  row["product_name"],
            "score":         row["score"],
            "frequency":     row["frequency"] or "",
            "barcode":       row["barcode"] or "",
            "llm_estimated": bool(row["llm_estimated"]),
            "scanned_at":    time_str,
            "scanned_date":  date_str,
            "report_data":   json.loads(row["report_json"] or "{}"),
        })
    return results


def delete_all_scans(email: str):
    """Wipe all scan history for a user (called from the 'Clear history' button)."""
    with _get_conn() as conn:
        conn.execute(
            "DELETE FROM scan_history WHERE user_email = ?",
            (email.strip().lower(),),
        )


def get_scan_count(email: str) -> int:
    """Return total number of scans stored for a user."""
    with _get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) as cnt FROM scan_history WHERE user_email = ?",
            (email.strip().lower(),),
        ).fetchone()
    return row["cnt"] if row else 0