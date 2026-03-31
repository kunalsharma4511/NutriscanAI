# utils/nutrition_parser.py
import re
from typing import Optional

# Regex patterns for each nutritional field
# Multiple patterns per field to handle label format variations
PATTERNS = {
    "energy_kcal": [
        r"energy[^\d]*(\d+[\.,]?\d*)\s*kcal",
        r"calories[^\d]*(\d+[\.,]?\d*)",
        r"(\d+[\.,]?\d*)\s*kcal",
    ],
    "energy_kj": [
        r"energy[^\d]*(\d+[\.,]?\d*)\s*kj",
        r"(\d+[\.,]?\d*)\s*kj",
    ],
    "protein": [
        r"protein[^\d]*(\d+[\.,]?\d*)\s*g",
        r"proteins[^\d]*(\d+[\.,]?\d*)\s*g",
    ],
    "total_fat": [
        r"total\s*fat[^\d]*(\d+[\.,]?\d*)\s*g",
        r"fat[^\d]*(\d+[\.,]?\d*)\s*g",
    ],
    "saturated_fat": [
        r"saturated\s*fat[^\d]*(\d+[\.,]?\d*)\s*g",
        r"saturates[^\d]*(\d+[\.,]?\d*)\s*g",
    ],
    "trans_fat": [
        r"trans\s*fat[^\d]*(\d+[\.,]?\d*)\s*g",
        r"trans\s*fatty[^\d]*(\d+[\.,]?\d*)\s*g",
    ],
    "carbohydrates": [
        r"total\s*carbohydrate[^\d]*(\d+[\.,]?\d*)\s*g",
        r"carbohydrate[^\d]*(\d+[\.,]?\d*)\s*g",
        r"carbs[^\d]*(\d+[\.,]?\d*)\s*g",
    ],
    "sugar": [
        r"of\s*which\s*sugar[^\d]*(\d+[\.,]?\d*)\s*g",
        r"total\s*sugar[^\d]*(\d+[\.,]?\d*)\s*g",
        r"sugar[^\d]*(\d+[\.,]?\d*)\s*g",
    ],
    "dietary_fibre": [
        r"dietary\s*fibre[^\d]*(\d+[\.,]?\d*)\s*g",
        r"dietary\s*fiber[^\d]*(\d+[\.,]?\d*)\s*g",
        r"fibre[^\d]*(\d+[\.,]?\d*)\s*g",
    ],
    "sodium": [
        r"sodium[^\d]*(\d+[\.,]?\d*)\s*mg",
        r"salt[^\d]*(\d+[\.,]?\d*)\s*g",
    ],
    "serving_size": [
        r"serving\s*size[^\d]*(\d+[\.,]?\d*)\s*(g|ml|gm)",
        r"per\s*serving[^\d]*(\d+[\.,]?\d*)\s*(g|ml|gm)",
    ],
}


def parse_nutrition_from_text(ocr_text: str) -> dict:
    """
    Parse raw OCR text into a structured nutrition dict.
    Any field not found is set to None.
    Also extracts ingredients list and a best-guess product name.
    """
    text = ocr_text.lower()
    nutrition = {}

    for field, patterns in PATTERNS.items():
        nutrition[field] = _extract_first_match(text, patterns)

    # Normalise European comma decimals → dot decimals
    for key, val in nutrition.items():
        if isinstance(val, str):
            nutrition[key] = val.replace(",", ".")

    # Cast string numbers to float
    for key, val in nutrition.items():
        if val is not None:
            try:
                nutrition[key] = float(val)
            except (ValueError, TypeError):
                pass

    nutrition["ingredients"] = extract_ingredients(ocr_text)
    nutrition["product_name"] = extract_product_name(ocr_text)
    return nutrition


def _extract_first_match(text: str, patterns: list) -> Optional[str]:
    """Try each regex in order; return first captured group or None."""
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def extract_ingredients(ocr_text: str) -> Optional[str]:
    """
    Extract the ingredients block from OCR text.
    Stops at common section-break keywords.
    """
    match = re.search(
        r"ingredients[\s:]+(.{10,500}?)(?:\n\n|allergen|contains|manufactured|\Z)",
        ocr_text,
        re.IGNORECASE | re.DOTALL
    )
    if match:
        return re.sub(r"\s+", " ", match.group(1).strip())
    return None


def extract_product_name(ocr_text: str) -> Optional[str]:
    """
    Best-effort: return the first substantive non-nutritional line
    as a candidate product name.
    """
    lines = [l.strip() for l in ocr_text.split("\n") if l.strip()]
    for line in lines:
        if len(line) > 3 and not line.lower().startswith(
            ("nutrition", "ingredient", "energy", "per ", "serving")
        ):
            return line
    return None


def nutrition_completeness_score(nutrition: dict) -> float:
    """
    Returns 0.0–1.0 based on how many key fields were successfully parsed.
    Used by Agent 1 to flag low-confidence extractions.
    """
    key_fields = ["energy_kcal", "protein", "total_fat",
                  "carbohydrates", "sugar", "sodium"]
    filled = sum(1 for f in key_fields if nutrition.get(f) is not None)
    return round(filled / len(key_fields), 2)