#!/usr/bin/env python3
"""
Tool: YouTube SEO Trend Database
Purpose: Database storage for tracking YouTube autocomplete suggestions,
         Google Trends data, and rising videos over time. Supports day-over-day comparison.

Usage:
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/trend_db.py --init-db
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/trend_db.py --save-suggestions input.json
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/trend_db.py --save-trends input.json
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/trend_db.py --save-videos input.json
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/trend_db.py --diff-suggestions
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/trend_db.py --stats
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/trend_db.py --today-data

Dependencies:
    - lib.db (dual-backend: SQLite default, Supabase Postgres optional)

Output: JSON with success status and data
"""

import sys
import json
import argparse
from datetime import date, timedelta
from pathlib import Path

# Resolve plugin root for lib imports
import os
PLUGIN_ROOT = os.environ.get(
    "CLAUDE_PLUGIN_ROOT",
    str(Path(__file__).resolve().parent.parent.parent)
)
PROJECT_ROOT = Path(PLUGIN_ROOT).parent  # project root
sys.path.insert(0, PLUGIN_ROOT)
from lib.db import execute, execute_one, get_backend


def init_db():
    """Verify tables exist (migration creates them, this just confirms)."""
    expected_tables = ['seo_suggestions', 'seo_trends', 'seo_rising_queries', 'seo_rising_videos', 'seo_reports']

    if get_backend() == "sqlite":
        row = execute_one(
            "SELECT COUNT(*) as count FROM sqlite_master "
            "WHERE type = 'table' AND name LIKE 'seo_%'"
        )
    else:
        row = execute_one(
            "SELECT COUNT(*) as count FROM information_schema.tables "
            "WHERE table_schema = 'ops' AND table_name LIKE 'seo_%'"
        )

    count = row['count'] if row else 0
    if count >= 5:
        return {"success": True, "message": f"All {count} YouTube SEO tables found"}
    return {"success": False, "message": f"Only {count}/5 tables found. Run the database migration."}


def save_suggestions(data):
    """Save autocomplete suggestions. Tracks first_seen and updates last_seen."""
    today = date.today().isoformat()

    new_count = 0
    updated_count = 0

    items = data if isinstance(data, list) else data.get("suggestions", [])

    for item in items:
        seed = item.get("seed_keyword", item.get("seed", ""))
        suggestion = item.get("suggestion", "")
        if not seed or not suggestion:
            continue

        # Check if this suggestion already exists
        existing = execute_one(
            "SELECT first_seen, times_seen FROM ops.seo_suggestions "
            "WHERE seed_keyword = %s AND suggestion = %s",
            (seed, suggestion)
        )

        if existing is None:
            # New suggestion — insert
            execute("""
                INSERT INTO ops.seo_suggestions (seed_keyword, suggestion, first_seen, last_seen, times_seen, is_new)
                VALUES (%s, %s, %s, %s, 1, TRUE)
            """, (seed, suggestion, today, today), fetch=False)
            new_count += 1
        else:
            # Existing — update
            is_new = existing['first_seen'] == today
            times = (existing['times_seen'] or 0) + 1
            execute("""
                UPDATE ops.seo_suggestions SET last_seen = %s, times_seen = %s, is_new = %s
                WHERE seed_keyword = %s AND suggestion = %s
            """, (today, times, is_new, seed, suggestion), fetch=False)
            updated_count += 1

    return {
        "success": True,
        "new_suggestions": new_count,
        "updated_suggestions": updated_count,
        "total_processed": len(items)
    }


def save_trends(data):
    """Save Google Trends data."""
    today = date.today().isoformat()

    saved = 0
    items = data if isinstance(data, list) else data.get("trends", [])

    for item in items:
        keyword = item.get("keyword", "")
        interest = item.get("interest_score", item.get("interest", 0))
        is_breakout = item.get("is_breakout", False)
        rising_pct = item.get("rising_percent", item.get("change_pct", None))

        if not keyword:
            continue

        # Check if entry exists for today
        existing = execute_one(
            "SELECT keyword FROM ops.seo_trends WHERE keyword = %s AND date = %s",
            (keyword, today)
        )

        if existing is None:
            execute("""
                INSERT INTO ops.seo_trends (keyword, date, interest_score, is_breakout, rising_percent)
                VALUES (%s, %s, %s, %s, %s)
            """, (keyword, today, interest, is_breakout, rising_pct), fetch=False)
        else:
            execute("""
                UPDATE ops.seo_trends SET interest_score = %s, is_breakout = %s, rising_percent = %s
                WHERE keyword = %s AND date = %s
            """, (interest, is_breakout, rising_pct, keyword, today), fetch=False)
        saved += 1

    # Save rising queries if present
    rising_queries = data.get("rising_queries", []) if isinstance(data, dict) else []
    for rq in rising_queries:
        seed = rq.get("seed_keyword", "")
        query = rq.get("query", "")
        value = str(rq.get("value", ""))
        if seed and query:
            existing = execute_one(
                "SELECT seed_keyword FROM ops.seo_rising_queries "
                "WHERE seed_keyword = %s AND query = %s AND date = %s",
                (seed, query, today)
            )
            if existing is None:
                execute("""
                    INSERT INTO ops.seo_rising_queries (seed_keyword, query, value, date)
                    VALUES (%s, %s, %s, %s)
                """, (seed, query, value, today), fetch=False)
            else:
                execute("""
                    UPDATE ops.seo_rising_queries SET value = %s
                    WHERE seed_keyword = %s AND query = %s AND date = %s
                """, (value, seed, query, today), fetch=False)

    return {"success": True, "trends_saved": saved, "rising_queries_saved": len(rising_queries)}


def save_videos(data):
    """Save rising video data."""
    today = date.today().isoformat()

    saved = 0
    items = data if isinstance(data, list) else data.get("videos", [])

    for item in items:
        vid = item.get("video_id", "")
        if not vid:
            continue

        title = item.get("title", "")
        channel = item.get("channel", "")
        published_at = item.get("published_at", "")
        views = item.get("views", 0)
        velocity = item.get("view_velocity", item.get("velocity", 0))
        keyword = item.get("keyword_match", item.get("keyword", ""))

        existing = execute_one(
            "SELECT video_id FROM ops.seo_rising_videos WHERE video_id = %s",
            (vid,)
        )

        if existing is None:
            execute("""
                INSERT INTO ops.seo_rising_videos
                    (video_id, title, channel, published_at, views, view_velocity, keyword_match, first_spotted)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (vid, title, channel, published_at, views, velocity, keyword, today), fetch=False)
        else:
            execute("""
                UPDATE ops.seo_rising_videos SET views = %s, view_velocity = %s
                WHERE video_id = %s
            """, (views, velocity, vid), fetch=False)
        saved += 1

    return {"success": True, "videos_saved": saved}


def diff_suggestions():
    """Find suggestions that are new today (first_seen = today)."""
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()

    new_today = execute("""
        SELECT seed_keyword, suggestion, first_seen, times_seen
        FROM ops.seo_suggestions
        WHERE first_seen = %s
        ORDER BY seed_keyword, suggestion
    """, (today,))

    # Suggestions that disappeared (seen yesterday but not today)
    disappeared = execute("""
        SELECT seed_keyword, suggestion, first_seen, last_seen, times_seen
        FROM ops.seo_suggestions
        WHERE last_seen = %s AND last_seen != %s
        ORDER BY seed_keyword, suggestion
    """, (yesterday, today))

    return {
        "success": True,
        "new_today": new_today,
        "new_count": len(new_today),
        "disappeared": disappeared,
        "disappeared_count": len(disappeared),
        "date": today
    }


def get_today_data():
    """Get all data collected today for scoring."""
    today = date.today().isoformat()

    new_suggestions = execute("""
        SELECT seed_keyword, suggestion FROM ops.seo_suggestions
        WHERE first_seen = %s
    """, (today,))

    trends = execute("""
        SELECT keyword, interest_score, is_breakout, rising_percent FROM ops.seo_trends
        WHERE date = %s
    """, (today,))

    rising_queries = execute("""
        SELECT seed_keyword, query, value FROM ops.seo_rising_queries
        WHERE date = %s
    """, (today,))

    videos = execute("""
        SELECT video_id, title, channel, views, view_velocity, keyword_match
        FROM ops.seo_rising_videos
        WHERE first_spotted = %s
        ORDER BY view_velocity DESC
    """, (today,))

    return {
        "success": True,
        "date": today,
        "new_suggestions": new_suggestions,
        "trends": trends,
        "rising_queries": rising_queries,
        "rising_videos": videos
    }


def get_stats():
    """Get database statistics."""
    today = date.today().isoformat()

    total_row = execute_one("SELECT COUNT(*) as total FROM ops.seo_suggestions")
    total_suggestions = total_row['total']

    new_row = execute_one("SELECT COUNT(*) as count FROM ops.seo_suggestions WHERE first_seen = %s", (today,))
    new_today = new_row['count']

    seeds_row = execute_one("SELECT COUNT(DISTINCT seed_keyword) as count FROM ops.seo_suggestions")
    unique_seeds = seeds_row['count']

    trends_row = execute_one("SELECT COUNT(*) as total FROM ops.seo_trends")
    total_trends = trends_row['total']

    videos_row = execute_one("SELECT COUNT(*) as total FROM ops.seo_rising_videos")
    total_videos = videos_row['total']

    reports_row = execute_one("SELECT COUNT(*) as total FROM ops.seo_reports")
    total_reports = reports_row['total']

    earliest_row = execute_one("SELECT MIN(first_seen) as earliest FROM ops.seo_suggestions")
    earliest = earliest_row['earliest'] if earliest_row else None

    return {
        "success": True,
        "total_suggestions": total_suggestions,
        "new_today": new_today,
        "unique_seed_keywords": unique_seeds,
        "total_trend_entries": total_trends,
        "total_rising_videos": total_videos,
        "total_reports": total_reports,
        "tracking_since": earliest
    }


def save_report_meta(report_path, new_sug, breakout, hot_vids, top_opp):
    """Save report metadata."""
    today = date.today().isoformat()

    execute("""
        INSERT INTO ops.seo_reports (date, report_path, new_suggestions_count,
                    breakout_trends_count, hot_videos_count, top_opportunity)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT(date) DO UPDATE SET
            report_path = EXCLUDED.report_path,
            new_suggestions_count = EXCLUDED.new_suggestions_count,
            breakout_trends_count = EXCLUDED.breakout_trends_count,
            hot_videos_count = EXCLUDED.hot_videos_count,
            top_opportunity = EXCLUDED.top_opportunity
    """, (today, report_path, new_sug, breakout, hot_vids, top_opp), fetch=False)

    return {"success": True, "message": f"Report metadata saved for {today}"}


def main():
    parser = argparse.ArgumentParser(description="YouTube SEO Trend Database")
    parser.add_argument("--init-db", action="store_true", help="Verify database tables exist")
    parser.add_argument("--save-suggestions", metavar="FILE", help="Save suggestions from JSON file")
    parser.add_argument("--save-trends", metavar="FILE", help="Save trends from JSON file")
    parser.add_argument("--save-videos", metavar="FILE", help="Save rising videos from JSON file")
    parser.add_argument("--diff-suggestions", action="store_true", help="Show new/disappeared suggestions")
    parser.add_argument("--today-data", action="store_true", help="Get all data collected today")
    parser.add_argument("--stats", action="store_true", help="Show database statistics")

    args = parser.parse_args()
    result = None

    if args.init_db:
        result = init_db()

    elif args.save_suggestions:
        with open(args.save_suggestions) as f:
            data = json.load(f)
        result = save_suggestions(data)

    elif args.save_trends:
        with open(args.save_trends) as f:
            data = json.load(f)
        result = save_trends(data)

    elif args.save_videos:
        with open(args.save_videos) as f:
            data = json.load(f)
        result = save_videos(data)

    elif args.diff_suggestions:
        result = diff_suggestions()

    elif args.today_data:
        result = get_today_data()

    elif args.stats:
        result = get_stats()

    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, indent=2, default=str))

    if result and not result.get("success"):
        sys.exit(1)


if __name__ == "__main__":
    main()
