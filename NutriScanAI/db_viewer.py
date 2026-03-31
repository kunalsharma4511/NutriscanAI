# db_viewer.py
# NutriScan AI — Developer Database Viewer
#
# Run with:  streamlit run db_viewer.py
# Keep this file OFF production — it exposes all user data.
#
# Features:
#   - Live view of all tables (users, scan_history)
#   - Search / filter by email or product name
#   - View full report_json for any scan
#   - Delete individual rows or wipe a table
#   - DB stats summary

import streamlit as st
import sqlite3
import json
import os
import pandas as pd
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "nutriscan.db")

st.set_page_config(
    page_title="NutriScan DB Viewer",
    page_icon="🛢️",
    layout="wide",
)

# ── Simple dev password gate ──────────────────────────────────────────────────
DEV_PASSWORD = "nutriscan_dev"   # ← change this

if "dev_auth" not in st.session_state:
    st.session_state.dev_auth = False

if not st.session_state.dev_auth:
    st.title("🛢️ NutriScan DB Viewer")
    st.caption("Developer access only | pass: nutriscan_dev")
    pw = st.text_input("Password", type="password")
    if st.button("Enter", type="primary"):
        if pw == DEV_PASSWORD:
            st.session_state.dev_auth = True
            st.rerun()
        else:
            st.error("Wrong password.")
    st.stop()

# ── DB helpers ────────────────────────────────────────────────────────────────

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def run_query(sql: str, params: tuple = ()) -> list[dict]:
    with get_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [dict(r) for r in rows]


def run_write(sql: str, params: tuple = ()):
    with get_conn() as conn:
        conn.execute(sql, params)
        conn.commit()


def table_exists(name: str) -> bool:
    rows = run_query(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    )
    return len(rows) > 0


# ── Header ────────────────────────────────────────────────────────────────────

st.title("🛢️ NutriScan DB Viewer")
st.caption(f"Connected to: `{DB_PATH}`")

if not os.path.exists(DB_PATH):
    st.error("Database file not found. Run the main app first to create it.")
    st.stop()

# ── Stats row ─────────────────────────────────────────────────────────────────

col1, col2, col3, col4 = st.columns(4)

with col1:
    user_count = run_query("SELECT COUNT(*) as n FROM users")[0]["n"] \
        if table_exists("users") else 0
    st.metric("Total users", user_count)

with col2:
    scan_count = run_query("SELECT COUNT(*) as n FROM scan_history")[0]["n"] \
        if table_exists("scan_history") else 0
    st.metric("Total scans", scan_count)

with col3:
    db_size = os.path.getsize(DB_PATH) / 1024
    st.metric("DB size", f"{db_size:.1f} KB")

with col4:
    last_scan = run_query(
        "SELECT scanned_at FROM scan_history ORDER BY scanned_at DESC LIMIT 1"
    ) if table_exists("scan_history") else []
    last = last_scan[0]["scanned_at"][:16] if last_scan else "—"
    st.metric("Last scan", last)

st.divider()

# ── Tab layout ────────────────────────────────────────────────────────────────

tab_users, tab_scans, tab_sql = st.tabs(["👤 Users", "🔍 Scan History", "⌨️ Raw SQL"])


# ══════════════════════════════════════════════════════════════════════════════
# USERS TABLE
# ══════════════════════════════════════════════════════════════════════════════

with tab_users:
    st.subheader("Users")

    if not table_exists("users"):
        st.info("Users table not found.")
    else:
        search = st.text_input("Search by email or name", placeholder="e.g. demo@nutriscan.ai")

        if search:
            users = run_query(
                "SELECT id, email, name, avatar_url, created_at, last_login "
                "FROM users WHERE email LIKE ? OR name LIKE ?",
                (f"%{search}%", f"%{search}%")
            )
        else:
            users = run_query(
                "SELECT id, email, name, avatar_url, created_at, last_login FROM users"
            )

        if not users:
            st.info("No users found.")
        else:
            df = pd.DataFrame(users)
            # Mask password hash — never shown
            df["avatar_url"] = df["avatar_url"].apply(
                lambda x: "✓ set" if x and len(x) > 10 else "—"
            )
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption(f"{len(users)} user(s) shown")

        st.divider()

        # ── Delete user ───────────────────────────────────────────────────────
        with st.expander("⚠️ Delete a user"):
            del_email = st.text_input("Email to delete", key="del_user_email")
            if st.button("Delete user + all their scans", type="primary", key="del_user_btn"):
                if del_email:
                    run_write("DELETE FROM scan_history WHERE user_email = ?", (del_email,))
                    run_write("DELETE FROM users WHERE email = ?", (del_email,))
                    st.success(f"Deleted user: {del_email}")
                    st.rerun()
                else:
                    st.warning("Enter an email first.")

        with st.expander("☠️ Wipe ALL users"):
            st.warning("This will delete every user and all their scans.")
            if st.button("Wipe users table", key="wipe_users"):
                run_write("DELETE FROM scan_history")
                run_write("DELETE FROM users")
                st.success("All users and scans deleted.")
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# SCAN HISTORY TABLE
# ══════════════════════════════════════════════════════════════════════════════

with tab_scans:
    st.subheader("Scan History")

    if not table_exists("scan_history"):
        st.info("Scan history table not found.")
    else:
        # ── Filters ───────────────────────────────────────────────────────────
        fcol1, fcol2 = st.columns(2)
        with fcol1:
            filter_email = st.text_input("Filter by email", placeholder="user@example.com")
        with fcol2:
            filter_product = st.text_input("Filter by product name", placeholder="e.g. Maggi")

        base_sql = """
            SELECT id, user_email, product_name, score, frequency,
                   barcode, llm_estimated, scanned_at
            FROM scan_history
            WHERE 1=1
        """
        params = []
        if filter_email:
            base_sql += " AND user_email LIKE ?"
            params.append(f"%{filter_email}%")
        if filter_product:
            base_sql += " AND product_name LIKE ?"
            params.append(f"%{filter_product}%")
        base_sql += " ORDER BY scanned_at DESC LIMIT 200"

        scans = run_query(base_sql, tuple(params))

        if not scans:
            st.info("No scans found.")
        else:
            df = pd.DataFrame(scans)
            df["llm_estimated"] = df["llm_estimated"].apply(lambda x: "✓" if x else "")
            df["score"] = df["score"].apply(
                lambda x: f"{x}/10" if x is not None else "—"
            )
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption(f"{len(scans)} scan(s) shown (max 200)")

        st.divider()

        # ── Full report JSON viewer ───────────────────────────────────────────
        st.subheader("View full report JSON")
        scan_id = st.number_input("Scan ID", min_value=1, step=1, value=1)
        if st.button("Load report", key="load_report"):
            row = run_query(
                "SELECT product_name, user_email, scanned_at, report_json "
                "FROM scan_history WHERE id = ?", (scan_id,)
            )
            if row:
                r = row[0]
                st.markdown(f"**{r['product_name']}** — {r['user_email']} — {r['scanned_at']}")
                try:
                    parsed = json.loads(r["report_json"] or "{}")
                    st.json(parsed)
                except Exception:
                    st.code(r["report_json"])
            else:
                st.warning(f"No scan found with ID {scan_id}.")

        st.divider()

        # ── Delete scan ───────────────────────────────────────────────────────
        with st.expander("⚠️ Delete a scan by ID"):
            del_id = st.number_input("Scan ID to delete", min_value=1, step=1, key="del_scan_id")
            if st.button("Delete scan", type="primary", key="del_scan_btn"):
                run_write("DELETE FROM scan_history WHERE id = ?", (del_id,))
                st.success(f"Deleted scan ID {del_id}.")
                st.rerun()

        with st.expander("⚠️ Delete all scans for a user"):
            del_scan_email = st.text_input("Email", key="del_scan_email")
            if st.button("Delete all scans", type="primary", key="del_scan_user_btn"):
                if del_scan_email:
                    run_write("DELETE FROM scan_history WHERE user_email = ?", (del_scan_email,))
                    st.success(f"Deleted all scans for {del_scan_email}.")
                    st.rerun()

        with st.expander("☠️ Wipe ALL scan history"):
            st.warning("This will permanently delete every scan in the database.")
            if st.button("Wipe scan_history table", key="wipe_scans"):
                run_write("DELETE FROM scan_history")
                st.success("All scans deleted.")
                st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# RAW SQL CONSOLE
# ══════════════════════════════════════════════════════════════════════════════

with tab_sql:
    st.subheader("Raw SQL console")
    st.caption("SELECT queries only — write operations are blocked here for safety.")

    default_sql = "SELECT * FROM scan_history ORDER BY scanned_at DESC LIMIT 20"
    sql_input = st.text_area("SQL", value=default_sql, height=120)

    if st.button("Run query", type="primary"):
        stripped = sql_input.strip().upper()
        if not stripped.startswith("SELECT"):
            st.error("Only SELECT queries are allowed here.")
        else:
            try:
                results = run_query(sql_input)
                if results:
                    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
                    st.caption(f"{len(results)} row(s) returned")
                else:
                    st.info("Query returned no rows.")
            except Exception as e:
                st.error(f"SQL error: {e}")

    st.divider()
    st.caption("**Useful queries:**")
    st.code("SELECT * FROM users")
    st.code("SELECT user_email, COUNT(*) as scans FROM scan_history GROUP BY user_email")
    st.code("SELECT * FROM scan_history WHERE score >= 8 ORDER BY scanned_at DESC")
    st.code("SELECT product_name, AVG(score) as avg_score FROM scan_history GROUP BY product_name ORDER BY avg_score DESC")