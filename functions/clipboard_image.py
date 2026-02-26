"""
Clipboard and file-path image utilities for CodeCrafter.
Handles grabbing images from the Windows clipboard and detecting image file paths in user input.
"""

import os
import io
import re

SUPPORTED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "gif", "bmp"}

MIME_MAP = {
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
    "bmp": "image/bmp",
}


def grab_clipboard_image():
    """
    Grab the current image from the Windows clipboard using Pillow.
    Returns (image_bytes, mime_type) or (None, None) if no image on clipboard.
    """
    try:
        from PIL import ImageGrab
    except ImportError:
        return None, None

    try:
        img = ImageGrab.grabclipboard()
        if img is None:
            return None, None

        # Convert to PNG bytes
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue(), "image/png"
    except Exception:
        return None, None


def detect_image_path(text):
    """
    Check if the user's text is or contains an image file path.
    Returns (file_path, remaining_text) if an image path is found,
    otherwise (None, original_text).

    Handles:
    - Absolute paths:  D:\\photos\\img.png
    - Relative paths:  ./screenshot.jpg
    - Quoted paths:    "C:\\My Folder\\pic.png"
    """
    text = text.strip()

    # Try quoted path first: "path/to/image.png" rest of text
    quoted = re.match(r'^"([^"]+\.({}))"\s*(.*)$'.format("|".join(SUPPORTED_IMAGE_EXTENSIONS)), text, re.IGNORECASE)
    if quoted:
        return quoted.group(1), quoted.group(3).strip()

    # Try unquoted path — grab the first token that looks like a path with image ext
    # Supports:  D:\foo\bar.png   ./img.jpg   ../assets/pic.webp   images/test.bmp
    path_pattern = r'(?:(?:[A-Za-z]:)?[\\/])?(?:[^\s"<>|*?]+[\\/])*[^\s"<>|*?]+\.({})'.format("|".join(SUPPORTED_IMAGE_EXTENSIONS))
    match = re.match(r'^({pat})\s*(.*)$'.format(pat=path_pattern), text, re.IGNORECASE)
    if match:
        return match.group(1), match.group(match.lastindex).strip()

    return None, text


def read_image_file(file_path):
    """
    Read an image file and return (bytes, mime_type) or (None, None) on failure.
    Accepts absolute or relative paths.
    """
    path = os.path.abspath(file_path)
    if not os.path.isfile(path):
        return None, None

    ext = os.path.splitext(path)[1].lower().lstrip(".")
    if ext not in SUPPORTED_IMAGE_EXTENSIONS:
        return None, None

    mime = MIME_MAP.get(ext, "image/png")
    try:
        with open(path, "rb") as f:
            return f.read(), mime
    except Exception:
        return None, None


def parse_image_input(user_input):
    """
    High-level parser: given raw user input, determine if it contains an image.

    Returns a dict:
      {
        "has_image": bool,
        "image_bytes": bytes | None,
        "mime_type": str | None,
        "text": str,           # the remaining text prompt
        "source": str | None,  # "clipboard" | "file" | None
        "file_path": str | None
      }
    """
    stripped = user_input.strip()

    # --- /image  or  /paste  command ---
    if stripped.lower().startswith("/image") or stripped.lower().startswith("/paste"):
        # Extract remaining text after the command
        parts = stripped.split(None, 1)
        remaining_text = parts[1] if len(parts) > 1 else ""

        img_bytes, mime = grab_clipboard_image()
        if img_bytes:
            return {
                "has_image": True,
                "image_bytes": img_bytes,
                "mime_type": mime,
                "text": remaining_text or "Describe this image in detail.",
                "source": "clipboard",
                "file_path": None,
            }
        else:
            return {
                "has_image": False,
                "image_bytes": None,
                "mime_type": None,
                "text": stripped,
                "source": None,
                "file_path": None,
                "error": "No image found on clipboard. Copy an image first, then try again.",
            }

    # --- File path detection ---
    file_path, remaining_text = detect_image_path(stripped)
    if file_path:
        img_bytes, mime = read_image_file(file_path)
        if img_bytes:
            return {
                "has_image": True,
                "image_bytes": img_bytes,
                "mime_type": mime,
                "text": remaining_text or "Describe this image in detail.",
                "source": "file",
                "file_path": file_path,
            }
        else:
            # Path looked like an image but couldn't be read
            return {
                "has_image": False,
                "image_bytes": None,
                "mime_type": None,
                "text": stripped,
                "source": None,
                "file_path": file_path,
                "error": f'Could not read image file: "{file_path}". Check the path exists.',
            }

    # --- Plain text (no image) ---
    return {
        "has_image": False,
        "image_bytes": None,
        "mime_type": None,
        "text": stripped,
        "source": None,
        "file_path": None,
    }
