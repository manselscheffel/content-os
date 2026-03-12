#!/usr/bin/env python3
"""Show the themed weekly content calendar with draft/gap status.

Queries ops.content_calendar for the 7-day template and ops.content_items
for recent LinkedIn content to show what's covered and what's missing.

Usage:
    python3 calendar_view.py
    python3 calendar_view.py --week current
    python3 calendar_view.py --week next

Output: JSON with calendar grid, gaps, and suggestions.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# PLUGIN_ROOT is 3 levels up: scripts/ -> linkedin-content/ -> skills/ -> root
PLUGIN_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PLUGIN_ROOT))
from lib.db import execute


DAY_ORDER = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def get_calendar():
    """Fetch the weekly theme template."""
    rows = execute(
        "SELECT * FROM ops.content_calendar WHERE active = TRUE ORDER BY id"
    )
    return {r["day_of_week"]: dict(r) for r in rows}


def get_recent_content(days_back=7):
    """Fetch recent LinkedIn content items."""
    rows = execute(
        """SELECT id, category, status, title, content_type, scheduled_for, created_at
           FROM ops.content_items
           WHERE platform = 'linkedin'
             AND created_at > NOW() - INTERVAL '1 day' * %s
           ORDER BY created_at DESC""",
        (days_back,),
    )
    return [_serialize(r) for r in rows]


def get_repurpose_candidates():
    """Find YouTube videos that could be repurposed but haven't been."""
    rows = execute(
        """SELECT ci.id, ci.title, ci.metadata
           FROM ops.content_items ci
           WHERE ci.platform = 'youtube'
             AND ci.content_type = 'video'
             AND ci.status = 'published'
             AND NOT EXISTS (
                 SELECT 1 FROM ops.content_items li
                 WHERE li.platform = 'linkedin'
                   AND li.source_type = 'repurpose'
                   AND li.metadata->>'source_video_title' = ci.title
             )
           ORDER BY ci.published_at DESC NULLS LAST
           LIMIT 5"""
    )
    return [_serialize(r) for r in rows]


def build_calendar_grid(calendar, content):
    """Map content to calendar days and identify gaps."""
    # Group content by category, preserving all items (not just first)
    by_category = {}
    for item in content:
        cat = item.get("category")
        if cat:
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(item)

    # Track which items have been assigned so each day gets a unique item
    used_ids = set()

    grid = []
    for day in DAY_ORDER:
        cal = calendar.get(day, {})
        category = cal.get("category", "")
        theme = cal.get("theme", "")

        # Find matching content not already assigned to another day
        matching = by_category.get(category, [])
        item = None
        for candidate in matching:
            if candidate.get("id") not in used_ids:
                item = candidate
                break

        if item:
            used_ids.add(item.get("id"))
            grid.append({
                "day": day.capitalize(),
                "theme": theme,
                "category": category,
                "status": item["status"],
                "title": item.get("title", ""),
                "content_item_id": item.get("id"),
            })
        else:
            grid.append({
                "day": day.capitalize(),
                "theme": theme,
                "category": category,
                "status": "gap",
                "title": "",
                "content_item_id": None,
            })

    return grid


def _serialize(row):
    if not row:
        return None
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, datetime):
            d[k] = v.isoformat()
    return d


def main():
    calendar = get_calendar()
    content = get_recent_content(days_back=7)
    repurpose_candidates = get_repurpose_candidates()

    grid = build_calendar_grid(calendar, content)
    gaps = [g for g in grid if g["status"] == "gap"]
    filled = [g for g in grid if g["status"] != "gap"]

    output = {
        "success": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "calendar": grid,
        "summary": {
            "total_days": 7,
            "filled": len(filled),
            "gaps": len(gaps),
            "gap_categories": [g["category"] for g in gaps],
        },
        "repurpose_candidates": repurpose_candidates,
        "recent_content": content,
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
