# utils/ocr_reader.py
import pytesseract
# Replace with your actual installation path if different
pytesseract.pytesseract.tesseract_cmd = r'C:\Users\KUNAL\AppData\Local\Programs\Tesseract-OCR\tesseract.exe'

from PIL import Image
from utils.image_utils import preprocess_for_ocr

# --psm 6  = uniform block of text (good for nutrition tables)
# --oem 3  = LSTM neural net engine (most accurate)
TESS_CONFIG = "--psm 6 --oem 3"


def extract_text_from_label(image: Image.Image) -> str:
    """Run OCR with preprocessing. Best for most label types."""
    processed = preprocess_for_ocr(image)
    return pytesseract.image_to_string(processed, config=TESS_CONFIG).strip()


def extract_text_raw(image: Image.Image) -> str:
    """Run OCR without preprocessing. Fallback for high-quality images."""
    return pytesseract.image_to_string(image, config=TESS_CONFIG).strip()


def extract_text_best(image: Image.Image) -> str:
    """
    Run both preprocessed and raw OCR.
    Return whichever produces more text content.
    """
    preprocessed_text = extract_text_from_label(image)
    raw_text = extract_text_raw(image)
    return preprocessed_text if len(preprocessed_text) >= len(raw_text) else raw_text


def is_nutrition_label(text: str) -> bool:
    """
    Heuristic: check if OCR output looks like a nutritional label.
    Matches 3+ keywords from a list of common label terms (FSSAI + international).
    """
    keywords = [
        "nutrition", "nutritional", "energy", "calories", "protein",
        "carbohydrate", "fat", "sodium", "sugar", "fibre", "fiber",
        "serving", "per 100g", "per 100 g", "daily value", "fssai",
        "ingredients", "contains", "trans fat", "saturated"
    ]
    text_lower = text.lower()
    matched = sum(1 for kw in keywords if kw in text_lower)
    return matched >= 3


def get_ocr_confidence(image: Image.Image) -> float:
    """
    Returns Tesseract's mean word-level confidence score (0–100).
    Scores below 50 suggest a poor image or non-label content.
    """
    processed = preprocess_for_ocr(image)
    data = pytesseract.image_to_data(
        processed,
        config=TESS_CONFIG,
        output_type=pytesseract.Output.DICT
    )
    confidences = [
        int(c) for c in data["conf"]
        if str(c).lstrip("-").isdigit() and int(c) >= 0
    ]
    if not confidences:
        return 0.0
    return round(sum(confidences) / len(confidences), 2)