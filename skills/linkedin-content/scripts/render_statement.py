#!/usr/bin/env python3
"""Generate a single statement image for LinkedIn posts using Gemini.

Uploads the dark-statement-reference image as a style reference along
with a text prompt describing the desired statement text. Gemini generates
a new image matching the style but with the new text.

Usage:
    python3 render_statement.py --primary "AI is not a coding tool" --accent "its modern infrastructure"
    python3 render_statement.py --input statement.json

Input JSON format (alternative to CLI args):
{
    "line_primary": "AI is not a coding tool",
    "line_accent": "its modern infrastructure"
}
"""

import argparse
import base64
import json
import mimetypes
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Paths — PLUGIN_ROOT is 3 levels up: scripts/ -> linkedin-content/ -> skills/ -> root
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PLUGIN_ROOT = SKILL_DIR.parent.parent
REFERENCE_IMAGE = SKILL_DIR / "assets" / "single-image" / "dark-statement-reference.png"
PROJECT_ROOT = Path.cwd()
OUTPUT_DIR = PROJECT_ROOT / "deliverables" / "statement-images"

import requests

GEMINI_MODEL = "gemini-3.1-flash-image-preview"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def get_gemini_key():
    """Get Gemini API key — try lib.config first, fall back to env vars."""
    # Try lib.config.get_key (plugin's config system)
    try:
        sys.path.insert(0, str(PLUGIN_ROOT))
        from lib.config import get_key
        key = get_key("gemini")
        if key:
            return key
    except (ImportError, Exception):
        pass

    # Fall back to environment variables
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")


def load_dotenv():
    """Load .env file if present (from project root)."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


load_dotenv()


def load_image_as_base64(path: Path) -> tuple[str, str]:
    """Load an image file and return (base64_data, mime_type)."""
    mime_type = mimetypes.guess_type(str(path))[0] or "image/png"
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")
    return data, mime_type


def generate_statement_image(
    line_primary: str,
    line_accent: str,
    gemini_api_key: str,
    output_path: Path,
) -> Path | None:
    """Generate a statement image via Gemini API using reference image."""

    # Build parts: reference image + text prompt
    parts = []

    # Upload reference image as style guide
    if REFERENCE_IMAGE.exists():
        b64, mime = load_image_as_base64(REFERENCE_IMAGE)
        parts.append({
            "inline_data": {
                "mime_type": mime,
                "data": b64,
            }
        })
    else:
        print(f"Warning: Reference image not found at {REFERENCE_IMAGE}", file=sys.stderr)

    # Text prompt describing what to generate
    prompt = f"""Generate an image that matches the exact style of the reference image I've uploaded.

The reference image has:
- A dark gradient background (darker at edges, slightly lighter in center)
- Bold uppercase text centered in the middle
- Two lines of text stacked vertically
- The first line is in a light gray/silver color
- The second line is in a blue/purple accent color
- Clean, modern sans-serif font (Inter or similar)
- No other elements — just the dark background and the text
- Square format (1:1 aspect ratio)

Generate a NEW image with the EXACT same visual style but with this text:
- Line 1 (light gray): {line_primary.upper()}
- Line 2 (blue/purple accent): {line_accent.upper()}

Keep everything else identical: same background gradient, same font style, same text positioning, same colors. The only thing that changes is the text content."""

    parts.append({"text": prompt})

    url = GEMINI_API_URL.format(model=GEMINI_MODEL)

    payload = {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "responseModalities": ["IMAGE", "TEXT"],
        },
    }

    headers = {"x-goog-api-key": gemini_api_key}

    print("  Generating statement image via Gemini...")

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=120)
    except Exception as e:
        print(f"  ERROR calling Gemini API: {e}", file=sys.stderr)
        return None

    if response.status_code != 200:
        print(f"  ERROR: Gemini API returned {response.status_code}", file=sys.stderr)
        try:
            err = response.json()
            print(f"  {json.dumps(err.get('error', err), indent=2)[:500]}", file=sys.stderr)
        except Exception:
            print(f"  {response.text[:500]}", file=sys.stderr)
        return None

    result = response.json()

    # Extract generated image from response
    img_data = None
    try:
        for part in result["candidates"][0]["content"]["parts"]:
            if "inlineData" in part and part["inlineData"]["mimeType"].startswith("image/"):
                img_data = base64.b64decode(part["inlineData"]["data"])
                break
    except (KeyError, IndexError) as e:
        print(f"  ERROR: Unexpected response structure: {e}", file=sys.stderr)
        return None

    if not img_data:
        print("  ERROR: No image in Gemini response", file=sys.stderr)
        return None

    # Save image
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(img_data)
    print(f"  Saved: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate statement image for LinkedIn via Gemini")
    parser.add_argument("--primary", help="Primary line text (light gray)")
    parser.add_argument("--accent", help="Accent line text (brand color)")
    parser.add_argument("--input", help="Path to JSON file with line_primary and line_accent")
    parser.add_argument("--output", help="Output PNG path (default: deliverables/statement-images/)")

    args = parser.parse_args()

    # Load from JSON or CLI args
    if args.input:
        input_path = Path(args.input)
        if not input_path.exists():
            print(json.dumps({"success": False, "error": f"Input file not found: {args.input}"}))
            sys.exit(1)
        with open(input_path) as f:
            data = json.load(f)
        line_primary = data.get("line_primary", "")
        line_accent = data.get("line_accent", "")
    elif args.primary:
        line_primary = args.primary
        line_accent = args.accent or ""
    else:
        print(json.dumps({"success": False, "error": "Provide --primary/--accent or --input"}))
        sys.exit(1)

    if not line_primary:
        print(json.dumps({"success": False, "error": "line_primary is required"}))
        sys.exit(1)

    # API key — try lib.config first, then env vars
    gemini_api_key = get_gemini_key()
    if not gemini_api_key:
        print(json.dumps({"success": False, "error": "Set GEMINI_API_KEY or GOOGLE_API_KEY in .env, or configure via lib.config"}))
        sys.exit(1)

    # Output path — project-relative, not plugin-relative
    if args.output:
        output_path = Path(args.output)
    else:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_text = line_primary[:30].replace(" ", "_").lower()
        safe_text = "".join(c for c in safe_text if c.isalnum() or c == "_")
        output_path = OUTPUT_DIR / f"{safe_text}_{timestamp}.png"

    # Generate
    result_path = generate_statement_image(line_primary, line_accent, gemini_api_key, output_path)

    if result_path:
        result = {
            "success": True,
            "image_path": str(result_path),
            "file_size_kb": round(result_path.stat().st_size / 1024, 1),
            "line_primary": line_primary,
            "line_accent": line_accent,
        }
    else:
        result = {"success": False, "error": "Image generation failed"}

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
