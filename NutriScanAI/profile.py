# profile.py
# NutriScan AI — User Profile Edit Page
#
# Call render_profile_page() from anywhere in app.py, e.g.:
#
#   from profile import render_profile_page
#   if st.sidebar.button("Edit profile"):
#       st.session_state.show_profile = True
#   if st.session_state.get("show_profile"):
#       render_profile_page()
#       st.stop()

import streamlit as st
import base64
from database import get_user, update_profile, update_password, verify_password


def _img_to_base64(path: str) -> str:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return ""


def _avatar_b64_from_upload(uploaded) -> str:
    """Convert a Streamlit uploaded file to base64 data URI."""
    if not uploaded:
        return ""
    data = base64.b64encode(uploaded.getvalue()).decode()
    mime = "image/png" if uploaded.name.endswith(".png") else "image/jpeg"
    return f"data:{mime};base64,{data}"


def render_profile_page():
    """Render the full profile edit UI. Call st.stop() after this."""
    user_sess = st.session_state.get("current_user", {})
    email     = user_sess.get("email", "")
    dark      = st.session_state.get("dark_mode", True)

    # Colour palette — matches auth.py / theme.py
    bg      = "#0e0e0e"  if dark else "#f7f9fc"
    card_bg = "#1a1a1a"  if dark else "#ffffff"
    border  = "#2a2a2a"  if dark else "#d8dde6"
    text    = "#f0f0f0"  if dark else "#1a1a1a"
    subtext = "#888888"  if dark else "#666666"
    green   = "#27ae60"
    input_bg = "#111111" if dark else "#f0f3f8"

    st.markdown(f"""
<style>
                
/* ── Kill ALL Streamlit chrome & spacing ── */
#MainMenu, footer, header {{ visibility: hidden; }}
.stApp {{ background: {bg} !important; overflow: hidden !important; }}
.stApp * {{ color: {text} !important; }}

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

#MainMenu,footer,header{{visibility:hidden}}
.stApp{{background:{bg}!important;overflow:hidden!important}}
.stApp *{{color:{text}!important}}
.main .block-container{{
    max-width:640px!important;
    padding:2rem 1.5rem!important;
    margin:0 auto!important;
}}
.profile-card{{
    background:{card_bg};
    border:1px solid {border};
    border-radius:14px;
    padding:24px 28px;
    margin-bottom:16px;
}}
.section-title{{
    font-size:13px;font-weight:700;
    color:{subtext}!important;
    letter-spacing:1px;
    text-transform:uppercase;
    margin-bottom:14px;
    padding-bottom:8px;
    border-bottom:1px solid {border};
}}
.avatar-wrap{{
    display:flex;align-items:center;gap:18px;margin-bottom:18px;
}}
.avatar-circle{{
    width:72px;height:72px;border-radius:50%;
    background:{green};
    display:flex;align-items:center;justify-content:center;
    font-size:26px;font-weight:700;color:#fff;
    flex-shrink:0;overflow:hidden;
}}
.avatar-circle img{{width:100%;height:100%;object-fit:cover;border-radius:50%;}}
.avatar-meta{{font-size:13px;color:{subtext}!important;line-height:1.6;}}
.avatar-meta strong{{display:block;font-size:15px;font-weight:700;
    color:{text}!important;margin-bottom:2px;}}
div[data-testid="stTextInput"] input{{
    background:{input_bg}!important;
    border:1px solid {border}!important;
    border-radius:8px!important;
    color:{text}!important;font-size:14px!important;
    padding:9px 12px!important;
}}
div[data-testid="stTextInput"] input:focus{{
    border-color:{green}!important;
    box-shadow:0 0 0 2px {"#27ae6030" if dark else "#27ae6018"}!important;
}}
div[data-testid="stTextInput"] label{{
    font-size:11px!important;font-weight:600!important;
    color:{subtext}!important;letter-spacing:0.3px;
    text-transform:uppercase;
}}
div[data-testid="stButton"]>button[kind="primary"]{{
    background:linear-gradient(135deg,{green},#2ecc71)!important;
    color:#fff!important;border:none!important;
    border-radius:9px!important;font-weight:700!important;
    font-size:13.5px!important;
}}
div[data-testid="stButton"]>button[kind="secondary"]{{
    background:transparent!important;
    border:1px solid {border}!important;
    border-radius:9px!important;color:{text}!important;
    font-size:13.5px!important;
}}
div[data-testid="stButton"]>button[kind="secondary"]:hover{{
    border-color:{green}!important;color:{green}!important;
}}
div[data-testid="stFileUploader"]{{
    background:{input_bg}!important;
    border:1.5px dashed {border}!important;
    border-radius:8px!important;padding:6px!important;
}}
.success-msg{{
    padding:10px 14px;border-radius:8px;font-size:13px;
    background:{"#1a2a1a" if dark else "#f0faf2"};
    border:1px solid {"#27ae6060" if dark else "#b7dfb7"};
    color:{green}!important;margin-top:8px;
}}
.err-msg{{
    padding:10px 14px;border-radius:8px;font-size:13px;
    background:{"#2a1a1a" if dark else "#fff5f5"};
    border:1px solid {"#e74c3c60" if dark else "#f5c6c6"};
    color:#e74c3c!important;margin-top:8px;
}}
</style>
""", unsafe_allow_html=True)

    # ── Back button ───────────────────────────────────────────────────────────
    if st.button("← Back to app", key="profile_back"):
        st.session_state.show_profile = False
        st.rerun()

    st.markdown(f"<h2 style='font-size:22px;font-weight:700;margin-bottom:4px;'>Edit Profile</h2>",
                unsafe_allow_html=True)
    st.markdown(f"<p style='font-size:13px;color:{subtext};margin-bottom:20px;'>"
                f"Manage your account details and password</p>",
                unsafe_allow_html=True)

    # Load fresh user data from DB
    user_db = get_user(email) or {}
    name       = user_db.get("name", user_sess.get("name", ""))
    avatar_url = user_db.get("avatar_url", user_sess.get("avatar_url", ""))
    initials   = "".join(p[0].upper() for p in name.split()[:2]) if name else "?"
    is_sso     = not user_db.get("password_hash")

    # ── Avatar + name card ────────────────────────────────────────────────────
    st.markdown('<div class="profile-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Profile</div>', unsafe_allow_html=True)

    # Avatar display
    if avatar_url and avatar_url.startswith("data:"):
        av_html = f'<img src="{avatar_url}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;"/>'
    elif avatar_url:
        av_html = f'<img src="{avatar_url}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;"/>'
    else:
        av_html = f'<span style="font-size:26px;font-weight:700;color:#fff;">{initials}</span>'

    st.markdown(f"""
<div class="avatar-wrap">
  <div class="avatar-circle">{av_html}</div>
  <div class="avatar-meta">
    <strong>{name}</strong>
    {email}
    {"<br><span style='font-size:11px;background:#1a2a3a;color:#7ab3d9;padding:2px 8px;border-radius:6px;'>Google account</span>" if is_sso else ""}
  </div>
</div>
""", unsafe_allow_html=True)

    # Name edit
    new_name = st.text_input("Display name", value=name, key="prof_name")

    # Avatar upload
    st.markdown('<div style="font-size:11px;font-weight:600;color:' + subtext +
                ';letter-spacing:0.3px;text-transform:uppercase;margin-bottom:4px;">'
                'Profile photo</div>', unsafe_allow_html=True)
    avatar_file = st.file_uploader("Upload new photo",
                                   type=["jpg", "jpeg", "png"],
                                   label_visibility="collapsed",
                                   key="prof_avatar")

    if st.button("Save profile", type="primary", use_container_width=True, key="save_profile"):
        new_name = new_name.strip()
        if not new_name:
            st.markdown('<div class="err-msg">Name cannot be empty.</div>', unsafe_allow_html=True)
        else:
            new_avatar = _avatar_b64_from_upload(avatar_file) if avatar_file else avatar_url
            update_profile(email, new_name, new_avatar)
            # Sync session state
            st.session_state.current_user["name"]       = new_name
            st.session_state.current_user["avatar_url"] = new_avatar
            st.markdown('<div class="success-msg">Profile updated!</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Change password card (hidden for SSO users) ───────────────────────────
    if not is_sso:
        st.markdown('<div class="profile-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Change Password</div>', unsafe_allow_html=True)

        curr_pw = st.text_input("Current password", type="password", key="curr_pw")
        new_pw  = st.text_input("New password",     type="password",
                                placeholder="Min. 8 characters", key="new_pw")
        conf_pw = st.text_input("Confirm new password", type="password", key="conf_pw")

        if st.button("Update password", type="primary",
                     use_container_width=True, key="save_pw"):
            if not curr_pw or not new_pw or not conf_pw:
                st.markdown('<div class="err-msg">Please fill in all fields.</div>',
                            unsafe_allow_html=True)
            elif not verify_password(email, curr_pw):
                st.markdown('<div class="err-msg">Current password is incorrect.</div>',
                            unsafe_allow_html=True)
            elif len(new_pw) < 8:
                st.markdown('<div class="err-msg">New password must be at least 8 characters.</div>',
                            unsafe_allow_html=True)
            elif new_pw != conf_pw:
                st.markdown('<div class="err-msg">New passwords do not match.</div>',
                            unsafe_allow_html=True)
            else:
                update_password(email, new_pw)
                st.markdown('<div class="success-msg">Password updated successfully!</div>',
                            unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.markdown(f"""
<div class="profile-card">
  <div class="section-title">Password</div>
  <p style="font-size:13px;color:{subtext};">
    You signed in with Google — no password is set for this account.
  </p>
</div>""", unsafe_allow_html=True)

    # ── Account info card ─────────────────────────────────────────────────────
    st.markdown('<div class="profile-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Account Info</div>', unsafe_allow_html=True)
    created = user_db.get("created_at", "")[:10] if user_db.get("created_at") else "—"
    last_login = user_db.get("last_login", "")[:16].replace("T", " ") \
                 if user_db.get("last_login") else "—"

    c1, c2 = st.columns(2)
    with c1:
        st.metric("Member since", created)
    with c2:
        st.metric("Last login", last_login)

    st.markdown('</div>', unsafe_allow_html=True)