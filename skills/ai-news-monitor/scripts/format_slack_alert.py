#!/usr/bin/env python3
"""
Tool: News Alert Slack Formatter
Purpose: Build Slack Block Kit messages for AI news alerts

Generates Block Kit JSON for different alert types:
- Immediate: Single high-priority item alert
- Daily Digest: Summary of all items from past 24 hours
- Weekly Roundup: Top 10 items with content opportunities

Usage:
    python tools/news_monitor/format_slack_alert.py --type immediate --items-file high_priority.json
    python tools/news_monitor/format_slack_alert.py --type daily --items-file digest.json
    python tools/news_monitor/format_slack_alert.py --type weekly --items-file weekly.json

    # Pipe from score_relevance.py
    cat scored_items.json | python format_slack_alert.py --type immediate

Dependencies:
    - json (stdlib)

Output:
    JSON with Slack Block Kit blocks
"""

import argparse
import json
import sys
from datetime import datetime
from typing import Optional

# Source emoji mapping
SOURCE_EMOJI = {
    "hackernews": ":hackernews:",
    "github": ":github:",
    "twitter": ":bird:",
    "reddit": ":reddit:",
    "perplexity": ":mag:",
    "newsletter": ":newspaper:"
}

# Tier colors (for attachments, not blocks)
TIER_COLORS = {
    "high": "#FF0000",
    "medium": "#FFA500",
    "low": "#808080"
}


def build_immediate_alert(item: dict) -> dict:
    """
    Build Block Kit blocks for a single high-priority alert.

    Args:
        item: Scored news item with title, url, relevance_score, etc.

    Returns:
        dict with blocks array and fallback text
    """
    source = item.get("source", "unknown")
    source_emoji = SOURCE_EMOJI.get(source, ":newspaper:")
    score = item.get("relevance_score", 0)
    tier = item.get("relevance_tier", "medium")

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "AI News Alert",
                "emoji": True
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*<{item.get('url', '#')}|{item.get('title', 'Untitled')}>*"
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"{source_emoji} *{source.title()}*"
                },
                {
                    "type": "mrkdwn",
                    "text": f"Score: *{score}/10* ({tier})"
                }
            ]
        }
    ]

    # Add reasoning if present
    if item.get("relevance_reasoning"):
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Why relevant:* {item['relevance_reasoning']}"
            }
        })

    # Add content angle if present
    if item.get("content_angle"):
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Video angle:* {item['content_angle']}"
            }
        })

    # Add DRIFT verdict if present
    if item.get("drift_verdict"):
        verdict = item["drift_verdict"]
        verdict_emoji = {"act_now": ":rotating_light:", "watch": ":eyes:", "ignore": ":zzz:"}.get(verdict, "")
        drift_total = item.get("drift_total", "?")
        drift_label = {"act_now": "ACT NOW", "watch": "WATCH", "ignore": "IGNORE"}.get(verdict, verdict.upper())
        drift_text = f"{verdict_emoji} *DRIFT: {drift_label}* ({drift_total}/10)"
        if item.get("drift_reasoning"):
            drift_text += f"\n_{item['drift_reasoning']}_"
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": drift_text
            }
        })

    # Add viral indicators if present
    if item.get("viral_indicators"):
        indicators = item["viral_indicators"]
        if isinstance(indicators, list) and indicators:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Viral signals:* {', '.join(indicators)}"
                    }
                ]
            })

    # Add topics matched
    if item.get("topics_matched"):
        topics = item["topics_matched"]
        if isinstance(topics, list) and topics:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Topics:* {', '.join(topics)}"
                    }
                ]
            })

    # Add HN-specific info if available
    if item.get("score") and source == "hackernews":
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"HN: {item.get('score', 0)} points | {item.get('comments', 0)} comments | <{item.get('hn_url', '#')}|Discussion>"
                }
            ]
        })

    # Add actions (informational for now)
    blocks.append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Open Link",
                    "emoji": True
                },
                "url": item.get("url", "#"),
                "action_id": f"open_link_{item.get('source_id', 'unknown')}"
            }
        ]
    })

    blocks.append({"type": "divider"})

    return {
        "blocks": blocks,
        "text": f"AI News Alert: {item.get('title', 'New item')}"
    }


def build_daily_digest(items: dict) -> dict:
    """
    Build Block Kit blocks for daily digest.

    Args:
        items: Result from get_daily_digest() with high_priority and medium_priority lists

    Returns:
        dict with blocks array and fallback text
    """
    high = items.get("high_priority", [])
    medium = items.get("medium_priority", [])
    total = items.get("total", len(high) + len(medium))
    hours = items.get("period_hours", 24)

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"AI News Digest",
                "emoji": True
            }
        },
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"Last {hours} hours | {total} items | {len(high)} high priority | {len(medium)} medium"
                }
            ]
        },
        {"type": "divider"}
    ]

    # High priority section
    if high:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*High Priority*"
            }
        })

        for item in high[:5]:  # Limit to 5 items
            source_emoji = SOURCE_EMOJI.get(item.get("source"), ":newspaper:")
            score = item.get("relevance_score", 0)
            verdict = item.get("drift_verdict")
            verdict_tag = ""
            if verdict:
                verdict_emoji = {"act_now": ":rotating_light:", "watch": ":eyes:", "ignore": ":zzz:"}.get(verdict, "")
                verdict_label = {"act_now": "ACT", "watch": "WATCH", "ignore": "IGNORE"}.get(verdict, "")
                verdict_tag = f" {verdict_emoji} DRIFT: {verdict_label}"

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{source_emoji} *<{item.get('url', '#')}|{item.get('title', 'Untitled')}>*\n_{item.get('relevance_reasoning', 'No reasoning')}_ (Score: {score}{verdict_tag})"
                }
            })

    # Medium priority section
    if medium:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Medium Priority*"
            }
        })

        # Compact list for medium items
        medium_text = "\n".join([
            f"• <{item.get('url', '#')}|{item.get('title', 'Untitled')[:60]}...>" if len(item.get('title', '')) > 60
            else f"• <{item.get('url', '#')}|{item.get('title', 'Untitled')}>"
            for item in medium[:10]
        ])

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": medium_text
            }
        })

    # Footer
    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} | AI News Monitor"
            }
        ]
    })

    return {
        "blocks": blocks,
        "text": f"AI News Digest: {len(high)} high priority, {len(medium)} medium"
    }


def build_weekly_roundup(items: list, week_stats: dict = None) -> dict:
    """
    Build Block Kit blocks for weekly roundup.

    Args:
        items: List of top items for the week
        week_stats: Optional stats dict with totals

    Returns:
        dict with blocks array and fallback text
    """
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": "Weekly AI News Roundup",
                "emoji": True
            }
        }
    ]

    # Stats if available
    if week_stats:
        blocks.append({
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": f"This week: {week_stats.get('total', 0)} items tracked | {week_stats.get('high', 0)} high priority | {week_stats.get('alerted', 0)} alerted"
                }
            ]
        })

    blocks.append({"type": "divider"})
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*Top 10 Content Opportunities*"
        }
    })

    # Top items
    for i, item in enumerate(items[:10], 1):
        source_emoji = SOURCE_EMOJI.get(item.get("source"), ":newspaper:")
        score = item.get("relevance_score", 0)
        angle = item.get("content_angle", "No angle suggested")

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{i}. {source_emoji} <{item.get('url', '#')}|{item.get('title', 'Untitled')}>*\n_{angle}_ (Score: {score})"
            }
        })

    # Footer
    blocks.append({"type": "divider"})
    blocks.append({
        "type": "context",
        "elements": [
            {
                "type": "mrkdwn",
                "text": f"Week ending {datetime.now().strftime('%Y-%m-%d')} | AI News Monitor"
            }
        ]
    })

    return {
        "blocks": blocks,
        "text": f"Weekly AI News Roundup: Top {len(items[:10])} content opportunities"
    }


def format_alert(
    alert_type: str,
    items,  # list or dict
    stats: dict = None
) -> dict:
    """
    Format items into Slack Block Kit based on alert type.

    Args:
        alert_type: immediate, daily, or weekly
        items: Items to format (list or dict depending on type)
        stats: Optional stats for context

    Returns:
        dict with blocks and text
    """
    if alert_type == "immediate":
        # For immediate, format each high-priority item separately
        if isinstance(items, dict):
            items = items.get("items", items.get("scored_items", [items]))

        high_items = [i for i in items if i.get("relevance_tier") == "high" or i.get("relevance_score", 0) >= 8]

        if not high_items:
            return {
                "success": False,
                "error": "No high-priority items to alert"
            }

        # Build alerts for each item
        all_blocks = []
        for item in high_items:
            result = build_immediate_alert(item)
            all_blocks.extend(result["blocks"])

        return {
            "success": True,
            "blocks": all_blocks,
            "text": f"AI News Alert: {len(high_items)} high-priority items",
            "item_count": len(high_items)
        }

    elif alert_type == "daily":
        if isinstance(items, list):
            # Convert list to expected format
            items = {
                "high_priority": [i for i in items if i.get("relevance_tier") == "high"],
                "medium_priority": [i for i in items if i.get("relevance_tier") == "medium"],
                "total": len(items)
            }

        result = build_daily_digest(items)
        return {
            "success": True,
            **result
        }

    elif alert_type == "weekly":
        if isinstance(items, dict):
            items = items.get("items", items.get("scored_items", []))

        result = build_weekly_roundup(items, stats)
        return {
            "success": True,
            **result
        }

    else:
        return {
            "success": False,
            "error": f"Unknown alert type: {alert_type}"
        }


def main():
    parser = argparse.ArgumentParser(
        description="Format AI news items as Slack Block Kit messages",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Format high-priority items for immediate alert
  python format_slack_alert.py --type immediate --items-file scored.json

  # Format daily digest
  python format_slack_alert.py --type daily --items-file digest.json

  # Format weekly roundup
  python format_slack_alert.py --type weekly --items-file weekly.json

  # Pipe from scoring
  cat scored.json | python format_slack_alert.py --type immediate
        """
    )

    parser.add_argument("--type", "-t", required=True,
                       choices=["immediate", "daily", "weekly"],
                       help="Alert type to generate")
    parser.add_argument("--items-file", "-f", help="JSON file with items")
    parser.add_argument("--output", "-o", help="Save output to file")

    args = parser.parse_args()

    # Load items
    if args.items_file:
        with open(args.items_file) as f:
            items = json.load(f)
    elif not sys.stdin.isatty():
        items = json.load(sys.stdin)
    else:
        print(json.dumps({"success": False, "error": "No items provided"}))
        sys.exit(1)

    # Format alert
    result = format_alert(args.type, items)

    # Output
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
