#!/usr/bin/env python3
"""
Tool: GitHub Trending AI Repos Scraper
Purpose: Fetch trending AI-related repositories from GitHub

Uses GitHub Search API (free, rate limited) to find:
- Recently created repos with high stars in AI topics
- Repos with recent activity in AI/ML/LLM space
- Specific repos from curated watchlist

Usage:
    python3 scrape_github_trending.py
    python3 scrape_github_trending.py --since weekly --min-stars 100
    python3 scrape_github_trending.py --language python --topics ai,llm
    python3 scrape_github_trending.py --check-new  # Skip items in DB

Rate Limits:
    - Unauthenticated: 10 requests/minute
    - With GITHUB_TOKEN: 30 requests/minute

Dependencies:
    - requests

Output:
    JSON with trending repos
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from urllib.parse import quote

import requests

# Resolve plugin root for lib imports and .env loading
PLUGIN_ROOT = os.environ.get(
    "CLAUDE_PLUGIN_ROOT",
    str(Path(__file__).resolve().parent.parent.parent)
)
SKILL_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SKILL_DIR / "scripts"))
sys.path.insert(0, PLUGIN_ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv(Path(PLUGIN_ROOT).parent / ".env")
except ImportError:
    pass

# GitHub API
GITHUB_API = "https://api.github.com"
SEARCH_ENDPOINT = f"{GITHUB_API}/search/repositories"

# Default AI-related topics to search
DEFAULT_TOPICS = [
    "llm",
    "ai-agents",
    "langchain",
    "claude",
    "gpt",
    "machine-learning",
    "artificial-intelligence",
    "mcp",
    "automation",
    "chatgpt"
]

# Default languages
DEFAULT_LANGUAGES = ["python", "typescript", "rust", "go"]

# Curated repos to always check — customize this list
WATCHLIST_REPOS = [
    "anthropics/claude-code",
    "anthropics/anthropic-cookbook",
    "langchain-ai/langchain",
    "microsoft/autogen",
    "crewAIInc/crewAI",
    "n8n-io/n8n"
]


def get_headers() -> dict:
    """Get headers with optional auth token."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "AI-News-Monitor/1.0"
    }

    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"token {token}"

    return headers


def search_trending_repos(
    topics: list = None,
    languages: list = None,
    since: str = "daily",
    min_stars: int = 50,
    max_results: int = 30
) -> dict:
    """
    Search for trending AI repos using GitHub Search API.
    """
    topics = topics or DEFAULT_TOPICS
    languages = languages or DEFAULT_LANGUAGES

    if since == "daily":
        date_threshold = datetime.now() - timedelta(days=1)
    elif since == "weekly":
        date_threshold = datetime.now() - timedelta(days=7)
    elif since == "monthly":
        date_threshold = datetime.now() - timedelta(days=30)
    else:
        date_threshold = datetime.now() - timedelta(days=1)

    date_str = date_threshold.strftime("%Y-%m-%d")

    all_repos = []
    seen_repos = set()
    headers = get_headers()

    for topic in topics[:5]:
        query = f"topic:{topic} stars:>={min_stars} pushed:>={date_str}"

        params = {
            "q": query,
            "sort": "stars",
            "order": "desc",
            "per_page": min(10, max_results)
        }

        try:
            response = requests.get(SEARCH_ENDPOINT, headers=headers, params=params, timeout=10)

            if response.status_code == 403:
                return {
                    "success": False,
                    "error": "GitHub API rate limit exceeded. Set GITHUB_TOKEN for higher limits.",
                    "items": all_repos
                }

            response.raise_for_status()
            data = response.json()

            for repo in data.get("items", []):
                full_name = repo["full_name"]
                if full_name not in seen_repos:
                    seen_repos.add(full_name)
                    all_repos.append(format_repo(repo, topic))

            time.sleep(0.5)

        except requests.RequestException as e:
            continue

    for lang in languages[:3]:
        query = f"language:{lang} (AI OR LLM OR agent OR GPT OR Claude) stars:>={min_stars} pushed:>={date_str}"

        params = {
            "q": query,
            "sort": "updated",
            "order": "desc",
            "per_page": min(10, max_results)
        }

        try:
            response = requests.get(SEARCH_ENDPOINT, headers=headers, params=params, timeout=10)

            if response.status_code == 403:
                break

            response.raise_for_status()
            data = response.json()

            for repo in data.get("items", []):
                full_name = repo["full_name"]
                if full_name not in seen_repos:
                    seen_repos.add(full_name)
                    all_repos.append(format_repo(repo, f"language:{lang}"))

            time.sleep(0.5)

        except requests.RequestException:
            continue

    all_repos.sort(key=lambda x: x.get("stars", 0), reverse=True)
    all_repos = all_repos[:max_results]

    return {
        "success": True,
        "items": all_repos,
        "count": len(all_repos),
        "since": since,
        "date_threshold": date_str
    }


def check_watchlist_repos() -> dict:
    """Check curated watchlist repos for recent activity."""
    headers = get_headers()
    active_repos = []

    for repo_name in WATCHLIST_REPOS:
        try:
            response = requests.get(
                f"{GITHUB_API}/repos/{repo_name}",
                headers=headers,
                timeout=10
            )

            if response.status_code == 404:
                continue

            response.raise_for_status()
            repo = response.json()

            pushed_at = datetime.fromisoformat(repo["pushed_at"].replace("Z", "+00:00"))
            if pushed_at > datetime.now(pushed_at.tzinfo) - timedelta(hours=24):
                active_repos.append(format_repo(repo, "watchlist"))

            time.sleep(0.3)

        except requests.RequestException:
            continue

    return {
        "success": True,
        "items": active_repos,
        "count": len(active_repos)
    }


def format_repo(repo: dict, matched_query: str = None) -> dict:
    """Format GitHub repo into standard item format."""
    description = repo.get("description") or "No description"
    return {
        "source": "github",
        "source_id": str(repo["id"]),
        "title": f"{repo['full_name']}: {description[:100]}",
        "url": repo["html_url"],
        "summary": description,
        "author": repo["owner"]["login"],
        "stars": repo["stargazers_count"],
        "forks": repo["forks_count"],
        "language": repo.get("language"),
        "topics": repo.get("topics", []),
        "created_at": repo["created_at"],
        "pushed_at": repo["pushed_at"],
        "source_timestamp": repo["pushed_at"],
        "matched_query": matched_query,
        "fetched_at": datetime.now().isoformat()
    }


def filter_new_items(items: list) -> list:
    """Filter out items already in database."""
    try:
        from news_db import is_duplicate

        new_items = []
        for item in items:
            if not is_duplicate("github", item["source_id"]).get("is_duplicate"):
                new_items.append(item)

        return new_items
    except ImportError:
        return items


def main():
    parser = argparse.ArgumentParser(
        description="Scrape trending AI repos from GitHub",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--since", choices=["daily", "weekly", "monthly"],
                       default="daily", help="Time period for trending")
    parser.add_argument("--min-stars", type=int, default=50,
                       help="Minimum star count (default: 50)")
    parser.add_argument("--max-results", type=int, default=30,
                       help="Maximum repos to return (default: 30)")
    parser.add_argument("--topics", help="Comma-separated topics to search")
    parser.add_argument("--languages", help="Comma-separated languages to search")
    parser.add_argument("--watchlist-only", action="store_true",
                       help="Only check watchlist repos")
    parser.add_argument("--check-new", action="store_true",
                       help="Filter out items already in database")
    parser.add_argument("--output", "-o", help="Save to file")

    args = parser.parse_args()

    topics = args.topics.split(",") if args.topics else None
    languages = args.languages.split(",") if args.languages else None

    if args.watchlist_only:
        result = check_watchlist_repos()
    else:
        result = search_trending_repos(
            topics=topics,
            languages=languages,
            since=args.since,
            min_stars=args.min_stars,
            max_results=args.max_results
        )

        watchlist_result = check_watchlist_repos()
        if watchlist_result.get("success") and watchlist_result.get("items"):
            seen_ids = {i["source_id"] for i in result.get("items", [])}
            for item in watchlist_result["items"]:
                if item["source_id"] not in seen_ids:
                    result["items"].append(item)
            result["watchlist_active"] = len(watchlist_result["items"])

    if args.check_new and result.get("success"):
        original_count = len(result.get("items", []))
        result["items"] = filter_new_items(result.get("items", []))
        result["filtered_duplicates"] = original_count - len(result["items"])

    output = json.dumps(result, indent=2, default=str)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Saved {len(result.get('items', []))} repos to {args.output}", file=sys.stderr)

    print(output)

    if not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
