"""
Tool: AI News Database Manager
Purpose: CRUD operations for AI news item tracking and deduplication.
Supports both SQLite (default) and Supabase Postgres via lib.db.

Usage:
    python3 news_db.py --action insert --source hackernews --source-id 12345 --title "Title" --url "https://..."
    python3 news_db.py --action is-duplicate --source hackernews --source-id 12345
    python3 news_db.py --action update-score --id 5 --score 8.5 --tier high --reasoning "Relevant because..."
    python3 news_db.py --action get-unalerted --limit 10
    python3 news_db.py --action mark-alerted --id 5 --slack-ts "1234567890.123456"
    python3 news_db.py --action get --id 5
    python3 news_db.py --action list [--status new|alerted|reviewed|used|dismissed] [--tier high|medium|low]
    python3 news_db.py --action stats
    python3 news_db.py --action daily-digest --hours 24

Output:
    JSON result with success status and data
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Resolve plugin root for lib imports
PLUGIN_ROOT = os.environ.get(
    "CLAUDE_PLUGIN_ROOT",
    str(Path(__file__).resolve().parent.parent.parent)
)
sys.path.insert(0, PLUGIN_ROOT)
from lib.db import execute, execute_one

# Valid values
VALID_SOURCES = ['hackernews', 'github', 'perplexity', 'reddit', 'twitter', 'newsletter']
VALID_STATUSES = ['new', 'alerted', 'reviewed', 'used', 'dismissed']
VALID_TIERS = ['high', 'medium', 'low', 'noise']


def row_to_dict(row):
    """Convert row to dict."""
    if row is None:
        return None
    return dict(row)


def is_duplicate(source: str, source_id: str) -> dict:
    """Check if an item already exists in the database."""
    row = execute_one(
        'SELECT id, title, created_at FROM ops.news_items WHERE source = %s AND source_id = %s',
        (source, source_id)
    )

    if row:
        return {
            "success": True,
            "is_duplicate": True,
            "existing_id": row['id'],
            "existing_title": row['title'],
            "created_at": row.get('created_at')
        }
    return {
        "success": True,
        "is_duplicate": False
    }


def insert_item(
    source: str,
    source_id: str,
    title: str,
    url: str = None,
    summary: str = None,
    raw_content: str = None,
    author: str = None,
    source_timestamp: str = None
) -> dict:
    """Insert a new news item."""
    if source not in VALID_SOURCES:
        return {"success": False, "error": f"Invalid source. Must be one of: {VALID_SOURCES}"}

    # Check for duplicate first
    dup = is_duplicate(source, source_id)
    if dup.get("is_duplicate"):
        return {"success": False, "error": "Duplicate item - already exists", "is_duplicate": True}

    execute('''
        INSERT INTO ops.news_items (source, source_id, title, url, summary, author, status, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, 'new', NOW())
    ''', (source, source_id, title, url, summary, author), fetch=False)

    # Fetch the inserted item
    item = execute_one(
        'SELECT * FROM ops.news_items WHERE source = %s AND source_id = %s',
        (source, source_id)
    )

    return {"success": True, "item": row_to_dict(item), "message": f"Item inserted"}


def update_score(
    item_id: int,
    relevance_score: float,
    relevance_tier: str,
    relevance_reasoning: str = None,
    content_angle: str = None,
    topics_matched: list = None,
    viral_indicators: list = None,
    drift_scores: dict = None,
    drift_total: float = None,
    drift_verdict: str = None,
    drift_reasoning: str = None
) -> dict:
    """Update relevance scoring for an item."""
    if relevance_tier not in VALID_TIERS:
        return {"success": False, "error": f"Invalid tier. Must be one of: {VALID_TIERS}"}

    existing = execute_one('SELECT id FROM ops.news_items WHERE id = %s', (item_id,))
    if not existing:
        return {"success": False, "error": f"Item {item_id} not found"}

    execute('''
        UPDATE ops.news_items
        SET relevance_score = %s, relevance_tier = %s, relevance_reasoning = %s,
            content_angle = %s
        WHERE id = %s
    ''', (relevance_score, relevance_tier, relevance_reasoning, content_angle, item_id), fetch=False)

    item = execute_one('SELECT * FROM ops.news_items WHERE id = %s', (item_id,))
    return {"success": True, "item": row_to_dict(item), "message": f"Item {item_id} scored"}


def get_item(item_id: int) -> dict:
    """Get a single item by ID."""
    item = execute_one('SELECT * FROM ops.news_items WHERE id = %s', (item_id,))

    if not item:
        return {"success": False, "error": f"Item {item_id} not found"}

    return {"success": True, "item": row_to_dict(item)}


def list_items(
    status: str = None,
    tier: str = None,
    source: str = None,
    drift_verdict: str = None,
    limit: int = 50,
    offset: int = 0
) -> dict:
    """List items with optional filters."""
    conditions = []
    params = []

    if status:
        if status not in VALID_STATUSES:
            return {"success": False, "error": f"Invalid status. Must be one of: {VALID_STATUSES}"}
        conditions.append("status = %s")
        params.append(status)

    if tier:
        if tier not in VALID_TIERS:
            return {"success": False, "error": f"Invalid tier. Must be one of: {VALID_TIERS}"}
        conditions.append("relevance_tier = %s")
        params.append(tier)

    if source:
        if source not in VALID_SOURCES:
            return {"success": False, "error": f"Invalid source. Must be one of: {VALID_SOURCES}"}
        conditions.append("source = %s")
        params.append(source)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    count_row = execute_one(f'SELECT COUNT(*) as count FROM ops.news_items {where_clause}', params or None)
    total = count_row['count'] if count_row else 0

    data_params = list(params) + [limit, offset]
    items = execute(f'''
        SELECT * FROM ops.news_items
        {where_clause}
        ORDER BY created_at DESC
        LIMIT %s OFFSET %s
    ''', data_params)

    items = [row_to_dict(row) for row in items]

    return {"success": True, "items": items, "total": total, "limit": limit, "offset": offset}


def get_unalerted_high_priority(limit: int = 10, min_score: float = 8.0) -> dict:
    """Get high-priority items that haven't been alerted yet."""
    items = execute('''
        SELECT * FROM ops.news_items
        WHERE status = 'new'
          AND relevance_score >= %s
          AND relevance_tier = 'high'
        ORDER BY relevance_score DESC, created_at DESC
        LIMIT %s
    ''', (min_score, limit))

    items = [row_to_dict(row) for row in items]
    return {"success": True, "items": items, "count": len(items)}


def mark_alerted(item_id: int, slack_ts: str = None, channel: str = None, alert_type: str = 'immediate') -> dict:
    """Mark an item as alerted."""
    existing = execute_one('SELECT id FROM ops.news_items WHERE id = %s', (item_id,))
    if not existing:
        return {"success": False, "error": f"Item {item_id} not found"}

    execute('''
        UPDATE ops.news_items
        SET status = 'alerted'
        WHERE id = %s
    ''', (item_id,), fetch=False)

    return {"success": True, "message": f"Item {item_id} marked as alerted"}


def update_status(item_id: int, status: str) -> dict:
    """Update item status."""
    if status not in VALID_STATUSES:
        return {"success": False, "error": f"Invalid status. Must be one of: {VALID_STATUSES}"}

    existing = execute_one('SELECT id FROM ops.news_items WHERE id = %s', (item_id,))
    if not existing:
        return {"success": False, "error": f"Item {item_id} not found"}

    execute('''
        UPDATE ops.news_items
        SET status = %s
        WHERE id = %s
    ''', (status, item_id), fetch=False)

    item = execute_one('SELECT * FROM ops.news_items WHERE id = %s', (item_id,))
    return {"success": True, "item": row_to_dict(item), "message": f"Item {item_id} status updated to {status}"}


def get_daily_digest(hours: int = 24) -> dict:
    """Get items from the last N hours for daily digest."""
    items = execute('''
        SELECT * FROM ops.news_items
        WHERE created_at >= NOW() - INTERVAL '1 day' * %s
          AND relevance_score >= 5
          AND relevance_tier IN ('high', 'medium')
        ORDER BY relevance_score DESC, created_at DESC
    ''', (hours / 24,))

    items = [row_to_dict(row) for row in items]

    high = [i for i in items if i.get('relevance_tier') == 'high']
    medium = [i for i in items if i.get('relevance_tier') == 'medium']

    return {
        "success": True,
        "period_hours": hours,
        "total": len(items),
        "high_priority": high,
        "high_count": len(high),
        "medium_priority": medium,
        "medium_count": len(medium)
    }


def get_stats() -> dict:
    """Get database statistics."""
    total_row = execute_one('SELECT COUNT(*) as total FROM ops.news_items')
    total = total_row['total'] if total_row else 0

    return {
        "success": True,
        "total": total,
    }


def main():
    parser = argparse.ArgumentParser(description='AI News Database Manager')
    parser.add_argument('--action', required=True,
                       choices=['insert', 'is-duplicate', 'update-score', 'get', 'list',
                               'get-unalerted', 'mark-alerted', 'update-status', 'daily-digest', 'stats'],
                       help='Action to perform')
    parser.add_argument('--id', type=int, help='Item ID')
    parser.add_argument('--source', help='News source')
    parser.add_argument('--source-id', help='Source-specific ID')
    parser.add_argument('--title', help='Item title')
    parser.add_argument('--url', help='Item URL')
    parser.add_argument('--summary', help='Item summary')
    parser.add_argument('--author', help='Author name')
    parser.add_argument('--score', type=float, help='Relevance score (1-10)')
    parser.add_argument('--tier', help='Relevance tier')
    parser.add_argument('--reasoning', help='Relevance reasoning')
    parser.add_argument('--angle', help='Content angle')
    parser.add_argument('--status', help='Item status')
    parser.add_argument('--slack-ts', help='Slack message timestamp')
    parser.add_argument('--channel', help='Slack channel')
    parser.add_argument('--hours', type=int, default=24, help='Hours for daily digest')
    parser.add_argument('--limit', type=int, default=50, help='Limit for list')
    parser.add_argument('--offset', type=int, default=0, help='Offset for list')
    parser.add_argument('--min-score', type=float, default=8.0, help='Min score for unalerted')
    parser.add_argument('--drift-verdict', choices=['act_now', 'watch', 'ignore'], help='Filter by DRIFT verdict')

    args = parser.parse_args()
    result = None

    if args.action == 'insert':
        if not args.source or not args.source_id or not args.title:
            print(json.dumps({"success": False, "error": "--source, --source-id, and --title required"}))
            sys.exit(1)
        result = insert_item(
            source=args.source,
            source_id=args.source_id,
            title=args.title,
            url=args.url,
            summary=args.summary,
            author=args.author
        )

    elif args.action == 'is-duplicate':
        if not args.source or not args.source_id:
            print(json.dumps({"success": False, "error": "--source and --source-id required"}))
            sys.exit(1)
        result = is_duplicate(args.source, args.source_id)

    elif args.action == 'update-score':
        if not args.id or args.score is None or not args.tier:
            print(json.dumps({"success": False, "error": "--id, --score, and --tier required"}))
            sys.exit(1)
        result = update_score(
            item_id=args.id,
            relevance_score=args.score,
            relevance_tier=args.tier,
            relevance_reasoning=args.reasoning,
            content_angle=args.angle
        )

    elif args.action == 'get':
        if not args.id:
            print(json.dumps({"success": False, "error": "--id required"}))
            sys.exit(1)
        result = get_item(args.id)

    elif args.action == 'list':
        result = list_items(
            status=args.status,
            tier=args.tier,
            source=args.source,
            drift_verdict=args.drift_verdict,
            limit=args.limit,
            offset=args.offset
        )

    elif args.action == 'get-unalerted':
        result = get_unalerted_high_priority(limit=args.limit, min_score=args.min_score)

    elif args.action == 'mark-alerted':
        if not args.id:
            print(json.dumps({"success": False, "error": "--id required"}))
            sys.exit(1)
        result = mark_alerted(args.id, args.slack_ts, args.channel)

    elif args.action == 'update-status':
        if not args.id or not args.status:
            print(json.dumps({"success": False, "error": "--id and --status required"}))
            sys.exit(1)
        result = update_status(args.id, args.status)

    elif args.action == 'daily-digest':
        result = get_daily_digest(hours=args.hours)

    elif args.action == 'stats':
        result = get_stats()

    print(json.dumps(result, indent=2, default=str))

    if not result.get('success'):
        sys.exit(1)


if __name__ == "__main__":
    main()
