# utils/food_facts_client.py
# Wrapper around the Open Food Facts SDK

from openfoodfacts import API, APIVersion, Country, Environment, Flavor


def get_off_api() -> API:
    return API(
        user_agent="NutriScan/1.0",
        country=Country["in"],
        flavor=Flavor.off,
        version=APIVersion.v2,
        environment=Environment.org,
    )


def fetch_product_by_barcode(barcode: str) -> dict | None:
    """
    Fetch full product data from Open Food Facts by barcode.
    Returns the product dict, or None if not found.
    """
    try:
        api = get_off_api()
        result = api.product.get(barcode)
        if result and result.get("status") == 1:
            return result.get("product", {})
        return None
    except Exception as e:
        print(f"[FoodFacts] Error fetching barcode {barcode}: {e}")
        return None


def extract_nutrition_from_product(product: dict) -> dict:
    """
    Pull the fields your pipeline needs out of the raw OFF product dict.
    """
    nutriments = product.get("nutriments", {})

    return {
        "product_name":   product.get("product_name") or product.get("product_name_en"),
        "brands":         product.get("brands"),
        "ingredients":    product.get("ingredients_text"),
        "energy_kcal":    nutriments.get("energy-kcal_100g"),
        "fat":            nutriments.get("fat_100g"),
        "saturated_fat":  nutriments.get("saturated-fat_100g"),
        "carbohydrates":  nutriments.get("carbohydrates_100g"),
        "sugars":         nutriments.get("sugars_100g"),
        "fiber":          nutriments.get("fiber_100g"),
        "proteins":       nutriments.get("proteins_100g"),
        "salt":           nutriments.get("salt_100g"),
        "sodium":         nutriments.get("sodium_100g"),
        "nutriscore":     product.get("nutriscore_grade"),
        "nova_group":     product.get("nova_group"),
        "allergens":      product.get("allergens"),
        "barcode":        product.get("code"),
    }