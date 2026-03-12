#!/usr/bin/env python3
"""
Tool: Reddit AI Subreddits Scraper
Purpose: Fetch AI-related posts from Reddit subreddits

Uses Reddit's free JSON API (no auth required).

Usage:
    python3 scrape_reddit.py
    python3 scrape_reddit.py --subreddits ClaudeAI,LocalLLaMA --sort hot
    python3 scrape_reddit.py --min-score 50 --max-age-hours 24
    python3 scrape_reddit.py --check-new  # Skip items in DB

Rate Limits:
    - Free JSON API: ~60 requests/minute
    - Be respectful - 1 second delay between requests

Dependencies:
    - requests

Output:
    JSON with Reddit posts
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests

# Resolve plugin root for lib imports
PLUGIN_ROOT = os.environ.get(
    "CLAUDE_PLUGIN_ROOT",
    str(Path(__file__).resolve().parent.parent.parent)
)
SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))
sys.path.insert(0, PLUGIN_ROOT)

# Reddit JSON API (no auth required)
REDDIT_BASE = "https://www.reddit.com"

# Default subreddits to monitor — customize for your niche
DEFAULT_SUBREDDITS = [
    "MachineLearning",
    "artificial",
    "ChatGPT",
    "OpenAI",
    "LocalLLaMA",
]

# AI keywords to boost relevance
AI_KEYWORDS = [
    "claude", "anthropic", "mcp", "agent", "agentic",
    "llm", "gpt", "openai", "coding", "automation",
    "workflow", "n8n", "cursor", "copilot", "api",
    "prompt", "tool", "framework", "release", "update"
]


def get_subreddit_posts(
    subreddit: str,
    sort: str = "hot",
    limit: int = 25,
    time_filter: str = "day"
) -> dict:
    """Fetch posts from a subreddit using Reddit's JSON API."""
    url = f"{REDDIT_BASE}/r/{subreddit}/{sort}.json"

    params = {
        "limit": min(limit, 100),
        "raw_json": 1
    }

    if sort == "top":
        params["t"] = time_filter

    headers = {
        "User-Agent": "AI-News-Monitor/1.0 (monitoring AI news for content creation)"
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)

        if response.status_code == 429:
            return {"success": False, "error": "Reddit rate limit exceeded.", "subreddit": subreddit}

        if response.status_code == 403:
            return {"success": False, "error": f"r/{subreddit} is private or quarantined", "subreddit": subreddit}

        if response.status_code == 404:
            return {"success": False, "error": f"r/{subreddit} not found", "subreddit": subreddit}

        response.raise_for_status()
        data = response.json()

        posts = []
        for child in data.get("data", {}).get("children", []):
            post_data = child.get("data", {})
            if post_data:
                posts.append(format_post(post_data, subreddit))

        return {"success": True, "subreddit": subreddit, "posts": posts, "count": len(posts)}

    except requests.RequestException as e:
        return {"success": False, "error": str(e), "subreddit": subreddit}


def format_post(post: dict, subreddit: str) -> dict:
    """Format Reddit post into standard item format."""
    created_utc = post.get("created_utc", 0)
    created_at = datetime.fromtimestamp(created_utc) if created_utc else None

    permalink = post.get("permalink", "")
    url = post.get("url", "")
    reddit_url = f"https://reddit.com{permalink}" if permalink else url

    title_lower = post.get("title", "").lower()
    selftext_lower = post.get("selftext", "").lower()
    combined_text = f"{title_lower} {selftext_lower}"

    matched_keywords = [kw for kw in AI_KEYWORDS if kw in combined_text]

    is_self = post.get("is_self", False)
    external_url = None if is_self else post.get("url")

    return {
        "source": "reddit",
        "source_id": post.get("id", ""),
        "title": post.get("title", ""),
        "url": external_url or reddit_url,
        "reddit_url": reddit_url,
        "summary": post.get("selftext", "")[:500] if post.get("selftext") else "",
        "author": post.get("author", "[deleted]"),
        "subreddit": subreddit,
        "score": post.get("score", 0),
        "upvote_ratio": post.get("upvote_ratio", 0),
        "num_comments": post.get("num_comments", 0),
        "is_self": is_self,
        "link_flair_text": post.get("link_flair_text"),
        "created_utc": created_utc,
        "source_timestamp": created_at.isoformat() if created_at else None,
        "matched_keywords": matched_keywords,
        "keyword_count": len(matched_keywords),
        "fetched_at": datetime.now().isoformat()
    }


def scrape_multiple_subreddits(
    subreddits: list = None,
    sort: str = "hot",
    limit_per_sub: int = 25,
    min_score: int = 10,
    max_age_hours: int = 48,
    time_filter: str = "day"
) -> dict:
    """Scrape multiple subreddits and combine results."""
    subreddits = subreddits or DEFAULT_SUBREDDITS

    all_posts = []
    errors = []
    cutoff_time = datetime.now() - timedelta(hours=max_age_hours)

    for subreddit in subreddits:
        result = get_subreddit_posts(subreddit=subreddit, sort=sort, limit=limit_per_sub, time_filter=time_filter)

        if result.get("success"):
            for post in result.get("posts", []):
                if post.get("score", 0) < min_score:
                    continue
                if post.get("created_utc"):
                    post_time = datetime.fromtimestamp(post["created_utc"])
                    if post_time < cutoff_time:
                        continue
                all_posts.append(post)
        else:
            errors.append({"subreddit": subreddit, "error": result.get("error")})

        time.sleep(1)

    all_posts.sort(key=lambda x: x.get("score", 0), reverse=True)

    return {
        "success": True,
        "items": all_posts,
        "count": len(all_posts),
        "subreddits_scraped": len(subreddits) - len(errors),
        "errors": errors if errors else None
    }


def filter_new_items(items: list) -> list:
    """Filter out items already in database."""
    try:
        from news_db import is_duplicate
        return [item for item in items if not is_duplicate("reddit", item["source_id"]).get("is_duplicate")]
    except ImportError:
        return items


def main():
    parser = argparse.ArgumentParser(description="Scrape AI-related posts from Reddit")

    parser.add_argument("--subreddits", "-s", help="Comma-separated subreddit names")
    parser.add_argument("--sort", choices=["hot", "new", "top", "rising"], default="hot")
    parser.add_argument("--time", choices=["hour", "day", "week", "month", "year", "all"], default="day")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--min-score", type=int, default=10)
    parser.add_argument("--max-age-hours", type=int, default=48)
    parser.add_argument("--check-new", action="store_true")
    parser.add_argument("--output", "-o", help="Save to file")

    args = parser.parse_args()

    subreddits = args.subreddits.split(",") if args.subreddits else None

    result = scrape_multiple_subreddits(
        subreddits=subreddits, sort=args.sort, limit_per_sub=args.limit,
        min_score=args.min_score, max_age_hours=args.max_age_hours, time_filter=args.time
    )

    if args.check_new and result.get("success"):
        original_count = len(result.get("items", []))
        result["items"] = filter_new_items(result.get("items", []))
        result["filtered_duplicates"] = original_count - len(result["items"])

    output = json.dumps(result, indent=2, default=str)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)

    print(output)

    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
