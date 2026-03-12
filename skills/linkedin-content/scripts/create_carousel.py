#!/usr/bin/env python3
"""Generate carousel slide content for LinkedIn.

Takes a topic and generates actual slide content — real headlines and
supporting text, not placeholders. Output is JSON that feeds into
render_carousel.py for HTML->PDF conversion.

Usage:
    python3 create_carousel.py --topic "5 things AI code review actually catches" --slides 8
    python3 create_carousel.py --topic "The ATOM framework" --slides 10 --save

Output: JSON with slide content ready for rendering.
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

# PLUGIN_ROOT is 3 levels up: scripts/ -> linkedin-content/ -> skills/ -> root
PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))
from lib.db import execute_one


def save_to_db(title, slides, topic):
    """Save carousel to content_items."""
    metadata = {
        "slides": slides,
        "slide_count": len(slides),
        "topic": topic,
        "post_format": "carousel",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    row = execute_one(
        """INSERT INTO ops.content_items
           (platform, content_type, status, title, body, metadata, source_type)
           VALUES ('linkedin', 'carousel', 'draft', %s, %s, %s, 'manual')
           RETURNING id, title, status""",
        (title, json.dumps(slides, indent=2), json.dumps(metadata)),
    )
    return row


def main():
    parser = argparse.ArgumentParser(description="Generate LinkedIn carousel slides")
    parser.add_argument("--topic", required=True, help="Carousel topic")
    parser.add_argument("--slides", type=int, default=8, help="Number of slides (4-12)")
    parser.add_argument("--save", action="store_true", help="Save to content_items DB")

    args = parser.parse_args()
    slide_count = max(4, min(12, args.slides))

    # The script outputs the structure — Claude fills in the actual content
    # based on the topic, voice guide, and frameworks.
    # This keeps content generation in Claude's hands (where it belongs)
    # while the script handles structure, validation, and DB persistence.

    output = {
        "success": True,
        "topic": args.topic,
        "slide_count": slide_count,
        "instructions": {
            "what_to_do": (
                "Generate actual slide content for each slide below. "
                "Write real headlines and supporting text — not placeholders. "
                "Each headline should be punchy (5-8 words max). "
                "Supporting text is 1-2 lines max."
            ),
            "voice": "Read context/my-voice.md and context/linkedin/voice.md for tone.",
            "structure": [
                f"Slide 1: Title/hook slide — bold provocative headline + author name (from config)",
                *[f"Slide {i}: Content — one key point with supporting detail"
                  for i in range(2, slide_count - 1)],
                f"Slide {slide_count - 1}: Summary — recap 3-5 key takeaways",
                f"Slide {slide_count}: CTA — 'Follow for more' + engagement prompt",
            ],
        },
        "slide_template": {
            "slides": [
                {"slide": i + 1, "type": t, "primary_text": "", "supporting_text": ""}
                for i, t in enumerate(
                    ["title"]
                    + ["content"] * (slide_count - 3)
                    + ["summary", "cta"]
                )
            ]
        },
        "render_specs": {
            "dimensions": "1080x1350px (portrait 4:5)",
            "primary_font": "40-60pt bold sans-serif",
            "supporting_font": "20-28pt regular",
            "background": "#0a0a0a (near-black)",
            "accent_color": "#38bdf8 (sky blue)",
            "text_color": "#f8fafc (off-white)",
            "safe_zone": "15% from all edges (162px on 1080px width)",
        },
        "next_step": (
            "After Claude fills in the slide content, run render_carousel.py "
            "with the completed JSON to generate the PDF."
        ),
    }

    if args.save:
        try:
            row = save_to_db(
                f"Carousel: {args.topic[:80]}",
                output["slide_template"]["slides"],
                args.topic,
            )
            output["saved"] = True
            output["content_item_id"] = row["id"] if row else None
        except Exception as e:
            output["saved"] = False
            output["save_error"] = str(e)

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
