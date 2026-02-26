import os
import base64
from google.genai import types


SUPPORTED_IMAGE_FORMATS = ["png", "jpg", "jpeg", "webp", "gif", "bmp"]


def encode_image_to_base64(image_path):
    """Encode an image file to base64."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")


def get_image_format(file_path):
    """Get the image format from file extension."""
    ext = os.path.splitext(file_path)[1].lower().lstrip(".")
    return ext if ext in SUPPORTED_IMAGE_FORMATS else "jpeg"


def analyze_image(working_directory, file_path, prompt=None):
    """
    Analyzes an image file using Gemini's vision capabilities.
    Returns a description of the image or error if not found/invalid.
    """

    # Normalize paths
    working_directory_abs = os.path.abspath(working_directory)
    target_file_abs = os.path.abspath(os.path.join(working_directory, file_path))

    # 1. Validate scope
    if not target_file_abs.startswith(working_directory_abs):
        return f'Error: Cannot access "{file_path}" as it is outside the permitted working directory'

    # 2. Validate file exists
    if not os.path.isfile(target_file_abs):
        return f'Error: File not found: "{file_path}"'

    # 3. Validate image format
    ext = os.path.splitext(file_path)[1].lower().lstrip(".")
    if ext not in SUPPORTED_IMAGE_FORMATS:
        return f'Error: Unsupported image format "{ext}". Supported: {", ".join(SUPPORTED_IMAGE_FORMATS)}'

    try:
        # Encode image to base64
        image_data = encode_image_to_base64(target_file_abs)
        image_format = get_image_format(file_path)
        mime_type = f"image/{image_format}"

        # Build the prompt for analysis
        analysis_prompt = prompt if prompt else "Describe this image in detail."

        # Return a structured response that main.py will process
        # This includes the image data and the analysis prompt
        return {
            "type": "image_analysis",
            "mime_type": mime_type,
            "data": image_data,
            "prompt": analysis_prompt,
            "file_name": os.path.basename(file_path),
            "success": True
        }

    except Exception as e:
        return f"Error reading image: {e}"


# --- Gemini Function Schema ---
def make_function_schema(name, description, params):
    return {
        "name": name,
        "description": description,
        "parameters": {
            "type": "object",
            "properties": params,
        },
    }


schema_analyze_image = make_function_schema(
    name="analyze_image",
    description=(
        "Analyzes an image file using Gemini's vision capabilities. "
        "Can describe the image, extract text, identify objects, or answer questions about the image. "
        "Supports PNG, JPG, JPEG, WebP, GIF, and BMP formats."
    ),
    params={
        "file_path": {
            "type": types.Type.STRING,
            "description": "The relative path of the image file to analyze.",
        },
        "prompt": {
            "type": types.Type.STRING,
            "description": "Optional question or task for the image analysis. If not provided, will provide a general description.",
        },
    },
)
