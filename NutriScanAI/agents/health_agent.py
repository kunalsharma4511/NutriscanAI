# agents/health_agent.py
# Agent 3 — Health Analysis Agent
#
# Responsibilities:
# - Send enriched nutrition profile to Claude via Anthropic SDK
# - Generate a general health score (1–10)
# - Determine safe consumption frequency
# - Identify red flags and nutritional positives
# - Produce a plain-English health summary
# - All analysis is product-level (not yet personalised)

import json
from groq import Groq
from state import NutriScanState
from config import GROQ_API_KEY, GROQ_MODEL, GROQ_MAX_TOKENS, GROQ_TEMPERATURE
from utils.error_handler import safe_agent

client = Groq(api_key=GROQ_API_KEY)

# Consumption frequency options (used to constrain Claude's output)
FREQUENCY_OPTIONS = [
    "daily",
    "a few times a week",
    "weekly",
    "occasional (once or twice a month)",
    "avoid"
]


@safe_agent("Agent 3 (Health)")
def run_health_agent(state: NutriScanState) -> NutriScanState:
    """
    LangGraph node function for Agent 3.
    Calls Claude to analyse the enriched nutrition profile.
    """
    errors = list(state.get("pipeline_errors") or [])
    nutrition = state.get("nutrition_enriched") or state.get("nutrition_raw") or {}

    if not nutrition:
        errors.append("Agent 3: No nutrition data available for health analysis.")
        return {
            **state,
            "health_score": None,
            "consumption_frequency": None,
            "red_flags": [],
            "positives": [],
            "health_summary": "Insufficient data for health analysis.",
            "pipeline_errors": errors,
        }

    # ── Build the prompt ──────────────────────────────────────────────────────
    nutrition_summary = _format_nutrition_for_prompt(nutrition, state)
    prompt = _build_health_prompt(nutrition_summary)

    # ── Call GROQ ───────────────────────────────────────────────────────────
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=GROQ_MAX_TOKENS,
            temperature=GROQ_TEMPERATURE,
            messages=[
                {"role": "system", "content": "You are a nutrition expert. Respond with valid JSON only — no preamble, no markdown, no extra text."},
                {"role": "user", "content": prompt}
            ]
        )
        raw_text = response.choices[0].message.content.strip()
        parsed = _parse_response(raw_text)

    except Exception as e:
        errors.append(f"Agent 3: GROQ API error — {str(e)}")
        return {
            **state,
            "health_score": None,
            "consumption_frequency": None,
            "red_flags": [],
            "positives": [],
            "health_summary": "Health analysis could not be completed due to an API error.",
            "pipeline_errors": errors,
        }

    # ── Return updated state ──────────────────────────────────────────────────
    return {
        **state,
        "health_score":          parsed.get("health_score"),
        "consumption_frequency": parsed.get("consumption_frequency"),
        "red_flags":             parsed.get("red_flags", []),
        "positives":             parsed.get("positives", []),
        "health_summary":        parsed.get("health_summary", ""),
        "pipeline_errors":       errors,
    }


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_health_prompt(nutrition_summary: str) -> str:
    return f"""You are a certified nutritionist and food safety expert.
Analyse the following nutritional data for a packaged food product and provide a structured health evaluation.

NUTRITIONAL DATA:
{nutrition_summary}

Respond ONLY in the following JSON format with no preamble, no markdown, and no additional text:

{{
  "health_score": <number from 1.0 to 10.0, one decimal place>,
  "consumption_frequency": "<one of: daily | a few times a week | weekly | occasional (once or twice a month) | avoid>",
  "red_flags": [
    "<specific concern 1, e.g. 'Sodium is 42% of daily recommended value per serving'>",
    "<specific concern 2>"
  ],
  "positives": [
    "<specific positive 1, e.g. 'Good source of dietary fibre (6g per serving)'>",
    "<specific positive 2>"
  ],
  "health_summary": "<2-3 sentence plain English summary of the product's overall healthiness. Be specific, not generic.>"
}}

Scoring guide:
- 8-10: Nutrient-dense, minimally processed, safe for daily consumption
- 6-7:  Reasonably healthy with minor concerns
- 4-5:  Moderate concerns; limit consumption
- 2-3:  High in harmful nutrients; occasional only
- 1:    Strongly advise against regular consumption

Base your evaluation on WHO dietary guidelines and FSSAI/ICMR recommended daily values for Indian adults.
If certain values are missing, note this but still provide your best assessment based on available data."""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_nutrition_for_prompt(nutrition: dict, state: NutriScanState) -> str:
    """Format the nutrition dict into a clean text block for the prompt."""
    lines = []

    if nutrition.get("product_name"):
        lines.append(f"Product Name: {nutrition['product_name']}")
    if state.get("nutri_score"):
        lines.append(f"Nutri-Score: {state['nutri_score']}")
    if state.get("nova_group"):
        lines.append(f"NOVA Group: {state['nova_group']} (1=unprocessed, 4=ultra-processed)")

    lines.append("\nNutritional values per 100g (or per serving if noted):")

    field_labels = {
        "energy_kcal":   "Energy (kcal)",
        "energy_kj":     "Energy (kJ)",
        "protein":       "Protein (g)",
        "total_fat":     "Total Fat (g)",
        "saturated_fat": "Saturated Fat (g)",
        "trans_fat":     "Trans Fat (g)",
        "carbohydrates": "Carbohydrates (g)",
        "sugar":         "Sugar (g)",
        "dietary_fibre": "Dietary Fibre (g)",
        "sodium":        "Sodium (mg)",
        "serving_size":  "Serving Size",
    }

    for field, label in field_labels.items():
        val = nutrition.get(field)
        if val is not None:
            lines.append(f"  {label}: {val}")

    if nutrition.get("ingredients"):
        lines.append(f"\nIngredients: {nutrition['ingredients'][:500]}")

    if state.get("additives_flagged"):
        lines.append(f"\nFlagged additives: {', '.join(state['additives_flagged'])}")

    if state.get("allergens"):
        lines.append(f"Allergens: {', '.join(state['allergens'])}")

    return "\n".join(lines)


def _parse_response(raw_text: str) -> dict:
    """
    Parse Claude's JSON response.
    Falls back to safe defaults if parsing fails.
    """
    # Strip any accidental markdown fences
    clean = raw_text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()

    try:
        data = json.loads(clean)

        # Validate and clamp health score
        score = float(data.get("health_score", 5.0))
        data["health_score"] = round(max(1.0, min(10.0, score)), 1)

        # Ensure lists
        data["red_flags"] = data.get("red_flags") or []
        data["positives"] = data.get("positives") or []

        return data

    except (json.JSONDecodeError, ValueError):
        return {
            "health_score": 5.0,
            "consumption_frequency": "weekly",
            "red_flags": ["Could not fully parse health analysis."],
            "positives": [],
            "health_summary": raw_text[:500] if raw_text else "Analysis unavailable.",
        }