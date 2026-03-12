#!/usr/bin/env python3
"""
Tool: YouTube SEO Opportunity Scorer
Purpose: Combine signals from autocomplete suggestions, Google Trends, and rising
         videos into a single opportunity score per topic. Ranks content opportunities.

Usage:
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/score_opportunities.py
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/score_opportunities.py --text
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/score_opportunities.py --save

Dependencies: lib.db (dual-backend: SQLite default, Supabase Postgres optional)

Scoring:
    - New autocomplete suggestion:    +3 points
    - Google Trends breakout:         +5 points
    - Google Trends rising >200%:     +3 points
    - Google Trends rising >100%:     +1 point
    - High-velocity video exists:     +2 points
    - Rising query match:             +2 points
    - Multiple signal sources:        1.5x multiplier

Output: JSON with scored and ranked opportunities
"""

import sys
import os
import json
import argparse
from collections import defaultdict
from pathlib import Path

# Resolve plugin root for portable paths
PLUGIN_ROOT = os.environ.get(
    "CLAUDE_PLUGIN_ROOT",
    str(Path(__file__).resolve().parent.parent.parent)
)
SKILL_DIR = Path(PLUGIN_ROOT) / "skills" / "youtube-seo"
PROJECT_ROOT = Path(PLUGIN_ROOT).parent  # project root
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from trend_db import get_today_data


def normalize_topic(text):
    """Normalize a topic string for grouping similar terms."""
    return text.lower().strip()


def score_opportunities(data=None):
    """Score and rank content opportunities from all signals."""
    if data is None:
        data = get_today_data()

    if not data.get("success"):
        return {"success": False, "error": "Failed to load today's data"}

    # Collect all signals grouped by topic
    topics = defaultdict(lambda: {
        "score": 0,
        "signals": [],
        "signal_sources": set(),
        "keywords": set(),
        "details": {},
    })

    # Score new autocomplete suggestions
    for sug in data.get("new_suggestions", []):
        topic = normalize_topic(sug["suggestion"])
        seed = sug.get("seed_keyword", "")
        topics[topic]["score"] += 3
        topics[topic]["signals"].append(f"New autocomplete: '{sug['suggestion']}' (seed: {seed})")
        topics[topic]["signal_sources"].add("autocomplete")
        topics[topic]["keywords"].add(seed)
        topics[topic]["details"]["suggestion"] = sug["suggestion"]

    # Score Google Trends data
    for trend in data.get("trends", []):
        topic = normalize_topic(trend["keyword"])
        rising = trend.get("rising_percent", 0) or 0

        if trend.get("is_breakout"):
            topics[topic]["score"] += 5
            topics[topic]["signals"].append(f"Google Trends BREAKOUT: {trend['keyword']}")
        elif rising > 200:
            topics[topic]["score"] += 3
            topics[topic]["signals"].append(f"Google Trends rising {rising}%: {trend['keyword']}")
        elif rising > 100:
            topics[topic]["score"] += 1
            topics[topic]["signals"].append(f"Google Trends rising {rising}%: {trend['keyword']}")

        if trend.get("is_breakout") or rising > 100:
            topics[topic]["signal_sources"].add("trends")
            topics[topic]["keywords"].add(trend["keyword"])
            topics[topic]["details"]["interest_score"] = trend.get("interest_score", 0)
            topics[topic]["details"]["rising_percent"] = rising

    # Score rising queries from Google Trends
    for rq in data.get("rising_queries", []):
        topic = normalize_topic(rq["query"])
        value = rq.get("value", "")
        topics[topic]["score"] += 2
        topics[topic]["signals"].append(f"Rising query: '{rq['query']}' ({value}) from seed '{rq['seed_keyword']}'")
        topics[topic]["signal_sources"].add("rising_query")
        topics[topic]["keywords"].add(rq["seed_keyword"])
        topics[topic]["details"]["rising_query_value"] = value

    # Score rising videos
    for vid in data.get("rising_videos", []):
        topic = normalize_topic(vid.get("keyword_match", vid.get("title", "")))
        velocity = vid.get("view_velocity", 0)

        if velocity > 0:
            topics[topic]["score"] += 2
            topics[topic]["signals"].append(
                f"Hot video: '{vid['title']}' by {vid.get('channel', '?')} "
                f"({vid.get('views', 0):,} views, {velocity:.0f} v/hr)"
            )
            topics[topic]["signal_sources"].add("video")
            topics[topic]["keywords"].add(vid.get("keyword_match", ""))
            topics[topic]["details"]["hot_video"] = {
                "title": vid["title"],
                "channel": vid.get("channel", ""),
                "views": vid.get("views", 0),
                "velocity": velocity,
            }

    # Apply multi-signal multiplier
    for topic, info in topics.items():
        num_sources = len(info["signal_sources"])
        if num_sources >= 2:
            info["score"] = round(info["score"] * 1.5, 1)
            info["signals"].append(f"Multi-signal bonus (1.5x): {num_sources} sources")

    # Build ranked list
    opportunities = []
    for topic, info in topics.items():
        opportunities.append({
            "topic": topic,
            "score": info["score"],
            "signal_count": len(info["signals"]),
            "signal_sources": sorted(info["signal_sources"]),
            "signals": info["signals"],
            "related_keywords": sorted(info["keywords"]),
            "details": info["details"],
        })

    # Sort by score descending
    opportunities.sort(key=lambda x: x["score"], reverse=True)

    return {
        "success": True,
        "opportunities": opportunities,
        "total_opportunities": len(opportunities),
        "date": data.get("date", ""),
    }


def run(text_output=False, save=False):
    """Run the scorer."""
    result = score_opportunities()

    if save:
        output_path = PROJECT_ROOT / ".tmp" / "youtube_seo_scored.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        result["saved_to"] = str(output_path)

    if text_output:
        print(f"\n=== Content Opportunities — {result.get('date', 'today')} ===")
        print(f"Total: {result['total_opportunities']}\n")

        for i, opp in enumerate(result["opportunities"][:10], 1):
            sources = ", ".join(opp["signal_sources"])
            print(f"  #{i} [{opp['score']:.1f} pts] {opp['topic']}")
            print(f"     Sources: {sources}")
            for sig in opp["signals"]:
                print(f"       - {sig}")
            print()
    else:
        print(json.dumps(result, indent=2))

    return result


def main():
    parser = argparse.ArgumentParser(description="Score YouTube SEO opportunities")
    parser.add_argument("--text", action="store_true", help="Human-readable output")
    parser.add_argument("--save", action="store_true", help="Save output to .tmp/")

    args = parser.parse_args()
    result = run(text_output=args.text, save=args.save)

    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
