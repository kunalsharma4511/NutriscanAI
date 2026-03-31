# utils/image_utils.py
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import io


def load_image_from_upload(uploaded_file) -> Image.Image:
    """Load a PIL Image from a Streamlit UploadedFile object."""
    image_bytes = uploaded_file.read()
    return Image.open(io.BytesIO(image_bytes)).convert("RGB")


def load_image_from_bytes(image_bytes: bytes) -> Image.Image:
    """Load a PIL Image from raw bytes (e.g. from st.camera_input)."""
    return Image.open(io.BytesIO(image_bytes)).convert("RGB")


def resize_image(image: Image.Image, max_width: int = 1200) -> Image.Image:
    """Resize proportionally so width does not exceed max_width."""
    w, h = image.size
    if w <= max_width:
        return image
    ratio = max_width / w
    return image.resize((max_width, int(h * ratio)), Image.LANCZOS)


def preprocess_for_ocr(image: Image.Image) -> Image.Image:
    """
    Greyscale + sharpness + contrast + unsharp mask.
    Optimised for extracting text from printed food labels.
    """
    image = image.convert("L")
    image = ImageEnhance.Sharpness(image).enhance(2.5)
    image = ImageEnhance.Contrast(image).enhance(2.0)
    image = image.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
    return image


def preprocess_for_barcode(image: Image.Image) -> np.ndarray:
    """Greyscale + contrast boost → numpy array for pyzbar."""
    image = image.convert("L")
    image = ImageEnhance.Contrast(image).enhance(1.8)
    return np.array(image)


def pil_to_bytes(image: Image.Image, fmt: str = "JPEG") -> bytes:
    """Convert PIL Image to raw bytes for Streamlit display."""
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


def crop_region(image: Image.Image, box: tuple) -> Image.Image:
    """Crop a region. box = (left, upper, right, lower) in pixels."""
    return image.crop(box)