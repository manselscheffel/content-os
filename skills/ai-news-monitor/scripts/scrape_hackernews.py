#!/usr/bin/env python3
"""
Tool: Hacker News AI News Scraper
Purpose: Fetch AI-related stories from Hacker News API (free, no auth)

API: HN Firebase API (https://hacker-news.firebaseio.com/v0/)

Usage:
    python tools/news_monitor/scrape_hackernews.py --max-stories 100 --min-score 30
    python tools/news_monitor/scrape_hackernews.py --keywords "Claude,MCP,AI agents" --output json
    python tools/news_monitor/scrape_hackernews.py --type top  # top, new, best
    python tools/news_monitor/scrape_hackernews.py --check-new  # Only return items not in DB

Dependencies:
    - requests

Output:
    JSON with filtered AI-related stories
"""

import argparse
import json
import sys
import time
from datetime import datetime
from typing import Optional

try:
    import requests
except ImportError:
    print(json.dumps({
        "success": False,
        "error": "Missing dependency: requests",
        "fix": "pip install requests"
    }))
    sys.exit(1)

# HN API endpoints
HN_API_BASE = "https://hacker-news.firebaseio.com/v0"
HN_ENDPOINTS = {
    "top": f"{HN_API_BASE}/topstories.json",
    "new": f"{HN_API_BASE}/newstories.json",
    "best": f"{HN_API_BASE}/beststories.json",
    "show": f"{HN_API_BASE}/showstories.json",
    "ask": f"{HN_API_BASE}/askstories.json"
}

# Default AI-related keywords
DEFAULT_KEYWORDS = [
    # Core AI terms
    "AI", "artificial intelligence", "machine learning", "ML", "deep learning",
    "LLM", "large language model", "GPT", "Claude", "Gemini", "Llama",
    # Agentic AI
    "agent", "agentic", "autonomous", "MCP", "model context protocol",
    # Tools
    "n8n", "automation", "workflow", "Claude Code", "Cursor", "Copilot",
    "coding assistant", "AI assistant", "Codex",
    # Claude ecosystem & bot systems
    "Claude Code", "claude-code", "Anthropic", "openclaw", "zeptoclaw",
    "claw", "AI bot", "bot system", "agent harness", "skills",
    # Google / AntiGravity ecosystem
    "AntiGravity", "Antigravity", "antigravity", "Google AI IDE",
    "Gemini Pro", "Gemini Flash", "Google AI Studio", "Vertex AI",
    # Companies
    "OpenAI", "Anthropic", "Google AI", "DeepMind", "Mistral", "Cohere",
    # Concepts
    "RAG", "retrieval", "embedding", "vector", "fine-tuning", "prompt",
    "transformer", "neural network"
]


def fetch_story_ids(story_type: str = "top") -> list:
    """Fetch story IDs from HN API."""
    endpoint = HN_ENDPOINTS.get(story_type, HN_ENDPOINTS["top"])

    try:
        response = requests.get(endpoint, timeout=30)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching story IDs: {e}", file=sys.stderr)
        return []


def fetch_item(item_id: int) -> Optional[dict]:
    """Fetch a single item from HN API."""
    url = f"{HN_API_BASE}/item/{item_id}.json"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.RequestException:
        return None


def matches_keywords(text: str, keywords: list) -> tuple[bool, list]:
    """Check if text matches any keywords. Returns (matched, list of matched keywords)."""
    if not text:
        return False, []

    text_lower = text.lower()
    matched = []

    for kw in keywords:
        # Handle multi-word keywords
        kw_lower = kw.lower()
        if kw_lower in text_lower:
            matched.append(kw)

    return len(matched) > 0, matched


def scrape_hackernews(
    story_type: str = "top",
    max_stories: int = 100,
    min_score: int = 30,
    keywords: list = None,
    delay_ms: int = 100,
    check_db: bool = False
) -> dict:
    """
    Scrape AI-related stories from Hacker News.

    Args:
        story_type: Type of stories (top, new, best, show, ask)
        max_stories: Maximum stories to fetch
        min_score: Minimum HN score threshold
        keywords: List of keywords to filter (default: AI-related)
        delay_ms: Delay between API calls in ms
        check_db: If True, skip items already in database

    Returns:
        dict with filtered stories
    """
    if keywords is None:
        keywords = DEFAULT_KEYWORDS

    print(f"Fetching {story_type} stories from Hacker News...", file=sys.stderr)

    # Get story IDs
    story_ids = fetch_story_ids(story_type)
    if not story_ids:
        return {
            "success": False,
            "error": "Failed to fetch story IDs"
        }

    # Limit to max_stories
    story_ids = story_ids[:max_stories * 3]  # Fetch more since we'll filter

    print(f"Checking {len(story_ids)} stories for AI content...", file=sys.stderr)

    # Import DB functions if checking duplicates
    if check_db:
        try:
            from news_db import is_duplicate
        except ImportError:
            sys.path.insert(0, str(Path(__file__).parent))
            from news_db import is_duplicate

    items = []
    checked = 0
    skipped_score = 0
    skipped_keywords = 0
    skipped_duplicate = 0

    for item_id in story_ids:
        if len(items) >= max_stories:
            break

        # Fetch item
        item = fetch_item(item_id)
        checked += 1

        if not item or item.get('type') != 'story':
            continue

        # Check score threshold
        score = item.get('score', 0)
        if score < min_score:
            skipped_score += 1
            continue

        # Check keywords in title
        title = item.get('title', '')
        matches, matched_keywords = matches_keywords(title, keywords)

        if not matches:
            skipped_keywords += 1
            continue

        # Check if already in database
        if check_db:
            dup_result = is_duplicate("hackernews", str(item_id))
            if dup_result.get('is_duplicate'):
                skipped_duplicate += 1
                continue

        # Build item dict
        items.append({
            "source": "hackernews",
            "source_id": str(item_id),
            "title": title,
            "url": item.get('url', f"https://news.ycombinator.com/item?id={item_id}"),
            "score": score,
            "comments": item.get('descendants', 0),
            "author": item.get('by', ''),
            "source_timestamp": datetime.fromtimestamp(item.get('time', 0)).isoformat(),
            "hn_url": f"https://news.ycombinator.com/item?id={item_id}",
            "matched_keywords": matched_keywords,
            "type": "story"
        })

        # Rate limiting
        if delay_ms > 0:
            time.sleep(delay_ms / 1000)

        # Progress update
        if checked % 20 == 0:
            print(f"  Checked {checked} stories, found {len(items)} matches...", file=sys.stderr)

    return {
        "success": True,
        "items": items,
        "total_found": len(items),
        "total_checked": checked,
        "skipped_low_score": skipped_score,
        "skipped_no_keywords": skipped_keywords,
        "skipped_duplicate": skipped_duplicate,
        "story_type": story_type,
        "min_score": min_score,
        "keywords_used": len(keywords),
        "fetched_at": datetime.now().isoformat()
    }


def format_text_output(result: dict) -> str:
    """Format result as readable text."""
    if not result.get("success"):
        return f"Error: {result.get('error')}"

    lines = []
    lines.append("=" * 70)
    lines.append("HACKER NEWS AI STORIES")
    lines.append("=" * 70)
    lines.append(f"Found: {result['total_found']} stories")
    lines.append(f"Checked: {result['total_checked']} | Skipped: {result['skipped_low_score']} (score), {result['skipped_no_keywords']} (keywords)")
    lines.append("")

    for i, item in enumerate(result['items'], 1):
        lines.append(f"{i}. [{item['score']} pts] {item['title']}")
        lines.append(f"   {item['url']}")
        lines.append(f"   Keywords: {', '.join(item['matched_keywords'])} | Comments: {item['comments']}")
        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Scrape AI-related stories from Hacker News",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Get top AI stories with default settings
  python scrape_hackernews.py

  # Get new stories, lower score threshold
  python scrape_hackernews.py --type new --min-score 10

  # Custom keywords
  python scrape_hackernews.py --keywords "Claude,MCP,agent"

  # Check against database for new items only
  python scrape_hackernews.py --check-new

  # Text output
  python scrape_hackernews.py --text
        """
    )

    parser.add_argument("--type", "-t", choices=["top", "new", "best", "show", "ask"],
                       default="top", help="Story type (default: top)")
    parser.add_argument("--max-stories", "-m", type=int, default=50,
                       help="Max stories to return (default: 50)")
    parser.add_argument("--min-score", "-s", type=int, default=30,
                       help="Minimum HN score (default: 30)")
    parser.add_argument("--keywords", "-k",
                       help="Comma-separated keywords to filter (default: AI-related)")
    parser.add_argument("--delay", type=int, default=100,
                       help="Delay between API calls in ms (default: 100)")
    parser.add_argument("--check-new", action="store_true",
                       help="Only return items not already in database")
    parser.add_argument("--text", action="store_true",
                       help="Output formatted text instead of JSON")
    parser.add_argument("--output", "-o", help="Save output to file")

    args = parser.parse_args()

    # Parse keywords
    keywords = None
    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(",")]

    # Run scraper
    result = scrape_hackernews(
        story_type=args.type,
        max_stories=args.max_stories,
        min_score=args.min_score,
        keywords=keywords,
        delay_ms=args.delay,
        check_db=args.check_new
    )

    # Output
    if args.text:
        output = format_text_output(result)
    else:
        output = json.dumps(result, indent=2)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Saved to {args.output}", file=sys.stderr)

    print(output)

    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
