# agents/report_agent.py
# Agent 5 — Report Generation Agent
#
# Responsibilities:
# - Compile all prior agent outputs into a polished final report
# - Build report_data dict for structured Streamlit UI rendering
# - Generate a downloadable plain-text report string
# - Use Claude for the narrative summary section

import json
from datetime import datetime
from groq import Groq
from state import NutriScanState
from config import GROQ_API_KEY, GROQ_MODEL, GROQ_MAX_TOKENS, GROQ_TEMPERATURE
from utils.error_handler import safe_agent

client = Groq(api_key=GROQ_API_KEY)


@safe_agent("Agent 5 (Report)")
def run_report_agent(state: NutriScanState) -> NutriScanState:
    """
    LangGraph node function for Agent 5.
    Produces final_report (text) and report_data (dict for UI).
    """
    errors = list(state.get("pipeline_errors") or [])

    # ── Determine which score/frequency to display ────────────────────────────
    # Use personalised values if available, otherwise fall back to general
    display_score = (
        state.get("personalized_score")
        if state.get("personalized_score") is not None
        else state.get("health_score")
    )
    display_frequency = (
        state.get("personalized_frequency")
        or state.get("consumption_frequency")
    )
    is_personalized = state.get("personalized_score") is not None

    # ── Generate narrative report via Claude ──────────────────────────────────
    narrative = ""
    try:
        prompt = _build_report_prompt(state, display_score, display_frequency, is_personalized)
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=GROQ_MAX_TOKENS,
            temperature=GROQ_TEMPERATURE,
            messages=[
                {"role": "system", "content": "You are a friendly nutritionist writing consumer health reports. Respond in plain flowing paragraphs only — no JSON, no bullet points, no markdown, no headers."},
                {"role": "user", "content": prompt}
            ]
        )
        raw_narrative = response.choices[0].message.content.strip()
        narrative = _extract_plain_narrative(raw_narrative)
    except Exception as e:
        errors.append(f"Agent 5: Claude report generation error — {str(e)}")
        narrative = _build_fallback_narrative(state, display_score, display_frequency)

    # ── Build structured report_data for Streamlit UI ─────────────────────────
    nutrition = state.get("nutrition_enriched") or state.get("nutrition_raw") or {}

    report_data = {
        "product_name":       nutrition.get("product_name", "Unknown Product"),
        "product_image_url":  state.get("product_image_url"),
        "barcode":            state.get("barcode_number"),
        "nutri_score":        state.get("nutri_score"),
        "nova_group":         state.get("nova_group"),

        # Scores
        "general_score":      state.get("health_score"),
        "personalized_score": state.get("personalized_score"),
        "display_score":      display_score,
        "is_personalized":    is_personalized,

        # Frequency
        "consumption_frequency": display_frequency,

        # Analysis
        "red_flags":             state.get("red_flags", []),
        "positives":             state.get("positives", []),
        "personalized_warnings": state.get("personalized_warnings", []),
        "personalized_tips":     state.get("personalized_tips", []),
        "health_summary":        state.get("health_summary", ""),
        "personalization_note":  state.get("personalization_note", ""),

        # Nutrition table (key fields for display)
        "nutrition_table": _build_nutrition_table(nutrition),

        # Additives & allergens
        "additives_flagged": state.get("additives_flagged", []),
        "allergens":         state.get("allergens", []),

        # Agent notes
        "extraction_note":   state.get("extraction_note", ""),
        "lookup_note":       state.get("lookup_note", ""),

        # Narrative
        "narrative": narrative,

        # Meta
        "generated_at":    datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
        "pipeline_errors": errors,
    }

    # ── Build plain-text final_report for download ────────────────────────────
    final_report = _build_plain_text_report(report_data)

    return {
        **state,
        "final_report":    final_report,
        "report_data":     report_data,
        "pipeline_errors": errors,
    }


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_report_prompt(
    state: NutriScanState,
    display_score: float,
    display_frequency: str,
    is_personalized: bool
) -> str:
    nutrition = state.get("nutrition_enriched") or state.get("nutrition_raw") or {}
    product_name = nutrition.get("product_name", "this product")
    profile_line = ""

    if is_personalized and state.get("user_profile"):
        profile = state["user_profile"]
        conditions = profile.get("conditions", [])
        if conditions:
            cond_str = ", ".join(conditions) if isinstance(conditions, list) else conditions
            profile_line = f"The user has the following health conditions: {cond_str}."

    score_label = _score_label(display_score)
    warnings_block = ""
    if state.get("personalized_warnings"):
        warnings_block = "Personalised warnings:\n" + "\n".join(
            f"- {w}" for w in state["personalized_warnings"]
        )

    return f"""You are a friendly nutritionist writing a consumer health report.

Write a clear, helpful, and encouraging 3-4 paragraph report for a food product with the following profile:

Product: {product_name}
Health Score: {display_score}/10 ({score_label})
Recommended consumption: {display_frequency}
Key red flags: {'; '.join(state.get('red_flags', [])) or 'None identified'}
Key positives: {'; '.join(state.get('positives', [])) or 'None identified'}
{profile_line}
{warnings_block}

Guidelines:
- Write in plain English, as if speaking directly to the consumer
- Start with an overall verdict on the product
- Mention the most important red flags and positives
- Include the recommended consumption frequency with a brief reason
- If personalised, address how the user's conditions affect their relationship with this product
- End with a practical, positive suggestion
- Do NOT use bullet points — write in flowing paragraphs
- Keep it under 250 words"""


# ── Report builders ───────────────────────────────────────────────────────────

def _build_nutrition_table(nutrition: dict) -> list:
    """Build a list of (label, value, unit) tuples for UI display."""
    fields = [
        ("energy_kcal",   "Energy",         "kcal"),
        ("protein",       "Protein",         "g"),
        ("total_fat",     "Total Fat",       "g"),
        ("saturated_fat", "Saturated Fat",   "g"),
        ("trans_fat",     "Trans Fat",       "g"),
        ("carbohydrates", "Carbohydrates",   "g"),
        ("sugar",         "Sugar",           "g"),
        ("dietary_fibre", "Dietary Fibre",   "g"),
        ("sodium",        "Sodium",          "mg"),
    ]
    table = []
    for key, label, unit in fields:
        val = nutrition.get(key)
        if val is not None:
            table.append({"label": label, "value": val, "unit": unit})
    return table


def _build_plain_text_report(report_data: dict) -> str:
    """Build a clean plain-text version of the report for download."""
    lines = [
        "=" * 60,
        f"  NUTRISCAN AI — HEALTH REPORT",
        f"  {report_data.get('generated_at', '')}",
        "=" * 60,
        "",
        f"Product:  {report_data['product_name']}",
    ]

    if report_data.get("barcode"):
        lines.append(f"Barcode:  {report_data['barcode']}")
    if report_data.get("nutri_score"):
        lines.append(f"Nutri-Score: {report_data['nutri_score']}")
    if report_data.get("nova_group"):
        lines.append(f"NOVA Group:  {report_data['nova_group']}")

    lines += [
        "",
        f"Health Score:          {report_data.get('display_score', 'N/A')}/10",
        f"Consumption Frequency: {report_data.get('consumption_frequency', 'N/A')}",
        f"Personalised:          {'Yes' if report_data.get('is_personalized') else 'No'}",
        "",
        "─" * 60,
        "NUTRITIONAL VALUES (per 100g)",
        "─" * 60,
    ]

    for row in report_data.get("nutrition_table", []):
        lines.append(f"  {row['label']:<20} {row['value']} {row['unit']}")

    if report_data.get("red_flags"):
        lines += ["", "─" * 60, "RED FLAGS", "─" * 60]
        for flag in report_data["red_flags"]:
            lines.append(f"  ! {flag}")

    if report_data.get("positives"):
        lines += ["", "─" * 60, "POSITIVES", "─" * 60]
        for pos in report_data["positives"]:
            lines.append(f"  + {pos}")

    if report_data.get("personalized_warnings"):
        lines += ["", "─" * 60, "PERSONALISED WARNINGS", "─" * 60]
        for w in report_data["personalized_warnings"]:
            lines.append(f"  ! {w}")

    if report_data.get("personalized_tips"):
        lines += ["", "─" * 60, "PERSONALISED TIPS", "─" * 60]
        for t in report_data["personalized_tips"]:
            lines.append(f"  > {t}")

    if report_data.get("allergens"):
        lines += ["", f"Allergens: {', '.join(report_data['allergens'])}"]

    if report_data.get("additives_flagged"):
        lines += [f"Flagged Additives: {', '.join(report_data['additives_flagged'])}"]

    lines += [
        "",
        "─" * 60,
        "SUMMARY",
        "─" * 60,
        report_data.get("narrative", report_data.get("health_summary", "")),
        "",
        "=" * 60,
        "Generated by NutriScan AI v2.0",
        "This report is for informational purposes only.",
        "Consult a qualified dietitian for personalised medical advice.",
        "=" * 60,
    ]

    return "\n".join(lines)



def _extract_plain_narrative(text: str) -> str:
    """
    Ensure the narrative is plain prose.
    If Groq returns JSON despite instructions, extract the most useful text value from it.
    """
    import json, re
    stripped = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()

    # If it looks like JSON, try to extract prose fields from it
    if stripped.startswith("{"):
        try:
            data = json.loads(stripped)
            # Flatten all string values into one narrative
            parts = []
            def extract_strings(obj):
                if isinstance(obj, str) and len(obj) > 30:
                    parts.append(obj)
                elif isinstance(obj, dict):
                    for v in obj.values():
                        extract_strings(v)
                elif isinstance(obj, list):
                    for item in obj:
                        extract_strings(item)
            extract_strings(data)
            if parts:
                return " ".join(parts)
        except (json.JSONDecodeError, ValueError):
            pass

    # Strip any remaining markdown artifacts
    clean = re.sub(r"```[a-z]*", "", text).strip()
    return clean

def _build_fallback_narrative(
    state: NutriScanState,
    display_score: float,
    display_frequency: str
) -> str:
    nutrition = state.get("nutrition_enriched") or {}
    name = nutrition.get("product_name", "This product")
    score_label = _score_label(display_score)
    return (
        f"{name} has received a health score of {display_score}/10 ({score_label}). "
        f"Recommended consumption: {display_frequency}. "
        f"{state.get('health_summary', '')}"
    )


def _score_label(score: float) -> str:
    if score is None:
        return "N/A"
    if score >= 8:
        return "Excellent"
    if score >= 6:
        return "Good"
    if score >= 4:
        return "Moderate"
    if score >= 2:
        return "Poor"
    return "Avoid"