#!/usr/bin/env python3
"""Render carousel slides to PDF using Playwright.

Takes a JSON file with slide content, renders via HTML template
using Jinja2, and produces a LinkedIn-ready PDF using Playwright's
headless Chromium.

LinkedIn carousels are multi-page PDFs where each page = one swipeable slide.
Dimensions: 1080x1350px (portrait 4:5 ratio) at 300 DPI equivalent.

Usage:
    python3 render_carousel.py --input slides.json --output carousel.pdf
    python3 render_carousel.py --input slides.json  # defaults to deliverables/carousels/

Input JSON format:
{
    "slides": [
        {"type": "title", "primary_text": "...", "supporting_text": "..."},
        {"type": "content", "primary_text": "...", "supporting_text": "...", "point_number": 1},
        {"type": "summary", "primary_text": "...", "takeaways": ["...", "..."]},
        {"type": "cta", "primary_text": "..."}
    ],
    "theme": {  // optional — overrides default colors
        "bg_color": "#0a0a0a",
        "accent_color": "#38bdf8",
        "text_color": "#f8fafc",
        "muted_color": "#94a3b8"
    }
}
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

# Jinja2 is part of the standard Python ecosystem — used for HTML templating
from jinja2 import Template
from playwright.sync_api import sync_playwright


# Default theme: elegant black with sky blue accents
DEFAULT_THEME = {
    "bg_color": "#0a0a0a",
    "accent_color": "#38bdf8",
    "text_color": "#f8fafc",
    "muted_color": "#94a3b8",
}

# PLUGIN_ROOT is 3 levels up: scripts/ -> linkedin-content/ -> skills/ -> root
SKILL_DIR = Path(__file__).resolve().parent.parent
PLUGIN_ROOT = SKILL_DIR.parent.parent
TEMPLATE_PATH = SKILL_DIR / "assets" / "carousel_template.html"
PROJECT_ROOT = Path.cwd()
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "deliverables" / "carousels"

SLIDE_WIDTH = 1080
SLIDE_HEIGHT = 1350


def load_template():
    """Load the Jinja2 HTML template."""
    if not TEMPLATE_PATH.exists():
        print(f"Error: Template not found at {TEMPLATE_PATH}", file=sys.stderr)
        sys.exit(1)
    return Template(TEMPLATE_PATH.read_text())


def render_html(template, slides, theme):
    """Render slides into a single HTML document."""
    return template.render(slides=slides, **theme)


def html_to_pdf(html_content, output_path, slide_count):
    """Use Playwright to convert HTML to a multi-page PDF."""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(
            viewport={"width": SLIDE_WIDTH, "height": SLIDE_HEIGHT}
        )

        page.set_content(html_content, wait_until="networkidle")

        # Wait for fonts to load
        page.wait_for_timeout(1000)

        page.pdf(
            path=str(output_path),
            width=f"{SLIDE_WIDTH}px",
            height=f"{SLIDE_HEIGHT}px",
            print_background=True,
            margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
        )

        # Also generate a preview PNG of the first slide (for thumbnails/previews)
        preview_path = output_path.with_suffix(".preview.png")
        page.set_viewport_size({"width": SLIDE_WIDTH, "height": SLIDE_HEIGHT})
        page.screenshot(
            path=str(preview_path),
            clip={"x": 0, "y": 0, "width": SLIDE_WIDTH, "height": SLIDE_HEIGHT},
        )

        browser.close()

    return output_path, preview_path


def main():
    parser = argparse.ArgumentParser(description="Render carousel slides to PDF")
    parser.add_argument("--input", required=True, help="Path to slides JSON file")
    parser.add_argument("--output", help="Output PDF path (default: deliverables/carousels/)")
    parser.add_argument("--preview-html", action="store_true",
                        help="Also save the rendered HTML for debugging")

    args = parser.parse_args()

    # Load slide data
    input_path = Path(args.input)
    if not input_path.exists():
        print(json.dumps({"success": False, "error": f"Input file not found: {args.input}"}))
        sys.exit(1)

    with open(input_path) as f:
        data = json.load(f)

    slides = data.get("slides", [])
    if not slides:
        print(json.dumps({"success": False, "error": "No slides found in input JSON"}))
        sys.exit(1)

    # Merge theme with defaults
    theme = {**DEFAULT_THEME, **data.get("theme", {})}

    # Determine output path — project-relative, not plugin-relative
    if args.output:
        output_path = Path(args.output)
    else:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_topic = data.get("topic", "carousel")[:40].replace(" ", "_").lower()
        safe_topic = "".join(c for c in safe_topic if c.isalnum() or c == "_")
        output_path = DEFAULT_OUTPUT_DIR / f"{safe_topic}_{timestamp}.pdf"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Load template and render HTML
    template = load_template()
    html_content = render_html(template, slides, theme)

    # Optionally save HTML for debugging
    if args.preview_html:
        html_path = output_path.with_suffix(".html")
        html_path.write_text(html_content)

    # Render to PDF
    pdf_path, preview_path = html_to_pdf(html_content, output_path, len(slides))

    result = {
        "success": True,
        "pdf_path": str(pdf_path),
        "preview_path": str(preview_path),
        "slide_count": len(slides),
        "dimensions": f"{SLIDE_WIDTH}x{SLIDE_HEIGHT}px",
        "file_size_kb": round(pdf_path.stat().st_size / 1024, 1),
        "theme": theme,
    }

    if args.preview_html:
        result["html_path"] = str(output_path.with_suffix(".html"))

    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
