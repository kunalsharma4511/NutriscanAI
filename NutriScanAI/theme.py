# theme.py
# NutriScan AI — Unified Theme
#
# Replace the entire _inject_theme() function in app.py with this file's version.
# Also add  `from theme import inject_theme`  to your imports in app.py,
# then call  inject_theme(st.session_state.dark_mode)  instead of _inject_theme(...).
#
# This theme matches the auth page's design language exactly:
#   - Same background, card, and border colours
#   - Same green (#27ae60) accent throughout
#   - Same DM Sans font
#   - Same input, button, and sidebar styling
#   - Preserves all existing score-badge, insight-card, freq-pill classes

import streamlit as st


def inject_theme(dark: bool):

    # ── Palette (mirrors auth.py exactly) ────────────────────────────────────
    if dark:
        bg           = "#0e0e0e"
        sidebar_bg   = "#111111"
        card_bg      = "#1a1a1a"
        input_bg     = "#111111"
        border       = "#2a2a2a"
        border_focus = "#27ae60"
        text         = "#f0f0f0"
        subtext      = "#888888"
        shadow       = "rgba(0,0,0,0.4)"
        freq_bg      = "#1a2a3a"
        freq_color   = "#aed6f1"
        freq_border  = "#2e6da4"
        narrative_bg = "#1a1a1a"
        redflag_bg   = "#2a1a1a"
        positive_bg  = "#1a2a1a"
        warning_bg   = "#2a2010"
        tip_bg       = "#1e1a2a"
        history_bg   = "#1a1a1a"
        divider      = "#2a2a2a"
        agent_color  = "#ccc"
        progress_bg  = "#2a2a2a"
        tab_bg       = "#0e0e0e"
        green_glow   = "rgba(39,174,96,0.25)"
    else:
        bg           = "#f7f9fc"
        sidebar_bg   = "#eef1f5"
        card_bg      = "#ffffff"
        input_bg     = "#f0f3f8"
        border       = "#d8dde6"
        border_focus = "#27ae60"
        text         = "#1a1a1a"
        subtext      = "#666666"
        shadow       = "rgba(0,0,0,0.07)"
        freq_bg      = "#eaf4fb"
        freq_color   = "#1b4f72"
        freq_border  = "#aed6f1"
        narrative_bg = "#ffffff"
        redflag_bg   = "#fff5f5"
        positive_bg  = "#f0fff4"
        warning_bg   = "#fffbf0"
        tip_bg       = "#f8f0ff"
        history_bg   = "#ffffff"
        divider      = "#e0e4ea"
        agent_color  = "#444"
        progress_bg  = "#e5e7eb"
        tab_bg       = "#eef1f5"
        green_glow   = "rgba(39,174,96,0.15)"

    green   = "#27ae60"
    green_h = "#2ecc71"

    st.markdown(f"""
<style>
/* ── Google Font ── */
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

/* ══════════════════════════════════════════════════════
   BASE
══════════════════════════════════════════════════════ */
html, body, .stApp {{
    font-family: 'DM Sans', sans-serif !important;
    background-color: {bg} !important;
}}

/* Hide Streamlit chrome */
#MainMenu, footer, header {{ visibility: hidden; }}

/* Global text colour — broad reset */
.stApp, .stMarkdown, p, label, span, div,
.stApp * {{ color: {text} !important; }}

/* ══════════════════════════════════════════════════════
   SIDEBAR
══════════════════════════════════════════════════════ */
section[data-testid="stSidebar"] {{
    background-color: {sidebar_bg} !important;
    border-right: 1px solid {border} !important;
}}
section[data-testid="stSidebar"] * {{
    color: {text} !important;
    font-family: 'DM Sans', sans-serif !important;
}}
/* Sidebar title */
section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3 {{
    font-weight: 700 !important;
    letter-spacing: -0.3px !important;
}}
/* Sidebar divider */
section[data-testid="stSidebar"] hr {{
    border-color: {border} !important;
    margin: 12px 0 !important;
}}

/* ══════════════════════════════════════════════════════
   PAGE TITLE & HEADINGS
══════════════════════════════════════════════════════ */
h1 {{
    font-size: 28px !important;
    font-weight: 700 !important;
    letter-spacing: -0.5px !important;
    color: {text} !important;
}}
h2 {{
    font-size: 20px !important;
    font-weight: 700 !important;
    letter-spacing: -0.3px !important;
}}
h3 {{
    font-size: 16px !important;
    font-weight: 600 !important;
}}
/* st.subheader */
[data-testid="stHeadingWithActionElements"] h2 {{
    font-size: 18px !important;
    font-weight: 700 !important;
    letter-spacing: -0.3px !important;
    padding-bottom: 6px !important;
    border-bottom: 1px solid {border} !important;
    margin-bottom: 12px !important;
}}

/* ══════════════════════════════════════════════════════
   INPUTS  (text, number, selectbox, multiselect)
══════════════════════════════════════════════════════ */
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stTextArea"] textarea {{
    background: {input_bg} !important;
    border: 1px solid {border} !important;
    border-radius: 8px !important;
    color: {text} !important;
    font-family: 'DM Sans', sans-serif !important;
    font-size: 14px !important;
    padding: 10px 13px !important;
    transition: border-color 0.2s !important;
}}
div[data-testid="stTextInput"] input:focus,
div[data-testid="stNumberInput"] input:focus,
div[data-testid="stTextArea"] textarea:focus {{
    border-color: {border_focus} !important;
    box-shadow: 0 0 0 3px {green_glow} !important;
}}
div[data-testid="stTextInput"] label,
div[data-testid="stNumberInput"] label,
div[data-testid="stTextArea"] label,
div[data-testid="stSelectbox"] label,
div[data-testid="stMultiSelect"] label,
div[data-testid="stRadio"] label {{
    font-size: 12px !important;
    font-weight: 600 !important;
    color: {subtext} !important;
    letter-spacing: 0.3px !important;
    text-transform: uppercase !important;
}}

/* Selectbox */
div[data-testid="stSelectbox"] > div > div {{
    background: {input_bg} !important;
    border: 1px solid {border} !important;
    border-radius: 8px !important;
    color: {text} !important;
}}
div[data-testid="stSelectbox"] > div > div:focus-within {{
    border-color: {border_focus} !important;
    box-shadow: 0 0 0 3px {green_glow} !important;
}}

/* Multiselect */
div[data-testid="stMultiSelect"] > div > div {{
    background: {input_bg} !important;
    border: 1px solid {border} !important;
    border-radius: 8px !important;
}}
/* Multiselect tags */
div[data-testid="stMultiSelect"] span[data-baseweb="tag"] {{
    background: {"#1a2a1a" if dark else "#e8f5e9"} !important;
    border: 1px solid {"#27ae6060" if dark else "#a5d6a7"} !important;
    border-radius: 6px !important;
    color: {green} !important;
}}

/* ══════════════════════════════════════════════════════
   BUTTONS
══════════════════════════════════════════════════════ */
/* Primary */
div[data-testid="stButton"] > button[kind="primary"],
div[data-testid="stDownloadButton"] > button[kind="primary"] {{
    background: linear-gradient(135deg, {green}, {green_h}) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 9px !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    font-family: 'DM Sans', sans-serif !important;
    padding: 0.55rem 1.2rem !important;
    letter-spacing: 0.2px !important;
    box-shadow: 0 2px 12px {green_glow} !important;
    transition: all 0.2s !important;
}}
div[data-testid="stButton"] > button[kind="primary"]:hover,
div[data-testid="stDownloadButton"] > button[kind="primary"]:hover {{
    opacity: 0.9 !important;
    box-shadow: 0 4px 18px {green_glow} !important;
    transform: translateY(-1px) !important;
}}
div[data-testid="stButton"] > button[kind="primary"]:active {{
    transform: scale(0.98) !important;
}}

/* Secondary */
div[data-testid="stButton"] > button[kind="secondary"],
div[data-testid="stDownloadButton"] > button[kind="secondary"] {{
    background: transparent !important;
    border: 1px solid {border} !important;
    border-radius: 9px !important;
    color: {text} !important;
    font-weight: 600 !important;
    font-size: 14px !important;
    font-family: 'DM Sans', sans-serif !important;
    transition: border-color 0.2s, background 0.2s !important;
}}
div[data-testid="stButton"] > button[kind="secondary"]:hover {{
    border-color: {green} !important;
    background: {"#1a2a1a" if dark else "#f0faf2"} !important;
    color: {green} !important;
}}

/* ══════════════════════════════════════════════════════
   RADIO  (input method selector)
══════════════════════════════════════════════════════ */
div[data-testid="stRadio"] > div {{
    display: flex !important;
    gap: 8px !important;
    flex-wrap: wrap !important;
}}
div[data-testid="stRadio"] > div > label {{
    background: {input_bg} !important;
    border: 1px solid {border} !important;
    border-radius: 8px !important;
    padding: 8px 16px !important;
    cursor: pointer !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    color: {subtext} !important;
    transition: all 0.2s !important;
    text-transform: none !important;
    letter-spacing: 0 !important;
}}
div[data-testid="stRadio"] > div > label:has(input:checked) {{
    background: {"#1a2a1a" if dark else "#f0faf2"} !important;
    border-color: {green} !important;
    color: {green} !important;
}}
/* Hide the actual radio circle */
div[data-testid="stRadio"] input[type="radio"] {{
    display: none !important;
}}

/* ══════════════════════════════════════════════════════
   EXPANDER
══════════════════════════════════════════════════════ */
div[data-testid="stExpander"] {{
    background: {card_bg} !important;
    border: 1px solid {border} !important;
    border-radius: 10px !important;
    overflow: hidden !important;
}}
div[data-testid="stExpander"] summary {{
    background: {card_bg} !important;
    padding: 12px 16px !important;
    font-weight: 600 !important;
    font-size: 14px !important;
}}
div[data-testid="stExpander"] summary:hover {{
    background: {"#222" if dark else "#f5f7fa"} !important;
}}

/* ══════════════════════════════════════════════════════
   FILE UPLOADER
══════════════════════════════════════════════════════ */
div[data-testid="stFileUploader"] {{
    background: {input_bg} !important;
    border: 1.5px dashed {border} !important;
    border-radius: 10px !important;
    padding: 12px !important;
    transition: border-color 0.2s !important;
}}
div[data-testid="stFileUploader"]:hover {{
    border-color: {green} !important;
}}

/* ══════════════════════════════════════════════════════
   CAMERA INPUT
══════════════════════════════════════════════════════ */
div[data-testid="stCameraInput"] > div {{
    border: 1.5px dashed {border} !important;
    border-radius: 10px !important;
    background: {input_bg} !important;
    overflow: hidden !important;
}}

/* ══════════════════════════════════════════════════════
   PROGRESS BAR
══════════════════════════════════════════════════════ */
div[data-testid="stProgress"] > div > div {{
    background: {progress_bg} !important;
    border-radius: 99px !important;
    height: 6px !important;
}}
div[data-testid="stProgress"] > div > div > div {{
    background: linear-gradient(90deg, {green}, {green_h}) !important;
    border-radius: 99px !important;
}}

/* ══════════════════════════════════════════════════════
   METRIC CARDS  (st.metric)
══════════════════════════════════════════════════════ */
div[data-testid="stMetric"] {{
    background: {card_bg} !important;
    border: 1px solid {border} !important;
    border-radius: 10px !important;
    padding: 14px 18px !important;
}}
div[data-testid="stMetric"] label {{
    font-size: 11px !important;
    font-weight: 600 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.5px !important;
    color: {subtext} !important;
}}
div[data-testid="stMetric"] [data-testid="stMetricValue"] {{
    font-size: 24px !important;
    font-weight: 700 !important;
    color: {text} !important;
    letter-spacing: -0.5px !important;
}}

/* ══════════════════════════════════════════════════════
   ALERTS  (st.info / st.success / st.warning / st.error)
══════════════════════════════════════════════════════ */
div[data-testid="stAlert"] {{
    border-radius: 10px !important;
    border-width: 1px !important;
    font-size: 13.5px !important;
    font-family: 'DM Sans', sans-serif !important;
    padding: 12px 16px !important;
}}
/* Info */
div[data-testid="stAlert"][data-type="info"] {{
    background: {"#1a2233" if dark else "#eff6ff"} !important;
    border-color: {"#2e4a80" if dark else "#93c5fd"} !important;
}}
/* Success */
div[data-testid="stAlert"][data-type="success"] {{
    background: {"#1a2a1a" if dark else "#f0fdf4"} !important;
    border-color: {"#27ae6060" if dark else "#86efac"} !important;
}}
/* Warning */
div[data-testid="stAlert"][data-type="warning"] {{
    background: {"#2a2010" if dark else "#fffbeb"} !important;
    border-color: {"#92400e80" if dark else "#fcd34d"} !important;
}}
/* Error */
div[data-testid="stAlert"][data-type="error"] {{
    background: {"#2a1a1a" if dark else "#fef2f2"} !important;
    border-color: {"#e74c3c60" if dark else "#fca5a5"} !important;
}}

/* ══════════════════════════════════════════════════════
   SPINNER
══════════════════════════════════════════════════════ */
div[data-testid="stSpinner"] > div {{
    border-top-color: {green} !important;
}}

/* ══════════════════════════════════════════════════════
   DIVIDER  (st.divider)
══════════════════════════════════════════════════════ */
hr {{
    border-color: {border} !important;
    margin: 20px 0 !important;
}}

/* ══════════════════════════════════════════════════════
   DOWNLOAD BUTTON
══════════════════════════════════════════════════════ */
div[data-testid="stDownloadButton"] > button {{
    background: linear-gradient(135deg, {green}, {green_h}) !important;
    color: #fff !important;
    border: none !important;
    border-radius: 9px !important;
    font-weight: 700 !important;
    font-family: 'DM Sans', sans-serif !important;
}}

/* ══════════════════════════════════════════════════════
   CAPTION  (st.caption)
══════════════════════════════════════════════════════ */
div[data-testid="stCaptionContainer"] p,
.stCaption {{
    font-size: 12px !important;
    color: {subtext} !important;
}}

/* ══════════════════════════════════════════════════════
   IMAGE captions
══════════════════════════════════════════════════════ */
div[data-testid="stImage"] p {{
    font-size: 11px !important;
    color: {subtext} !important;
    text-align: center !important;
    margin-top: 4px !important;
}}

/* ══════════════════════════════════════════════════════
   CUSTOM COMPONENT CLASSES  (unchanged from original)
   These must stay so the results panel still renders
══════════════════════════════════════════════════════ */
.score-badge {{
    display: inline-block;
    padding: 12px 28px;
    border-radius: 50px;
    font-size: 2.4rem;
    font-weight: 800;
    color: white;
    text-align: center;
    margin: 8px 0;
    font-family: 'DM Sans', sans-serif;
}}
.score-excellent {{ background: linear-gradient(135deg, #27ae60, #2ecc71); }}
.score-good      {{ background: linear-gradient(135deg, #2980b9, #3498db); }}
.score-moderate  {{ background: linear-gradient(135deg, #f39c12, #f1c40f); color: #333 !important; }}
.score-poor      {{ background: linear-gradient(135deg, #e67e22, #e74c3c); }}
.score-avoid     {{ background: linear-gradient(135deg, #c0392b, #922b21); }}

.freq-pill {{
    display: inline-block;
    padding: 5px 16px;
    border-radius: 20px;
    background: {freq_bg};
    color: {freq_color} !important;
    font-weight: 600;
    font-size: 0.95rem;
    border: 1px solid {freq_border};
    font-family: 'DM Sans', sans-serif;
}}

.insight-card {{
    background: {card_bg};
    border-radius: 10px;
    padding: 14px 18px;
    margin: 7px 0;
    border-left: 3px solid #3498db;
    box-shadow: 0 1px 3px {shadow};
    font-family: 'DM Sans', sans-serif;
    font-size: 14px;
    line-height: 1.6;
    color: {text} !important;
}}
.red-flag-card  {{ border-left-color: #e74c3c; background: {redflag_bg}; }}
.positive-card  {{ border-left-color: #27ae60; background: {positive_bg}; }}
.warning-card   {{ border-left-color: #e67e22; background: {warning_bg}; }}
.tip-card       {{ border-left-color: #8e44ad; background: {tip_bg}; }}

.nutr-label {{
    font-size: 12px;
    color: {subtext} !important;
    margin-bottom: 2px;
    font-family: 'DM Sans', sans-serif;
}}

.ai-badge {{
    display: inline-block;
    padding: 3px 10px;
    border-radius: 12px;
    background: #3a2e00;
    color: #f1c40f !important;
    font-size: 0.78rem;
    font-weight: 600;
    border: 1px solid #f1c40f55;
    margin-left: 8px;
    font-family: 'DM Sans', sans-serif;
}}

.agent-step {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 7px 0;
    font-size: 13.5px;
    color: {agent_color} !important;
    font-family: 'DM Sans', sans-serif;
}}
.agent-dot {{
    width: 9px; height: 9px;
    border-radius: 50%;
    background: {green};
    flex-shrink: 0;
}}

.history-card {{
    background: {history_bg};
    border-radius: 10px;
    padding: 10px 14px;
    margin: 6px 0;
    border: 1px solid {border};
    border-left: 3px solid #3498db;
    font-size: 13px;
    font-family: 'DM Sans', sans-serif;
    color: {text} !important;
}}

.narrative-box {{
    background: {narrative_bg};
    border-radius: 12px;
    padding: 20px 24px;
    border: 1px solid {border};
    box-shadow: 0 1px 4px {shadow};
    line-height: 1.75;
    font-size: 14.5px;
    font-family: 'DM Sans', sans-serif;
    color: {text} !important;
}}

/* Keep coloured elements from being overridden by the global * rule */
.score-badge span,
.freq-pill,
.ai-badge,
.red-flag-card,
.positive-card {{
    color: inherit !important;
}}
</style>
""", unsafe_allow_html=True)