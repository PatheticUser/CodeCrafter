import os
import webbrowser
import json
from google.genai import types
from config import MAX_FILE_CHARS

def preview_html_file(working_dir, path):
    """
    Opens an HTML file in the default web browser for preview.
    This function also works with HTML files that reference CSS files.
    
    Args:
        working_dir: The working directory path
        path: Path to the HTML file (relative to working_dir)
    
    Returns:
        JSON string containing preview status and file information
    """
    full_path = os.path.abspath(os.path.join(working_dir, path))
    working_dir_abs = os.path.abspath(working_dir)
    
    if not os.path.exists(full_path):
        return json.dumps({"error": f"File not found: {path}"})
    
    if not full_path.startswith(working_dir_abs + os.sep):
        return json.dumps({"error": "Security: Path traversal detected"})
    
    # Check if file is HTML
    if not path.lower().endswith(('.html', '.htm')):
        return json.dumps({"error": f"Not an HTML file: {path}. Only .html and .htm files can be previewed."})
    
    result = {
        "file": path,
        "action": "preview",
        "status": "success",
        "message": ""
    }
    
    try:
        # Convert to file:// URL for browser
        file_url = f"file://{full_path}"
        
        # Open in default browser
        webbrowser.open(file_url)
        
        result["message"] = f"Successfully opened {path} in the default web browser at {file_url}"
        result["url"] = file_url
        
        # Also read and return a preview of the HTML content
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.read(MAX_FILE_CHARS)
            result["content_preview"] = content if len(content) <= 500 else content[:500] + "... (truncated)"
            
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
    
    return json.dumps(result, indent=2)


# Function schema for Gemini
schema_preview_html_file = types.FunctionDeclaration(
    name="preview_html_file",
    description="Opens an HTML file in the default web browser for preview. Works with HTML files that reference CSS stylesheets. This is the appropriate tool for viewing HTML/CSS output.",
    parameters=types.Schema(
        type=types.Type.OBJECT,
        properties={
            "path": types.Schema(
                type=types.Type.STRING,
                description="Path to the HTML file relative to the working directory (e.g., 'index.html' or 'pages/about.html')"
            )
        },
        required=["path"]
    )
)
