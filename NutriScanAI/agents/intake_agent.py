# agents/intake_agent.py
# Agent 1 — Intake & Extraction Agent
#
# Responsibilities:
# - Load and preprocess the raw image
# - Attempt barcode detection (pyzbar + OpenCV, 4-strategy fallback)
# - If no barcode → run OCR on the label image
# - Parse OCR text into a structured nutrition dict
# - Populate extraction_confidence and extraction_note
# - Pass enriched state to Agent 2

from state import NutriScanState
from utils.image_utils import load_image_from_bytes, resize_image
from utils.barcode_reader import decode_barcode, get_barcode_type, is_valid_food_barcode
from utils.ocr_reader import extract_text_best, is_nutrition_label, get_ocr_confidence
from utils.nutrition_parser import parse_nutrition_from_text, nutrition_completeness_score
from utils.error_handler import safe_agent, validate_image_bytes


@safe_agent("Agent 1 (Intake)")
def run_intake_agent(state: NutriScanState) -> NutriScanState:
    """
    LangGraph node function for Agent 1.
    Receives state, processes the image, returns updated state.
    """
    errors = list(state.get("pipeline_errors") or [])

    # ── Shortcut: manual barcode already in state — skip image processing ────
    if state.get("barcode_number") and state.get("nutrition_raw") is not None:
        return {**state, "pipeline_errors": errors}

    # ── Step 1: Load image ────────────────────────────────────────────────────
    raw_bytes = state.get("raw_image_bytes")
    if not raw_bytes:
        errors.append("Agent 1: No image bytes found in state.")
        return {**state, "pipeline_errors": errors, "extraction_note": "No image provided."}

    try:
        image = load_image_from_bytes(raw_bytes)
        image = resize_image(image)
    except Exception as e:
        errors.append(f"Agent 1: Failed to load image — {str(e)}")
        return {**state, "pipeline_errors": errors, "extraction_note": "Image load failed."}

    # ── Step 2: Attempt barcode detection ─────────────────────────────────────
    barcode_number = None
    barcode_type = None
    ocr_text = None
    ocr_confidence = None
    nutrition_raw = {}
    extraction_note = ""

    try:
        barcode_number = decode_barcode(image)
    except Exception as e:
        errors.append(f"Agent 1: Barcode detection error — {str(e)}")

    if barcode_number and is_valid_food_barcode(barcode_number):
        barcode_type = get_barcode_type(image)
        extraction_note = (
            f"Barcode detected ({barcode_type}): {barcode_number}. "
            f"Nutrition data will be fetched from Open Food Facts."
        )
        # nutrition_raw stays minimal — Agent 2 will populate from API
        nutrition_raw = {"product_name": None, "barcode": barcode_number}

    else:
        # ── Step 3: OCR fallback ─────────────────────────────────────────────
        barcode_number = None
        try:
            ocr_text = extract_text_best(image)
            ocr_confidence = get_ocr_confidence(image)
        except Exception as e:
            errors.append(f"Agent 1: OCR error — {str(e)}")
            ocr_text = ""
            ocr_confidence = 0.0

        if not ocr_text or not is_nutrition_label(ocr_text):
            extraction_note = (
                "No barcode found and OCR did not detect a recognisable "
                "nutrition label. Please try a clearer image."
            )
            errors.append("Agent 1: Could not extract usable data from image.")
        else:
            # ── Step 4: Parse OCR text into structured nutrition dict ─────────
            try:
                nutrition_raw = parse_nutrition_from_text(ocr_text)
            except Exception as e:
                errors.append(f"Agent 1: Nutrition parsing error — {str(e)}")
                nutrition_raw = {}

            extraction_note = (
                f"No barcode found. OCR fallback used "
                f"(confidence: {ocr_confidence:.1f}/100)."
            )

    # ── Step 5: Score extraction completeness ────────────────────────────────
    extraction_confidence = nutrition_completeness_score(nutrition_raw)

    if extraction_confidence < 0.4 and not barcode_number:
        extraction_note += (
            f" Warning: only {int(extraction_confidence * 100)}% of key "
            f"nutritional fields were parsed. Results may be incomplete."
        )

    # ── Return updated state ──────────────────────────────────────────────────
    return {
        **state,
        "barcode_number":        barcode_number,
        "barcode_type":          barcode_type,
        "ocr_text":              ocr_text,
        "ocr_confidence":        ocr_confidence,
        "nutrition_raw":         nutrition_raw,
        "extraction_confidence": extraction_confidence,
        "extraction_note":       extraction_note,
        "pipeline_errors":       errors,
    }