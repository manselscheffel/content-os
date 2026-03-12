#!/usr/bin/env python3
"""Orchestrate the post-publish workflow for a YouTube video.

Chains: transcript fetch -> timestamp extraction -> description generation -> DB update.

Usage:
    python3 post_publish.py --video-url "https://youtube.com/watch?v=abc123" --title "Video Title"
    python3 post_publish.py --video-id abc123 --title "Video Title"

Note: Transcript fetching uses youtube-analytics MCP (invoked by Claude, not this script).
This script handles the deterministic parts: timestamp extraction, description assembly, DB ops.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from datetime import datetime, timezone
import re

# Plugin root: scripts/ -> youtube-content/ -> skills/ -> content-os root
PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parent.parent.parent))
SCRIPTS_DIR = Path(__file__).resolve().parent

sys.path.insert(0, PLUGIN_ROOT)
from lib.db import execute, execute_one


def extract_video_id(url_or_id):
    """Extract YouTube video ID from URL or bare ID."""
    if not url_or_id:
        return None

    # Already a bare ID
    if re.match(r'^[a-zA-Z0-9_-]{11}$', url_or_id):
        return url_or_id

    # youtube.com/watch?v=
    match = re.search(r'[?&]v=([a-zA-Z0-9_-]{11})', url_or_id)
    if match:
        return match.group(1)

    # youtu.be/
    match = re.search(r'youtu\.be/([a-zA-Z0-9_-]{11})', url_or_id)
    if match:
        return match.group(1)

    return url_or_id  # Return as-is, let caller handle


def run_script(script_name, args=None):
    """Run a sibling script and return parsed JSON output."""
    script_path = SCRIPTS_DIR / script_name
    cmd = ["python3", str(script_path)] + (args or [])

    result = subprocess.run(
        cmd, capture_output=True, text=True, check=False, cwd=str(PLUGIN_ROOT)
    )

    if result.returncode != 0:
        return {"success": False, "error": result.stderr.strip() or "Script failed"}

    # Extract JSON from stdout — search from end to skip logs/warnings before JSON
    stdout = result.stdout.strip()
    json_start = stdout.rfind("{")
    while json_start >= 0:
        try:
            return json.loads(stdout[json_start:])
        except json.JSONDecodeError:
            json_start = stdout.rfind("{", 0, json_start)

    return {"success": False, "error": "No JSON in output", "raw": stdout[:500]}


def find_content_item(video_url, title):
    """Find the content item for this video in the DB."""
    # Try by URL in metadata
    if video_url:
        row = execute_one(
            """SELECT * FROM ops.content_items
               WHERE platform = 'youtube' AND content_type = 'video'
                 AND metadata->>'video_url' = %s
               LIMIT 1""",
            (video_url,),
        )
        if row:
            return row

    # Try by title
    if title:
        row = execute_one(
            """SELECT * FROM ops.content_items
               WHERE platform = 'youtube' AND content_type = 'video'
                 AND title = %s
               ORDER BY created_at DESC
               LIMIT 1""",
            (title,),
        )
        if row:
            return row

    return None


def main():
    parser = argparse.ArgumentParser(description="Post-publish workflow orchestrator")
    parser.add_argument("--video-url", help="YouTube video URL")
    parser.add_argument("--video-id", help="YouTube video ID")
    parser.add_argument("--title", required=True, help="Video title")
    parser.add_argument("--transcript-file", help="Path to transcript file (if already fetched)")
    parser.add_argument("--resources", help="JSON array of resources mentioned")
    parser.add_argument("--summary", help="2-3 sentence summary")

    args = parser.parse_args()

    video_id = args.video_id or extract_video_id(args.video_url)
    video_url = args.video_url or f"https://youtube.com/watch?v={video_id}"

    results = {
        "video_id": video_id,
        "video_url": video_url,
        "title": args.title,
        "steps": {},
    }

    # Step 1: Extract timestamps (if transcript available)
    if args.transcript_file:
        ts_result = run_script("extract_timestamps.py", [
            "--transcript-file", args.transcript_file
        ])
        results["steps"]["timestamps"] = ts_result

        # Save timestamps to temp file for description generator
        if ts_result.get("success"):
            ts_path = str(Path(".tmp") / "timestamps.json")
            Path(ts_path).parent.mkdir(exist_ok=True)
            with open(ts_path, "w") as f:
                json.dump(ts_result, f)
    else:
        results["steps"]["timestamps"] = {
            "success": False,
            "note": "No transcript file provided. Claude should fetch via youtube-analytics MCP "
                    "get_video_transcript, save to .tmp/transcript.txt, then rerun with --transcript-file."
        }

    # Step 2: Generate description
    desc_args = ["--title", args.title]
    if args.summary:
        desc_args.extend(["--summary", args.summary])
    if args.transcript_file and results["steps"].get("timestamps", {}).get("success"):
        desc_args.extend(["--timestamps-file", str(Path(".tmp") / "timestamps.json")])
    if args.resources:
        desc_args.extend(["--resources", args.resources])

    desc_result = run_script("generate_description.py", desc_args)
    results["steps"]["description"] = desc_result

    # Step 3: Update DB record
    content_item = find_content_item(video_url, args.title)
    if content_item:
        try:
            metadata = dict(content_item.get("metadata") or {})
            metadata["video_url"] = video_url
            metadata["video_id"] = video_id
            metadata["published_at"] = datetime.now(timezone.utc).isoformat()
            if results["steps"].get("timestamps", {}).get("success"):
                metadata["timestamps"] = results["steps"]["timestamps"].get("segments", [])

            execute(
                """UPDATE ops.content_items
                   SET status = 'published', published_at = NOW(),
                       metadata = %s, updated_at = NOW()
                   WHERE id = %s""",
                (json.dumps(metadata), content_item["id"]),
                fetch=False,
            )
            results["steps"]["db_update"] = {
                "success": True,
                "content_item_id": content_item["id"],
                "status": "published",
            }
        except Exception as e:
            results["steps"]["db_update"] = {"success": False, "error": str(e)}
    else:
        results["steps"]["db_update"] = {
            "success": False,
            "note": "No matching content_item found. Claude should create one via content_db.py --action insert."
        }

    # Step 4: Note about LinkedIn repurpose
    results["steps"]["linkedin_repurpose"] = {
        "note": "Claude should analyze the transcript and create 3-5 LinkedIn repurpose ideas "
                "via content_db.py --action insert --platform linkedin. "
                "One must be category=video_drop (announcement post)."
    }

    results["success"] = True
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
