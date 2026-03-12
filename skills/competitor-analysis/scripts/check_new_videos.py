#!/usr/bin/env python3
"""
Competitor Analysis — State Manager

Tracks which channels have been checked, which videos have been processed,
and stores contrarian angles for later reference.

Supports both SQLite (default) and Supabase Postgres via lib.db.

Usage:
    python3 check_new_videos.py --init-db
    python3 check_new_videos.py --status
    python3 check_new_videos.py --mark-processed VIDEO_ID --channel "@handle" --title "Title" --path "path/to/analysis.md"
    python3 check_new_videos.py --set-last-checked "@handle"
    python3 check_new_videos.py --is-processed VIDEO_ID
    python3 check_new_videos.py --unprocessed
    python3 check_new_videos.py --add-angle --video-id VIDEO_ID --angle "Text" --risk medium --reward high
    python3 check_new_videos.py --angles [--status new]
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# Resolve plugin root for lib imports
PLUGIN_ROOT = os.environ.get(
    "CLAUDE_PLUGIN_ROOT",
    str(Path(__file__).resolve().parent.parent.parent)
)
sys.path.insert(0, PLUGIN_ROOT)
from lib.db import execute, execute_one

COMPETITORS_PATH = Path(__file__).resolve().parent.parent / "references" / "competitors.yaml"


def init_db():
    """Seed channels from competitors.yaml (tables created by migration)."""
    # Ensure tables exist via lib.db init
    from lib.db import init_db as db_init
    db_init()

    if COMPETITORS_PATH.exists():
        try:
            import yaml
            with open(COMPETITORS_PATH) as f:
                config = yaml.safe_load(f)
            for comp in config.get("competitors", []):
                handle = comp.get("handle", "")
                name = comp.get("name", "")
                if not handle:
                    continue
                execute(
                    """INSERT INTO ops.channels (handle, channel_name)
                       VALUES (%s, %s)
                       ON CONFLICT (handle) DO NOTHING""",
                    (handle, name),
                    fetch=False
                )
        except ImportError:
            pass
        except Exception as e:
            print(json.dumps({"success": True, "warning": f"Could not seed channels: {e}"}))
            return

    print(json.dumps({"success": True, "message": "Database initialized"}))


def show_status():
    channels = execute("SELECT handle, channel_name, last_checked FROM ops.channels ORDER BY handle")
    total_videos = execute_one("SELECT COUNT(*) as cnt FROM ops.processed_videos")
    total_angles = execute_one("SELECT COUNT(*) as cnt FROM ops.contrarian_angles WHERE status = 'new'")

    result = {
        "channels": [],
        "total_processed_videos": total_videos["cnt"] if total_videos else 0,
        "pending_contrarian_angles": total_angles["cnt"] if total_angles else 0
    }

    for ch in channels:
        video_count = execute_one(
            "SELECT COUNT(*) as cnt FROM ops.processed_videos WHERE channel_handle = %s",
            (ch["handle"],)
        )

        result["channels"].append({
            "handle": ch["handle"],
            "name": ch["channel_name"],
            "last_checked": ch["last_checked"],
            "videos_analyzed": video_count["cnt"] if video_count else 0
        })

    print(json.dumps(result, indent=2, default=str))


def mark_processed(video_id, channel_handle, title=None, path=None, pillar=None, published_at=None, views=None):
    # Ensure channel exists
    execute(
        "INSERT INTO ops.channels (handle) VALUES (%s) ON CONFLICT (handle) DO NOTHING",
        (channel_handle,),
        fetch=False
    )
    execute("""
        INSERT INTO ops.processed_videos
        (video_id, channel_handle, title, analysis_path, content_pillar, published_at, views)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (video_id) DO UPDATE SET
            channel_handle = EXCLUDED.channel_handle,
            title = EXCLUDED.title,
            analysis_path = EXCLUDED.analysis_path,
            content_pillar = EXCLUDED.content_pillar,
            published_at = EXCLUDED.published_at,
            views = EXCLUDED.views
    """, (video_id, channel_handle, title, path, pillar, published_at, views), fetch=False)
    print(json.dumps({"success": True, "video_id": video_id, "status": "processed"}))


def set_last_checked(handle):
    now = datetime.utcnow().isoformat()
    execute(
        "INSERT INTO ops.channels (handle) VALUES (%s) ON CONFLICT (handle) DO NOTHING",
        (handle,),
        fetch=False
    )
    execute(
        "UPDATE ops.channels SET last_checked = NOW() WHERE handle = %s",
        (handle,),
        fetch=False
    )
    print(json.dumps({"success": True, "handle": handle, "last_checked": now}))


def is_processed(video_id):
    row = execute_one("SELECT * FROM ops.processed_videos WHERE video_id = %s", (video_id,))
    if row:
        print(json.dumps({"processed": True, "video_id": video_id, "title": row.get("title"), "analyzed_at": row.get("created_at")}, default=str))
    else:
        print(json.dumps({"processed": False, "video_id": video_id}))


def list_unprocessed():
    """Show channels that haven't been checked recently."""
    channels = execute(
        "SELECT handle, channel_name, last_checked FROM ops.channels WHERE last_checked IS NULL OR last_checked < NOW() - INTERVAL '1 day' * %s",
        (1,),
    )

    result = [{"handle": ch["handle"], "name": ch.get("channel_name"), "last_checked": ch.get("last_checked")} for ch in channels]
    print(json.dumps({"channels_needing_check": result}, indent=2, default=str))


def add_angle(video_id, angle, risk="medium", reward="high"):
    execute("""
        INSERT INTO ops.contrarian_angles (video_id, angle, risk_level, reward_potential)
        VALUES (%s, %s, %s, %s)
    """, (video_id, angle, risk, reward), fetch=False)
    print(json.dumps({"success": True, "video_id": video_id, "angle": angle[:80]}))


def list_angles(status_filter=None):
    if status_filter:
        rows = execute("""
            SELECT ca.*, pv.title, pv.channel_handle
            FROM ops.contrarian_angles ca
            JOIN ops.processed_videos pv ON ca.video_id = pv.video_id
            WHERE ca.status = %s
            ORDER BY ca.created_at DESC
        """, (status_filter,))
    else:
        rows = execute("""
            SELECT ca.*, pv.title, pv.channel_handle
            FROM ops.contrarian_angles ca
            JOIN ops.processed_videos pv ON ca.video_id = pv.video_id
            ORDER BY ca.created_at DESC
        """)

    result = [{
        "id": r.get("id"),
        "video_id": r.get("video_id"),
        "channel": r.get("channel_handle"),
        "video_title": r.get("title"),
        "angle": r.get("angle"),
        "risk": r.get("risk_level"),
        "reward": r.get("reward_potential"),
        "status": r.get("status"),
        "created": r.get("created_at")
    } for r in rows]
    print(json.dumps({"angles": result, "count": len(result)}, indent=2, default=str))


def main():
    parser = argparse.ArgumentParser(description="Competitor Analysis State Manager")

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--init-db", action="store_true", help="Initialize the database")
    group.add_argument("--status", action="store_true", help="Show status of all channels")
    group.add_argument("--mark-processed", metavar="VIDEO_ID", help="Mark a video as processed")
    group.add_argument("--set-last-checked", metavar="HANDLE", help="Update last_checked for a channel")
    group.add_argument("--is-processed", metavar="VIDEO_ID", help="Check if a video was already processed")
    group.add_argument("--unprocessed", action="store_true", help="List channels needing a check")
    group.add_argument("--add-angle", action="store_true", help="Store a contrarian angle")
    group.add_argument("--angles", action="store_true", help="List contrarian angles")

    parser.add_argument("--channel", help="Channel handle (for --mark-processed)")
    parser.add_argument("--title", help="Video title (for --mark-processed)")
    parser.add_argument("--path", help="Analysis file path (for --mark-processed)")
    parser.add_argument("--pillar", help="Content pillar (for --mark-processed)")
    parser.add_argument("--published-at", help="Published date (for --mark-processed)")
    parser.add_argument("--views", type=int, help="View count (for --mark-processed)")
    parser.add_argument("--video-id", help="Video ID (for --add-angle)")
    parser.add_argument("--angle", help="Angle text (for --add-angle)")
    parser.add_argument("--risk", default="medium", help="Risk level (for --add-angle)")
    parser.add_argument("--reward", default="high", help="Reward potential (for --add-angle)")
    parser.add_argument("--filter-status", help="Filter by status (for --angles)")

    args = parser.parse_args()

    if args.init_db:
        init_db()
    elif args.status:
        show_status()
    elif args.mark_processed:
        if not args.channel:
            print(json.dumps({"success": False, "error": "--channel required with --mark-processed"}))
            sys.exit(1)
        mark_processed(args.mark_processed, args.channel, args.title, args.path, args.pillar, args.published_at, args.views)
    elif args.set_last_checked:
        set_last_checked(args.set_last_checked)
    elif args.is_processed:
        is_processed(args.is_processed)
    elif args.unprocessed:
        list_unprocessed()
    elif args.add_angle:
        if not args.video_id or not args.angle:
            print(json.dumps({"success": False, "error": "--video-id and --angle required with --add-angle"}))
            sys.exit(1)
        add_angle(args.video_id, args.angle, args.risk, args.reward)
    elif args.angles:
        list_angles(args.filter_status)


if __name__ == "__main__":
    main()
