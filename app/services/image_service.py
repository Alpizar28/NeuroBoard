import io
from PIL import Image, ImageEnhance, ImageFilter
from app.utils.hashing import sha256_bytes

class ImageService:
    @staticmethod
    def calculate_hash(image_bytes: bytes) -> str:
        """Calculate SHA256 hash of image bytes to detect duplicates."""
        return sha256_bytes(image_bytes)

    @staticmethod
    def preprocess_image(image_bytes: bytes, max_width: int = 1024) -> bytes:
        """
        Resize to fixed width, apply contrast enhancement and noise reduction.
        Returns preprocessed image as bytes.
        """
        img = Image.open(io.BytesIO(image_bytes))

        # Convert to RGB (in case of PNG with alpha)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        # Resize to fixed width
        if img.width > max_width:
            ratio = max_width / float(img.width)
            new_height = int(float(img.height) * float(ratio))
            img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)
            
        # Contrast enhancement
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2.0)

        # Noise reduction using a gentle filter
        img = img.filter(ImageFilter.SMOOTH_MORE)
        
        # Save to bytes
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=85)
        return output.getvalue()
