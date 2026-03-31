# dashboard.py
# NutriScan AI — Nutrition Trends Dashboard
#
# Call render_dashboard() from app.py:
#
#   from dashboard import render_dashboard
#   if st.session_state.get("show_dashboard"):
#       render_dashboard()
#       st.stop()

import streamlit as st
import json
from database import load_scans, get_scan_count


def render_dashboard():
    """Render the full nutrition trends dashboard."""
    email = st.session_state.get("current_user", {}).get("email", "")
    dark  = st.session_state.get("dark_mode", True)

    # Colour palette
    bg       = "#0e0e0e"  if dark else "#f7f9fc"
    card_bg  = "#1a1a1a"  if dark else "#ffffff"
    border   = "#2a2a2a"  if dark else "#d8dde6"
    text     = "#f0f0f0"  if dark else "#1a1a1a"
    subtext  = "#888888"  if dark else "#666666"
    green    = "#27ae60"

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
.stApp{{background:{bg}!important}}
.stApp *{{color:{text}!important}}
.main .block-container{{padding:2rem 2rem!important;max-width:1100px!important;}}
.dash-card{{
    background:{card_bg};border:1px solid {border};
    border-radius:12px;padding:18px 20px;height:100%;
}}
.dash-card-title{{
    font-size:11px;font-weight:700;color:{subtext}!important;
    letter-spacing:1px;text-transform:uppercase;margin-bottom:12px;
}}
.score-pill{{
    display:inline-block;padding:3px 12px;border-radius:20px;
    font-size:12px;font-weight:700;color:#fff;
}}
.trend-row{{
    display:flex;align-items:center;justify-content:space-between;
    padding:10px 0;border-bottom:1px solid {border};
    font-size:13px;
}}
.trend-row:last-child{{border-bottom:none;}}
.nutrient-bar-wrap{{margin:6px 0;}}
.nutrient-label{{font-size:12px;color:{subtext}!important;margin-bottom:3px;}}
div[data-testid="stButton"]>button[kind="secondary"]{{
    background:transparent!important;border:1px solid {border}!important;
    border-radius:9px!important;color:{text}!important;font-size:13px!important;
}}
div[data-testid="stButton"]>button[kind="secondary"]:hover{{
    border-color:{green}!important;color:{green}!important;
}}
div[data-testid="stMetric"]{{
    background:{card_bg}!important;border:1px solid {border}!important;
    border-radius:10px!important;padding:14px 16px!important;
}}
div[data-testid="stMetric"] label{{
    font-size:10px!important;font-weight:700!important;
    text-transform:uppercase!important;letter-spacing:0.5px!important;
    color:{subtext}!important;
}}
div[data-testid="stMetric"] [data-testid="stMetricValue"]{{
    font-size:22px!important;font-weight:700!important;
    letter-spacing:-0.5px!important;
}}
</style>
""", unsafe_allow_html=True)

    # ── Header ────────────────────────────────────────────────────────────────
    col_back, col_title = st.columns([1, 5])
    with col_back:
        if st.button("← Back", key="dash_back"):
            st.session_state.show_dashboard = False
            st.rerun()
    with col_title:
        st.markdown(f"<h2 style='font-size:22px;font-weight:700;margin:0;'>Nutrition Trends</h2>",
                    unsafe_allow_html=True)
        st.markdown(f"<p style='font-size:13px;color:{subtext};margin:0;'>"
                    f"Your personalised scan history & insights</p>",
                    unsafe_allow_html=True)

    st.divider()

    # ── Load all scans ────────────────────────────────────────────────────────
    all_scans = load_scans(email, limit=50)
    total     = get_scan_count(email)

    if not all_scans:
        st.info("No scans yet — scan a product to start building your nutrition history.")
        return

    # ── Summary metrics ───────────────────────────────────────────────────────
    scores = [s["score"] for s in all_scans if s["score"] is not None]
    avg_score  = round(sum(scores) / len(scores), 1) if scores else 0
    best_score = max(scores) if scores else 0
    worst_score = min(scores) if scores else 0
    ai_est_count = sum(1 for s in all_scans if s.get("llm_estimated"))

    m1, m2, m3, m4 = st.columns(4)
    with m1: st.metric("Total scans",   total)
    with m2: st.metric("Average score", f"{avg_score}/10")
    with m3: st.metric("Best scan",     f"{best_score}/10")
    with m4: st.metric("AI estimated",  ai_est_count)

    st.markdown("<br/>", unsafe_allow_html=True)

    # ── Score distribution ────────────────────────────────────────────────────
    left, right = st.columns([1.2, 1])

    with left:
        st.markdown('<div class="dash-card">', unsafe_allow_html=True)
        st.markdown('<div class="dash-card-title">Score distribution</div>', unsafe_allow_html=True)

        buckets = {
            "Excellent (8-10)": ("#27ae60", len([s for s in scores if s >= 8])),
            "Good (6-8)":       ("#2980b9", len([s for s in scores if 6 <= s < 8])),
            "Moderate (4-6)":   ("#f39c12", len([s for s in scores if 4 <= s < 6])),
            "Poor (2-4)":       ("#e67e22", len([s for s in scores if 2 <= s < 4])),
            "Avoid (0-2)":      ("#e74c3c", len([s for s in scores if s < 2])),
        }
        total_scored = len(scores) or 1
        for label, (colour, count) in buckets.items():
            pct = count / total_scored
            st.markdown(f"""
<div class="nutrient-bar-wrap">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;">
    <span class="nutrient-label">{label}</span>
    <span style="font-size:12px;font-weight:600;color:{colour}!important;">{count}</span>
  </div>
  <div style="background:{"#2a2a2a" if dark else "#e5e7eb"};border-radius:99px;height:6px;">
    <div style="width:{int(pct*100)}%;background:{colour};border-radius:99px;height:6px;"></div>
  </div>
</div>""", unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    with right:
        st.markdown('<div class="dash-card">', unsafe_allow_html=True)
        st.markdown('<div class="dash-card-title">Most scanned products</div>',
                    unsafe_allow_html=True)

        product_counts: dict = {}
        for s in all_scans:
            name = s["product_name"]
            if name and name != "Unknown Product":
                product_counts[name] = product_counts.get(name, 0) + 1

        top_products = sorted(product_counts.items(), key=lambda x: x[1], reverse=True)[:6]

        if top_products:
            for prod, count in top_products:
                st.markdown(f"""
<div class="trend-row">
  <span style="font-size:13px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:200px;">{prod}</span>
  <span style="font-size:12px;font-weight:700;color:{green}!important;">{count}x</span>
</div>""", unsafe_allow_html=True)
        else:
            st.caption("Not enough data yet.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<br/>", unsafe_allow_html=True)

    # ── Recent scans with scores ──────────────────────────────────────────────
    st.markdown('<div class="dash-card">', unsafe_allow_html=True)
    st.markdown('<div class="dash-card-title">Recent scan history</div>', unsafe_allow_html=True)

    def score_colour(s):
        if s is None: return "#888"
        if s >= 8:  return "#27ae60"
        if s >= 6:  return "#2980b9"
        if s >= 4:  return "#f39c12"
        if s >= 2:  return "#e67e22"
        return "#e74c3c"

    for scan in all_scans:
        sc    = scan["score"]
        col   = score_colour(sc)
        score_txt = f"{sc}/10" if sc is not None else "N/A"
        freq  = scan["frequency"].title() if scan.get("frequency") else ""
        ai_tag = " <span style='font-size:10px;background:#3a2e00;color:#f1c40f;padding:1px 6px;border-radius:4px;'>AI est.</span>" \
                 if scan.get("llm_estimated") else ""
        date  = f"{scan.get('scanned_date','')} {scan.get('scanned_at','')}"

        st.markdown(f"""
<div class="trend-row">
  <div style="flex:1;min-width:0;">
    <div style="font-weight:600;font-size:13px;overflow:hidden;
                text-overflow:ellipsis;white-space:nowrap;">
      {scan['product_name']}{ai_tag}
    </div>
    <div style="font-size:11px;color:{subtext}!important;">{freq}</div>
  </div>
  <div style="text-align:right;flex-shrink:0;margin-left:16px;">
    <div style="font-weight:700;color:{col}!important;">{score_txt}</div>
    <div style="font-size:11px;color:{subtext}!important;">{date}</div>
  </div>
</div>""", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("<br/>", unsafe_allow_html=True)

    # ── Avg macros across all scans ───────────────────────────────────────────
    # Pull nutrition data from stored report_json
    macro_sums: dict = {}
    macro_counts: dict = {}
    nutrient_keys = ["Energy", "Protein", "Total Fat", "Carbohydrates",
                     "Sugar", "Dietary Fibre", "Sodium", "Saturated Fat"]

    for scan in all_scans:
        rd = scan.get("report_data", {})
        table = rd.get("nutrition_table", [])
        for row in table:
            label = row.get("label", "")
            if label in nutrient_keys:
                try:
                    val = float(row.get("value", 0))
                    macro_sums[label]   = macro_sums.get(label, 0) + val
                    macro_counts[label] = macro_counts.get(label, 0) + 1
                except Exception:
                    pass

    if macro_sums:
        st.markdown('<div class="dash-card">', unsafe_allow_html=True)
        st.markdown('<div class="dash-card-title">Average nutrients across all scans (per 100g)</div>',
                    unsafe_allow_html=True)

        daily_ref = {
            "Energy": 2000, "Protein": 50, "Total Fat": 65,
            "Saturated Fat": 20, "Carbohydrates": 300,
            "Sugar": 50, "Dietary Fibre": 30, "Sodium": 2000,
        }
        cols = st.columns(3)
        for idx, label in enumerate(nutrient_keys):
            if label not in macro_sums:
                continue
            avg_val = macro_sums[label] / macro_counts[label]
            ref     = daily_ref.get(label, 1)
            pct     = min(avg_val / ref, 1.0)
            unit    = "kcal" if label == "Energy" else "mg" if label == "Sodium" else "g"
            with cols[idx % 3]:
                st.markdown(f"""
<div style="margin-bottom:14px;">
  <div style="display:flex;justify-content:space-between;margin-bottom:3px;">
    <span style="font-size:12px;color:{subtext}!important;">{label}</span>
    <span style="font-size:12px;font-weight:600;">{avg_val:.1f}{unit}</span>
  </div>
  <div style="background:{"#2a2a2a" if dark else "#e5e7eb"};border-radius:99px;height:5px;">
    <div style="width:{int(pct*100)}%;background:{green};border-radius:99px;height:5px;"></div>
  </div>
  <div style="font-size:10px;color:{subtext}!important;margin-top:2px;">{int(pct*100)}% daily value</div>
</div>""", unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)