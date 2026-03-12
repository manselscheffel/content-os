#!/usr/bin/env python3
"""Generate a complete YouTube video description from components.

Footer content (connect links, about text, hashtags) is loaded from config.
See .claude/content-os.local.md for configuration.

Usage:
    python3 generate_description.py --title "Video Title" --summary "2-3 sentences" \
        --timestamps-file .tmp/timestamps.json --resources '["tool1", "tool2"]'

Output: Markdown-formatted YouTube description ready to paste.
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Plugin root: scripts/ -> youtube-content/ -> skills/ -> content-os root
PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, PLUGIN_ROOT)

try:
    from lib.config import get_config
    config = get_config()
except ImportError:
    config = None

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
TEMPLATE_PATH = SKILL_DIR / "references" / "description_template.md"


def get_footer_config():
    """Load footer content from config, with fallback defaults."""
    if config:
        footer = config.get("youtube", {}).get("description_footer", {})
        return {
            "connect_links": footer.get("connect_links", [
                "Community: [Your community link]",
                "LinkedIn: [Your LinkedIn URL]",
                "Newsletter: [Your newsletter link]",
            ]),
            "about_text": footer.get("about_text",
                "[Your about text — configure in .claude/content-os.local.md]"
            ),
            "base_hashtags": footer.get("hashtags",
                "#AI #AIAutomation #AICoding #BuildWithAI"
            ),
        }

    return {
        "connect_links": [
            "Community: [Your community link]",
            "LinkedIn: [Your LinkedIn URL]",
            "Newsletter: [Your newsletter link]",
        ],
        "about_text": "[Your about text — configure in .claude/content-os.local.md]",
        "base_hashtags": "#AI #AIAutomation #AICoding #BuildWithAI",
    }


def format_timestamps(timestamps_data):
    """Format timestamps into description-ready text."""
    if not timestamps_data:
        return ""

    lines = []
    segments = timestamps_data.get("segments", [])
    for seg in segments:
        time = seg.get("time", seg.get("timestamp", ""))
        label = seg.get("label", seg.get("text", "")[:60])
        if time and label:
            lines.append(f"{time} - {label}")

    return "\n".join(lines) if lines else ""


def main():
    parser = argparse.ArgumentParser(description="Generate YouTube description")
    parser.add_argument("--title", required=True, help="Video title")
    parser.add_argument("--summary", help="2-3 sentence summary")
    parser.add_argument("--timestamps-file", help="Path to timestamps JSON")
    parser.add_argument("--timestamps-json", help="Timestamps as JSON string")
    parser.add_argument("--resources", help="JSON array of resources mentioned")
    parser.add_argument("--hashtags", help="Comma-separated extra hashtags")

    args = parser.parse_args()

    footer_config = get_footer_config()

    # Build description sections
    sections = []

    # Summary
    if args.summary:
        sections.append(args.summary)
    else:
        sections.append(f"[Summary for: {args.title}]")

    sections.append("")

    # Timestamps
    timestamps_data = None
    if args.timestamps_file:
        try:
            with open(args.timestamps_file) as f:
                timestamps_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
    elif args.timestamps_json:
        try:
            timestamps_data = json.loads(args.timestamps_json)
        except json.JSONDecodeError:
            pass

    if timestamps_data:
        ts_text = format_timestamps(timestamps_data)
        if ts_text:
            sections.append("=== TIMESTAMPS ===")
            sections.append(ts_text)
            sections.append("")

    # Resources
    if args.resources:
        try:
            resources = json.loads(args.resources)
            if resources:
                sections.append("=== RESOURCES MENTIONED ===")
                for r in resources:
                    sections.append(f"- {r}")
                sections.append("")
        except json.JSONDecodeError:
            pass

    # Footer — loaded from config
    sections.append("=== CONNECT ===")
    for link in footer_config["connect_links"]:
        sections.append(link)
    sections.append("")
    sections.append("=== ABOUT ===")
    sections.append(footer_config["about_text"])
    sections.append("")

    # Hashtags
    base_tags = footer_config["base_hashtags"]
    if args.hashtags:
        extra = " ".join(f"#{t.strip().replace(' ', '')}" for t in args.hashtags.split(","))
        sections.append(f"{base_tags} {extra}")
    else:
        sections.append(base_tags)

    description = "\n".join(sections)

    output = {
        "success": True,
        "title": args.title,
        "description": description,
        "char_count": len(description),
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
