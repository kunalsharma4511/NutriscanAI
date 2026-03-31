# utils/error_handler.py
import functools
import traceback
from typing import Optional
from state import NutriScanState


def safe_agent(agent_name: str):
    """
    Decorator that wraps agent node functions with crash protection.
    On exception: logs error to state pipeline_errors and passes state through.
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(state: NutriScanState) -> NutriScanState:
            try:
                return fn(state)
            except Exception as e:
                errors = list(state.get("pipeline_errors") or [])
                errors.append(
                    f"{agent_name} crashed: {type(e).__name__}: {str(e)}"
                )
                return {**state, "pipeline_errors": errors}
        return wrapper
    return decorator


def validate_image_bytes(image_bytes: Optional[bytes]) -> tuple:
    if not image_bytes:
        return False, "No image data provided."
    if len(image_bytes) < 1000:
        return False, "Image file is too small — may be corrupted."
    jpg = image_bytes[:3] == b'\xff\xd8\xff'
    png = image_bytes[:8] == b'\x89PNG\r\n\x1a\n'
    webp = image_bytes[8:12] == b'WEBP'
    if not (jpg or png or webp):
        return False, "Unsupported format. Use JPEG, PNG, or WebP."
    return True, "Image is valid."


def validate_nutrition_data(nutrition: dict) -> tuple:
    if not nutrition:
        return False, "No nutritional data was extracted."
    key_fields = ["energy_kcal", "protein", "total_fat",
                  "carbohydrates", "sugar", "sodium"]
    filled = sum(1 for f in key_fields if nutrition.get(f) is not None)
    if filled == 0:
        return False, "No nutritional values could be extracted."
    if filled < 2:
        return False, f"Only {filled}/6 key fields found — results may be unreliable."
    return True, f"{filled}/6 key nutritional fields extracted."


def check_pipeline_health(state: NutriScanState) -> dict:
    issues = []
    agent_statuses = {}

    agent_statuses["Agent 1 (Intake)"] = "ok" if state.get("nutrition_raw") is not None else "failed"
    agent_statuses["Agent 2 (Lookup)"] = "ok" if state.get("nutrition_enriched") is not None else "failed"
    agent_statuses["Agent 3 (Health)"] = "ok" if state.get("health_score") is not None else "failed"

    if state.get("personalized_score") is not None:
        agent_statuses["Agent 4 (Personalisation)"] = "ok"
    elif not any((state.get("user_profile") or {}).values()):
        agent_statuses["Agent 4 (Personalisation)"] = "skipped"
    else:
        agent_statuses["Agent 4 (Personalisation)"] = "failed"

    agent_statuses["Agent 5 (Report)"] = "ok" if state.get("final_report") else "failed"

    conf = state.get("extraction_confidence")
    if conf is not None and conf < 0.4:
        issues.append(
            f"Low extraction confidence ({int(conf*100)}%) — "
            "try a clearer image with better lighting."
        )

    for name, status in agent_statuses.items():
        if status == "failed":
            issues.append(f"{name} did not complete successfully.")

    errors = state.get("pipeline_errors") or []
    issues.extend(errors)

    failed = [k for k, v in agent_statuses.items() if v == "failed"]
    status = "error" if len(failed) >= 2 else ("warning" if issues else "ok")

    return {
        "status":         status,
        "issues":         issues,
        "agent_statuses": agent_statuses,
    }