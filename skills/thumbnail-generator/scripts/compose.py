#!/usr/bin/env python3
"""
PIL-based thumbnail compositor.

Deterministic thumbnail generation — no AI guessing.
Places real logos, real text, real face onto a styled background.

Usage:
    python3.11 compose.py --prompts-file prompts.json --output-dir .tmp/thumbnails/test/
    python3.11 compose.py --text "GOD MODE" --left-logo github --right-logo claude-color --style electro_black
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

# Paths — plugin-relative
SCRIPT_DIR = Path(__file__).parent
SKILL_DIR = SCRIPT_DIR.parent
PLUGIN_ROOT = SKILL_DIR.parent.parent  # content-os/
LOGOS_DIR = SKILL_DIR / "assets" / "logos"
FACE_PHOTO_DIR = SKILL_DIR / "assets"

# Project-relative output
sys.path.insert(0, str(PLUGIN_ROOT / "lib"))
try:
    from config import get_project_root
    PROJECT_ROOT = get_project_root()
except ImportError:
    PROJECT_ROOT = Path.cwd()

OUTPUT_BASE = PROJECT_ROOT / ".tmp" / "thumbnails"

# Canvas
WIDTH, HEIGHT = 1280, 720

# Fonts
IMPACT_PATH = "/System/Library/Fonts/Supplemental/Impact.ttf"
HELVETICA_BOLD_PATH = "/System/Library/Fonts/HelveticaNeue.ttc"

# Style palettes
STYLES = {
    "electro_black": {
        "bg_gradient": [(10, 5, 25), (25, 10, 50)],  # deep purple-black
        "glow_left": (255, 100, 50, 80),   # warm orange glow
        "glow_right": (130, 80, 255, 80),  # purple glow
        "text_color": (255, 255, 255),
        "text_outline": (0, 0, 0),
        "text_shadow": (255, 100, 50),  # warm glow behind text
        "vignette": True,
    },
    "pixar_style": {
        "bg_gradient": [(40, 30, 25), (60, 45, 35)],  # warm dark brown
        "glow_left": (255, 180, 80, 60),   # warm gold
        "glow_right": (255, 140, 60, 60),  # amber
        "text_color": (255, 255, 255),
        "text_outline": (0, 0, 0),
        "text_shadow": (255, 180, 80),
        "vignette": True,
    },
    "before_after": {
        "bg_gradient": [(20, 10, 10), (10, 20, 10)],  # red-left, green-right split
        "glow_left": (255, 50, 50, 80),    # red
        "glow_right": (50, 255, 50, 80),   # green
        "text_color": (255, 255, 255),
        "text_outline": (0, 0, 0),
        "text_shadow": (255, 255, 255),
        "vignette": False,
    },
}


def create_gradient_bg(style_name: str) -> Image.Image:
    """Create a dark cinematic gradient background."""
    style = STYLES[style_name]
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)

    c1, c2 = style["bg_gradient"]
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(c1[0] + (c2[0] - c1[0]) * ratio)
        g = int(c1[1] + (c2[1] - c1[1]) * ratio)
        b = int(c1[2] + (c2[2] - c1[2]) * ratio)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    # Add subtle noise/texture
    if style.get("vignette"):
        vignette = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
        vdraw = ImageDraw.Draw(vignette)
        cx, cy = WIDTH // 2, HEIGHT // 2
        max_dist = math.sqrt(cx**2 + cy**2)
        for ring in range(0, int(max_dist), 3):
            alpha = int(min(255, (ring / max_dist) * 180))
            vdraw.ellipse(
                [cx - ring, cy - ring, cx + ring, cy + ring],
                outline=(0, 0, 0, alpha)
            )
        img = Image.alpha_composite(img.convert("RGBA"), vignette).convert("RGB")

    return img


def add_glow(canvas: Image.Image, center: tuple, color: tuple, radius: int = 200) -> Image.Image:
    """Add a soft colored glow behind an icon position."""
    glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    cx, cy = center
    for r in range(radius, 0, -2):
        alpha = int(color[3] * (1 - r / radius) ** 1.5)
        draw.ellipse(
            [cx - r, cy - r, cx + r, cy + r],
            fill=(color[0], color[1], color[2], alpha)
        )
    canvas_rgba = canvas.convert("RGBA")
    return Image.alpha_composite(canvas_rgba, glow).convert("RGB")


def load_logo(slug: str, size: int = 160) -> Image.Image | None:
    """Load a logo PNG and resize it. Returns RGBA image."""
    path = LOGOS_DIR / f"{slug}.png"
    if not path.exists():
        print(f"  Logo not found: {slug}")
        return None
    img = Image.open(path).convert("RGBA")
    img = img.resize((size, size), Image.LANCZOS)
    return img


def add_icon_bg(logo: Image.Image, bg_color: tuple, padding: int = 20, radius: int = 30) -> Image.Image:
    """Put the logo on a rounded square background (app-icon style)."""
    total = logo.width + padding * 2
    bg = Image.new("RGBA", (total, total), (0, 0, 0, 0))
    draw = ImageDraw.Draw(bg)
    # Rounded rectangle background
    draw.rounded_rectangle(
        [0, 0, total - 1, total - 1],
        radius=radius,
        fill=bg_color
    )
    # Center the logo on the background
    offset = padding
    bg.paste(logo, (offset, offset), logo)
    return bg


def load_face(max_height: int = 480) -> Image.Image | None:
    """Load and prepare the face photo."""
    for ext in ['.jpg', '.jpeg', '.png', '.webp']:
        path = FACE_PHOTO_DIR / f"base-face{ext}"
        if path.exists():
            img = Image.open(path).convert("RGBA")
            # Scale to fit
            ratio = max_height / img.height
            new_w = int(img.width * ratio)
            img = img.resize((new_w, max_height), Image.LANCZOS)
            return img
    return None


def create_face_mask(face: Image.Image) -> Image.Image:
    """Create a soft-edge mask for the face to blend into background."""
    mask = Image.new("L", face.size, 255)
    draw = ImageDraw.Draw(mask)
    w, h = face.size
    # Fade the bottom edge
    fade_height = h // 4
    for y in range(h - fade_height, h):
        alpha = int(255 * (1 - (y - (h - fade_height)) / fade_height))
        draw.line([(0, y), (w, y)], fill=alpha)
    # Fade left and right edges slightly
    fade_width = w // 6
    for x in range(fade_width):
        alpha = int(255 * (x / fade_width))
        draw.line([(x, 0), (x, h)], fill=alpha)
    for x in range(w - fade_width, w):
        alpha = int(255 * (1 - (x - (w - fade_width)) / fade_width))
        draw.line([(x, 0), (x, h)], fill=alpha)
    return mask


def render_text(
    canvas: Image.Image, text: str, style_name: str,
    y_position: int = None, font_size: int = None
) -> Image.Image:
    """Render bold text with outline and glow at the bottom."""
    style = STYLES[style_name]
    canvas_rgba = canvas.convert("RGBA")

    # Auto-size font to fit ~80% of width
    if font_size is None:
        font_size = 100
        try:
            font = ImageFont.truetype(IMPACT_PATH, font_size)
        except OSError:
            font = ImageFont.truetype(HELVETICA_BOLD_PATH, font_size)

        # Shrink until text fits 80% of width
        while font_size > 40:
            bbox = font.getbbox(text)
            text_width = bbox[2] - bbox[0]
            if text_width <= WIDTH * 0.85:
                break
            font_size -= 4
            try:
                font = ImageFont.truetype(IMPACT_PATH, font_size)
            except OSError:
                font = ImageFont.truetype(HELVETICA_BOLD_PATH, font_size)
    else:
        try:
            font = ImageFont.truetype(IMPACT_PATH, font_size)
        except OSError:
            font = ImageFont.truetype(HELVETICA_BOLD_PATH, font_size)

    bbox = font.getbbox(text)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    if y_position is None:
        y_position = HEIGHT - text_height - 50

    x_position = (WIDTH - text_width) // 2

    # Text glow layer
    glow_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    glow_color = style["text_shadow"]
    for offset in range(12, 0, -1):
        alpha = int(40 * (1 - offset / 12))
        for dx in range(-offset, offset + 1, 2):
            for dy in range(-offset, offset + 1, 2):
                glow_draw.text(
                    (x_position + dx, y_position + dy),
                    text, font=font,
                    fill=(glow_color[0], glow_color[1], glow_color[2], alpha)
                )
    canvas_rgba = Image.alpha_composite(canvas_rgba, glow_layer)

    # Text outline (thick black border)
    text_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)
    outline_width = max(4, font_size // 18)
    for dx in range(-outline_width, outline_width + 1):
        for dy in range(-outline_width, outline_width + 1):
            if dx * dx + dy * dy <= outline_width * outline_width:
                text_draw.text(
                    (x_position + dx, y_position + dy),
                    text, font=font,
                    fill=(0, 0, 0, 255)
                )

    # Main text fill
    text_draw.text(
        (x_position, y_position),
        text, font=font,
        fill=(style["text_color"][0], style["text_color"][1], style["text_color"][2], 255)
    )

    canvas_rgba = Image.alpha_composite(canvas_rgba, text_layer)
    return canvas_rgba.convert("RGB")


def compose_thumbnail(
    text: str,
    left_logo_slug: str,
    right_logo_slug: str,
    style_name: str = "electro_black",
    include_face: bool = True,
    output_path: Path = None,
) -> Path:
    """Compose a complete thumbnail from components."""
    style = STYLES[style_name]

    # 1. Background
    canvas = create_gradient_bg(style_name)

    # 2. Glow behind icon positions
    left_center = (220, 200)
    right_center = (1060, 200)
    canvas = add_glow(canvas, left_center, style["glow_left"], radius=180)
    canvas = add_glow(canvas, right_center, style["glow_right"], radius=180)

    # 3. Face (centered, behind icons)
    if include_face:
        face = load_face(max_height=500)
        if face:
            face_x = (WIDTH - face.width) // 2
            face_y = HEIGHT - face.height - 60
            mask = create_face_mask(face)
            canvas_rgba = canvas.convert("RGBA")
            canvas_rgba.paste(face, (face_x, face_y), mask)
            canvas = canvas_rgba.convert("RGB")

    # 4. Logos with app-icon backgrounds
    left_logo = load_logo(left_logo_slug, size=120)
    right_logo = load_logo(right_logo_slug, size=120)

    canvas_rgba = canvas.convert("RGBA")

    if left_logo:
        icon_left = add_icon_bg(left_logo, (45, 40, 55, 230), padding=22, radius=28)
        lx = left_center[0] - icon_left.width // 2
        ly = left_center[1] - icon_left.height // 2
        canvas_rgba.paste(icon_left, (lx, ly), icon_left)

    if right_logo:
        icon_right = add_icon_bg(right_logo, (45, 40, 55, 230), padding=22, radius=28)
        rx = right_center[0] - icon_right.width // 2
        ry = right_center[1] - icon_right.height // 2
        canvas_rgba.paste(icon_right, (rx, ry), icon_right)

    canvas = canvas_rgba.convert("RGB")

    # 5. Text
    canvas = render_text(canvas, text, style_name)

    # Save
    if output_path is None:
        output_path = OUTPUT_BASE / "pil_test" / "thumbnail.png"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, "PNG", quality=95)
    size_kb = output_path.stat().st_size / 1024
    print(f"  Saved: {output_path} ({size_kb:.0f} KB)")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="PIL-based thumbnail compositor")
    parser.add_argument("--text", help="Text to render on thumbnail")
    parser.add_argument("--left-logo", help="Left logo slug")
    parser.add_argument("--right-logo", help="Right logo slug")
    parser.add_argument("--style", default="electro_black",
                        choices=list(STYLES.keys()))
    parser.add_argument("--no-face", action="store_true")
    parser.add_argument("--prompts-file", help="Load concepts from prompts.json")
    parser.add_argument("--output-dir", help="Output directory")
    args = parser.parse_args()

    if args.prompts_file:
        with open(args.prompts_file) as f:
            prompts = json.load(f)
        output_dir = Path(args.output_dir) if args.output_dir else OUTPUT_BASE / "pil-compose"
        output_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n=== PIL Thumbnail Compositor ===")
        print(f"Prompts: {args.prompts_file}")
        print(f"Output: {output_dir}\n")

        for i, p in enumerate(prompts):
            text = p.get("text_on_image", "TEXT")
            logos = p.get("logos_used", [])
            left = logos[0] if len(logos) > 0 else ""
            right = logos[1] if len(logos) > 1 else ""
            style = p.get("archetype", "electro_black")
            out = output_dir / f"thumbnail_{i+1}.png"
            print(f"  [{i+1}] {style} — \"{text}\" ({left} + {right})")
            compose_thumbnail(text, left, right, style, not args.no_face, out)

        print(f"\nGenerated {len(prompts)} thumbnails to {output_dir}")
    elif args.text and args.left_logo and args.right_logo:
        output_dir = Path(args.output_dir) if args.output_dir else OUTPUT_BASE / "pil-compose"
        out = output_dir / "thumbnail.png"
        compose_thumbnail(args.text, args.left_logo, args.right_logo, args.style, not args.no_face, out)
    else:
        parser.error("Provide --prompts-file OR (--text, --left-logo, --right-logo)")


if __name__ == "__main__":
    main()
