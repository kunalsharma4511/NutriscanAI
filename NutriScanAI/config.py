# config.py — NutriScan AI v2.0
# LLM Provider: Groq (free tier)

import os
from dotenv import load_dotenv

load_dotenv()

# API Keys
GROQ_API_KEY          = os.getenv("GROQ_API_KEY", "")
GOOGLE_VISION_API_KEY = os.getenv("GOOGLE_CLOUD_VISION_API_KEY", "")

# Groq Model — free tier options:
#   llama-3.1-70b-versatile  (best quality, recommended)
#   llama-3.1-8b-instant     (fastest)
#   mixtral-8x7b-32768       (large context window)
#   gemma2-9b-it             (lightweight)
GROQ_MODEL       = "llama-3.1-8b-instant"
GROQ_MAX_TOKENS  = 1500
GROQ_TEMPERATURE = 0.3

# App Settings
APP_TITLE   = os.getenv("APP_TITLE", "NutriScan AI")
APP_VERSION = os.getenv("APP_VERSION", "2.0")
DEBUG       = os.getenv("DEBUG", "False").lower() == "true"

# OCR Settings
OCR_CONFIDENCE_THRESHOLD    = 50.0
NUTRITION_COMPLETENESS_WARN = 0.4

# Image Settings
MAX_IMAGE_WIDTH = 1200


def validate_config():
    if not GROQ_API_KEY:
        raise EnvironmentError(
            "GROQ_API_KEY is not set.\n"
            "1. Sign up free at https://console.groq.com\n"
            "2. Copy env.example to .env\n"
            "3. Add: GROQ_API_KEY=your_key_here"
        )