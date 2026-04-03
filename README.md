# NutriScan AI v2.0

Intelligent Food Label & Barcode Nutrition Analyzer powered by a LangGraph multi-agent pipeline.

## Setup

1. Clone the repo and navigate into it
2. Install dependencies:
   pip install -r requirements.txt
3. Copy env.example to .env and add your API keys
4. Install Tesseract OCR on your system:
   - Ubuntu: sudo apt install tesseract-ocr
   - macOS:  brew install tesseract
5. Run the app:
   streamlit run app.py

## Project Structure

nutriscan/
├── app.py                        # Streamlit UI entry point (Phase 5)
├── config.py                     # App config & env loader (Phase 6)
├── state.py                      # LangGraph shared state schema (Phase 3)
├── graph.py                      # LangGraph pipeline definition (Phase 3)
├── agents/
│   ├── intake_agent.py           # Agent 1 — Barcode/OCR extraction (Phase 4)
│   ├── lookup_agent.py           # Agent 2 — Open Food Facts lookup (Phase 4)
│   ├── health_agent.py           # Agent 3 — Health scoring (Phase 4)
│   ├── personalization_agent.py  # Agent 4 — User profile tailoring (Phase 4)
│   └── report_agent.py           # Agent 5 — Report generation (Phase 4)
├── utils/
│   ├── image_utils.py            # Image preprocessing helpers (Phase 2)
│   ├── barcode_reader.py         # pyzbar + OpenCV barcode logic (Phase 2)
│   ├── ocr_reader.py             # pytesseract OCR wrapper (Phase 2)
│   └── nutrition_parser.py       # Raw text → nutrition dict parser (Phase 2)
├── exports/
│   └── report_exporter.py        # DOCX / PDF report export (Phase 5)
├── requirements.txt
└── env.example 
