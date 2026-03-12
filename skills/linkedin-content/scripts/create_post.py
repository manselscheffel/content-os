#!/usr/bin/env python3
"""Generate a LinkedIn post structure for a given category and topic.

Provides the framework template and context file paths. Claude fills in
the actual content using voice and framework files.

Usage:
    python3 create_post.py --category contrarian --topic "Why most AI agents fail"
    python3 create_post.py --category video_drop --topic "New video on Claude Code" --video-url "https://..."
    python3 create_post.py --category list --topic "5 things I stopped doing"

Output: JSON with framework template, context file paths, and post metadata.
"""

import argparse
import json
import sys
from pathlib import Path

PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PROJECT_ROOT = Path.cwd()

CATEGORIES = {
    "contrarian": {
        "day": "Thursday",
        "char_range": "800-1200",
        "structure": [
            "Hook — State the common belief or industry trope (2 lines)",
            "Twist — Undercut with reality using a vivid, absurd analogy",
            "Problem — What's actually broken (2-3 short lines)",
            "Bridge — 'I made a video about...' or 'Here's what I've found...'",
            "CTA — 'Watch before [humorous consequence]'",
        ],
    },
    "video_drop": {
        "day": "Friday",
        "char_range": "400-600",
        "structure": [
            "Insight hook — Something you tested, discovered, or found surprising",
            "What happened — The unexpected result (2-3 lines)",
            "Bridge — Natural reference to the video",
            "CTA — Short command",
        ],
    },
    "psp": {
        "day": "Wednesday",
        "char_range": "1000-1500",
        "structure": [
            "Problem — State the specific problem (1-2 lines)",
            "Agitate — Cost, side effects, consequences (3-4 lines)",
            "Solution — Your framework or approach (numbered, 3-5 points)",
            "Proof — Numbers, case study, or experience marker",
            "CTA — Question to prompt comments",
        ],
    },
    "new_tool": {
        "day": "Tuesday",
        "char_range": "600-800",
        "structure": [
            "Hook — What changed in your workflow",
            "What it does — 2-3 sentences, plain language",
            "Why it matters — 3 bullets max",
            "Honest verdict — Including limitations",
            "Question — 'Have you tried it yet?'",
        ],
    },
    "motivation": {
        "day": "Monday",
        "char_range": "800-1200",
        "structure": [
            "Vulnerable hook — Admission that sounds wrong or surprising",
            "Story — Specific sensory details, internal monologue, short punchy lines",
            "The lesson — What it taught you",
            "What they should take — Direct address to reader",
        ],
    },
    "story": {
        "day": "Saturday",
        "char_range": "800-1200",
        "structure": [
            "Before — Where things were / what the problem was",
            "Bridge — What you did (the build, decision, pivot)",
            "After — The result with specifics",
            "Takeaway — One memorable line",
        ],
    },
    "list": {
        "day": "Sunday",
        "char_range": "600-800",
        "structure": [
            "Title hook — The list premise (e.g., '7 things I stopped doing')",
            "Items — One line each, punchy, no explanation needed",
            "Closer — 'Which one hits hardest?' or 'What would you add?'",
        ],
    },
}

CONTEXT_FILES = {
    "voice_core": "context/my-voice.md",
    "voice_linkedin": "context/linkedin/voice.md",
    "frameworks": "context/linkedin/frameworks.md",
    "examples": "context/linkedin/examples.md",
}


def main():
    parser = argparse.ArgumentParser(description="Generate LinkedIn post structure")
    parser.add_argument(
        "--category",
        required=True,
        choices=list(CATEGORIES.keys()),
        help="Post category",
    )
    parser.add_argument("--topic", required=True, help="Post topic")
    parser.add_argument("--video-url", help="Video URL (for video_drop category)")
    parser.add_argument("--save", action="store_true", help="Save to DB via content_db.py")

    args = parser.parse_args()

    cat = CATEGORIES[args.category]

    output = {
        "success": True,
        "category": args.category,
        "topic": args.topic,
        "calendar_day": cat["day"],
        "target_char_range": cat["char_range"],
        "framework": {
            "structure": cat["structure"],
        },
        "context_files": CONTEXT_FILES,
        "formatting_rules": {
            "mobile_fold": "First 140 chars must land the hook",
            "paragraphs": "Never longer than 2 lines",
            "white_space": "Blank line between every thought",
            "bolding": "Max 1 phrase per section",
            "emojis": "Only pointing-down hand at end for video links",
            "length": cat["char_range"] + " characters",
        },
        "instructions": (
            "Claude should read the context files listed above, then write the post "
            "following the framework structure. Match the quality and tone of the "
            "example posts. Social links, hashtags, and about text come from "
            ".claude/content-os.local.md config."
        ),
    }

    if args.video_url:
        output["video_url"] = args.video_url

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
