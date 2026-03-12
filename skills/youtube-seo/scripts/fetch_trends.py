#!/usr/bin/env python3
"""
Tool: Google Trends Fetcher (YouTube Filter)
Purpose: Pull YouTube-specific search interest from Google Trends for seed keywords.
         Flags breakout terms and captures related rising queries.

Usage:
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/fetch_trends.py
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/fetch_trends.py --keywords "keyword1,keyword2"
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/fetch_trends.py --save
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/fetch_trends.py --text

Dependencies: pytrends, PyYAML

Output: JSON with trends and rising queries
"""

import sys
import json
import time
import argparse
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


def fetch_trends_for_keywords(keywords, timeframe="now 7-d", max_retries=3):
    """Fetch Google Trends data for a batch of keywords (max 5 at a time)."""
    try:
        from pytrends.request import TrendReq
    except ImportError:
        return {"error": "pytrends not installed. Run: pip3 install pytrends"}

    pytrends = TrendReq(hl="en-US", tz=360)
    all_trends = []
    all_rising = []

    # pytrends supports max 5 keywords at a time
    batches = [keywords[i:i + 5] for i in range(0, len(keywords), 5)]

    for batch in batches:
        retries = 0
        while retries < max_retries:
            try:
                pytrends.build_payload(batch, cat=0, timeframe=timeframe, gprop="youtube")

                # Interest over time
                interest_df = pytrends.interest_over_time()
                if not interest_df.empty:
                    for kw in batch:
                        if kw in interest_df.columns:
                            values = interest_df[kw].tolist()
                            current = values[-1] if values else 0
                            previous = values[0] if values else 0

                            if previous > 0:
                                change_pct = ((current - previous) / previous) * 100
                            else:
                                change_pct = 100.0 if current > 0 else 0.0

                            all_trends.append({
                                "keyword": kw,
                                "interest_score": int(current),
                                "previous_score": int(previous),
                                "change_pct": round(change_pct, 1),
                                "is_breakout": change_pct > 500,
                                "rising_percent": round(change_pct, 1),
                                "trend_direction": "rising" if change_pct > 10 else "falling" if change_pct < -10 else "stable",
                            })

                # Related queries for each keyword
                for kw in batch:
                    try:
                        pytrends.build_payload([kw], cat=0, timeframe=timeframe, gprop="youtube")
                        related = pytrends.related_queries()

                        if kw in related and related[kw].get("rising") is not None:
                            rising_df = related[kw]["rising"]
                            if not rising_df.empty:
                                for _, row in rising_df.head(10).iterrows():
                                    all_rising.append({
                                        "seed_keyword": kw,
                                        "query": str(row.get("query", "")),
                                        "value": str(row.get("value", "")),
                                    })
                        time.sleep(1)  # Rate limit between related query calls

                    except Exception as e:
                        print(f"Warning: Related queries failed for '{kw}': {e}", file=sys.stderr)
                        continue

                break  # Success, exit retry loop

            except Exception as e:
                retries += 1
                error_str = str(e)

                if "429" in error_str or "Too Many" in error_str:
                    wait = 2 ** retries * 5
                    print(f"Rate limited. Waiting {wait}s before retry {retries}/{max_retries}...", file=sys.stderr)
                    time.sleep(wait)
                else:
                    print(f"Warning: Trends fetch failed for batch {batch}: {e}", file=sys.stderr)
                    break

        time.sleep(2)  # Delay between batches

    return {"trends": all_trends, "rising_queries": all_rising}


def run(keywords=None, save=False, text_output=False):
    """Run the trends fetcher."""
    config = load_config()
    settings = config.get("settings", {})

    if keywords:
        seed_keywords = [k.strip() for k in keywords.split(",")]
    else:
        seed_keywords = config.get("seed_keywords", [])

    timeframe = settings.get("trends_timeframe", "now 7-d")

    data = fetch_trends_for_keywords(seed_keywords, timeframe=timeframe)

    if "error" in data:
        result = {"success": False, "error": data["error"]}
        print(json.dumps(result, indent=2))
        sys.exit(1)

    result = {
        "success": True,
        "trends": data["trends"],
        "rising_queries": data["rising_queries"],
        "trends_count": len(data["trends"]),
        "rising_queries_count": len(data["rising_queries"]),
        "timeframe": timeframe,
    }

    if save:
        output_path = PROJECT_ROOT / ".tmp" / "youtube_seo_trends.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        result["saved_to"] = str(output_path)

    if text_output:
        print(f"\n=== Google Trends (YouTube) — {timeframe} ===\n")

        # Sort by change percentage descending
        sorted_trends = sorted(data["trends"], key=lambda x: x.get("change_pct", 0), reverse=True)

        for t in sorted_trends:
            direction = "▲" if t["change_pct"] > 10 else "▼" if t["change_pct"] < -10 else "→"
            breakout = " 🔥 BREAKOUT" if t.get("is_breakout") else ""
            print(f"  {direction} {t['keyword']}: {t['interest_score']}/100 ({t['change_pct']:+.1f}%){breakout}")

        if data["rising_queries"]:
            print(f"\n  Rising Related Queries:")
            for rq in data["rising_queries"][:15]:
                print(f"    - [{rq['seed_keyword']}] {rq['query']} ({rq['value']})")
        print()
    else:
        print(json.dumps(result, indent=2))

    return result


def main():
    parser = argparse.ArgumentParser(description="Fetch Google Trends data (YouTube filter)")
    parser.add_argument("--keywords", help="Comma-separated keywords (overrides config)")
    parser.add_argument("--save", action="store_true", help="Save output to .tmp/")
    parser.add_argument("--text", action="store_true", help="Human-readable output")

    args = parser.parse_args()
    result = run(keywords=args.keywords, save=args.save, text_output=args.text)

    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
