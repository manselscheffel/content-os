#!/usr/bin/env python3
"""
Tool: Rising Videos Detector
Purpose: Find recent YouTube uploads with high view velocity — signals hot topics.
         Uses youtube-analytics MCP search_videos when available, otherwise outputs
         instructions for manual MCP invocation.

Usage:
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/fetch_rising_videos.py
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/fetch_rising_videos.py --keywords "keyword1,keyword2"
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/fetch_rising_videos.py --input videos.json
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/fetch_rising_videos.py --text

Dependencies: PyYAML

Note: This script is designed to be called by the skill workflow. When run
      interactively, the SKILL.md instructs Claude to use the youtube-analytics MCP
      directly and then pipe the results through this script for velocity calculation.

      For standalone/cron use, pass pre-fetched video data via --input.

Output: JSON with videos array sorted by view_velocity
"""

import sys
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path

import os
import yaml

# Resolve plugin root for portable paths
PLUGIN_ROOT = os.environ.get(
    "CLAUDE_PLUGIN_ROOT",
    str(Path(__file__).resolve().parent.parent.parent)
)
SKILL_DIR = Path(PLUGIN_ROOT) / "skills" / "youtube-seo"
PROJECT_ROOT = Path(PLUGIN_ROOT).parent  # project root
CONFIG_PATH = SKILL_DIR / "references" / "seed_keywords.yaml"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def calculate_velocity(videos, max_age_hours=72, velocity_threshold=500):
    """Calculate view velocity for each video and flag hot ones."""
    now = datetime.now(timezone.utc)
    results = []

    for video in videos:
        published = video.get("published_at", video.get("publishedAt", ""))
        views = int(video.get("views", video.get("viewCount", 0)))
        video_id = video.get("video_id", video.get("videoId", video.get("id", "")))
        title = video.get("title", "")
        channel = video.get("channel", video.get("channelTitle", ""))
        keyword = video.get("keyword_match", video.get("keyword", ""))

        if not published or not video_id:
            continue

        # Parse published date
        try:
            if "T" in published:
                pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
            else:
                pub_dt = datetime.strptime(published, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            continue

        hours_since = (now - pub_dt).total_seconds() / 3600

        # Skip videos older than max age
        if hours_since > max_age_hours or hours_since < 0.5:
            continue

        velocity = views / hours_since if hours_since > 0 else 0

        results.append({
            "video_id": video_id,
            "title": title,
            "channel": channel,
            "published_at": published,
            "views": views,
            "hours_since_upload": round(hours_since, 1),
            "view_velocity": round(velocity, 1),
            "is_hot": velocity >= velocity_threshold,
            "keyword_match": keyword,
        })

    # Sort by velocity descending
    results.sort(key=lambda x: x["view_velocity"], reverse=True)
    return results


def run(keywords=None, input_file=None, text_output=False, save=False):
    """Run the rising videos detector."""
    config = load_config()
    settings = config.get("settings", {})
    max_age = settings.get("rising_video_max_age_hours", 72)
    threshold = settings.get("velocity_threshold", 500)

    if input_file:
        with open(input_file) as f:
            data = json.load(f)
        videos = data if isinstance(data, list) else data.get("videos", data.get("items", []))
    else:
        # When no input file, output MCP instructions
        if keywords:
            seed_keywords = [k.strip() for k in keywords.split(",")]
        else:
            seed_keywords = config.get("seed_keywords", [])

        result = {
            "success": True,
            "mode": "mcp_required",
            "message": "Use youtube-analytics MCP search_videos for each keyword, then pass results via --input",
            "keywords_to_search": seed_keywords,
            "instructions": [
                f"For each keyword, use MCP: search_videos(query='{kw}', max_results=10)"
                for kw in seed_keywords[:5]  # Show first 5 as examples
            ],
        }
        print(json.dumps(result, indent=2))
        return result

    processed = calculate_velocity(videos, max_age_hours=max_age, velocity_threshold=threshold)
    hot_videos = [v for v in processed if v["is_hot"]]

    result = {
        "success": True,
        "videos": processed,
        "count": len(processed),
        "hot_count": len(hot_videos),
        "velocity_threshold": threshold,
        "max_age_hours": max_age,
    }

    if save:
        output_path = PROJECT_ROOT / ".tmp" / "youtube_seo_videos.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        result["saved_to"] = str(output_path)

    if text_output:
        print(f"\n=== Rising Videos (threshold: {threshold} views/hr) ===\n")
        for v in processed[:20]:
            hot = " 🔥 HOT" if v["is_hot"] else ""
            print(f"  {v['view_velocity']:,.0f} v/hr | {v['views']:,} views | {v['hours_since_upload']}h ago{hot}")
            print(f"    {v['title']}")
            print(f"    {v['channel']} | keyword: {v['keyword_match']}")
            print()
    else:
        print(json.dumps(result, indent=2))

    return result


def main():
    parser = argparse.ArgumentParser(description="Detect rising YouTube videos by view velocity")
    parser.add_argument("--keywords", help="Comma-separated keywords (overrides config)")
    parser.add_argument("--input", metavar="FILE", help="Pre-fetched video data JSON")
    parser.add_argument("--save", action="store_true", help="Save output to .tmp/")
    parser.add_argument("--text", action="store_true", help="Human-readable output")

    args = parser.parse_args()
    result = run(keywords=args.keywords, input_file=args.input,
                 text_output=args.text, save=args.save)

    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
