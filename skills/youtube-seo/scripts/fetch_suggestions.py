#!/usr/bin/env python3
"""
Tool: YouTube Autocomplete Suggestions Fetcher
Purpose: Hit YouTube's free autocomplete API for seed keywords and track suggestions
         over time. New suggestions that weren't there before = rising search demand.

Usage:
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/fetch_suggestions.py
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/fetch_suggestions.py --keywords "keyword1,keyword2"
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/fetch_suggestions.py --save
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/fetch_suggestions.py --text

Dependencies: requests, PyYAML

Output: JSON with suggestions array
"""

import sys
import json
import time
import argparse
import urllib.parse
from pathlib import Path

import os
import requests
import yaml

# Resolve plugin root for portable paths
PLUGIN_ROOT = os.environ.get(
    "CLAUDE_PLUGIN_ROOT",
    str(Path(__file__).resolve().parent.parent.parent)
)
SKILL_DIR = Path(PLUGIN_ROOT) / "skills" / "youtube-seo"
PROJECT_ROOT = Path(PLUGIN_ROOT).parent  # project root
CONFIG_PATH = SKILL_DIR / "references" / "seed_keywords.yaml"

AUTOCOMPLETE_URL = "https://suggestqueries.google.com/complete/search"

# Headers to mimic a browser request
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def load_config():
    """Load seed keywords and settings from YAML config."""
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def fetch_suggestions(query, delay_ms=200):
    """Fetch YouTube autocomplete suggestions for a query."""
    params = {
        "client": "youtube",
        "ds": "yt",
        "q": query,
        "hl": "en",
        "gl": "us",
    }

    try:
        resp = requests.get(
            AUTOCOMPLETE_URL,
            params=params,
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()

        # Response is JSONP: window.google.ac.h([...])
        # Strip the wrapper to get the JSON array
        text = resp.text
        start = text.index("(") + 1
        end = text.rindex(")")
        data = json.loads(text[start:end])

        suggestions = []
        if len(data) > 1 and isinstance(data[1], list):
            for item in data[1]:
                if isinstance(item, list) and len(item) > 0:
                    suggestions.append(str(item[0]))
                elif isinstance(item, str):
                    suggestions.append(item)

        time.sleep(delay_ms / 1000.0)
        return suggestions

    except requests.exceptions.RequestException as e:
        print(f"Warning: Failed to fetch suggestions for '{query}': {e}", file=sys.stderr)
        return []
    except (ValueError, IndexError, json.JSONDecodeError) as e:
        print(f"Warning: Failed to parse suggestions for '{query}': {e}", file=sys.stderr)
        return []


def run(keywords=None, save=False, text_output=False):
    """Run the suggestions fetcher for all seed keywords."""
    config = load_config()
    settings = config.get("settings", {})

    if keywords:
        seed_keywords = [k.strip() for k in keywords.split(",")]
    else:
        seed_keywords = config.get("seed_keywords", [])

    prefixes = settings.get("suggestion_prefixes", [""])
    delay_ms = settings.get("request_delay_ms", 200)

    all_suggestions = []
    seen = set()

    for seed in seed_keywords:
        for prefix in prefixes:
            # Build query with prefix
            if prefix.endswith(" "):
                query = f"{prefix}{seed}"
            elif prefix.startswith(" "):
                query = f"{seed}{prefix}"
            else:
                query = f"{prefix}{seed}" if prefix else seed

            suggestions = fetch_suggestions(query.strip(), delay_ms)

            for sug in suggestions:
                sug_lower = sug.lower().strip()
                if sug_lower not in seen:
                    seen.add(sug_lower)
                    all_suggestions.append({
                        "seed_keyword": seed,
                        "suggestion": sug.strip(),
                        "query_used": query.strip(),
                    })

    result = {
        "success": True,
        "suggestions": all_suggestions,
        "count": len(all_suggestions),
        "seeds_checked": len(seed_keywords),
        "queries_made": len(seed_keywords) * len(prefixes),
    }

    if save:
        output_path = PROJECT_ROOT / ".tmp" / "youtube_seo_suggestions.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(result, f, indent=2)
        result["saved_to"] = str(output_path)

    if text_output:
        print(f"\n=== YouTube Autocomplete Suggestions ===")
        print(f"Seeds checked: {len(seed_keywords)}")
        print(f"Total unique suggestions: {len(all_suggestions)}\n")

        current_seed = None
        for item in sorted(all_suggestions, key=lambda x: x["seed_keyword"]):
            if item["seed_keyword"] != current_seed:
                current_seed = item["seed_keyword"]
                print(f"\n  [{current_seed}]")
            print(f"    - {item['suggestion']}")
        print()
    else:
        print(json.dumps(result, indent=2))

    return result


def main():
    parser = argparse.ArgumentParser(description="Fetch YouTube autocomplete suggestions")
    parser.add_argument("--keywords", help="Comma-separated keywords (overrides config)")
    parser.add_argument("--save", action="store_true", help="Save output to .tmp/")
    parser.add_argument("--text", action="store_true", help="Human-readable output")

    args = parser.parse_args()
    result = run(keywords=args.keywords, save=args.save, text_output=args.text)

    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
