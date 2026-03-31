# agents/lookup_agent.py
# Agent 2 — Nutrition Lookup Agent
#
# Lookup chain:
#   1. Go-UPC (cached, 150/month) — product name, brand, image
#   2. LLM fallback — estimate nutrition from product name

import json
import re
import openfoodfacts
from groq import Groq
from state import NutriScanState
from config import GROQ_API_KEY, GROQ_MODEL, GROQ_TEMPERATURE
from utils.goupc_client import fetch_product_by_barcode as goupc_fetch
from utils.error_handler import safe_agent

client = Groq(api_key=GROQ_API_KEY)

CONCERNING_ADDITIVE_PREFIXES = (
    "e102", "e104", "e110", "e122", "e124", "e129",
    "e211", "e212", "e213", "e214", "e215",
    "e249", "e250", "e251", "e252",
    "e320", "e321",
    "e621",
    "e951", "e950", "e955", "e954",
)

KEY_NUTRITION_FIELDS = [
    "energy_kcal", "protein", "total_fat",
    "carbohydrates", "sugar", "sodium"
]


def _repair_json(text: str) -> dict:
    """
    Robustly parse JSON that may be truncated by token limits.
    Tries progressively more aggressive repair strategies.
    Returns a dict or empty dict on total failure.
    """
    # Step 1 — strip markdown fences
    text = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()

    # Step 2 — try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Step 3 — truncated string fix: find last complete key-value pair
    # Cut everything after the last comma that ends a complete value
    try:
        # Remove the incomplete last field and close the JSON object
        truncated = re.sub(r',\s*"[^"]*":\s*[^,}\]]*$', '', text)
        if not truncated.endswith('}'):
            truncated += '}'
        return json.loads(truncated)
    except (json.JSONDecodeError, Exception):
        pass

    # Step 4 — try common closings
    for closing in ['"}', '"}}', '"}]', '}}', '}']:
        try:
            return json.loads(text + closing)
        except json.JSONDecodeError:
            continue

    # Step 5 — extract whatever key-value pairs we can with regex
    result = {}
    # Extract numeric fields
    for field in ["energy_kcal", "protein", "total_fat", "saturated_fat",
                  "trans_fat", "carbohydrates", "sugar", "dietary_fibre", "sodium"]:
        match = re.search(rf'"{field}"\s*:\s*(\d+\.?\d*)', text)
        if match:
            try:
                result[field] = float(match.group(1))
            except ValueError:
                pass
    # Extract product_name string
    name_match = re.search(r'"product_name"\s*:\s*"([^"]+)"', text)
    if name_match:
        result["product_name"] = name_match.group(1)

    return result if result else {}


def _llm_nutrition_fallback(product_name: str, barcode: str) -> dict:
    """
    Ask Groq to estimate nutrition for a named product.
    Returns null for uncertain fields. Uses repair logic for truncated JSON.
    """
    prompt = f"""You are a nutrition database assistant.

Product: {product_name}
Barcode: {barcode}

Provide estimated nutritional values per 100g based on your knowledge of this exact product.

STRICT RULES:
- Only provide values you are highly confident about from verified nutrition labels
- If even slightly unsure about a specific numeric value, set it to null
- NEVER guess sodium, sugar, or fat — return null if not certain
- Keep ingredients string SHORT (max 100 chars) to avoid truncation
- Return ONLY valid JSON, no markdown, no preamble

JSON structure:
{{
  "product_name": "{product_name}",
  "energy_kcal": <number or null>,
  "protein": <number or null>,
  "total_fat": <number or null>,
  "saturated_fat": <number or null>,
  "trans_fat": <number or null>,
  "carbohydrates": <number or null>,
  "sugar": <number or null>,
  "dietary_fibre": <number or null>,
  "sodium": <number or null>,
  "ingredients": <string max 100 chars or null>,
  "llm_estimated": true
}}"""

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            max_tokens=800,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a nutrition database. Return valid JSON only. "
                        "Never guess numeric values — use null if uncertain. "
                        "Keep all string values under 100 characters."
                    )
                },
                {"role": "user", "content": prompt}
            ]
        )
        raw = response.choices[0].message.content.strip()
        result = _repair_json(raw)

        if result:
            result["llm_estimated"] = True
            return result
        else:
            return {"llm_estimated": True, "llm_error": "Could not parse response"}

    except Exception as e:
        return {"llm_estimated": True, "llm_error": str(e)}


@safe_agent("Agent 2 (Lookup)")
def run_lookup_agent(state: NutriScanState) -> NutriScanState:
    errors         = list(state.get("pipeline_errors") or [])
    nutrition_raw  = state.get("nutrition_raw", {})
    barcode_number = state.get("barcode_number")

    nutrition_enriched = dict(nutrition_raw)
    product_image_url  = None
    nova_group         = None
    nutri_score        = None
    additives_flagged  = []
    allergens          = []
    lookup_note        = ""
    llm_estimated      = False

    # ── Barcode path ──────────────────────────────────────────────────────────
    if barcode_number:

        # ── Step 1: Go-UPC — product name, brand, image ───────────────────────
        try:
            goupc_data = goupc_fetch(barcode_number)

            if goupc_data and goupc_data.get("product_name"):
                nutrition_enriched["product_name"] = goupc_data["product_name"]
                nutrition_enriched["brands"]        = goupc_data.get("brands")
                product_image_url                   = goupc_data.get("image_url")
                lookup_note = (
                    f"Product identified via Go-UPC: "
                    f"{goupc_data['product_name']} "
                    f"by {goupc_data.get('brands', 'Unknown brand')}."
                )
            else:
                errors.append(f"Agent 2: Barcode {barcode_number} not found on Go-UPC.")
                lookup_note = f"Barcode {barcode_number} not found on Go-UPC."

        except Exception as e:
            errors.append(f"Agent 2: Go-UPC error — {str(e)}")
            lookup_note = "Go-UPC lookup failed."

        # ── Step 2: LLM — estimate nutrition from product name ────────────────
        product_name = nutrition_enriched.get("product_name")

        if product_name:
            try:
                llm_data = _llm_nutrition_fallback(product_name, barcode_number)

                if not llm_data.get("llm_error"):
                    for key, val in llm_data.items():
                        if val is not None and key not in ("llm_estimated", "llm_error"):
                            nutrition_enriched[key] = val
                    llm_estimated = True
                    lookup_note += " Nutrition values are AI-estimated — verify with product label."
                else:
                    errors.append(f"Agent 2: LLM fallback failed — {llm_data['llm_error']}")

            except Exception as e:
                errors.append(f"Agent 2: LLM error — {str(e)}")
        else:
            errors.append("Agent 2: No product name — skipping LLM nutrition estimation.")

    # ── OCR path ──────────────────────────────────────────────────────────────
    else:
        lookup_note = "No barcode — enrichment based on OCR-parsed data only."
        ingredients_text = nutrition_enriched.get("ingredients", "") or ""
        additives_flagged = _flag_additives_from_text(ingredients_text)

    return {
        **state,
        "nutrition_enriched": nutrition_enriched,
        "product_image_url":  product_image_url,
        "nova_group":         nova_group,
        "nutri_score":        nutri_score,
        "additives_flagged":  additives_flagged,
        "allergens":          allergens,
        "lookup_note":        lookup_note,
        "llm_estimated":      llm_estimated,
        "pipeline_errors":    errors,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _safe_float(value) -> float | None:
    try:
        return float(value) if value is not None else None
    except (ValueError, TypeError):
        return None


def _flag_additives(additive_tags: list) -> list:
    flagged = []
    for tag in additive_tags:
        code = tag.lower().replace("en:", "").strip()
        if any(code.startswith(prefix) for prefix in CONCERNING_ADDITIVE_PREFIXES):
            flagged.append(code.upper())
    return flagged


def _flag_additives_from_text(ingredients_text: str) -> list:
    found = re.findall(r"\b(e\d{3,4}[a-z]?)\b", ingredients_text.lower())
    flagged = [
        code.upper() for code in found
        if any(code.startswith(p) for p in CONCERNING_ADDITIVE_PREFIXES)
    ]
    return list(set(flagged))