# app.py
# NutriScan AI v2.0 — Streamlit UI Entry Point
#
# Sections:
#   1. Page config & global styles
#   2. Sidebar — user health profile + scan history
#   3. Main input panel — webcam + upload + manual
#   4. Pipeline trigger & progress display
#   5. Results panel — score, nutrition, insights
#   6. Report download
import streamlit as st
import streamlit.components.v1 as components
from PIL import Image
import io
from datetime import datetime
from auth import require_auth, render_user_widget, render_auth_page
from database import save_scan, load_scans, delete_all_scans
from profile import render_profile_page
from dashboard import render_dashboard
from notifications import show_scan_toast, render_notification_settings
from config import validate_config, APP_TITLE, APP_VERSION
from graph import run_pipeline
from utils.error_handler import validate_image_bytes, check_pipeline_health
from utils.image_utils import load_image_from_bytes, load_image_from_upload, pil_to_bytes

# ── MUST be the very first Streamlit call ─────────────────────────────────────
st.set_page_config(
    page_title="NutriScan AI v2.0",
    page_icon="assets/new_logo.png",
    layout="wide",
    initial_sidebar_state="expanded"
)
# ── Auth check ────────────────────────────────────────────────────────────────
if not require_auth():
    st.stop()

# st.sidebar.write("test")  # ← add this temporarily


# ── Page routing ──────────────────────────────────────────────────────────────
if st.session_state.get("show_profile"):
    render_profile_page()
    st.stop()

if st.session_state.get("show_dashboard"):
    render_dashboard()
    st.stop()

# ── Helper functions ──────────────────────────────────────────────────────────
def _get_score_class(score: float) -> str:
    if score >= 8: return "score-excellent"
    if score >= 6: return "score-good"
    if score >= 4: return "score-moderate"
    if score >= 2: return "score-poor"
    return "score-avoid"

def _get_score_label(score: float) -> str:
    if score >= 8: return "Excellent"
    if score >= 6: return "Good"
    if score >= 4: return "Moderate"
    if score >= 2: return "Poor"
    return "Avoid"

def _score_colour(score: float) -> str:
    if score >= 8: return "#27ae60"
    if score >= 6: return "#2980b9"
    if score >= 4: return "#f39c12"
    if score >= 2: return "#e67e22"
    return "#c0392b"
# ── 1. Page config & global styles ───────────────────────────────────────────

# Add at the very top of app.py, before anything else
if "sidebar_state" not in st.session_state:
    st.session_state.sidebar_state = "expanded"

st.set_page_config(
    page_title="NutriScan AI",
    layout="wide",
    initial_sidebar_state=st.session_state.sidebar_state  # force expanded
)

if not require_auth():
    st.stop()
 
# Profile page routing
if st.session_state.get("show_profile"):
    render_profile_page()
    st.stop()
 
# Dashboard routing
if st.session_state.get("show_dashboard"):
    render_dashboard()
    st.stop()

def _inject_theme(dark: bool):
    """Inject CSS variables based on current theme."""
    if dark:
        bg          = "#0e0e0e"
        sidebar_bg  = "#111111"
        card_bg     = "#1a1a1a"
        text        = "#f0f0f0"
        subtext     = "#aaa"
        freq_bg     = "#1a2a3a"
        freq_color  = "#aed6f1"
        freq_border = "#2e6da4"
        narrative_bg = "#1a1a1a"
        shadow      = "rgba(0,0,0,0.4)"
        redflag_bg  = "#2a1a1a"
        positive_bg = "#1a2a1a"
        warning_bg  = "#2a2010"
        tip_bg      = "#1e1a2a"
        agent_color = "#ccc"
        agent_skip  = "#555"
    else:
        bg          = "#f7f9fc"
        sidebar_bg  = "#eef1f5"
        card_bg     = "#ffffff"
        text        = "#1a1a1a"
        subtext     = "#555"
        freq_bg     = "#eaf4fb"
        freq_color  = "#1b4f72"
        freq_border = "#aed6f1"
        narrative_bg = "#ffffff"
        shadow      = "rgba(0,0,0,0.07)"
        redflag_bg  = "#fff5f5"
        positive_bg = "#f0fff4"
        warning_bg  = "#fffbf0"
        tip_bg      = "#f8f0ff"
        agent_color = "#444"
        agent_skip  = "#bbb"

    st.markdown(f"""
<style>
/* ── Kill Streamlit chrome ── */
#MainMenu, footer, header {{ visibility: hidden; }}
.stApp {{ background: {bg} !important; }}
.stApp * {{ color: {text} !important; }}

/* ── Sidebar always expanded, toggle hidden ── */
section[data-testid="stSidebar"] {{
    transform: none !important;
    display: flex !important;
    visibility: visible !important;
    margin-left: 0 !important;
    left: 0 !important;
}}
button[data-testid="stSidebarCollapsedControl"],
button[data-testid="stSidebarNavCollapseButton"] {{
    display: none !important;
}}
button[data-testid="stSidebarNavCollapseButton"],
button[data-testid="stSidebarCollapsedControl"] {{
    display: none !important;
}}

/* ── Hide sidebar collapse button ── */
button[data-testid="stSidebarNavCollapseButton"],
button[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebarNavCollapseButton"],
[data-testid="collapsedControl"] {{
    display: none !important;
}}


/* ── Widget text colours ── */
.stRadio label, .stCheckbox label, .stSelectbox label,
.stMultiSelect label, .stNumberInput label,
.stTextInput label, .stExpander label,
.stExpander p, .stExpander span,
[data-testid="stSidebarContent"] *,
[data-testid="stSidebarContent"] p,
[data-testid="stSidebarContent"] span,
[data-testid="stSidebarContent"] label,
[data-testid="stCaption"] *,
.stCaption, .stText, .element-container p,
.stMarkdown p, .stMarkdown span, .stMarkdown li {{
    color: {text} !important;
}}

/* ── Score badges ── */
.score-badge {{
    display: inline-block;
    padding: 12px 28px;
    border-radius: 50px;
    font-size: 2.4rem;
    font-weight: 800;
    color: white !important;
    text-align: center;
    margin: 8px 0;
}}
.score-excellent {{ background: linear-gradient(135deg, #27ae60, #2ecc71); }}
.score-good      {{ background: linear-gradient(135deg, #2980b9, #3498db); }}
.score-moderate  {{ background: linear-gradient(135deg, #f39c12, #f1c40f); color: #333 !important; }}
.score-poor      {{ background: linear-gradient(135deg, #e67e22, #e74c3c); }}
.score-avoid     {{ background: linear-gradient(135deg, #c0392b, #922b21); }}

/* ── Freq pill ── */
.freq-pill {{
    display: inline-block;
    padding: 5px 16px;
    border-radius: 20px;
    background: {freq_bg};
    color: {freq_color} !important;
    font-weight: 600;
    font-size: 0.95rem;
    border: 1px solid {freq_border};
}}

/* ── Insight cards ── */
.insight-card {{
    background: {card_bg};
    border-radius: 12px;
    padding: 16px 20px;
    margin: 8px 0;
    border-left: 4px solid #3498db;
    box-shadow: 0 1px 4px {shadow};
}}
.red-flag-card {{ border-left-color: #e74c3c; background: {redflag_bg}; }}
.positive-card {{ border-left-color: #27ae60; background: {positive_bg}; }}
.warning-card  {{ border-left-color: #e67e22; background: {warning_bg}; }}
.tip-card      {{ border-left-color: #8e44ad; background: {tip_bg}; }}

/* ── Misc ── */
.nutr-label {{ font-size: 0.85rem; color: {subtext} !important; margin-bottom: 2px; }}

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
}}

.agent-step {{
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 6px 0;
    font-size: 0.92rem;
    color: {agent_color} !important;
}}
.agent-dot {{
    width: 10px; height: 10px;
    border-radius: 50%;
    background: #27ae60;
    flex-shrink: 0;
}}

.history-card {{
    background: {card_bg};
    border-radius: 10px;
    padding: 10px 14px;
    margin: 6px 0;
    border-left: 4px solid #3498db;
    font-size: 0.85rem;
}}

.narrative-box {{
    background: {narrative_bg};
    border-radius: 12px;
    padding: 20px 24px;
    box-shadow: 0 1px 4px {shadow};
    line-height: 1.7;
}}
</style>
""", unsafe_allow_html=True)

if "scan_history" not in st.session_state:
    st.session_state.scan_history = []   # list of dicts, max 5
if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = True    # default: dark theme
if "live_barcode" not in st.session_state:
    st.session_state.live_barcode = None  # barcode detected by live scanner

_inject_theme(st.session_state.dark_mode)


# ── Validate config on startup ────────────────────────────────────────────────
try:
    validate_config()
except EnvironmentError as e:
    st.error(f" Configuration error: {e}")
    st.stop()


# ── Session state init ────────────────────────────────────────────────────────

def _add_to_history(report_data: dict):
    """Save scan to SQLite and refresh session state from DB."""
    email = st.session_state.get("current_user", {}).get("email")
    if email:
        # Persist to DB (deduplication handled inside save_scan)
        save_scan(email, report_data)
        # Reload from DB so sidebar always reflects truth
        st.session_state.scan_history = load_scans(email)
    else:
        # Fallback: not logged in — use session only (shouldn't normally happen)
        entry = {
            "product_name":  report_data.get("product_name", "Unknown Product"),
            "score":         report_data.get("display_score"),
            "frequency":     report_data.get("consumption_frequency", ""),
            "barcode":       report_data.get("barcode", ""),
            "llm_estimated": report_data.get("llm_estimated", False),
            "scanned_at":    datetime.now().strftime("%H:%M"),
            "scanned_date":  "",
        }
        if not (st.session_state.scan_history
                and st.session_state.scan_history[0].get("barcode") == entry["barcode"]
                and entry["barcode"]):
            st.session_state.scan_history.insert(0, entry)
            st.session_state.scan_history = st.session_state.scan_history[:5]
 
# ── 2. Sidebar — User Health Profile + Scan History ──────────────────────────

with st.sidebar:
    render_user_widget()

    # Navigation buttons
    if st.button("Nutrition Dashboard", use_container_width=True, key="nav_dash"):
        st.session_state.show_dashboard = True
        st.session_state.show_profile   = False
        st.rerun()
 
    if st.button("Edit Profile", use_container_width=True, key="nav_profile"):
        st.session_state.show_profile   = True
        st.session_state.show_dashboard = False
        st.rerun()
 
    st.divider()
 
    # Notification settings
    render_notification_settings()

    st.divider()

    st.subheader(" Your Health Profile")

    with st.expander("Fill in your profile", expanded=False):
        age = st.number_input("Age", min_value=1, max_value=120, value=None,
                              placeholder="e.g. 35")
        gender = st.selectbox("Gender", ["Prefer not to say", "Male", "Female", "Other"])

        conditions = st.multiselect(
            "Health conditions (select all that apply)",
            options=[
                "Type 1 Diabetes", "Type 2 Diabetes", "Hypertension",
                "High Cholesterol", "Cardiovascular Disease", "Obesity",
                "Celiac Disease / Gluten Intolerance", "Lactose Intolerance",
                "Kidney Disease", "Thyroid Disorder", "PCOS",
                "Irritable Bowel Syndrome (IBS)", "Food Allergies",
            ]
        )

        dietary_preferences = st.multiselect(
            "Dietary preferences / restrictions",
            options=[
                "Vegetarian", "Vegan", "Jain", "Keto", "Low-Carb",
                "Low-Sodium", "Low-Fat", "High-Protein", "Gluten-Free",
                "Dairy-Free", "Nut-Free", "Halal", "Kosher",
            ]
        )

        fitness_goal = st.selectbox(
            "Primary health/fitness goal",
            ["None specified", "Weight Loss", "Muscle Gain", "Maintain Weight",
             "Manage Blood Sugar", "Improve Heart Health", "Boost Energy",
             "Improve Digestion"]
        )

    # Build profile dict
    user_profile = {}
    if age:
        user_profile["age"] = int(age)
    if gender != "Prefer not to say":
        user_profile["gender"] = gender
    if conditions:
        user_profile["conditions"] = conditions
    if dietary_preferences:
        user_profile["dietary_preferences"] = dietary_preferences
    if fitness_goal != "None specified":
        user_profile["fitness_goal"] = fitness_goal

    if user_profile:
        st.success(" Profile active — analysis will be personalised")
    else:
        st.info(" No profile set — general analysis will be shown")

    # ── Scan History ──────────────────────────────────────────────────────────
    st.subheader(" Recent Scans")

    if st.session_state.scan_history:
        for entry in st.session_state.scan_history:
            score     = entry["score"]
            colour    = _score_colour(score) if score is not None else "#888"
            score_txt = f"{score}/10" if score is not None else "N/A"
            ai_tag    = " <span style='color:#f1c40f;font-size:0.7rem'> AI est.</span>" \
                        if entry.get("llm_estimated") else ""
            freq      = entry["frequency"].title() if entry["frequency"] else ""
            freq_line = f"<div style='color:#aaa;font-size:0.75rem'> {freq}</div>" if freq else ""

            st.markdown(
                f"<div class='history-card' style='border-left-color:{colour}'>"
                f"<div style='font-weight:600'>{entry['product_name']}{ai_tag}</div>"
                f"<div style='color:{colour};font-weight:700'>{score_txt}</div>"
                f"{freq_line}"
                f"<div style='color:#666;font-size:0.72rem'> {entry['scanned_at']}</div>"
                f"</div>",
                unsafe_allow_html=True
            )

        if st.button("🗑️ Clear history", use_container_width=True):
            email = st.session_state.get("current_user", {}).get("email")
            if email:
                delete_all_scans(email)
            st.session_state.scan_history = []   # ← indented inside the if
            st.rerun()  
    else:
        st.caption("No scans yet — results will appear here after each analysis.")

    


# ── Live barcode scanner component ───────────────────────────────────────────

def _live_scanner_html(dark: bool) -> str:
    bg      = "#0e0e0e" if dark else "#f7f9fc"
    text    = "#f0f0f0" if dark else "#1a1a1a"
    card_bg = "#1a1a1a" if dark else "#ffffff"
    green   = "#27ae60"
    amber   = "#f39c12"

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ background: {bg}; font-family: Arial, sans-serif; color: {text}; padding: 10px; }}
#wrap {{ max-width: 520px; margin: 0 auto; }}
video, canvas {{ width: 100%; border-radius: 10px; display: block; }}
#canvas {{ display: none; }}
#overlay-wrap {{ position: relative; }}
#reticle {{
  position: absolute; top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  width: 72%; height: 32%;
  border: 3px solid {amber};
  border-radius: 8px;
  pointer-events: none;
  transition: border-color 0.2s;
}}
#reticle.found {{ border-color: {green}; }}
#status {{
  margin-top: 8px; padding: 10px;
  background: {card_bg}; border-radius: 8px;
  text-align: center; font-size: 0.9rem;
}}
#result {{ display:none; margin-top:6px; padding:10px;
  background:{card_bg}; border:2px solid {green};
  border-radius:8px; text-align:center; font-weight:700; font-size:1rem; }}
.btn {{
  display:none; width:100%; margin-top:6px; padding:10px;
  border:none; border-radius:8px; font-size:0.95rem;
  font-weight:700; cursor:pointer;
}}
#use-btn {{ background:{green}; color:#fff; }}
#retry-btn {{ background:transparent; color:{text}; border:1px solid #666; }}
</style>
</head>
<body>
<div id="wrap">
  <div id="overlay-wrap">
    <video id="video" autoplay muted playsinline></video>
    <div id="reticle"></div>
  </div>
  <canvas id="canvas"></canvas>
  <div id="status"> Starting camera...</div>
  <div id="result"></div>
  <button class="btn" id="use-btn"  onclick="useBarcode()"> Use this barcode</button>
  <button class="btn" id="retry-btn" onclick="retry()">⟳ Scan again</button>
</div>

<script src="https://cdn.jsdelivr.net/npm/@zxing/library@0.21.3/umd/index.min.js"></script>
<script>
const video    = document.getElementById('video');
const canvas   = document.getElementById('canvas');
const ctx      = canvas.getContext('2d', {{willReadFrequently: true}});
const status   = document.getElementById('status');
const resultEl = document.getElementById('result');
const reticle  = document.getElementById('reticle');
const useBtn   = document.getElementById('use-btn');
const retryBtn = document.getElementById('retry-btn');

let found = false;
let detected = '';
let rafId = null;
let hints = null;

// Configure ZXing hints for faster EAN/UPC decoding
try {{
  hints = new Map();
  hints.set(ZXing.DecodeHintType.POSSIBLE_FORMATS, [
    ZXing.BarcodeFormat.EAN_13,
    ZXing.BarcodeFormat.EAN_8,
    ZXing.BarcodeFormat.UPC_A,
    ZXing.BarcodeFormat.UPC_E,
    ZXing.BarcodeFormat.CODE_128,
  ]);
  hints.set(ZXing.DecodeHintType.TRY_HARDER, true);
}} catch(e) {{ hints = null; }}

const reader = hints
  ? new ZXing.MultiFormatReader(hints)
  : new ZXing.MultiFormatReader();

function isFood(t) {{ return /^[0-9]{{8,14}}$/.test(t); }}

function decode() {{
  if (found || video.readyState < 2) {{ rafId = requestAnimationFrame(decode); return; }}
  canvas.width  = video.videoWidth  || 640;
  canvas.height = video.videoHeight || 480;
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

  try {{
    const imgData = ctx.getImageData(0, 0, canvas.width, canvas.height);
    const lum = new ZXing.RGBLuminanceSource(imgData.data, canvas.width, canvas.height);
    const bin = new ZXing.HybridBinarizer(lum);
    const bmp = new ZXing.BinaryBitmap(bin);
    const res = reader.decode(bmp);
    const txt = res.getText();
    if (isFood(txt)) {{
      found    = true;
      detected = txt;
      reticle.classList.add('found');
      status.textContent        = 'Barcode found!';
      resultEl.textContent      = 'txt';
      resultEl.style.display    = 'block';
      useBtn.style.display      = 'block';
      retryBtn.style.display    = 'block';
      return;
    }}
  }} catch(e) {{
    // NotFoundException is normal when no barcode in frame — keep scanning
  }}
  rafId = requestAnimationFrame(decode);
}}

async function start() {{
  try {{
    const stream = await navigator.mediaDevices.getUserMedia({{
      video: {{ facingMode: {{ideal:'environment'}}, width:{{ideal:1280}}, height:{{ideal:720}} }}
    }});
    video.srcObject = stream;
    video.onloadedmetadata = () => {{
      video.play();
      status.textContent = '🔍 Scanning... aim at barcode';
      rafId = requestAnimationFrame(decode);
    }};
  }} catch(e) {{
    if (e.name === 'NotAllowedError')
      status.textContent = 'Camera permission denied. Allow access and reload.';
    else if (e.name === 'NotFoundError')
      status.textContent = 'No camera found. Use Upload or Manual Entry.';
    else
      status.textContent = e.message;
  }}
}}

function useBarcode() {{
  // Send to Streamlit via postMessage
  window.parent.postMessage({{type:'streamlit:setComponentValue', value: detected}}, '*');
  status.textContent     = 'Sent to NutriScan AI — click Analyse Product above.';
  useBtn.style.display   = 'none';
}}

function retry() {{
  found    = false;
  detected = '';
  reticle.classList.remove('found');
  resultEl.style.display  = 'none';
  useBtn.style.display    = 'none';
  retryBtn.style.display  = 'none';
  status.textContent      = 'Scanning... aim at barcode';
  rafId = requestAnimationFrame(decode);
}}

start();
</script>
</body>
</html>"""


# ── 3. Main Input Panel ───────────────────────────────────────────────────────

st.title("NutriScan AI")
st.markdown("**Scan any packaged food — get instant AI-powered nutrition insights.**")
st.divider()

input_col, guide_col = st.columns([2, 1])

with input_col:
    input_mode = st.radio(
        "Choose input method",
        ["Upload Image", "Enter Barcode Manually"],
        horizontal=True
    )

    image_bytes = None
    manual_barcode = None

    if input_mode == "Webcam Scan":
        st.caption("Point your camera at the barcode or nutrition label.")
        camera_image = st.camera_input("Capture product image")
        if camera_image:
            image_bytes = camera_image.getvalue()

    elif input_mode == "Upload Image":
        st.caption("Upload a photo of the barcode or the nutritional label.")
        uploaded_file = st.file_uploader(
            "Upload product image",
            type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed"
        )
        if uploaded_file:
            image_bytes = uploaded_file.getvalue()

    elif input_mode == "Enter Barcode Manually":
        st.caption("Type the barcode number printed under the barcode lines.")
        manual_barcode = st.text_input(
            "Barcode number",
            placeholder="e.g. 8904004400762",
            max_chars=14,
            label_visibility="collapsed"
        )
        if manual_barcode:
            if manual_barcode.isdigit() and 8 <= len(manual_barcode) <= 14:
                st.success(f"Barcode entered: `{manual_barcode}`")
            else:
                st.error("Please enter a valid barcode — 8 to 14 digits, numbers only.")
                manual_barcode = None

    else:  # Live Scan
        st.caption("Point your camera at a barcode — it will be detected automatically.")
        # Render the ZXing-js live scanner
        components.html(_live_scanner_html(st.session_state.dark_mode), height=480, scrolling=False)
        # Hidden text input receives barcode from JS via postMessage → Streamlit component bridge
        live_detected = st.text_input(
            "Detected barcode (auto-filled by live scanner)",
            key="live_barcode_input",
            label_visibility="collapsed",
            placeholder="Barcode will appear here automatically..."
        )
        if live_detected and live_detected.isdigit() and 8 <= len(live_detected) <= 14:
            manual_barcode = live_detected
            st.success(f"Live scan detected: `{live_detected}`")
        elif live_detected:
            st.caption("Scanner active — waiting for valid barcode...")

with guide_col:
    st.markdown("#### Tips for best results")
    st.markdown("""
- **Barcode scan:** Keep it flat, well-lit, centred in frame
- **Manual entry:** Use if scanner fails — number is printed under the barcode
""")

st.divider()

# ── Preview uploaded image ────────────────────────────────────────────────────
if image_bytes:
    preview_image = load_image_from_bytes(image_bytes)
    col_prev, col_btn = st.columns([3, 1])
    with col_prev:
        st.image(preview_image, caption="Input image", use_container_width=True)
    with col_btn:
        st.markdown("<br><br>", unsafe_allow_html=True)
        analyse_clicked = st.button("Analyse Product", type="primary", use_container_width=True)
elif manual_barcode:
    st.info(f"Will look up barcode **{manual_barcode}** directly on Open Food Facts.")
    analyse_clicked = st.button("Analyse Product", type="primary")
else:
    analyse_clicked = False


# ── 4. Pipeline Trigger & Agent Progress ─────────────────────────────────────

if analyse_clicked and (image_bytes or manual_barcode):
    if image_bytes:
        is_valid_img, img_msg = validate_image_bytes(image_bytes)
        if not is_valid_img:
            st.error(f"{img_msg}")
            st.stop()

    agent_steps = [
        ("Agent 1", "Extracting barcode / reading label..."),
        ("Agent 2", "Looking up nutrition database..."),
        ("Agent 3", "Analysing health profile..."),
        ("Agent 4", "Personalising for your health conditions..."),
        ("Agent 5", "Generating your health report..."),
    ]

    st.subheader("Running Analysis Pipeline")
    progress_bar = st.progress(0)
    status_placeholder = st.empty()

    for i, (name, desc) in enumerate(agent_steps):
        if i == 2 and not user_profile:
            status_placeholder.markdown(
                f"<div class='agent-step'><div class='agent-dot' style='background:#555'></div>"
                f"<span style='color:#666'>{name} — Skipped (no health profile)</span></div>",
                unsafe_allow_html=True
            )
        else:
            status_placeholder.markdown(
                f"<div class='agent-step'><div class='agent-dot'></div>"
                f"<strong>{name}</strong> — {desc}</div>",
                unsafe_allow_html=True
            )
        progress_bar.progress((i + 1) * 18)

    with st.spinner("Finalising report..."):
        try:
            final_state = run_pipeline(
                image_bytes=image_bytes,
                user_profile=user_profile if user_profile else None,
                manual_barcode=manual_barcode
            )
        except Exception as e:
            st.error(f"Pipeline error: {e}")
            st.stop()

    progress_bar.progress(100)
    status_placeholder.success("Analysis complete!")

    health = check_pipeline_health(final_state)
    if health["status"] == "error":
        st.error("The pipeline encountered critical errors. Results may be incomplete.")
        for issue in health["issues"]:
            st.warning(issue)
    elif health["status"] == "warning":
        with st.expander("Pipeline completed with warnings — click to view"):
            for issue in health["issues"]:
                st.caption(f"• {issue}")

    st.divider()

    # ── 5. Results Panel ──────────────────────────────────────────────────────
    report_data = final_state.get("report_data", {})

    if not report_data:
        st.error("No results were returned. Please try again with a clearer image.")
        st.stop()

    # Add to session history
    _add_to_history(report_data)
    show_scan_toast(report_data)

    # ── Product header ─────────────────────────────────────────────────────────
    prod_col, score_col = st.columns([3, 2])

    with prod_col:
        st.subheader(report_data.get("product_name", "Unknown Product"))

        meta_parts = []
        if report_data.get("barcode"):
            meta_parts.append(f"Barcode: `{report_data['barcode']}`")
        if report_data.get("nutri_score"):
            meta_parts.append(f"Nutri-Score: **{report_data['nutri_score']}**")
        if report_data.get("nova_group"):
            nova_labels = {1: "Unprocessed", 2: "Processed ingredient",
                           3: "Processed", 4: "Ultra-processed"}
            nova_text = nova_labels.get(report_data["nova_group"], str(report_data["nova_group"]))
            meta_parts.append(f"NOVA: **{report_data['nova_group']}** ({nova_text})")

        for part in meta_parts:
            st.markdown(part)

        if report_data.get("product_image_url"):
            st.image(report_data["product_image_url"], width=160)

        if report_data.get("extraction_note"):
            st.caption(f"{report_data['extraction_note']}")
        if report_data.get("lookup_note"):
            st.caption(f"{report_data['lookup_note']}")

    with score_col:
        display_score = report_data.get("display_score")
        if display_score is not None:
            score_class = _get_score_class(display_score)
            score_label = _get_score_label(display_score)
            personalised_tag = " (personalised)" if report_data.get("is_personalized") else ""

            st.markdown(
                f"<div class='score-badge {score_class}'>"
                f"{display_score}/10<br>"
                f"<span style='font-size:1rem;font-weight:500'>{score_label}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
            st.caption(f"Health Score{personalised_tag}")

        if report_data.get("consumption_frequency"):
            st.markdown(
                f"<div style='margin-top:8px'>Recommended frequency:<br>"
                f"<span class='freq-pill'>{report_data['consumption_frequency'].title()}</span>"
                f"</div>",
                unsafe_allow_html=True
            )

        if report_data.get("is_personalized") and report_data.get("general_score"):
            st.caption(
                f"General score: {report_data['general_score']}/10 · "
                f"Adjusted for your profile: {report_data['personalized_score']}/10"
            )

    st.divider()

    # ── Nutrition breakdown ───────────────────────────────────────────────────
    st.subheader("Nutritional Breakdown (per 100g)")

    # AI estimated badge + disclaimer
    llm_estimated = report_data.get("llm_estimated", False)
    if llm_estimated:
        st.markdown(
            "<span class='ai-badge'>AI Estimated</span>"
            "<span style='color:#aaa; font-size:0.82rem; margin-left:10px'>"
            "Nutrition values were estimated by AI — Open Food Facts had no data for this product. "
            "Always verify against the physical product label.</span>",
            unsafe_allow_html=True
        )
        st.markdown("")

    nutrition_table = report_data.get("nutrition_table", [])

    if nutrition_table:
        daily_ref = {
            "Energy":        2000,
            "Protein":         50,
            "Total Fat":       65,
            "Saturated Fat":   20,
            "Trans Fat":        2,
            "Carbohydrates":  300,
            "Sugar":           50,
            "Dietary Fibre":   30,
            "Sodium":        2000,
        }

        # Use amber colour for AI-estimated bars, blue for verified
        bar_css = "color: #f1c40f;" if llm_estimated else ""
        badge_note = " <span style='color:#f1c40f;font-size:0.7rem'>~est</span>" \
                     if llm_estimated else ""

        nutr_cols = st.columns(3)
        for idx, row in enumerate(nutrition_table):
            col = nutr_cols[idx % 3]
            with col:
                ref = daily_ref.get(row["label"])
                if ref:
                    pct = min(float(row["value"]) / ref, 1.0)
                    st.markdown(
                        f"<div class='nutr-label' style='{bar_css}'>{row['label']}{badge_note} "
                        f"<span style='color:#888'>({row['value']} {row['unit']} · "
                        f"{int(pct*100)}% DV)</span></div>",
                        unsafe_allow_html=True
                    )
                    st.progress(pct)
                else:
                    st.metric(row["label"], f"{row['value']} {row['unit']}")
    else:
        st.info("Nutritional breakdown not available for this product.")

    st.divider()

    # ── Insights: red flags + positives ──────────────────────────────────────
    flags_col, pos_col = st.columns(2)

    with flags_col:
        st.subheader("Red Flags")
        red_flags = report_data.get("red_flags", [])
        if red_flags:
            for flag in red_flags:
                st.markdown(
                    f"<div class='insight-card red-flag-card'>{flag}</div>",
                    unsafe_allow_html=True
                )
        else:
            st.markdown(
                "<div class='insight-card positive-card'>No significant red flags identified.</div>",
                unsafe_allow_html=True
            )

    with pos_col:
        st.subheader("Positives")
        positives = report_data.get("positives", [])
        if positives:
            for pos in positives:
                st.markdown(
                    f"<div class='insight-card positive-card'>{pos}</div>",
                    unsafe_allow_html=True
                )
        else:
            st.markdown(
                "<div class='insight-card red-flag-card'>No notable nutritional positives found.</div>",
                unsafe_allow_html=True
            )

    # ── Personalised warnings & tips ─────────────────────────────────────────
    if report_data.get("is_personalized"):
        st.divider()
        st.subheader("Personalised Insights")

        if report_data.get("personalization_note"):
            st.info(f" {report_data['personalization_note']}")

        warn_col, tips_col = st.columns(2)

        with warn_col:
            st.markdown("**Warnings for your profile**")
            for w in report_data.get("personalized_warnings", []):
                st.markdown(
                    f"<div class='insight-card warning-card'>{w}</div>",
                    unsafe_allow_html=True
                )

        with tips_col:
            st.markdown("**Tips for you**")
            for t in report_data.get("personalized_tips", []):
                st.markdown(
                    f"<div class='insight-card tip-card'>{t}</div>",
                    unsafe_allow_html=True
                )

    # ── Allergens & additives ─────────────────────────────────────────────────
    if report_data.get("allergens") or report_data.get("additives_flagged"):
        st.divider()
        add_col, allerg_col = st.columns(2)

        with allerg_col:
            if report_data.get("allergens"):
                st.subheader("Allergens")
                allergen_str = " · ".join(report_data["allergens"])
                st.warning(f"Contains: {allergen_str}")

        with add_col:
            if report_data.get("additives_flagged"):
                st.subheader("Flagged Additives")
                st.warning(
                    "The following additives of concern were detected: "
                    + ", ".join(report_data["additives_flagged"])
                )

    # ── Narrative summary ─────────────────────────────────────────────────────
    st.divider()
    st.subheader("Health Report Summary")
    narrative = report_data.get("narrative") or report_data.get("health_summary", "")
    if narrative:
        st.markdown(
            f"<div class='narrative-box'>{narrative}</div>",
            unsafe_allow_html=True
        )

    # ── Pipeline errors (debug) ───────────────────────────────────────────────
    pipeline_errors = report_data.get("pipeline_errors", [])
    if pipeline_errors:
        with st.expander("Pipeline warnings / debug info"):
            for err in pipeline_errors:
                st.caption(f"• {err}")

    # ── 6. Report Download ────────────────────────────────────────────────────
    st.divider()
    st.subheader("Download My Report!")

    final_report_text = final_state.get("final_report", "")
    if final_report_text:
        try:
            from exports.report_exporter import generate_docx
            docx_bytes = generate_docx(report_data, final_report_text)
            st.download_button(
                label="📄 Download Report (.docx)",
                data=docx_bytes,
                file_name=f"nutriscan_report_{report_data.get('product_name','product').replace(' ','_')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
                type="primary",
            )
        except Exception:
            st.info("DOCX export coming soon.")

    st.caption(
        f"Generated: {report_data.get('generated_at', '')} · "
        f"NutriScan AI v{APP_VERSION} · "
        "For informational purposes only. Consult a qualified dietitian for medical advice."
    )

#temp
# st.write(st.session_state.get("current_user"))

