# agents/personalization_agent.py
# Agent 4 — Personalization Agent
#
# Responsibilities:
# - Read the user's health profile from state (age, conditions, goals)
# - Re-evaluate the product specifically against that profile using Claude
# - Adjust the health score and consumption frequency
# - Generate condition-specific warnings and personalised tips
# - If no profile provided, this node is skipped via graph conditional routing

import json
from groq import Groq
from state import NutriScanState
from config import GROQ_API_KEY, GROQ_MODEL, GROQ_MAX_TOKENS, GROQ_TEMPERATURE
from utils.error_handler import safe_agent

client = Groq(api_key=GROQ_API_KEY)


@safe_agent("Agent 4 (Personalisation)")
def run_personalization_agent(state: NutriScanState) -> NutriScanState:
    """
    LangGraph node function for Agent 4.
    Only reached if user_profile is non-empty (enforced by graph conditional).
    """
    errors = list(state.get("pipeline_errors") or [])
    user_profile = state.get("user_profile", {})
    nutrition = state.get("nutrition_enriched") or state.get("nutrition_raw") or {}

    # Safety check — should not be reached without a profile, but guard anyway
    if not user_profile or not any(user_profile.values()):
        return {
            **state,
            "personalized_score":     state.get("health_score"),
            "personalized_frequency": state.get("consumption_frequency"),
            "personalized_warnings":  [],
            "personalized_tips":      [],
            "personalization_note":   "No health profile provided — showing general analysis.",
        }

    # ── Build prompt ──────────────────────────────────────────────────────────
    nutrition_summary = _format_nutrition_summary(nutrition, state)
    profile_summary   = _format_profile_summary(user_profile)
    general_analysis  = _format_general_analysis(state)
    prompt = _build_personalization_prompt(nutrition_summary, profile_summary, general_analysis)

    # ── Call Claude ───────────────────────────────────────────────────────────
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
        errors.append(f"Agent 4: Claude API error — {str(e)}")
        return {
            **state,
            "personalized_score":     state.get("health_score"),
            "personalized_frequency": state.get("consumption_frequency"),
            "personalized_warnings":  ["Personalisation could not be completed."],
            "personalized_tips":      [],
            "personalization_note":   "Personalisation failed — showing general analysis.",
            "pipeline_errors":        errors,
        }

    # ── Return updated state ──────────────────────────────────────────────────
    return {
        **state,
        "personalized_score":     parsed.get("personalized_score"),
        "personalized_frequency": parsed.get("personalized_frequency"),
        "personalized_warnings":  parsed.get("personalized_warnings", []),
        "personalized_tips":      parsed.get("personalized_tips", []),
        "personalization_note":   parsed.get("personalization_note", ""),
        "pipeline_errors":        errors,
    }


# ── Prompt builder ────────────────────────────────────────────────────────────

def _build_personalization_prompt(
    nutrition_summary: str,
    profile_summary: str,
    general_analysis: str
) -> str:
    return f"""You are a clinical dietitian providing personalised food safety advice.

A general health analysis of a food product has already been completed.
Your task is to RE-EVALUATE this product specifically for a user with the health profile below.

PRODUCT NUTRITION DATA:
{nutrition_summary}

GENERAL HEALTH ANALYSIS (already completed):
{general_analysis}

USER HEALTH PROFILE:
{profile_summary}

Based on this specific user's conditions, age, and goals, provide a personalised assessment.
Consider interactions between the product's nutritional content and the user's health conditions.
For example: high sugar is especially concerning for diabetics; high sodium for hypertensive patients;
high saturated fat for cardiovascular conditions; gluten for celiac disease, and so on.

Respond ONLY in the following JSON format with no preamble, no markdown, and no additional text:

{{
  "personalized_score": <adjusted score from 1.0 to 10.0, one decimal place>,
  "personalized_frequency": "<one of: daily | a few times a week | weekly | occasional (once or twice a month) | avoid>",
  "personalized_warnings": [
    "<specific warning relevant to user's condition, e.g. 'High sugar content (18g) — not suitable for Type 2 diabetes management'>",
    "<another condition-specific warning if applicable>"
  ],
  "personalized_tips": [
    "<actionable tip for this user, e.g. 'If consuming, pair with high-fibre foods to slow glucose absorption'>",
    "<another tip>"
  ],
  "personalization_note": "<1-2 sentence explanation of how the user's profile changed the assessment>"
}}

If the user's conditions don't significantly change the general assessment, reflect that honestly.
Keep warnings and tips specific and evidence-based."""


# ── Helpers ───────────────────────────────────────────────────────────────────

def _format_nutrition_summary(nutrition: dict, state: NutriScanState) -> str:
    lines = []
    if nutrition.get("product_name"):
        lines.append(f"Product: {nutrition['product_name']}")
    fields = [
        ("energy_kcal", "Energy (kcal)"), ("protein", "Protein (g)"),
        ("total_fat", "Total Fat (g)"), ("saturated_fat", "Saturated Fat (g)"),
        ("trans_fat", "Trans Fat (g)"), ("carbohydrates", "Carbohydrates (g)"),
        ("sugar", "Sugar (g)"), ("dietary_fibre", "Fibre (g)"),
        ("sodium", "Sodium (mg)"),
    ]
    for key, label in fields:
        val = nutrition.get(key)
        if val is not None:
            lines.append(f"  {label}: {val}")
    if state.get("allergens"):
        lines.append(f"Allergens: {', '.join(state['allergens'])}")
    if state.get("additives_flagged"):
        lines.append(f"Flagged additives: {', '.join(state['additives_flagged'])}")
    return "\n".join(lines)


def _format_profile_summary(profile: dict) -> str:
    lines = []
    if profile.get("age"):
        lines.append(f"Age: {profile['age']}")
    if profile.get("gender"):
        lines.append(f"Gender: {profile['gender']}")
    if profile.get("conditions"):
        conditions = profile["conditions"]
        if isinstance(conditions, list):
            lines.append(f"Health conditions: {', '.join(conditions)}")
        else:
            lines.append(f"Health conditions: {conditions}")
    if profile.get("dietary_preferences"):
        prefs = profile["dietary_preferences"]
        if isinstance(prefs, list):
            lines.append(f"Dietary preferences/restrictions: {', '.join(prefs)}")
        else:
            lines.append(f"Dietary preferences/restrictions: {prefs}")
    if profile.get("fitness_goal"):
        lines.append(f"Fitness/health goal: {profile['fitness_goal']}")
    return "\n".join(lines) if lines else "No specific profile details provided."


def _format_general_analysis(state: NutriScanState) -> str:
    lines = []
    if state.get("health_score") is not None:
        lines.append(f"General health score: {state['health_score']}/10")
    if state.get("consumption_frequency"):
        lines.append(f"Recommended frequency: {state['consumption_frequency']}")
    if state.get("red_flags"):
        lines.append(f"Red flags: {'; '.join(state['red_flags'])}")
    if state.get("positives"):
        lines.append(f"Positives: {'; '.join(state['positives'])}")
    if state.get("health_summary"):
        lines.append(f"Summary: {state['health_summary']}")
    return "\n".join(lines)


def _parse_response(raw_text: str) -> dict:
    clean = raw_text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    try:
        data = json.loads(clean)
        score = float(data.get("personalized_score", 5.0))
        data["personalized_score"] = round(max(1.0, min(10.0, score)), 1)
        data["personalized_warnings"] = data.get("personalized_warnings") or []
        data["personalized_tips"]     = data.get("personalized_tips") or []
        return data
    except (json.JSONDecodeError, ValueError):
        return {
            "personalized_score":     5.0,
            "personalized_frequency": "weekly",
            "personalized_warnings":  ["Could not parse personalised analysis."],
            "personalized_tips":      [],
            "personalization_note":   raw_text[:300] if raw_text else "",
        }