#!/usr/bin/env python3
"""
Tool: Perplexity AI News Aggregator
Purpose: Use Perplexity to aggregate AI news from Twitter, newsletters, Product Hunt

NOTE: Perplexity provides INDIRECT access to Twitter/X content through web search.
It finds mentions of tweets in articles/blogs/discussions, NOT real-time tweets.
Expect 6-24 hour delay on Twitter content. For real-time, use Twitter API ($100/mo).

Sources aggregated:
- Twitter/X mentions (indirect via web)
- Product Hunt AI launches
- AI newsletter content
- General AI news

Usage:
    python tools/news_monitor/fetch_perplexity_news.py
    python tools/news_monitor/fetch_perplexity_news.py --source twitter --accounts karpathy,AnthropicAI
    python tools/news_monitor/fetch_perplexity_news.py --source producthunt
    python tools/news_monitor/fetch_perplexity_news.py --source newsletters

Dependencies:
    - Perplexity MCP server (configured in Claude Code)
    - Or: PERPLEXITY_API_KEY for direct API

Output:
    JSON with aggregated news items
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

# Resolve plugin root for lib imports
PLUGIN_ROOT = os.environ.get(
    "CLAUDE_PLUGIN_ROOT",
    str(Path(__file__).resolve().parent.parent.parent)
)
SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))
sys.path.insert(0, PLUGIN_ROOT)

# Load .env from project root
try:
    from dotenv import load_dotenv
    load_dotenv(Path(PLUGIN_ROOT).parent / ".env")
except ImportError:
    pass  # dotenv not installed, rely on shell env

# Curated Twitter accounts — customize for your niche
TWITTER_TIER1 = [
    "AnthropicAI",
    "OpenAI",
    "karpathy",
]

TWITTER_TIER2 = [
    # Add accounts relevant to your niche
]

# Newsletter names
NEWSLETTERS = [
    "The Rundown AI",
    "Ben's Bites",
    "The Neuron",
    "Superhuman AI",
    "TLDR AI"
]


def fetch_via_perplexity_api(query: str, model: str = "sonar") -> dict:
    """
    Fetch news using Perplexity API directly.

    Args:
        query: Search query
        model: Perplexity model to use

    Returns:
        dict with response
    """
    api_key = os.getenv("PERPLEXITY_API_KEY")
    if not api_key:
        return {
            "success": False,
            "error": "PERPLEXITY_API_KEY not set. Use MCP tool or set API key."
        }

    import requests

    url = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "You are an AI news aggregator. Return factual, recent AI news items with URLs. Format each item as: TITLE | URL | SOURCE | SUMMARY (one line each). Only include items from the last 48 hours."
            },
            {
                "role": "user",
                "content": query
            }
        ],
        "temperature": 0.1,
        "return_citations": True
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()

        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        citations = data.get("citations", [])

        return {
            "success": True,
            "content": content,
            "citations": citations,
            "query": query
        }

    except requests.RequestException as e:
        return {
            "success": False,
            "error": str(e)
        }


def parse_perplexity_response(response: dict) -> list:
    """
    Parse Perplexity response into structured items.

    Args:
        response: Perplexity API response

    Returns:
        list of parsed items
    """
    items = []
    content = response.get("content", "")
    citations = response.get("citations", [])

    # Try to parse line-by-line format
    for line in content.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        # Try TITLE | URL | SOURCE | SUMMARY format
        if "|" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 2:
                items.append({
                    "source": "perplexity",
                    "source_id": f"pplx_{hash(line) % 1000000}",
                    "title": parts[0][:200],
                    "url": parts[1] if parts[1].startswith("http") else None,
                    "summary": parts[3] if len(parts) > 3 else "",
                    "source_name": parts[2] if len(parts) > 2 else "perplexity",
                    "fetched_at": datetime.now().isoformat()
                })

    # Also add citations as items if available
    for i, citation in enumerate(citations):
        if isinstance(citation, str) and citation.startswith("http"):
            # Avoid duplicates
            if not any(item.get("url") == citation for item in items):
                items.append({
                    "source": "perplexity",
                    "source_id": f"pplx_cite_{i}_{hash(citation) % 1000000}",
                    "title": f"Citation {i+1}",
                    "url": citation,
                    "summary": "",
                    "fetched_at": datetime.now().isoformat()
                })

    return items


def fetch_twitter_news(accounts: list = None, hours: int = 48) -> dict:
    """
    Fetch AI news from Twitter via Perplexity (indirect).

    Args:
        accounts: Twitter accounts to search
        hours: Lookback hours

    Returns:
        dict with items
    """
    accounts = accounts or (TWITTER_TIER1 + TWITTER_TIER2)

    # Build query for Perplexity
    account_str = ", ".join([f"@{a}" for a in accounts[:10]])  # Limit accounts
    query = f"""Find the latest AI and LLM news from Twitter/X from these accounts: {account_str}

Look for news from the last {hours} hours about:
- New AI tools, frameworks, or releases
- Claude, GPT, or LLM updates
- Viral AI techniques or discoveries
- AI coding tools (Cursor, Copilot, Claude Code)
- Agentic systems and MCP

For each item found, provide: TITLE | URL | SOURCE | SUMMARY"""

    response = fetch_via_perplexity_api(query)

    if not response.get("success"):
        return response

    items = parse_perplexity_response(response)

    # Mark source as twitter
    for item in items:
        item["source"] = "twitter"
        item["aggregated_via"] = "perplexity"

    return {
        "success": True,
        "items": items,
        "count": len(items),
        "accounts_queried": accounts[:10],
        "note": "Twitter content via Perplexity is indirect (6-24hr delay)"
    }


def fetch_producthunt_news(hours: int = 48) -> dict:
    """
    Fetch AI product launches from Product Hunt via Perplexity.
    """
    query = f"""Find the latest AI product launches from Product Hunt in the last {hours} hours.

Focus on:
- AI tools and apps
- LLM-powered products
- Developer tools
- Automation and workflow tools
- Claude or GPT integrations

For each product found, provide: PRODUCT_NAME | URL | CATEGORY | TAGLINE"""

    response = fetch_via_perplexity_api(query)

    if not response.get("success"):
        return response

    items = parse_perplexity_response(response)

    for item in items:
        item["source"] = "producthunt"
        item["aggregated_via"] = "perplexity"

    return {
        "success": True,
        "items": items,
        "count": len(items)
    }


def fetch_newsletter_news(newsletters: list = None, hours: int = 48) -> dict:
    """
    Fetch AI news from newsletters via Perplexity.
    """
    newsletters = newsletters or NEWSLETTERS

    newsletter_str = ", ".join(newsletters)
    query = f"""Find the latest AI news from these newsletters: {newsletter_str}

Look for news from the last {hours} hours about:
- Breaking AI announcements
- New tools and frameworks
- Notable AI use cases
- Viral AI content

For each item found, provide: HEADLINE | URL | NEWSLETTER | SUMMARY"""

    response = fetch_via_perplexity_api(query)

    if not response.get("success"):
        return response

    items = parse_perplexity_response(response)

    for item in items:
        item["source"] = "newsletter"
        item["aggregated_via"] = "perplexity"

    return {
        "success": True,
        "items": items,
        "count": len(items)
    }


def fetch_all_sources(hours: int = 48) -> dict:
    """
    Fetch from all Perplexity-aggregated sources.
    """
    all_items = []
    errors = []

    # Twitter
    twitter_result = fetch_twitter_news(hours=hours)
    if twitter_result.get("success"):
        all_items.extend(twitter_result.get("items", []))
    else:
        errors.append({"source": "twitter", "error": twitter_result.get("error")})

    # Product Hunt
    ph_result = fetch_producthunt_news(hours=hours)
    if ph_result.get("success"):
        all_items.extend(ph_result.get("items", []))
    else:
        errors.append({"source": "producthunt", "error": ph_result.get("error")})

    # Newsletters
    nl_result = fetch_newsletter_news(hours=hours)
    if nl_result.get("success"):
        all_items.extend(nl_result.get("items", []))
    else:
        errors.append({"source": "newsletter", "error": nl_result.get("error")})

    return {
        "success": len(all_items) > 0,
        "items": all_items,
        "count": len(all_items),
        "errors": errors if errors else None,
        "error": f"{len(errors)} sub-sources failed" if errors and not all_items else None,
        "note": "Content aggregated via Perplexity web search (may have delays)"
    }


def filter_new_items(items: list) -> list:
    """Filter out items already in database."""
    try:
        from news_db import is_duplicate

        new_items = []
        for item in items:
            source = item.get("source", "perplexity")
            source_id = item.get("source_id", "")
            if not is_duplicate(source, source_id).get("is_duplicate"):
                new_items.append(item)

        return new_items
    except ImportError:
        return items


def main():
    parser = argparse.ArgumentParser(
        description="Fetch AI news via Perplexity aggregation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch from all sources
  python fetch_perplexity_news.py

  # Fetch Twitter news (indirect)
  python fetch_perplexity_news.py --source twitter

  # Fetch from specific Twitter accounts
  python fetch_perplexity_news.py --source twitter --accounts karpathy,AnthropicAI

  # Fetch Product Hunt launches
  python fetch_perplexity_news.py --source producthunt

  # Fetch newsletter content
  python fetch_perplexity_news.py --source newsletters

NOTE: Twitter content is INDIRECT (via web search). Expect 6-24 hour delays.
For real-time Twitter, use Twitter API at $100/month.
        """
    )

    parser.add_argument("--source", "-s",
                       choices=["all", "twitter", "producthunt", "newsletters"],
                       default="all", help="Source to fetch (default: all)")
    parser.add_argument("--accounts",
                       help="Comma-separated Twitter accounts (for twitter source)")
    parser.add_argument("--hours", type=int, default=48,
                       help="Lookback hours (default: 48)")
    parser.add_argument("--check-new", action="store_true",
                       help="Filter out items already in database")
    parser.add_argument("--output", "-o", help="Save to file")

    args = parser.parse_args()

    # Fetch based on source
    if args.source == "twitter":
        accounts = args.accounts.split(",") if args.accounts else None
        result = fetch_twitter_news(accounts=accounts, hours=args.hours)
    elif args.source == "producthunt":
        result = fetch_producthunt_news(hours=args.hours)
    elif args.source == "newsletters":
        result = fetch_newsletter_news(hours=args.hours)
    else:
        result = fetch_all_sources(hours=args.hours)

    # Filter duplicates if requested
    if args.check_new and result.get("success"):
        original_count = len(result.get("items", []))
        result["items"] = filter_new_items(result.get("items", []))
        result["filtered_duplicates"] = original_count - len(result["items"])

    # Output
    output = json.dumps(result, indent=2, default=str)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Saved {len(result.get('items', []))} items to {args.output}", file=sys.stderr)

    print(output)

    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
