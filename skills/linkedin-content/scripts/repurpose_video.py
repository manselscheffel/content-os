#!/usr/bin/env python3
"""Analyze a YouTube video for LinkedIn repurpose angles.

Checks if youtube-content's post-publish already queued repurpose ideas
in ops.content_items. If found, returns those. If not, provides a template
for Claude to analyze the transcript and generate posts.

Usage:
    python3 repurpose_video.py --video-url "https://youtube.com/watch?v=abc123" --title "Video Title"
    python3 repurpose_video.py --transcript-file .tmp/transcript.txt --title "Video Title"

Output: JSON with existing ideas (if any) and framework for generating new ones.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from datetime import datetime

# PLUGIN_ROOT is 3 levels up: scripts/ -> linkedin-content/ -> skills/ -> root
PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))
from lib.db import execute


CATEGORIES = [
    "contrarian", "video_drop", "psp", "new_tool",
    "motivation", "story", "list",
]

CATEGORY_ANGLES = {
    "video_drop": "Announce the video — lead with an insight, not 'new video!'",
    "contrarian": "Challenge a common belief from the video with a brutal reality check",
    "psp": "Extract a problem/solution framework from the video's teaching",
    "new_tool": "If a tool was featured, share the honest verdict",
    "motivation": "Pull a vulnerable personal moment or lesson",
    "story": "Extract a build log or behind-the-scenes moment",
    "list": "Distill key points into a numbered list post",
}


def extract_video_id(url_or_id):
    """Extract YouTube video ID from URL or bare ID."""
    if not url_or_id:
        return None
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url_or_id):
        return url_or_id
    match = re.search(r'[?&]v=([a-zA-Z0-9_-]{11})', url_or_id)
    if match:
        return match.group(1)
    match = re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})', url_or_id)
    if match:
        return match.group(1)
    return url_or_id


def find_existing_ideas(video_url, title):
    """Check if post-publish already queued repurpose ideas."""
    ideas = []

    if video_url:
        rows = execute(
            """SELECT id, category, status, title, body, metadata
               FROM ops.content_items
               WHERE platform = 'linkedin'
                 AND source_type = 'repurpose'
                 AND metadata->>'source_video_url' = %s
               ORDER BY created_at DESC""",
            (video_url,),
        )
        ideas.extend([_serialize(r) for r in rows])

    if not ideas and title:
        rows = execute(
            """SELECT id, category, status, title, body, metadata
               FROM ops.content_items
               WHERE platform = 'linkedin'
                 AND source_type = 'repurpose'
                 AND metadata->>'source_video_title' = %s
               ORDER BY created_at DESC""",
            (title,),
        )
        ideas.extend([_serialize(r) for r in rows])

    return ideas


def _serialize(row):
    if not row:
        return None
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


def main():
    parser = argparse.ArgumentParser(description="Repurpose YouTube video for LinkedIn")
    parser.add_argument("--video-url", help="YouTube video URL")
    parser.add_argument("--title", required=True, help="Video title")
    parser.add_argument("--transcript-file", help="Path to transcript file")

    args = parser.parse_args()

    video_url = args.video_url or ""
    video_id = extract_video_id(video_url)

    # Check for existing repurpose ideas
    existing = find_existing_ideas(video_url, args.title)

    # Load transcript if available
    transcript_preview = None
    if args.transcript_file:
        try:
            text = Path(args.transcript_file).read_text()
            transcript_preview = text[:2000] + ("..." if len(text) > 2000 else "")
        except FileNotFoundError:
            pass

    output = {
        "success": True,
        "video_url": video_url,
        "video_id": video_id,
        "title": args.title,
        "existing_ideas": existing,
        "existing_count": len(existing),
        "has_transcript": transcript_preview is not None,
        "transcript_preview": transcript_preview,
        "generation_guide": {
            "requirements": [
                "Generate 3-5 posts from different angles",
                "One MUST be video_drop category (announcement post)",
                "Remaining posts should be standalone (work without watching the video)",
                "Each post should be a different category",
                "Each post should target a different insight from the video",
            ],
            "category_angles": CATEGORY_ANGLES,
            "context_files": {
                "voice_core": "context/my-voice.md",
                "voice_linkedin": "context/linkedin/voice.md",
                "frameworks": "context/linkedin/frameworks.md",
                "examples": "context/linkedin/examples.md",
            },
        },
    }

    if existing:
        output["note"] = (
            f"Found {len(existing)} existing repurpose ideas from post-publish. "
            "Claude should use these as starting points and generate full posts."
        )
    else:
        output["note"] = (
            "No existing repurpose ideas found. Claude should analyze the transcript "
            "and generate 3-5 categorized posts from scratch."
        )

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
