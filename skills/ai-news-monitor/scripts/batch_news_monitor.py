#!/usr/bin/env python3
"""
Tool: AI News Monitor Orchestrator
Purpose: Main orchestrator for the AI news monitoring pipeline

Modes:
- immediate: Fetch, score, and alert on high-priority items
- daily_digest: Generate daily summary of all relevant items
- weekly_roundup: Generate weekly top 10 content opportunities

Usage:
    python tools/news_monitor/batch_news_monitor.py --mode immediate
    python tools/news_monitor/batch_news_monitor.py --mode daily_digest
    python tools/news_monitor/batch_news_monitor.py --mode weekly_roundup
    python tools/news_monitor/batch_news_monitor.py --mode immediate --dry-run

Schedule with cron:
    # Every 2 hours
    0 */2 * * * python tools/news_monitor/batch_news_monitor.py --mode immediate

    # Daily digest at 7am
    0 7 * * 1-5 python tools/news_monitor/batch_news_monitor.py --mode daily_digest

    # Weekly roundup Sunday 6pm
    0 18 * * 0 python tools/news_monitor/batch_news_monitor.py --mode weekly_roundup

Dependencies:
    - All news_monitor tools
    - slack_sdk (for posting)

Environment Variables:
    - OPENAI_API_KEY or ANTHROPIC_API_KEY (for scoring)
    - SLACK_BOT_TOKEN (for alerts)
    - PERPLEXITY_API_KEY (optional, for extended sources)

Output:
    Summary of monitoring run
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Resolve plugin root for lib imports
PLUGIN_ROOT = os.environ.get(
    "CLAUDE_PLUGIN_ROOT",
    str(Path(__file__).resolve().parent.parent.parent)
)
SKILL_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = Path(PLUGIN_ROOT).parent  # project root
sys.path.insert(0, str(SKILL_DIR / "scripts"))
sys.path.insert(0, PLUGIN_ROOT)

# Load .env from project root
try:
    from dotenv import load_dotenv
    load_dotenv(WORKSPACE_ROOT / ".env")
except ImportError:
    pass

# Import our tools (sibling scripts in same directory)
from news_db import (
    insert_item, is_duplicate, mark_alerted,
    get_unalerted_high_priority, get_daily_digest, get_stats
)
from scrape_hackernews import scrape_hackernews
from scrape_github_trending import search_trending_repos, check_watchlist_repos
from scrape_reddit import scrape_multiple_subreddits
from format_slack_alert import format_alert

# Optional Perplexity import (requires API key)
try:
    from fetch_perplexity_news import fetch_all_sources as fetch_perplexity
    PERPLEXITY_AVAILABLE = True
except ImportError:
    PERPLEXITY_AVAILABLE = False

# Paths
LOGS_DIR = WORKSPACE_ROOT / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Default config
DEFAULT_CONFIG = {
    "sources": {
        "hackernews": {
            "enabled": True,
            "max_stories": 50,
            "min_score": 30
        },
        "github": {
            "enabled": True,
            "since": "daily",
            "min_stars": 50,
            "max_results": 30
        },
        "reddit": {
            "enabled": True,
            "subreddits": ["MachineLearning", "LocalLLaMA", "artificial", "ChatGPT", "OpenAI"],
            "sort": "hot",
            "min_score": 20,
            "max_age_hours": 48
        },
        "perplexity": {
            "enabled": True,  # Only runs if PERPLEXITY_API_KEY is set
            "hours": 48
        }
    },
    "scoring": {
        "model": "haiku",
        "min_score_to_store": 2
    },
    "alerts": {
        "immediate_threshold": 8,
        "slack_channel": "ai-news-alerts"
    }
}


def setup_logging(mode: str):
    """Set up logging to file and console."""
    LOGS_DIR.mkdir(exist_ok=True)

    log_file = LOGS_DIR / f"news_monitor_{datetime.now().strftime('%Y-%m-%d')}.log"

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )

    return logging.getLogger(__name__)


def post_to_slack(blocks: list, channel: str, text: str) -> dict:
    """Post blocks to Slack using SDK."""
    try:
        from slack_sdk import WebClient
        from slack_sdk.errors import SlackApiError
    except ImportError:
        return {"success": False, "error": "slack_sdk not installed. Run: pip install slack_sdk"}

    token = os.getenv("SLACK_BOT_TOKEN")
    if not token:
        return {"success": False, "error": "SLACK_BOT_TOKEN not set"}

    client = WebClient(token=token)

    try:
        response = client.chat_postMessage(
            channel=channel,
            text=text,
            blocks=blocks
        )
        return {
            "success": True,
            "ts": response["ts"],
            "channel": response["channel"]
        }
    except SlackApiError as e:
        return {"success": False, "error": str(e)}


def fetch_from_all_sources(config: dict, logger) -> tuple:
    """
    Fetch items from all enabled sources.

    Returns:
        tuple of (all_items, source_stats, errors)
    """
    all_items = []
    source_stats = {}
    errors = []
    sources_config = config.get("sources", DEFAULT_CONFIG["sources"])

    # 1. Hacker News
    hn_config = sources_config.get("hackernews", {})
    if hn_config.get("enabled", True):
        logger.info("  Fetching from Hacker News...")
        try:
            hn_result = scrape_hackernews(
                max_stories=hn_config.get("max_stories", 50),
                min_score=hn_config.get("min_score", 30),
                check_db=True
            )
            if hn_result.get("success"):
                items = hn_result.get("items", [])
                all_items.extend(items)
                source_stats["hackernews"] = len(items)
                logger.info(f"    Found {len(items)} HN stories")
            else:
                errors.append(f"HN: {hn_result.get('error')}")
        except Exception as e:
            errors.append(f"HN error: {str(e)}")

    # 2. GitHub Trending
    gh_config = sources_config.get("github", {})
    if gh_config.get("enabled", True):
        logger.info("  Fetching from GitHub...")
        try:
            gh_result = search_trending_repos(
                since=gh_config.get("since", "daily"),
                min_stars=gh_config.get("min_stars", 50),
                max_results=gh_config.get("max_results", 30)
            )
            if gh_result.get("success"):
                items = gh_result.get("items", [])
                # Filter already seen items
                new_items = [i for i in items if not is_duplicate("github", i["source_id"]).get("is_duplicate")]
                all_items.extend(new_items)
                source_stats["github"] = len(new_items)
                logger.info(f"    Found {len(new_items)} GitHub repos")
            else:
                errors.append(f"GitHub: {gh_result.get('error')}")
        except Exception as e:
            errors.append(f"GitHub error: {str(e)}")

    # 3. Reddit
    reddit_config = sources_config.get("reddit", {})
    if reddit_config.get("enabled", True):
        logger.info("  Fetching from Reddit...")
        try:
            reddit_result = scrape_multiple_subreddits(
                subreddits=reddit_config.get("subreddits"),
                sort=reddit_config.get("sort", "hot"),
                min_score=reddit_config.get("min_score", 20),
                max_age_hours=reddit_config.get("max_age_hours", 48)
            )
            if reddit_result.get("success"):
                items = reddit_result.get("items", [])
                # Filter already seen items
                new_items = [i for i in items if not is_duplicate("reddit", i["source_id"]).get("is_duplicate")]
                all_items.extend(new_items)
                source_stats["reddit"] = len(new_items)
                logger.info(f"    Found {len(new_items)} Reddit posts")
            else:
                errors.append(f"Reddit: {reddit_result.get('error')}")
        except Exception as e:
            errors.append(f"Reddit error: {str(e)}")

    # 4. Perplexity (Twitter/newsletters/Product Hunt) - only if API key set
    pplx_config = sources_config.get("perplexity", {})
    if pplx_config.get("enabled", True) and PERPLEXITY_AVAILABLE and os.getenv("PERPLEXITY_API_KEY"):
        logger.info("  Fetching from Perplexity (Twitter/newsletters)...")
        try:
            pplx_result = fetch_perplexity(hours=pplx_config.get("hours", 48))
            if pplx_result.get("success"):
                items = pplx_result.get("items", [])
                # Filter already seen items
                new_items = []
                for i in items:
                    source = i.get("source", "perplexity")
                    source_id = i.get("source_id", "")
                    if not is_duplicate(source, source_id).get("is_duplicate"):
                        new_items.append(i)
                all_items.extend(new_items)
                source_stats["perplexity"] = len(new_items)
                logger.info(f"    Found {len(new_items)} Perplexity items")
            else:
                errors.append(f"Perplexity: {pplx_result.get('error')}")
        except Exception as e:
            errors.append(f"Perplexity error: {str(e)}")
    elif pplx_config.get("enabled", True):
        logger.info("  Perplexity: Skipped (no API key)")

    return all_items, source_stats, errors


def run_immediate_mode(config: dict, dry_run: bool = False) -> dict:
    """
    Immediate mode: Fetch new items from all sources, score, alert on high-priority.

    Returns:
        dict with run summary
    """
    logger = logging.getLogger(__name__)

    logger.info("=" * 70)
    logger.info("AI NEWS MONITOR - IMMEDIATE MODE")
    logger.info("=" * 70)

    results = {
        "mode": "immediate",
        "fetched": 0,
        "new_items": 0,
        "sources": {},
        "errors": []
    }

    # Step 1: Fetch from all sources
    logger.info("\n[1/4] Fetching from all sources...")
    items, source_stats, fetch_errors = fetch_from_all_sources(config, logger)

    results["fetched"] = len(items)
    results["sources"] = source_stats
    results["errors"].extend(fetch_errors)

    logger.info(f"  Total: {len(items)} new items from {len(source_stats)} sources")

    if not items:
        logger.info("  No new items to process")
        results["success"] = True
        return results

    # Step 2: Insert into database
    logger.info(f"\n[2/4] Inserting {len(items)} items into database...")
    inserted_items = []

    for item in items:
        insert_result = insert_item(
            source=item["source"],
            source_id=item["source_id"],
            title=item["title"],
            url=item.get("url"),
            summary=item.get("summary"),
            author=item.get("author"),
            source_timestamp=item.get("source_timestamp")
        )

        if insert_result.get("success"):
            item["db_id"] = insert_result["item"]["id"]
            inserted_items.append(item)
            results["new_items"] += 1
        elif not insert_result.get("is_duplicate"):
            results["errors"].append(f"Insert failed for {item['title'][:30]}: {insert_result.get('error')}")

    logger.info(f"  Inserted {results['new_items']} items")

    if not inserted_items:
        logger.info("  No new items to score")
        results["success"] = True
        return results

    # Step 3: Done — scoring happens in conversation with Claude
    # When Claude reads the items (via /ai-news-monitor or /youtube-content ideate),
    # it scores them directly. No API calls needed.
    logger.info(f"\n[3/3] Fetch complete. {len(inserted_items)} items ready for Claude to score in conversation.")

    results["success"] = True
    return results


def run_daily_digest(config: dict, dry_run: bool = False) -> dict:
    """
    Daily digest mode: Summarize all items from past 24 hours.
    """
    logger = logging.getLogger(__name__)

    logger.info("=" * 70)
    logger.info("AI NEWS MONITOR - DAILY DIGEST")
    logger.info("=" * 70)

    results = {
        "mode": "daily_digest",
        "high_priority": 0,
        "medium_priority": 0,
        "total": 0,
        "alerted": False,
        "errors": []
    }

    # Get digest data
    digest = get_daily_digest(hours=24)

    if not digest.get("success"):
        results["errors"].append(f"Failed to get digest: {digest.get('error')}")
        results["success"] = False
        return results

    results["high_priority"] = digest.get("high_count", 0)
    results["medium_priority"] = digest.get("medium_count", 0)
    results["total"] = digest.get("total", 0)

    logger.info(f"  Found {results['total']} items from past 24 hours")
    logger.info(f"  High: {results['high_priority']}, Medium: {results['medium_priority']}")

    if results["total"] == 0:
        logger.info("  No items to include in digest")
        results["success"] = True
        return results

    # Format and post digest
    if dry_run:
        logger.info("  DRY RUN - would post digest")
        results["alerted"] = True
    else:
        alert_config = config.get("alerts", DEFAULT_CONFIG["alerts"])
        channel = alert_config.get("slack_channel", "ai-news-alerts")

        alert_result = format_alert("daily", digest)

        if alert_result.get("success"):
            slack_result = post_to_slack(
                blocks=alert_result["blocks"],
                channel=channel,
                text=alert_result["text"]
            )

            if slack_result.get("success"):
                results["alerted"] = True
                logger.info(f"  Posted daily digest to #{channel}")
            else:
                results["errors"].append(f"Slack post failed: {slack_result.get('error')}")
        else:
            results["errors"].append(f"Alert format failed: {alert_result.get('error')}")

    results["success"] = len(results["errors"]) == 0
    return results


def run_weekly_roundup(config: dict, dry_run: bool = False) -> dict:
    """
    Weekly roundup mode: Top 10 content opportunities.
    """
    logger = logging.getLogger(__name__)

    logger.info("=" * 70)
    logger.info("AI NEWS MONITOR - WEEKLY ROUNDUP")
    logger.info("=" * 70)

    results = {
        "mode": "weekly_roundup",
        "total_items": 0,
        "top_10": [],
        "alerted": False,
        "errors": []
    }

    # Get week's data (168 hours = 7 days)
    digest = get_daily_digest(hours=168)

    if not digest.get("success"):
        results["errors"].append(f"Failed to get weekly data: {digest.get('error')}")
        results["success"] = False
        return results

    # Combine and sort by score
    all_items = digest.get("high_priority", []) + digest.get("medium_priority", [])
    all_items.sort(key=lambda x: x.get("relevance_score", 0), reverse=True)

    results["total_items"] = len(all_items)
    results["top_10"] = [i.get("title") for i in all_items[:10]]

    logger.info(f"  Found {len(all_items)} items from past week")
    logger.info(f"  Top 10 content opportunities:")
    for i, item in enumerate(all_items[:10], 1):
        logger.info(f"    {i}. [{item.get('relevance_score')}] {item.get('title')[:50]}")

    if not all_items:
        logger.info("  No items for weekly roundup")
        results["success"] = True
        return results

    # Format and post
    if dry_run:
        logger.info("  DRY RUN - would post weekly roundup")
        results["alerted"] = True
    else:
        alert_config = config.get("alerts", DEFAULT_CONFIG["alerts"])
        channel = alert_config.get("slack_channel", "ai-news-alerts")

        stats = get_stats()
        alert_result = format_alert("weekly", all_items[:10], stats)

        if alert_result.get("success"):
            slack_result = post_to_slack(
                blocks=alert_result["blocks"],
                channel=channel,
                text=alert_result["text"]
            )

            if slack_result.get("success"):
                results["alerted"] = True
                logger.info(f"  Posted weekly roundup to #{channel}")
            else:
                results["errors"].append(f"Slack post failed: {slack_result.get('error')}")
        else:
            results["errors"].append(f"Alert format failed: {alert_result.get('error')}")

    results["success"] = len(results["errors"]) == 0
    return results


def load_config() -> dict:
    """Load config from args/news_monitor.yaml if exists."""
    config_path = WORKSPACE_ROOT / "args" / "news_monitor.yaml"

    if config_path.exists():
        try:
            import yaml
            with open(config_path) as f:
                return yaml.safe_load(f)
        except ImportError:
            pass
        except Exception as e:
            logging.warning(f"Failed to load config: {e}")

    return DEFAULT_CONFIG


def main():
    parser = argparse.ArgumentParser(
        description="AI News Monitor Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  immediate     Fetch new items, score, alert on high-priority
  daily_digest  Generate daily summary
  weekly_roundup Generate weekly top 10

Examples:
  # Run immediate monitoring
  python batch_news_monitor.py --mode immediate

  # Dry run (no Slack posting)
  python batch_news_monitor.py --mode immediate --dry-run

  # Daily digest
  python batch_news_monitor.py --mode daily_digest
        """
    )

    parser.add_argument("--mode", "-m", required=True,
                       choices=["immediate", "daily_digest", "weekly_roundup"],
                       help="Run mode")
    parser.add_argument("--dry-run", action="store_true",
                       help="Don't post to Slack, just show what would happen")
    parser.add_argument("--config", "-c", help="Path to config YAML")

    args = parser.parse_args()

    # Setup
    logger = setup_logging(args.mode)
    config = load_config()

    if args.config:
        try:
            import yaml
            with open(args.config) as f:
                config = yaml.safe_load(f)
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            sys.exit(1)

    # Run appropriate mode
    try:
        if args.mode == "immediate":
            result = run_immediate_mode(config, args.dry_run)
        elif args.mode == "daily_digest":
            result = run_daily_digest(config, args.dry_run)
        elif args.mode == "weekly_roundup":
            result = run_weekly_roundup(config, args.dry_run)

        # Summary
        logger.info("\n" + "=" * 70)
        logger.info("RUN SUMMARY")
        logger.info("=" * 70)
        logger.info(json.dumps(result, indent=2))

        # Output JSON for programmatic use
        print(json.dumps(result, indent=2))

        if result.get("success"):
            sys.exit(0)
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        logger.error("\n\nRun interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n\nFatal error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
