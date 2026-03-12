#!/usr/bin/env python3
"""CRUD operations for ops.content_items and ops.content_calendar.

Usage:
    python3 content_db.py --action insert --platform youtube --content-type video --title "..." [options]
    python3 content_db.py --action list --platform youtube [--status outline]
    python3 content_db.py --action get --id 42
    python3 content_db.py --action update-status --id 42 --status published [--metadata '{}']
    python3 content_db.py --action pillar-gaps --platform youtube
    python3 content_db.py --action calendar
    python3 content_db.py --action recent --platform youtube --limit 10
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Plugin root: scripts/ -> youtube-content/ -> skills/ -> content-os root
PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, PLUGIN_ROOT)
from lib.db import execute, execute_one


def insert_item(args):
    """Insert a new content item."""
    metadata = json.loads(args.metadata) if args.metadata else {}

    row = execute_one(
        """INSERT INTO ops.content_items
           (platform, content_type, category, status, title, body, metadata,
            source_type, source_id, pillar, scheduled_for)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           RETURNING *""",
        (
            args.platform, args.content_type, args.category,
            args.status or "idea", args.title, args.body,
            json.dumps(metadata), args.source_type, args.source_id,
            args.pillar, args.scheduled_for,
        ),
    )
    return {"success": True, "item": _serialize(row)}


def list_items(args):
    """List content items with optional filters."""
    conditions = ["platform = %s"]
    params = [args.platform]

    if args.status:
        conditions.append("status = %s")
        params.append(args.status)
    if args.content_type:
        conditions.append("content_type = %s")
        params.append(args.content_type)
    if args.source_type:
        conditions.append("source_type = %s")
        params.append(args.source_type)

    where = " AND ".join(conditions)
    limit = args.limit or 20

    rows = execute(
        f"SELECT * FROM ops.content_items WHERE {where} ORDER BY created_at DESC LIMIT %s",
        params + [limit],
    )
    return {"success": True, "items": [_serialize(r) for r in rows], "count": len(rows)}


def get_item(args):
    """Get a single content item by ID."""
    row = execute_one("SELECT * FROM ops.content_items WHERE id = %s", (args.id,))
    if not row:
        return {"success": False, "error": f"No content item with id={args.id}"}
    return {"success": True, "item": _serialize(row)}


def update_status(args):
    """Update status and optionally merge metadata."""
    current = execute_one("SELECT * FROM ops.content_items WHERE id = %s", (args.id,))
    if not current:
        return {"success": False, "error": f"No content item with id={args.id}"}

    new_metadata = dict(current["metadata"] or {})
    if args.metadata:
        new_metadata.update(json.loads(args.metadata))

    # Set published_at when transitioning to published
    published_at = None
    if args.status == "published" and current["status"] != "published":
        published_at = datetime.now(timezone.utc).isoformat()

    row = execute_one(
        """UPDATE ops.content_items
           SET status = %s, metadata = %s, published_at = COALESCE(%s, published_at),
               updated_at = NOW()
           WHERE id = %s
           RETURNING *""",
        (args.status, json.dumps(new_metadata), published_at, args.id),
    )
    return {"success": True, "item": _serialize(row)}


def pillar_gaps(args):
    """Show pillar distribution and gaps for a platform."""
    rows = execute(
        """SELECT pillar, COUNT(*) as count
           FROM ops.content_items
           WHERE platform = %s AND pillar IS NOT NULL
             AND created_at > NOW() - INTERVAL '30 days'
           GROUP BY pillar
           ORDER BY pillar""",
        (args.platform,),
    )

    # Pillars 1-7 (from competitive strategy tiers)
    distribution = {i: 0 for i in range(1, 8)}
    for r in rows:
        if r["pillar"] in distribution:
            distribution[r["pillar"]] = r["count"]

    total = sum(distribution.values())
    gaps = [p for p, c in distribution.items() if c == 0]
    underserved = [p for p, c in distribution.items() if 0 < c <= 1]

    return {
        "success": True,
        "distribution": distribution,
        "total_last_30_days": total,
        "gaps": gaps,
        "underserved": underserved,
    }


def get_calendar(_args):
    """Get the weekly content calendar."""
    rows = execute(
        "SELECT * FROM ops.content_calendar WHERE active = TRUE ORDER BY id",
    )
    return {"success": True, "calendar": [_serialize(r) for r in rows]}


def recent_items(args):
    """Get recent content items across statuses."""
    limit = args.limit or 10
    rows = execute(
        """SELECT id, platform, content_type, category, status, title, source_type, pillar, created_at
           FROM ops.content_items
           WHERE platform = %s
           ORDER BY created_at DESC
           LIMIT %s""",
        (args.platform, limit),
    )
    return {"success": True, "items": [_serialize(r) for r in rows], "count": len(rows)}


def _serialize(row):
    """Convert row to JSON-safe dict."""
    if not row:
        return None
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


def main():
    parser = argparse.ArgumentParser(description="Content DB CRUD")
    parser.add_argument("--action", required=True,
                        choices=["insert", "list", "get", "update-status", "pillar-gaps", "calendar", "recent"])
    parser.add_argument("--id", type=int)
    parser.add_argument("--platform", choices=["youtube", "linkedin"])
    parser.add_argument("--content-type")
    parser.add_argument("--category")
    parser.add_argument("--status")
    parser.add_argument("--title")
    parser.add_argument("--body")
    parser.add_argument("--metadata")
    parser.add_argument("--source-type")
    parser.add_argument("--source-id")
    parser.add_argument("--pillar", type=int)
    parser.add_argument("--scheduled-for")
    parser.add_argument("--limit", type=int)

    args = parser.parse_args()

    actions = {
        "insert": insert_item,
        "list": list_items,
        "get": get_item,
        "update-status": update_status,
        "pillar-gaps": pillar_gaps,
        "calendar": get_calendar,
        "recent": recent_items,
    }

    try:
        result = actions[args.action](args)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
