#!/usr/bin/env python3
"""
YouTube Thumbnail Generator

Usage:
    python3 generate.py "your video concept here"
    python3 generate.py "your concept" --variations 5
    python3 generate.py "your concept" --no-face

Generates N thumbnail variations (default 3) via Google Gemini REST API.
Claude generates optimized prompts from your raw concept using brand kit + best practices.
No external dependencies beyond requests + pyyaml (both already installed).
"""

import argparse
import base64
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

import requests
import yaml

# Paths — plugin-relative
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PLUGIN_ROOT = SKILL_DIR.parent.parent  # content-os/
BRAND_KIT_PATH = SKILL_DIR / "references" / "brand-kit.yaml"
PROMPT_SYSTEM_PATH = SKILL_DIR / "references" / "prompt-system.md"
BEST_PRACTICES_PATH = SKILL_DIR / "references" / "best-practices.md"
LOGOS_DIR = SKILL_DIR / "assets" / "logos"
REFERENCE_DIR = SKILL_DIR / "assets" / "reference-thumbnails"
FACE_PHOTO_DIR = SKILL_DIR / "assets"

# Project-relative output (deliverables/ in the user's project, not in the plugin)
sys.path.insert(0, str(PLUGIN_ROOT / "lib"))
try:
    from config import get_key, get_project_root
    PROJECT_ROOT = get_project_root()
except ImportError:
    PROJECT_ROOT = Path.cwd()
    def get_key(name):
        return os.environ.get(f"{name.upper()}_API_KEY")

OUTPUT_BASE = PROJECT_ROOT / ".tmp" / "thumbnails"

# Load .env file if present (simple loader, no dependency needed)
def load_dotenv():
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

# API URLs
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Gemini model
GEMINI_MODEL = "gemini-3.1-flash-image-preview"


def load_brand_kit() -> dict:
    if not BRAND_KIT_PATH.exists():
        print("ERROR: Brand kit not found. Run setup first:")
        print("  python3 scripts/setup_brand.py")
        sys.exit(1)
    with open(BRAND_KIT_PATH) as f:
        return yaml.safe_load(f)


def load_text(path: Path) -> str:
    with open(path) as f:
        return f.read()


def slugify(text: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '-', text.lower().strip())
    return slug[:50].strip('-')


LOBE_ICONS_CDN = "https://unpkg.com/@lobehub/icons-static-png@latest/dark/{slug}.png"


def scan_logos() -> list[str]:
    """Return list of locally cached logo filenames from assets/logos/."""
    if not LOGOS_DIR.exists():
        return []
    return sorted([
        f.stem for f in LOGOS_DIR.iterdir()
        if f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp')
    ])


def fetch_icon(slug: str) -> Path | None:
    """Fetch an icon from lobe-icons CDN, cache locally. Returns path or None."""
    LOGOS_DIR.mkdir(parents=True, exist_ok=True)
    cached = LOGOS_DIR / f"{slug}.png"
    if cached.exists():
        return cached

    url = LOBE_ICONS_CDN.format(slug=slug)
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code == 200 and resp.headers.get("content-type", "").startswith("image/"):
            cached.write_bytes(resp.content)
            print(f"      Fetched icon: {slug} ({len(resp.content)//1024}KB)")
            return cached
        else:
            print(f"      Icon not found on CDN: {slug} (HTTP {resp.status_code})")
            return None
    except Exception as e:
        print(f"      Failed to fetch icon {slug}: {e}")
        return None


def fetch_icons_for_prompt(slugs: list[str]) -> list[Path]:
    """Fetch all requested icon slugs, return paths to those that succeeded."""
    paths = []
    for slug in slugs:
        # Strip file extensions if Claude included them
        slug = slug.replace(".png", "").replace(".svg", "").replace(".webp", "")
        path = fetch_icon(slug)
        if path:
            paths.append(path)
    return paths


def scan_reference_thumbnails() -> dict[str, list[Path]]:
    """Scan assets/reference-thumbnails/ for categorized examples.

    Returns dict mapping archetype name to list of full Paths.
    """
    if not REFERENCE_DIR.exists():
        return {}
    refs = {}
    for subdir in REFERENCE_DIR.iterdir():
        if subdir.is_dir():
            files = sorted([
                f for f in subdir.iterdir()
                if f.suffix.lower() in ('.png', '.jpg', '.jpeg', '.webp')
            ], key=lambda f: f.name)
            if files:
                refs[subdir.name] = files
    return refs


def find_face_photo() -> Path | None:
    """Find the base face photo in assets/."""
    for ext in ['.jpg', '.jpeg', '.png', '.webp']:
        path = FACE_PHOTO_DIR / f"base-face{ext}"
        if path.exists():
            return path
    return None


def load_image_as_base64(path: Path) -> tuple[str, str]:
    """Load a local image file as base64 string and determine MIME type."""
    suffix = path.suffix.lower()
    mime_map = {
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.webp': 'image/webp',
    }
    mime_type = mime_map.get(suffix, 'image/jpeg')
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    return b64, mime_type


def generate_prompts(concept: str, brand_kit: dict, num_variations: int, include_face: bool, forced_style: str | None = None) -> list[dict]:
    """Call Claude to generate optimized image prompts."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set in environment")
        sys.exit(1)

    prompt_system = load_text(PROMPT_SYSTEM_PATH)

    face_note = "Face photo will be provided to the image model." if include_face else "NO face/person. Objects and text only."

    # Available styles
    refs = scan_reference_thumbnails()
    styles_available = ", ".join(refs.keys()) if refs else "electro_black, pixar_style, before_after"

    forced_style_section = ""
    if forced_style:
        forced_style_section = f"\nFORCED STYLE: Use ONLY \"{forced_style}\" for ALL variations. Vary text, icons, expression — not style."

    user_message = f"""Video concept: {concept}

Niche: {brand_kit.get('niche', 'AI automation, developer tools')}
{face_note}
Available styles: {styles_available}
Generate exactly {num_variations} variations.{forced_style_section}

Return ONLY the JSON array."""

    response = requests.post(
        ANTHROPIC_API_URL,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 2048,
            "system": prompt_system,
            "messages": [{"role": "user", "content": user_message}],
        },
        timeout=60,
    )

    if response.status_code != 200:
        print(f"ERROR: Claude API returned {response.status_code}")
        print(response.text)
        sys.exit(1)

    result = response.json()
    text = result["content"][0]["text"]

    # Extract JSON from response (handle markdown code blocks)
    json_match = re.search(r'\[.*\]', text, re.DOTALL)
    if not json_match:
        print("ERROR: Could not parse Claude's response as JSON")
        print(text)
        sys.exit(1)

    prompts = json.loads(json_match.group())
    return prompts


def get_reference_thumbnails_for_archetype(archetype: str) -> list[Path]:
    """Get reference thumbnail paths for a given archetype, falling back to all refs."""
    refs = scan_reference_thumbnails()
    if not refs:
        return []

    # Try exact match first
    if archetype in refs:
        return refs[archetype]

    # Fall back to all available references (first from each category, max 3)
    all_refs = []
    for paths in refs.values():
        all_refs.append(paths[0])
        if len(all_refs) >= 3:
            break
    return all_refs


def build_gemini_parts(
    prompt_text: str, include_face: bool, logos_used: list[str],
    archetype: str = ""
) -> list[dict]:
    """Build the parts array for the Gemini REST API call.

    Includes reference thumbnails, face photo, and logos as inline_data parts
    alongside the text prompt. Returns parts with image labels that map each
    uploaded image to a numbered reference so the prompt can say "use Image 3".
    """
    parts = []
    image_labels = []

    # Add reference thumbnails first (style reference)
    ref_paths = get_reference_thumbnails_for_archetype(archetype)
    for i, ref_path in enumerate(ref_paths):
        b64, mime = load_image_as_base64(ref_path)
        parts.append({
            "inline_data": {
                "mime_type": mime,
                "data": b64,
            }
        })
        image_labels.append(f"Image {len(image_labels)+1} is the BASE THUMBNAIL. Recreate this thumbnail exactly — same style, lighting, composition, colors, layout, everything. Only change what the prompt specifically asks you to change.")
    if ref_paths:
        print(f"      Uploaded {len(ref_paths)} reference thumbnail(s)")

    # Add face photo as reference
    if include_face:
        face_path = find_face_photo()
        if face_path:
            b64, mime = load_image_as_base64(face_path)
            parts.append({
                "inline_data": {
                    "mime_type": mime,
                    "data": b64,
                }
            })
            image_labels.append(f"Image {len(image_labels)+1} is the FACE REFERENCE photo. Place this exact person in the thumbnail — same face, same features, same expression, same skin tone. Do not alter or reinterpret.")

    # Fetch and add logo/icon reference images from lobe-icons CDN
    if logos_used:
        icon_paths = fetch_icons_for_prompt(logos_used)
        for icon_path in icon_paths:
            b64, mime = load_image_as_base64(icon_path)
            parts.append({
                "inline_data": {
                    "mime_type": mime,
                    "data": b64,
                }
            })
            slug = icon_path.stem
            image_labels.append(
                f"Image {len(image_labels)+1} is the {slug} LOGO. "
                f"This is a product logo — composite it into the thumbnail exactly as provided. "
                f"Do not redraw, reinterpret, or stylize this logo."
            )

    # Build labeled prompt: image role labels + original prompt text
    labeled_prompt = "\n".join(image_labels) + "\n\n" + prompt_text if image_labels else prompt_text
    parts.append({"text": labeled_prompt})

    return parts


def generate_single(
    idx: int, prompt_data: dict, brand_kit: dict, include_face: bool,
    output_dir: Path, gemini_api_key: str
) -> Path | None:
    """Generate a single thumbnail via Google Gemini REST API. Returns output path or None."""
    raw_prompt = prompt_data["prompt"]
    # Support both JSON object prompts (new) and plain string prompts (legacy)
    if isinstance(raw_prompt, dict):
        prompt_text = json.dumps(raw_prompt)
    else:
        prompt_text = raw_prompt
    archetype = prompt_data.get("archetype", "unknown")
    logos_used = prompt_data.get("logos_used", [])
    print(f"  [{idx+1}] Generating ({archetype})...")

    # Build parts with reference thumbnails, face, and logos
    parts = build_gemini_parts(prompt_text, include_face, logos_used, archetype)

    url = GEMINI_API_URL.format(model=GEMINI_MODEL) + f"?key={gemini_api_key}"

    payload = {
        "contents": [
            {
                "parts": parts
            }
        ],
        "generationConfig": {
            "responseModalities": ["IMAGE", "TEXT"],
            "imageConfig": {
                "aspectRatio": "16:9",
            },
            "thinkingConfig": {
                "thinkingLevel": "HIGH",
            },
        },
    }

    try:
        response = requests.post(url, json=payload, timeout=120)
    except Exception as e:
        print(f"  [{idx+1}] ERROR calling Gemini API: {e}")
        return None

    if response.status_code != 200:
        print(f"  [{idx+1}] ERROR: Gemini API returned {response.status_code}")
        try:
            err = response.json()
            print(f"  [{idx+1}] {json.dumps(err.get('error', err), indent=2)[:500]}")
        except Exception:
            print(f"  [{idx+1}] {response.text[:500]}")
        return None

    result = response.json()

    # Extract generated image from response
    img_data = None
    try:
        for part in result["candidates"][0]["content"]["parts"]:
            if "inlineData" in part and part["inlineData"]["mimeType"].startswith("image/"):
                img_data = base64.b64decode(part["inlineData"]["data"])
                mime_type = part["inlineData"]["mimeType"]
                break
            elif "text" in part:
                pass
    except (KeyError, IndexError) as e:
        print(f"  [{idx+1}] ERROR: Unexpected response structure: {e}")
        print(f"  [{idx+1}] Response keys: {list(result.keys())}")
        return None

    if not img_data:
        print(f"  [{idx+1}] ERROR: Gemini returned no image data")
        try:
            for part in result["candidates"][0]["content"]["parts"]:
                if "text" in part:
                    print(f"  [{idx+1}] Model response: {part['text'][:200]}")
        except Exception:
            pass
        return None

    # Determine file extension from mime type
    ext_map = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
    ext = ext_map.get(mime_type, ".png")

    output_path = output_dir / f"thumbnail_{idx+1}{ext}"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "wb") as f:
        f.write(img_data)

    size_kb = output_path.stat().st_size / 1024
    print(f"  [{idx+1}] Saved: {output_path} ({size_kb:.0f} KB)")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate YouTube thumbnails from a concept")
    parser.add_argument("concept", nargs="?", default=None, help="Video concept description")
    parser.add_argument("--prompts-file", default=None,
                        help="Path to pre-made prompts.json (skips Claude prompt generation)")
    parser.add_argument("--variations", type=int, default=None,
                        help="Number of variations (default: from brand kit)")
    parser.add_argument("--no-face", action="store_true",
                        help="Generate without face/person")
    parser.add_argument("--style", default=None,
                        choices=["electro_black", "pixar_style", "before_after"],
                        help="Force a specific thumbnail style/archetype")
    parser.add_argument("--output-dir", default=None,
                        help="Custom output directory")
    args = parser.parse_args()

    if not args.concept and not args.prompts_file:
        parser.error("Either provide a concept or --prompts-file")

    # Load config
    brand_kit = load_brand_kit()
    output_config = brand_kit.get("output", {})

    num_variations = args.variations or output_config.get("variations", 3)
    include_face = not args.no_face

    # Gemini API key — try lib.config first, fall back to env
    gemini_api_key = get_key("gemini")
    if not gemini_api_key:
        gemini_api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not gemini_api_key:
        print("ERROR: GEMINI_API_KEY (or GOOGLE_API_KEY) not set in environment")
        sys.exit(1)

    # Output directory
    date_slug = datetime.now().strftime("%Y-%m-%d")
    concept_slug = slugify(args.concept or "custom")
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = OUTPUT_BASE / f"{date_slug}-{concept_slug}"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== Thumbnail Generator ===")
    print(f"Concept: {args.concept or '(from prompts file)'}")
    print(f"Model: {GEMINI_MODEL}")
    print(f"Variations: {num_variations}")
    print(f"Face: {'yes' if include_face else 'no'}")
    if args.style:
        print(f"Style: {args.style} (forced)")
    if args.prompts_file:
        print(f"Prompts: {args.prompts_file} (pre-made)")
    print(f"Output: {output_dir}\n")

    # Step 1: Load or generate prompts
    if args.prompts_file:
        print(f"Loading pre-made prompts from {args.prompts_file}...")
        with open(args.prompts_file) as f:
            prompts = json.load(f)
        print(f"Loaded {len(prompts)} prompt variations.\n")
    else:
        print("Generating optimized prompts with Claude...")
        prompts = generate_prompts(args.concept, brand_kit, num_variations, include_face, forced_style=args.style)
        print(f"Generated {len(prompts)} prompt variations.\n")

    # Save prompts for reference
    prompts_path = output_dir / "prompts.json"
    with open(prompts_path, "w") as f:
        json.dump(prompts, f, indent=2)
    print(f"Prompts saved to: {prompts_path}\n")

    # Step 2: Generate images concurrently via Gemini REST API
    print("Generating thumbnails via Google Gemini API...")
    results = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {
            executor.submit(
                generate_single, i, prompt, brand_kit, include_face,
                output_dir, gemini_api_key
            ): i
            for i, prompt in enumerate(prompts)
        }

        for future in as_completed(futures):
            idx = futures[future]
            try:
                path = future.result()
                if path:
                    results.append((idx, path))
            except Exception as e:
                print(f"  [{idx+1}] ERROR: {e}")

    # Summary
    results.sort(key=lambda x: x[0])
    print(f"\n=== Results ===")
    print(f"Generated {len(results)}/{len(prompts)} thumbnails successfully.\n")

    for idx, path in results:
        prompt_data = prompts[idx]
        print(f"  [{idx+1}] {path}")
        print(f"      Archetype: {prompt_data.get('archetype', 'N/A')}")
        text = prompt_data.get('text_on_image')
        if text:
            print(f"      Text: \"{text}\"")
        print()

    if results:
        print(f"Output directory: {output_dir}")
    else:
        print("No thumbnails were generated. Check errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
