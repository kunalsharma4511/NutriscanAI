# auth.py
# NutriScan AI — Authentication Gate
#
# Drop this file next to app.py.
# In app.py, add at the very top (after imports, before st.set_page_config):
#

#
# Session keys managed here:
#   st.session_state.authenticated  — bool
#   st.session_state.current_user   — dict { name, email, avatar_url }

import streamlit as st
import re
import time
import requests
from database import (
    init_db, get_user, create_user, verify_password,
    update_last_login, load_scans, save_scan, delete_all_scans,
    create_reset_token, consume_reset_token, update_password, update_profile
)
from mailer import send_reset_email, is_configured as mail_configured

# Initialise DB on first import — safe to call multiple times
init_db()


# ─────────────────────────────────────────────────────────────────────────────
#  USER STORE — backed by SQLite via database.py
#  get_user / create_user / verify_password are imported from database.py
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
#  GOOGLE OAUTH HELPER  (requires google-auth package)
#  pip install google-auth requests
#
#  Set these in your .env / Streamlit secrets:
#    GOOGLE_CLIENT_ID     = "….apps.googleusercontent.com"
#    GOOGLE_CLIENT_SECRET = "GOCSPX-…"
#    GOOGLE_REDIRECT_URI  = "http://localhost:8501"   # must match Google Console
# ─────────────────────────────────────────────────────────────────────────────

def _google_auth_url() -> str:
    """Return the Google OAuth2 redirect URL."""
    try:
        client_id    = st.secrets["GOOGLE_CLIENT_ID"]
        redirect_uri = st.secrets.get("GOOGLE_REDIRECT_URI", "http://localhost:8501")
    except Exception:
        return ""

    params = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        "&response_type=code"
        "&scope=openid%20email%20profile"
        "&prompt=select_account"
    )
    return params


def _exchange_google_code(code: str) -> dict | None:
    """Exchange auth code for user info. Returns dict or None on failure."""
    try:
        client_id     = st.secrets["GOOGLE_CLIENT_ID"]
        client_secret = st.secrets["GOOGLE_CLIENT_SECRET"]
        redirect_uri  = st.secrets.get("GOOGLE_REDIRECT_URI", "http://localhost:8501")
    except Exception:
        return None

    token_resp = requests.post("https://oauth2.googleapis.com/token", data={
        "code":          code,
        "client_id":     client_id,
        "client_secret": client_secret,
        "redirect_uri":  redirect_uri,
        "grant_type":    "authorization_code",
    }, timeout=10)

    if not token_resp.ok:
        return None

    access_token = token_resp.json().get("access_token")
    info_resp    = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    if not info_resp.ok:
        return None

    return info_resp.json()   # { email, name, picture, ... }


def _handle_google_callback():
    """Called on every page load — picks up ?code= from Google redirect."""
    params = st.query_params
    code   = params.get("code")
    if not code:
        return

    # Clear the code from URL immediately
    st.query_params.clear()

    with st.spinner("Signing in with Google..."):
        info = _exchange_google_code(code)

    if not info or not info.get("email"):
        st.error("Google sign-in failed. Please try again.")
        return

    email      = info["email"].lower()
    name       = info.get("name", email.split("@")[0])
    avatar_url = info.get("picture", "")

    # Auto-create account on first Google login (no password for SSO users)
    create_user(email=email, name=name, password=None, avatar_url=avatar_url)
    update_last_login(email)

    # Load persisted scan history into session state
    st.session_state.authenticated = True
    st.session_state.current_user  = {
        "name":       name,
        "email":      email,
        "avatar_url": avatar_url,
    }
    st.session_state.scan_history = load_scans(email)
    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
#  AUTH CSS  — matches _inject_theme() palette exactly
# ─────────────────────────────────────────────────────────────────────────────

def _inject_auth_css(dark: bool):
    bg        = "#0e0e0e"     if dark else "#f7f9fc"
    card_bg   = "#1a1a1a"     if dark else "#ffffff"
    input_bg  = "#111111"     if dark else "#f0f3f8"
    border    = "#2a2a2a"     if dark else "#d8dde6"
    text      = "#f0f0f0"     if dark else "#1a1a1a"
    subtext   = "#888888"     if dark else "#666666"
    green     = "#27ae60"
    green_h   = "#2ecc71"
    brand_bg  = "#0d1f0e"     if dark else "#f0faf2"
    panel_bg  = "#111111"     if dark else "#ffffff"

    st.markdown(f"""
<style>
/* ── Kill ALL Streamlit chrome & spacing ── */
#MainMenu, footer, header {{ visibility: hidden; }}
.stApp {{ background: {bg} !important; overflow: hidden !important; }}
.stApp * {{ color: {text} !important; }}

/* ── Fix sidebar toggle button visibility ── */
button[data-testid="stSidebarNavCollapseButton"],
button[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarCollapsedControl"] {{
    visibility: visible !important;
    opacity: 1 !important;
    display: flex !important;
    pointer-events: all !important;
}}

/* ── Hide sidebar completely on auth page ── */
[data-testid="stSidebar"] {{
    display: none !important;
}}
button[data-testid="stSidebarCollapsedControl"] {{
    display: none !important;
}}

/* Strip every default margin/padding Streamlit injects */
.stApp > div,
.stApp > div > div,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewBlockContainer"],
[data-testid="block-container"],
.main .block-container {{
    padding: 0 !important;
    margin: 0 !important;
    max-width: 100% !important;
    width: 100% !important;
}}

# ADD inside the <style> block:
html, body, .stApp {{
    height: 100vh !important;
    overflow: hidden !important;
}}

[data-testid="stAppViewBlockContainer"] {{
    height: 100vh !important;
    overflow: hidden !important;
}}

section[data-testid="stMain"] {{
    overflow: hidden !important;
}}

[data-testid="stAppViewBlockContainer"] {{
    padding-top: 7rem !important;
}}
section[data-testid="stMain"] > div {{
    padding-top: 4rem !important;
}}
.main > div:first-child {{
    padding-top: 4rem !important;
}}



/* Lock the whole page to exactly the viewport — no scroll */
html, body, .stApp {{
    height: 100vh !important;
    max-height: 100vh !important;
    overflow: hidden !important;
}}

/* ── Two-column flex layout filling 100vh exactly ── */
.auth-outer {{
    display: flex;
    height: 140vh;
    width: 400%;
    overflow: hidden;
}}

/* ── Left brand panel ── */
.auth-brand {{
    flex: 1;
    background: {brand_bg};
    display: flex;
    flex-direction: column;
    justify-content: center;
    padding: 2rem 4rem;
    position: relative;
    overflow: hidden;
    min-width: 0;
}}
.auth-brand::before {{
    content: "";
    position: absolute;
    width: 340px; height: 340px;
    background: radial-gradient(circle, rgba(39,174,96,0.13) 0%, transparent 70%);
    top: -80px; left: -80px;
    pointer-events: none;
}}
.brand-logo-row {{
    display: flex; align-items: center; gap: 10px; margin-bottom: 1.5rem;
}}
.brand-icon {{
    width: 80px; height: 80px; border-radius: 10px;
    background: {green};
    display: flex; align-items: center; justify-content: center;
    font-size: 20px; flex-shrink: 0;
}}
.brand-name {{
    font-size: 18px; font-weight: 700;
    color: {text} !important; letter-spacing: -0.3px;
}}
.brand-name em {{ color: {green} !important; font-style: normal; }}
.brand-headline {{
    font-size: 24px; font-weight: 700; line-height: 1.3;
    letter-spacing: -0.4px; color: {text} !important;
    margin-bottom: 0.5rem;
}}
.brand-sub {{
    font-size: 13px; color: {subtext} !important;
    line-height: 1.6; max-width: 280px;
}}
.feature-list {{
    margin-top: 1.25rem;
    display: flex; flex-direction: column; gap: 9px;
}}
.feature-item {{
    display: flex; align-items: center; gap: 9px;
    font-size: 13px; color: {subtext} !important;
}}
.fdot {{
    width: 5px; height: 5px; border-radius: 50%;
    background: {green}; flex-shrink: 0;
}}

/* ── Right form panel — fixed width, full height, scrolls internally if needed ── */
.auth-right {{
    width: 420px;
    flex-shrink: 0;
    background: {panel_bg};
    border-left: 1px solid {border};
    display: flex;
    align-items: flex-start;
    justify-content: center;
    padding: 1.25rem 1.5rem;
    overflow-y: auto;
    height: 100vh;
}}
.auth-card {{ width: 100%; max-width: 340px; }}

/* ── Tab strip ── */
.tab-strip {{
    display: flex;
    background: {bg};
    border-radius: 9px; padding: 3px;
    margin-bottom: 1rem;
    border: 1px solid {border};
}}
.tab-btn {{
    flex: 1; text-align: center; padding: 7px 0;
    font-size: 12.5px; font-weight: 600;
    border-radius: 7px; cursor: pointer;
    color: {subtext} !important;
    border: none; background: transparent;
    font-family: inherit; transition: all 0.2s;
    text-decoration: none !important;
    display: block;
}}
.tab-btn:hover {{ color: {text} !important; text-decoration: none !important; }}
.tab-btn.active {{ background: {green}; color: #fff !important; }}
.tab-btn.active:hover {{ color: #fff !important; }}

/* ── Or divider ── */
.or-divider {{
    display: flex; align-items: center; gap: 8px; margin: 8px 0;
}}
.or-line {{ flex: 1; height: 1px; background: {border}; }}
.or-text {{ font-size: 11px; color: {subtext} !important; }}

/* ── Google button ── */
.google-btn {{
    display: flex; align-items: center; justify-content: center;
    gap: 9px; width: 100%; padding: 9px;
    background: {card_bg}; border: 1px solid {border};
    border-radius: 8px; font-size: 13px; font-weight: 600;
    cursor: pointer; text-decoration: none;
    color: {text} !important; transition: border-color 0.2s;
    margin-bottom: 0;
}}
.google-btn:hover {{ border-color: {green}; text-decoration: none !important; }}

/* ── Avatar hint ── */
.avatar-hint {{
    font-size: 11.5px; color: {subtext} !important; line-height: 1.4; margin-bottom: 6px;
}}
.avatar-hint strong {{
    display: block; font-size: 12.5px; font-weight: 600;
    color: {"#ccc" if dark else "#444"} !important; margin-bottom: 1px;
}}

/* ── Switch note ── */
.switch-note {{
    text-align: center; margin-top: 0.75rem;
    font-size: 12px; color: {subtext} !important;
}}

/* ── Feedback messages ── */
.auth-toast {{
    padding: 8px 12px; border-radius: 7px; font-size: 12.5px;
    background: {"#1a2a1a" if dark else "#f0faf2"};
    border: 1px solid {"#27ae6060" if dark else "#b7dfb7"};
    color: {green} !important; margin-top: 8px;
}}
.auth-err {{
    padding: 8px 12px; border-radius: 7px; font-size: 12.5px;
    background: {"#2a1a1a" if dark else "#fff5f5"};
    border: 1px solid {"#e74c3c60" if dark else "#f5c6c6"};
    color: #e74c3c !important; margin-top: 8px;
}}

/* ── Streamlit widget overrides ── */
div[data-testid="stTextInput"] {{
    margin-bottom: 0 !important;
}}
div[data-testid="stTextInput"] input {{
    background: {input_bg} !important;
    border: 1px solid {border} !important;
    border-radius: 7px !important;
    color: {text} !important;
    font-size: 13px !important;
    padding: 8px 11px !important;
}}
div[data-testid="stTextInput"] input:focus {{
    border-color: {green} !important;
    box-shadow: 0 0 0 2px {"#27ae6030" if dark else "#27ae6018"} !important;
}}
div[data-testid="stTextInput"] label {{
    font-size: 11px !important; font-weight: 600 !important;
    color: {"#aaa" if dark else "#555"} !important;
    letter-spacing: 0.3px; margin-bottom: 2px !important;
}}
/* Tighten the gap between label and input */
div[data-testid="stTextInput"] > label + div {{
    margin-top: 2px !important;
}}
/* Shrink vertical gap between stacked inputs */
div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlockBorderWrapper"],
div[data-testid="stVerticalBlock"] > div {{
    gap: 0 !important;
}}
.stTextInput {{ margin-bottom: 8px !important; }}

/* Primary buttons */
div[data-testid="stButton"] > button[kind="primary"] {{
    background: linear-gradient(135deg, {green}, {green_h}) !important;
    color: #fff !important; border: none !important;
    border-radius: 8px !important; font-weight: 700 !important;
    font-size: 13.5px !important; padding: 0.5rem 1rem !important;
    box-shadow: 0 2px 10px {"rgba(39,174,96,0.35)" if dark else "rgba(39,174,96,0.2)"} !important;
}}
div[data-testid="stButton"] > button[kind="primary"]:hover {{
    opacity: 0.9 !important;
}}
/* Secondary buttons */
div[data-testid="stButton"] > button[kind="secondary"] {{
    background: transparent !important;
    border: 1px solid {border} !important;
    border-radius: 8px !important;
    color: {text} !important;
    font-size: 13px !important;
    padding: 0.5rem 1rem !important;
}}
div[data-testid="stButton"] > button[kind="secondary"]:hover {{
    border-color: {green} !important;
    color: {green} !important;
}}

/* File uploader */
div[data-testid="stFileUploader"] {{
    background: {input_bg} !important;
    border: 1.5px dashed {border} !important;
    border-radius: 8px !important;
    padding: 6px !important;
}}

/* Caption / demo line */
div[data-testid="stCaptionContainer"] p {{
    font-size: 11px !important;
    color: {subtext} !important;
    margin-top: 6px !important;
}}

div[data-testid="stAppViewBlockContainer"] > div {{
    padding-top: 50 !important;
    margin-top: 50 !important;
}}
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
#  BRAND PANEL HTML
# ─────────────────────────────────────────────────────────────────────────────

def _brand_panel_html() -> str:
    try:
        import base64
        with open("assets/new_logo.png", "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        icon_html = f'<img src="data:image/png;base64,{b64}" width="74" height="74";object-fit:cover"/>'
    except Exception:
        icon_html = '🥗'

    return f"""
<div class="auth-brand">
  <div class="brand-logo-row">
    <div class="brand-icon">
        {icon_html}
    </div>
    <div class="brand-name">Nutri<em>Scan</em> AI</div>
  </div>
  <div class="brand-headline">Your personal<br>nutrition intelligence</div>
  <div class="brand-sub">Scan any packaged food — get instant AI-powered nutrition insights tailored to your health profile.</div>
  <div class="feature-list">
    <div class="feature-item"><div class="fdot"></div>Instant barcode & label scanning</div>
    <div class="feature-item"><div class="fdot"></div>5-agent AI analysis pipeline</div>
    <div class="feature-item"><div class="fdot"></div>Personalised health score & report</div>
    <div class="feature-item"><div class="fdot"></div>Tracks your scan history</div>
  </div>
</div>
"""

# ─────────────────────────────────────────────────────────────────────────────
#  VALIDATION HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _valid_email(email: str) -> bool:
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email.strip()))


def _valid_password(pw: str) -> tuple[bool, str]:
    if len(pw) < 8:
        return False, "Password must be at least 8 characters."
    return True, ""


# ─────────────────────────────────────────────────────────────────────────────
#  RENDER AUTH PAGE
# ─────────────────────────────────────────────────────────────────────────────

def render_auth_page():
    """Render the full login / register UI. Call this when not authenticated."""

    dark = st.session_state.get("dark_mode", True)
    _inject_auth_css(dark)
    _handle_google_callback()

    # Session defaults for the auth form
    if "auth_tab" not in st.session_state:
        st.session_state.auth_tab = "login"   # "login" | "register"
    if "_auth_msg" not in st.session_state:
        st.session_state._auth_msg = ("", "")  # (text, type)  type = "ok"|"err"

    google_url = _google_auth_url()

    # ── Layout: brand left | form right ──────────────────────────────────────
    brand_col, form_col = st.columns([1.0, 1.0])

    with brand_col:
        st.markdown(_brand_panel_html(), unsafe_allow_html=True)

    with form_col:
        # Pick up ?tab= from URL (set by the HTML tab buttons via window.location.href)
        url_tab = st.query_params.get("tab")
        if url_tab in ("login", "register") and url_tab != st.session_state.auth_tab:
            st.session_state.auth_tab = url_tab
            st.session_state._auth_msg = ("", "")
            st.rerun()

        tab_login_active    = "active" if st.session_state.auth_tab == "login"    else ""
        tab_register_active = "active" if st.session_state.auth_tab == "register" else ""

        st.markdown(f"""
<div class="tab-strip">
  <a class="tab-btn {tab_login_active}" href="?tab=login">Sign in</a>
  <a class="tab-btn {tab_register_active}" href="?tab=register">Create account</a>
</div>
""", unsafe_allow_html=True)

        # # ── Google SSO button ─────────────────────────────────────────────────
        # google_svg = (
        #     '<svg width="18" height="18" viewBox="0 0 24 24">'
        #     '<path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>'
        #     '<path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>'
        #     '<path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>'
        #     '<path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>'
        #     '</svg>'
        # )
        # or_div = '<div class="or-divider"><div class="or-line"></div><span class="or-text">or</span><div class="or-line"></div></div>'
        # if google_url:
        #     st.markdown(
        #         f'<a class="google-btn" href="{google_url}">{google_svg}Continue with Google</a>' + or_div,
        #         unsafe_allow_html=True,
        #     )
        # else:
        #     st.markdown(
        #         '<div style="font-size:12px;color:#888;padding:8px 0 4px;">'
        #         'Google sign-in not configured — add GOOGLE_CLIENT_ID to ' 
        #         '<code>.streamlit/secrets.toml</code></div>' + or_div,
        #         unsafe_allow_html=True,
        #     )

        # ── Feedback message area ─────────────────────────────────────────────
        msg_text, msg_type = st.session_state._auth_msg
        if msg_text:
            css_class = "auth-toast" if msg_type == "ok" else "auth-err"
            st.markdown(f'<div class="{css_class}">{msg_text}</div>', unsafe_allow_html=True)
            st.markdown("")

        # ══════════════════════════════════════════════════════════════════════
        #  LOGIN FORM
        # ══════════════════════════════════════════════════════════════════════
        if st.session_state.auth_tab == "login":
            st.markdown('<div style="font-size:17px;font-weight:700;margin-bottom:2px;">Welcome back</div><div style="font-size:12px;color:#888;margin-bottom:10px;">Sign in to your NutriScan account</div>', unsafe_allow_html=True)

            login_email = st.text_input("Email", placeholder="you@example.com",
                                        key="login_email")
            login_pw    = st.text_input("Password", type="password",
                                        placeholder="••••••••", key="login_pw")

            col_btn, col_forgot = st.columns([1, 1])
            with col_btn:
                login_clicked = st.button("Sign in", type="primary",
                                          use_container_width=True, key="do_login")
            with col_forgot:
                forgot_clicked = st.button("Forgot password?", type="tertiary", key="forgot_btn",
                                           use_container_width=True)

            if login_clicked:
                _do_login(login_email, login_pw)

            if forgot_clicked:
                _do_forgot(login_email)


        # ══════════════════════════════════════════════════════════════════════
        #  REGISTER FORM
        # ══════════════════════════════════════════════════════════════════════
        else:
            st.markdown('<div style="font-size:17px;font-weight:700;margin-bottom:2px;margin-top:1.5rem">Create your account</div><div style="font-size:12px;color:#888;margin-bottom:10px;">Join NutriScan AI — its free</div>', unsafe_allow_html=True)

            # Avatar upload
            st.markdown('<div class="avatar-hint"><strong>Profile photo</strong>Optional · JPG, PNG</div>',
                        unsafe_allow_html=True)
            avatar_file = st.file_uploader("Profile photo", type=["jpg", "jpeg", "png"],
                                           label_visibility="collapsed", key="reg_avatar")
            if avatar_file:
                st.image(avatar_file, width=72)

            rcol1, rcol2 = st.columns(2)
            with rcol1:
                reg_first = st.text_input("First name", placeholder="Alex", key="reg_first")
            with rcol2:
                reg_last  = st.text_input("Last name",  placeholder="Patel", key="reg_last")

            reg_email = st.text_input("Email", placeholder="you@example.com", key="reg_email")
            reg_pw    = st.text_input("Password", type="password",
                                      placeholder="Min. 8 characters", key="reg_pw")

            register_clicked = st.button("Create account", type="primary",
                                         use_container_width=True, key="do_register")

            if register_clicked:
                avatar_bytes = avatar_file.getvalue() if avatar_file else None
                _do_register(reg_first, reg_last, reg_email, reg_pw, avatar_bytes)


        # ── Demo credentials hint ─────────────────────────────────────────────
        st.caption("Demo: `demo@nutriscan.ai` / `demo1234`")


# ─────────────────────────────────────────────────────────────────────────────
#  ACTION HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

def _do_login(email: str, password: str):
    email = email.strip().lower()
    if not email or not password:
        st.session_state._auth_msg = ("Please fill in both fields.", "err")
        st.rerun()

    if not _valid_email(email):
        st.session_state._auth_msg = ("Enter a valid email address.", "err")
        st.rerun()

    if not verify_password(email, password):
        # Small delay to slow brute-force attempts
        time.sleep(0.4)
        st.session_state._auth_msg = ("Incorrect email or password.", "err")
        st.rerun()

    user = get_user(email)
    update_last_login(email)

    # Load this user's persisted scan history into session state
    st.session_state.authenticated = True
    st.session_state.current_user  = {
        "name":       user["name"],
        "email":      email,
        "avatar_url": user.get("avatar_url", ""),
    }
    st.session_state.scan_history = load_scans(email)
    st.session_state._auth_msg = ("", "")
    st.rerun()


def _do_register(first: str, last: str, email: str, password: str, avatar_bytes):
    first = first.strip()
    last  = last.strip()
    email = email.strip().lower()

    if not first or not last or not email or not password:
        st.session_state._auth_msg = ("Please fill in all fields.", "err")
        st.rerun()

    if not _valid_email(email):
        st.session_state._auth_msg = ("Enter a valid email address.", "err")
        st.rerun()

    ok, pw_msg = _valid_password(password)
    if not ok:
        st.session_state._auth_msg = (pw_msg, "err")
        st.rerun()

    created = create_user(email=email, name=f"{first} {last}", password=password)
    if not created:
        st.session_state._auth_msg = ("An account with this email already exists.", "err")
        st.rerun()

    update_last_login(email)

    # New user has no history yet — start with empty list
    st.session_state.authenticated = True
    st.session_state.current_user  = {
        "name":       f"{first} {last}",
        "email":      email,
        "avatar_url": "",
    }
    st.session_state.scan_history = []
    st.session_state._auth_msg = ("", "")
    st.rerun()


def _do_forgot(email: str):
    email = email.strip().lower()
    if not email or not _valid_email(email):
        st.session_state._auth_msg = ("Enter your email in the field above first.", "err")
        st.rerun()

    if not mail_configured():
        st.session_state._auth_msg = (
            "Email not configured. Add GMAIL_ADDRESS and GMAIL_APP_PASS "
            "to .streamlit/secrets.toml", "err"
        )
        st.rerun()

    token = create_reset_token(email)
    if token:
        ok = send_reset_email(email, token)
        if not ok:
            st.session_state._auth_msg = (
                "Email send failed — check GMAIL credentials in secrets.toml", "err"
            )
            st.rerun()

    # Always show the same message — never reveal if email exists
    st.session_state._auth_msg = (
        f"If {email} is registered, a reset link has been sent. Check your inbox.", "ok"
    )
    st.rerun()

    # Always show the same message — never reveal if email exists
    token = create_reset_token(email)
    if token:
        send_reset_email(email, token)

    st.session_state._auth_msg = (
        f"If {email} is registered, a reset link has been sent. Check your inbox.", "ok"
    )
    st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
#  PASSWORD RESET PAGE
# ─────────────────────────────────────────────────────────────────────────────

def _handle_reset_token():
    """
    Called on every page load. If ?reset_token= is in the URL,
    renders the reset-password form instead of the normal auth page.
    Returns True if the reset page was rendered (caller should st.stop()).
    """
    token = st.query_params.get("reset_token")
    if not token:
        return False

    dark    = st.session_state.get("dark_mode", True)
    bg      = "#0e0e0e" if dark else "#f7f9fc"
    card_bg = "#1a1a1a" if dark else "#ffffff"
    border  = "#2a2a2a" if dark else "#d8dde6"
    text    = "#f0f0f0" if dark else "#1a1a1a"
    green   = "#27ae60"

    st.markdown(f"""
<style>
#MainMenu,footer,header{{visibility:hidden}}
.stApp{{background:{bg}!important}}
.stApp *{{color:{text}!important}}
.main .block-container{{max-width:460px!important;padding:3rem 1.5rem!important;margin:0 auto!important}}
div[data-testid="stTextInput"] input{{
    background:{"#111" if dark else "#f0f3f8"}!important;
    border:1px solid {border}!important;border-radius:8px!important;
    color:{text}!important;font-size:14px!important;
}}
div[data-testid="stTextInput"] input:focus{{border-color:{green}!important}}
div[data-testid="stTextInput"] label{{font-size:12px!important;font-weight:600!important;color:{"#aaa" if dark else "#555"}!important}}
div[data-testid="stButton"]>button[kind="primary"]{{
    background:linear-gradient(135deg,{green},#2ecc71)!important;
    color:#fff!important;border:none!important;border-radius:9px!important;
    font-weight:700!important;font-size:14px!important;
}}
</style>""", unsafe_allow_html=True)

    st.markdown(f"""
<div style="text-align:center;margin-bottom:2rem;">
  <div style="display:inline-block;background:{green};border-radius:12px;
              padding:10px 20px;font-size:20px;font-weight:700;color:#fff;
              letter-spacing:-0.3px;">
    Nutri<span style="font-weight:400;color:#a8f0c0;">Scan</span> AI
  </div>
  <div style="font-size:22px;font-weight:700;margin-top:1.5rem;color:{text}">
    Set new password
  </div>
  <div style="font-size:13px;color:{"#888" if dark else "#666"};margin-top:4px;">
    Enter a new password for your account
  </div>
</div>""", unsafe_allow_html=True)

    # Verify token upfront
    from database import verify_reset_token
    email = verify_reset_token(token)

    if not email:
        st.error("This reset link is invalid or has expired. Please request a new one.")
        if st.button("Back to login", type="primary", use_container_width=True):
            st.query_params.clear()
            st.rerun()
        return True

    new_pw  = st.text_input("New password",     type="password", placeholder="Min. 8 characters")
    conf_pw = st.text_input("Confirm password", type="password", placeholder="Repeat password")

    if st.button("Set new password", type="primary", use_container_width=True):
        if not new_pw or not conf_pw:
            st.error("Please fill in both fields.")
        elif len(new_pw) < 8:
            st.error("Password must be at least 8 characters.")
        elif new_pw != conf_pw:
            st.error("Passwords do not match.")
        else:
            success = consume_reset_token(token, new_pw)
            if success:
                st.success("Password updated! You can now sign in.")
                st.query_params.clear()
                time.sleep(1.5)
                st.rerun()
            else:
                st.error("Reset failed — the link may have already been used.")

    st.markdown("")
    if st.button("Cancel", use_container_width=True):
        st.query_params.clear()
        st.rerun()

    return True


# ─────────────────────────────────────────────────────────────────────────────
#  GATE — call this at the top of app.py
# ─────────────────────────────────────────────────────────────────────────────

def require_auth() -> bool:
    """
    Returns True if the user is authenticated.
    If not, renders the auth page and returns False.

    Also reloads scan history from SQLite on every page load so that
    history from previous sessions is always visible — not just the
    current session's in-memory state.
    """
    # Check for password reset link first — intercepts before auth check
    if _handle_reset_token():
        return False

    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if st.session_state.authenticated:
        # ── Reload history from DB on every page load ──────────────────────
        email = st.session_state.get("current_user", {}).get("email")
        if email and "scan_history" not in st.session_state:
            st.session_state.scan_history = load_scans(email)
        return True

    render_auth_page()
    return False


# ─────────────────────────────────────────────────────────────────────────────
#  USER WIDGET — call anywhere in app.py sidebar to show logged-in user
# ─────────────────────────────────────────────────────────────────────────────

def render_user_widget():
    """
    Shows the logged-in user's name + logout button.
    Add inside your `with st.sidebar:` block in app.py.
    """
    user = st.session_state.get("current_user", {})
    name  = user.get("name", "User")
    email = user.get("email", "")
    avatar_url = user.get("avatar_url", "")

    dark    = st.session_state.get("dark_mode", True)
    card_bg = "#1a1a1a" if dark else "#ffffff"
    border  = "#2a2a2a" if dark else "#d8dde6"
    subtext = "#888888" if dark else "#666666"

    initials = "".join(p[0].upper() for p in name.split()[:2]) if name else "?"

    if avatar_url:
        avatar_html = f'<img src="{avatar_url}" width="36" height="36" style="border-radius:50%;object-fit:cover;">'
    else:
        avatar_html = (
            f'<div style="width:36px;height:36px;border-radius:50%;'
            f'background:#27ae60;display:flex;align-items:center;'
            f'justify-content:center;font-weight:700;font-size:14px;color:#fff;">'
            f'{initials}</div>'
        )

    st.markdown(f"""
<div style="background:{card_bg};border-radius:10px;padding:10px 14px;
            border:1px solid {border};display:flex;align-items:center;gap:10px;margin-bottom:12px;">
  {avatar_html}
  <div style="overflow:hidden;">
    <div style="font-weight:600;font-size:13px;color:{'#f0f0f0' if dark else '#1a1a1a'} !important;
                white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{name}</div>
    <div style="font-size:11px;color:{subtext} !important;
                white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{email}</div>
  </div>
</div>
""", unsafe_allow_html=True)

    if st.button("Sign out", use_container_width=True, key="_signout"):
        # History is already persisted in SQLite — just clear the session
        st.session_state.authenticated = False
        st.session_state.current_user  = {}
        st.session_state.scan_history  = []
        st.rerun()