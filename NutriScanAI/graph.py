# graph.py
# LangGraph pipeline definition for NutriScan AI v2.0
#
# Defines the StateGraph, registers all 5 agent nodes,
# and connects them with sequential edges + one conditional branch
# (skip personalisation if no user profile is provided).

from langgraph.graph import StateGraph, END
from state import NutriScanState

# Agent node functions (each built in Phase 4)
from agents.intake_agent import run_intake_agent
from agents.lookup_agent import run_lookup_agent
from agents.health_agent import run_health_agent
from agents.personalization_agent import run_personalization_agent
from agents.report_agent import run_report_agent


# ── Node names ────────────────────────────────────────────────────────────────

NODE_INTAKE          = "intake_extraction"
NODE_LOOKUP          = "nutrition_lookup"
NODE_HEALTH          = "health_analysis"
NODE_PERSONALIZATION = "personalization"
NODE_REPORT          = "report_generation"


# ── Conditional routing ───────────────────────────────────────────────────────

def should_personalize(state: NutriScanState) -> str:
    """
    Route to the Personalisation Agent only if the user provided a health profile.
    Otherwise jump directly to Report Generation.

    Returns the name of the next node to execute.
    """
    profile = state.get("user_profile")
    if profile and any(profile.values()):
        return NODE_PERSONALIZATION
    return NODE_REPORT


# ── Graph builder ─────────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    """
    Construct and compile the NutriScan LangGraph pipeline.

    Pipeline flow:
        intake_extraction
            → nutrition_lookup
                → health_analysis
                    → [conditional]
                        → personalization → report_generation → END
                        → report_generation → END
    """
    graph = StateGraph(NutriScanState)

    # Register agent nodes
    graph.add_node(NODE_INTAKE,          run_intake_agent)
    graph.add_node(NODE_LOOKUP,          run_lookup_agent)
    graph.add_node(NODE_HEALTH,          run_health_agent)
    graph.add_node(NODE_PERSONALIZATION, run_personalization_agent)
    graph.add_node(NODE_REPORT,          run_report_agent)

    # Set the entry point
    graph.set_entry_point(NODE_INTAKE)

    # Sequential edges: intake → lookup → health
    graph.add_edge(NODE_INTAKE, NODE_LOOKUP)
    graph.add_edge(NODE_LOOKUP, NODE_HEALTH)

    # Conditional branch after health analysis
    graph.add_conditional_edges(
        NODE_HEALTH,
        should_personalize,
        {
            NODE_PERSONALIZATION: NODE_PERSONALIZATION,
            NODE_REPORT:          NODE_REPORT,
        }
    )

    # Personalisation always leads to report generation
    graph.add_edge(NODE_PERSONALIZATION, NODE_REPORT)

    # Report generation is the terminal node
    graph.add_edge(NODE_REPORT, END)

    return graph.compile()


# ── Compiled graph instance (imported by app.py) ──────────────────────────────

nutriscan_graph = build_graph()


# ── Runner helper ─────────────────────────────────────────────────────────────

def run_pipeline(
    image_bytes: bytes = None,
    user_profile: dict = None,
    manual_barcode: str = None
) -> NutriScanState:
    """
    Entry point called by the Streamlit UI.

    Args:
        image_bytes:     Raw bytes from webcam capture or uploaded image file.
        user_profile:    Dict from the sidebar health form, or None.
        manual_barcode:  Barcode number typed manually by the user (bypasses image scanning).

    Returns:
        The final NutriScanState after all agents have run.
    """
    from datetime import datetime

    initial_state: NutriScanState = {
        "raw_image_bytes":  image_bytes,
        "user_profile":     user_profile or {},
        "pipeline_errors":  [],
        "pipeline_timestamp": datetime.utcnow().isoformat(),
    }

    # If a manual barcode was provided, inject it directly into state.
    # intake_agent will detect it and skip image processing entirely.
    if manual_barcode and manual_barcode.isdigit() and 8 <= len(manual_barcode) <= 14:
        initial_state["barcode_number"] = manual_barcode
        initial_state["extraction_note"] = f"Barcode entered manually by user: {manual_barcode}"
        initial_state["extraction_confidence"] = 1.0
        initial_state["nutrition_raw"] = {"barcode": manual_barcode, "product_name": None}

    final_state = nutriscan_graph.invoke(initial_state)
    return final_state