#!/usr/bin/env python3
"""
One-time brand kit setup for thumbnail generator.
Collects brand colors, font preferences, style keywords, and base face photo.
Writes config to references/brand-kit.yaml.
"""

import os
import sys
import shutil
import yaml

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(SCRIPT_DIR)
BRAND_KIT_PATH = os.path.join(SKILL_DIR, "references", "brand-kit.yaml")
ASSETS_DIR = os.path.join(SKILL_DIR, "assets")


def validate_hex(color: str) -> bool:
    color = color.strip().lstrip("#")
    if len(color) not in (3, 6):
        return False
    try:
        int(color, 16)
        return True
    except ValueError:
        return False


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    response = input(f"{prompt}{suffix}: ").strip()
    return response if response else default


def ask_hex(prompt: str, default: str = "") -> str:
    while True:
        color = ask(prompt, default)
        if not color:
            return ""
        if validate_hex(color):
            color = color.strip().lstrip("#")
            return f"#{color.upper()}" if len(color) == 6 else f"#{color.upper()}"
        print(f"  Invalid hex color: {color}. Use format like #FF3B3B or FF3B3B")


def main():
    print("\n=== Thumbnail Generator — Brand Kit Setup ===\n")

    existing = {}
    if os.path.exists(BRAND_KIT_PATH):
        with open(BRAND_KIT_PATH) as f:
            existing = yaml.safe_load(f) or {}
        print(f"Existing brand kit found. Press Enter to keep current values.\n")

    # Channel info
    channel_name = ask("Channel name", existing.get("channel_name", ""))
    niche = ask("Channel niche (e.g., AI automation, tech tutorials)", existing.get("niche", ""))

    # Colors
    print("\n--- Brand Colors (hex codes) ---")
    colors = existing.get("colors", {})
    primary = ask_hex("Primary color", colors.get("primary", "#FF3B3B"))
    secondary = ask_hex("Secondary color", colors.get("secondary", "#FFB418"))
    accent = ask_hex("Accent color", colors.get("accent", "#0A0A0A"))
    background = ask_hex("Default background color", colors.get("background", "#0A0A0A"))

    # Typography
    print("\n--- Typography ---")
    font_style = ask(
        "Font style for AI prompt guidance (e.g., 'bold Impact-style sans-serif')",
        existing.get("font_style", "bold Impact-style sans-serif")
    )

    # Style
    print("\n--- Visual Style ---")
    style_keywords = ask(
        "Style keywords (comma-separated, e.g., 'high contrast, dark backgrounds, tech aesthetic')",
        existing.get("style_keywords", "high contrast, dark backgrounds, tech/AI aesthetic, cinematic lighting")
    )

    # Camera spec
    camera_spec = ask(
        "Camera/lens spec for photorealism",
        existing.get("camera_spec", "Sony A7R IV, 85mm portrait lens, f/1.8, natural skin texture, hard rim lighting")
    )

    # Face photo
    print("\n--- Base Face Photo ---")
    print("  Note: Your face photo is uploaded directly to Google's API as a local file.")
    print("  No URL hosting required.\n")

    face_exists = os.path.exists(os.path.join(ASSETS_DIR, "base-face.jpg"))

    if face_exists:
        print(f"  Current face photo: assets/base-face.jpg (exists)")
        update_face = ask("Update face photo? (y/n)", "n").lower() == "y"
    else:
        update_face = True

    if update_face:
        face_path = ask("Path to your base face photo")
        if face_path:
            face_path = os.path.expanduser(face_path)
            if os.path.exists(face_path):
                os.makedirs(ASSETS_DIR, exist_ok=True)
                dest = os.path.join(ASSETS_DIR, "base-face.jpg")
                shutil.copy2(face_path, dest)
                print(f"  Copied to: {dest}")
            else:
                print(f"  WARNING: File not found: {face_path}")
                print("  You can add it manually later to the assets/ directory as base-face.jpg")

    # Build config
    config = {
        "channel_name": channel_name,
        "niche": niche,
        "colors": {
            "primary": primary,
            "secondary": secondary,
            "accent": accent,
            "background": background,
        },
        "font_style": font_style,
        "style_keywords": style_keywords,
        "camera_spec": camera_spec,
        "face_photo_path": "assets/base-face.jpg",
        "model": {
            "provider": "google",
            "model_id": "gemini-3.1-flash-image-preview",
            "resolution": "2K",
            "aspect_ratio": "16:9",
        },
        "output": {
            "width": 1280,
            "height": 720,
            "max_file_size_kb": 2048,
            "variations": 3,
        },
    }

    # Write
    os.makedirs(os.path.dirname(BRAND_KIT_PATH), exist_ok=True)
    with open(BRAND_KIT_PATH, "w") as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False)

    print(f"\n Brand kit saved to: {BRAND_KIT_PATH}")
    print(f"\nReview and edit the YAML directly if you need to adjust anything.")
    print(f"Run 'python3 scripts/generate.py \"your concept\"' to generate thumbnails.\n")


if __name__ == "__main__":
    main()
