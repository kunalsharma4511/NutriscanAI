# utils/goupc_client.py
# Go-UPC Barcode Lookup Client
# Docs: https://go-upc.com/docs
#
# Authentication: Bearer token (API key only)
# Endpoint: GET https://go-upc.com/api/v1/code/{barcode}
# Note: Go-UPC returns product name, brand, image, description
#       but NOT detailed nutrition facts — those still come from OFF/LLM

import os
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

API_KEY  = os.getenv("GOUPC_API_KEY")
BASE_URL = "https://go-upc.com/api/v1/code"

# ── Local cache to preserve your 150 req/month ───────────────────────────────
CACHE_FILE = Path("goupc_cache.json")


def _load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_cache(cache: dict):
    try:
        CACHE_FILE.write_text(json.dumps(cache, indent=2))
    except Exception:
        pass


def fetch_product_by_barcode(barcode: str) -> dict | None:
    """
    Lookup a product by EAN/UPC barcode via Go-UPC.
    Returns a dict with product_name, brands, image_url, description — or None.
    Results are cached locally so the same barcode never uses 2 API calls.
    """
    # ── Check cache first ─────────────────────────────────────────────────────
    cache = _load_cache()
    if barcode in cache:
        print(f"[GoUPC] Cache hit for {barcode}")
        return cache[barcode]

    # ── Call API ──────────────────────────────────────────────────────────────
    try:
        r = requests.get(
            f"{BASE_URL}/{barcode}",
            headers={"Authorization": f"Bearer {API_KEY}"},
            timeout=10,
        )

        if r.status_code == 404:
            print(f"[GoUPC] Barcode {barcode} not found.")
            return None

        if r.status_code == 429:
            print("[GoUPC] Rate limit hit — too many requests.")
            return None

        if r.status_code != 200:
            print(f"[GoUPC] HTTP {r.status_code}: {r.text}")
            return None

        data = r.json()
        product = data.get("product")
        if not product:
            return None

        result = {
            "product_name": product.get("name"),
            "brands":       product.get("brand"),
            "description":  product.get("description"),
            "image_url":    product.get("imageUrl"),
            "category":     product.get("category"),
            "region":       product.get("region"),
        }

        # Save to cache
        cache[barcode] = result
        _save_cache(cache)
        print(f"[GoUPC] Found: {result['product_name']}")
        return result

    except Exception as e:
        print(f"[GoUPC] Error: {e}")
        return None