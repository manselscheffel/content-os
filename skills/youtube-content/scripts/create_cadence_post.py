#!/usr/bin/env python3
"""Generate carousel-style slide content for YouTube community tab or shorts.

Creates 4-8 slides with visual hierarchy notes for image generation.
Maintains posting cadence between main video uploads without filming.

Usage:
    python3 create_cadence_post.py --topic "Why most AI agents fail" --slides 6
    python3 create_cadence_post.py --topic "5 Claude Code tricks" --slides 5 --save

Output: JSON with slide content and visual hierarchy notes.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Plugin root: scripts/ -> youtube-content/ -> skills/ -> content-os root
PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, PLUGIN_ROOT)
from lib.db import execute_one


def save_to_db(title, slides, topic):
    """Save cadence post to content_items."""
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
           VALUES ('youtube', 'cadence_post', 'draft', %s, %s, %s, 'manual')
           RETURNING id, title, status""",
        (title, json.dumps(slides, indent=2), json.dumps(metadata)),
    )
    return row


def main():
    parser = argparse.ArgumentParser(description="Generate cadence post slides")
    parser.add_argument("--topic", required=True, help="Topic for the carousel")
    parser.add_argument("--slides", type=int, default=6, help="Number of slides (4-8)")
    parser.add_argument("--save", action="store_true", help="Save to content_items DB")

    args = parser.parse_args()

    slide_count = max(4, min(8, args.slides))

    # Generate slide structure template
    # Claude will fill this in with actual content based on the topic
    slide_template = {
        "topic": args.topic,
        "requested_slides": slide_count,
        "structure": [
            {
                "slide": 1,
                "type": "hook",
                "primary_text": "[Hook/title — provocative or curiosity-driven]",
                "supporting_text": None,
                "visual_notes": "Large bold text, branded color background, no supporting text",
            },
        ],
    }

    # Add content slides
    for i in range(2, slide_count):
        slide_template["structure"].append({
            "slide": i,
            "type": "content",
            "primary_text": f"[Key point {i-1} — large bold phrase]",
            "supporting_text": "[1-2 line explanation, smaller text]",
            "visual_notes": "Primary text large and bold, supporting text smaller and lighter",
        })

    # Add CTA slide
    slide_template["structure"].append({
        "slide": slide_count,
        "type": "cta",
        "primary_text": "[Summary or call to action]",
        "supporting_text": "Follow for more | Watch the full video | What do you think?",
        "visual_notes": "CTA prominent, include channel branding",
    })

    slide_template["design_guidelines"] = {
        "dimensions": "1080x1080 (square) or 1080x1350 (portrait)",
        "primary_font_size": "48-64px, bold",
        "supporting_font_size": "24-32px, regular weight",
        "background": "Dark with subtle gradient or solid brand color",
        "readability": "Each slide readable on mobile in 2 seconds",
        "brand_colors": "Refer to thumbnail-generator brand kit",
    }

    output = {"success": True, "cadence_post": slide_template}

    if args.save:
        try:
            row = save_to_db(
                f"Cadence: {args.topic[:80]}",
                slide_template["structure"],
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
