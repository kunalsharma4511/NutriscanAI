# utils/barcode_reader.py
# Barcode detection using zxingcpp.
# Install: pip install zxing-cpp
#
# Key fixes applied based on diagnostic testing:
# 1. Always convert RGBA → RGB (zxingcpp fails silently on RGBA)
# 2. Always add padding (quiet zone fix for tightly cropped barcodes)
# 3. Try multiple scales with padding — 2x is the sweet spot

import zxingcpp
from PIL import Image, ImageEnhance, ImageOps
from typing import Optional


def decode_barcode(image: Image.Image) -> Optional[str]:
    """
    Detect and decode a barcode from a PIL Image.
    Returns a valid food barcode string (8-14 digits), or None.
    """
    # CRITICAL: convert RGBA/P/other modes to RGB first
    # zxingcpp silently returns empty results on RGBA images
    image = _to_rgb(image)

    # Attempt 1 — 2x upscale + padding (fastest reliable path)
    up2 = image.resize((image.width * 2, image.height * 2), Image.LANCZOS)
    result = _try_decode(ImageOps.expand(up2, border=60, fill="white"))
    if result:
        return result

    # Attempt 2 — 2x greyscale + padding
    up2_grey = ImageOps.expand(up2.convert("L"), border=60, fill=255)
    result = _try_decode(up2_grey)
    if result:
        return result

    # Attempt 3 — 3x upscale + padding (small/low-res barcodes)
    up3 = image.resize((image.width * 3, image.height * 3), Image.LANCZOS)
    result = _try_decode(ImageOps.expand(up3, border=80, fill="white"))
    if result:
        return result

    # Attempt 4 — contrast boost + padding (faded/low contrast barcodes)
    grey = image.convert("L")
    contrast = ImageEnhance.Contrast(grey).enhance(2.0)
    result = _try_decode(ImageOps.expand(contrast, border=40, fill=255))
    if result:
        return result

    # Attempt 5 — original + generous padding only
    result = _try_decode(ImageOps.expand(image, border=60, fill="white"))
    if result:
        return result

    # Attempt 6 — 4x upscale + padding (very small barcodes)
    up4 = image.resize((image.width * 4, image.height * 4), Image.LANCZOS)
    return _try_decode(ImageOps.expand(up4, border=100, fill="white"))


def _to_rgb(image: Image.Image) -> Image.Image:
    """
    Convert any image mode to RGB.
    RGBA, P (palette), LA, CMYK etc. all cause silent failures in zxingcpp.
    """
    if image.mode in ("RGBA", "LA"):
        # Paste onto white background to flatten transparency
        background = Image.new("RGB", image.size, (255, 255, 255))
        if image.mode == "RGBA":
            background.paste(image, mask=image.split()[3])
        else:
            background.paste(image)
        return background
    elif image.mode != "RGB":
        return image.convert("RGB")
    return image


def _try_decode(image: Image.Image) -> Optional[str]:
    """
    Run zxingcpp on a PIL Image.
    Only returns a result that passes strict food barcode validation.
    """
    try:
        results = zxingcpp.read_barcodes(image)
        for result in results:
            data = result.text.strip()
            if is_valid_food_barcode(data):
                return data
    except Exception:
        pass
    return None


def get_barcode_type(image: Image.Image) -> Optional[str]:
    """Returns barcode format string (e.g. 'EAN-13') or None."""
    image = _to_rgb(image)
    try:
        up2 = image.resize((image.width * 2, image.height * 2), Image.LANCZOS)
        padded = ImageOps.expand(up2, border=60, fill="white")
        results = zxingcpp.read_barcodes(padded)
        for result in results:
            if is_valid_food_barcode(result.text.strip()):
                return str(result.format)
    except Exception:
        pass
    return None


def is_valid_food_barcode(barcode: str) -> bool:
    """Food barcodes are 8-14 digits only. Filters garbage decode results."""
    return (
        barcode is not None
        and barcode.isdigit()
        and 8 <= len(barcode) <= 14
    )