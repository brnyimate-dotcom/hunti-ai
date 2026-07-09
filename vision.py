import base64
import io
from typing import Tuple

from PIL import Image
import mss
import mss.tools

# Maximum dimensions for the screenshot to save API tokens
MAX_WIDTH = 1024
MAX_HEIGHT = 768


def _resize_image(image: Image.Image) -> Image.Image:
    """Resize image if it exceeds maximum dimensions to save API tokens."""
    if image.width > MAX_WIDTH or image.height > MAX_HEIGHT:
        image.thumbnail((MAX_WIDTH, MAX_HEIGHT), Image.Resampling.LANCZOS)
    return image


def capture_screen() -> Tuple[Image.Image, str]:
    """Capture the primary screen, resize it, and return a PIL Image plus its base64 PNG string."""
    try:
        with mss.mss() as sct:
            monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
            screenshot = sct.grab(monitor)

            image = Image.frombytes("RGB", screenshot.size, screenshot.rgb)
            
            # Resize to save tokens
            image = _resize_image(image)

            buffered = io.BytesIO()
            image.save(buffered, format="PNG")
            encoded = base64.b64encode(buffered.getvalue()).decode("utf-8")

            return image, encoded
    except Exception as exc:
        raise RuntimeError(f"Failed to capture screen: {exc}") from exc


def image_to_base64(image: Image.Image) -> str:
    """Convert a PIL Image to a base64-encoded PNG string (with automatic resizing)."""
    try:
        # Resize to save tokens
        image = _resize_image(image)
        
        buffered = io.BytesIO()
        image.save(buffered, format="PNG")
        return base64.b64encode(buffered.getvalue()).decode("utf-8")
    except Exception as exc:
        raise RuntimeError(f"Failed to encode image to base64: {exc}") from exc


if __name__ == "__main__":
    try:
        image, image_b64 = capture_screen()
        print(f"Captured screen: size={image.size}, mode={image.mode}")
        print(f"Base64 length: {len(image_b64)} characters")
    except Exception as exc:
        print(f"Vision test failed: {exc}")