import io
from PIL import Image, ImageEnhance, ImageFilter
from app.core.config import settings
from app.utils.hashing import sha256_bytes


class ImageService:
    @staticmethod
    def calculate_hash(image_bytes: bytes) -> str:
        """Calculate SHA256 hash of image bytes to detect duplicates."""
        return sha256_bytes(image_bytes)

    @staticmethod
    def preprocess_image(image_bytes: bytes, max_width: int | None = None) -> bytes:
        """
        Resize to max_width, apply contrast enhancement and noise reduction.
        Converts all PIL modes to RGB for consistent JPEG output.
        Returns preprocessed image as JPEG bytes.
        """
        _max_width = max_width if max_width is not None else settings.IMAGE_MAX_WIDTH

        img = Image.open(io.BytesIO(image_bytes))

        # Convert any non-RGB mode to RGB (covers RGBA, P, L, LA, CMYK, I, F, etc.)
        if img.mode != "RGB":
            img = img.convert("RGB")

        # Resize down to fixed width (never upscale)
        if img.width > _max_width:
            ratio = _max_width / float(img.width)
            new_height = int(float(img.height) * float(ratio))
            img = img.resize((_max_width, new_height), Image.Resampling.LANCZOS)

        # Contrast enhancement
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(settings.IMAGE_CONTRAST_FACTOR)

        # Noise reduction using a gentle filter
        img = img.filter(ImageFilter.SMOOTH_MORE)

        # Save to bytes
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=85)
        return output.getvalue()
