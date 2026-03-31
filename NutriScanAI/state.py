# state.py
# LangGraph shared state schema for NutriScan AI v2.0
#
# This TypedDict flows through every agent node in the pipeline.
# Each agent reads the fields it needs and writes its own output fields.
# Fields are Optional so the graph can be partially populated at each step.

from typing import Optional, TypedDict


class NutriScanState(TypedDict, total=False):

    # ── Agent 1: Intake & Extraction ─────────────────────────────────────────

    # Raw image bytes from Streamlit (webcam or upload)
    raw_image_bytes: Optional[bytes]

    # Decoded barcode string if found (e.g. "8901030868702")
    # None if no barcode was detected → triggers OCR path
    barcode_number: Optional[str]

    # Type of barcode detected (e.g. "EAN13", "QRCODE")
    barcode_type: Optional[str]

    # Raw text extracted by OCR (populated when no barcode found)
    ocr_text: Optional[str]

    # Tesseract confidence score for the OCR pass (0–100)
    ocr_confidence: Optional[float]

    # Structured nutrition dict parsed from OCR text or barcode lookup
    # Keys: energy_kcal, protein, total_fat, saturated_fat, trans_fat,
    #       carbohydrates, sugar, dietary_fibre, sodium, serving_size,
    #       ingredients, product_name
    nutrition_raw: Optional[dict]

    # Completeness score of nutrition_raw (0.0–1.0)
    # Low scores trigger a warning in the UI
    extraction_confidence: Optional[float]

    # Human-readable note from Agent 1 (e.g. "Barcode found", "OCR fallback used")
    extraction_note: Optional[str]

    # ── Agent 2: Nutrition Lookup ─────────────────────────────────────────────

    # Merged and enriched nutrition dict (API data + OCR, API takes priority)
    nutrition_enriched: Optional[dict]

    # Product image URL from Open Food Facts (if available)
    product_image_url: Optional[str]

    # NOVA group classification (1=unprocessed, 4=ultra-processed)
    nova_group: Optional[int]

    # Nutri-Score letter grade from Open Food Facts (a–e)
    nutri_score: Optional[str]

    # List of flagged additives/preservatives found in ingredients
    additives_flagged: Optional[list]

    # List of detected allergens
    allergens: Optional[list]

    # Human-readable note from Agent 2
    lookup_note: Optional[str]

    # ── Agent 3: Health Analysis ──────────────────────────────────────────────

    # General health score out of 10 (product-level, not personalised)
    health_score: Optional[float]

    # Consumption frequency recommendation
    # Values: "daily" | "a few times a week" | "weekly" | "occasional" | "avoid"
    consumption_frequency: Optional[str]

    # List of health red flags (e.g. "High sodium: 45% DV per serving")
    red_flags: Optional[list]

    # List of nutritional positives (e.g. "Good source of dietary fibre")
    positives: Optional[list]

    # Plain-English product-level summary from Claude
    health_summary: Optional[str]

    # ── Agent 4: Personalisation ──────────────────────────────────────────────

    # User health profile collected from the Streamlit sidebar
    # Keys: age, gender, conditions (list), dietary_preferences (list), fitness_goal
    user_profile: Optional[dict]

    # Adjusted health score factoring in the user's health profile
    personalized_score: Optional[float]

    # Adjusted frequency recommendation based on user profile
    personalized_frequency: Optional[str]

    # Condition-specific warnings (e.g. "High sugar — not suitable for diabetics")
    personalized_warnings: Optional[list]

    # Personalised tips tailored to the user's goals/conditions
    personalized_tips: Optional[list]

    # Note if personalisation was skipped (no profile provided)
    personalization_note: Optional[str]

    # ── Agent 5: Report Generation ────────────────────────────────────────────

    # Full formatted plain-text health report (displayed in Streamlit)
    final_report: Optional[str]

    # Structured report dict for UI rendering (scores, sections, badges)
    report_data: Optional[dict]

    # ── Pipeline Metadata ─────────────────────────────────────────────────────

    # Timestamp of when the pipeline was triggered
    pipeline_timestamp: Optional[str]

    # Any error messages collected during the run (non-fatal)
    pipeline_errors: Optional[list]