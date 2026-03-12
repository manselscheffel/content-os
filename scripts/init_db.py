#!/usr/bin/env python3
"""Initialize the content-os database.

Creates tables and seeds the content calendar.
Works with both SQLite and Supabase backends.

Usage:
    python3 init_db.py
    python3 init_db.py --seed-calendar
"""

import json
import os
import sys
from pathlib import Path

# Add plugin root to path
PLUGIN_ROOT = os.environ.get(
    "CLAUDE_PLUGIN_ROOT",
    str(Path(__file__).resolve().parent.parent),
)
sys.path.insert(0, PLUGIN_ROOT)

from lib.db import init_db, execute, execute_one


CALENDAR_SEED = [
    ("monday", "Motivation", "motivation", "Vulnerable admission, lesson learned, or mindset shift"),
    ("tuesday", "Tools", "new_tool", "Tool review, comparison, or workflow showcase"),
    ("wednesday", "Deep Dive", "psp", "Problem/Solution/Path — full build or technical deep dive"),
    ("thursday", "Contrarian", "contrarian", "Counter-claim to popular opinion, debunk, or honest take"),
    ("friday", "Video Drop", "video_drop", "YouTube video announcement post with key insight"),
    ("saturday", "Story", "story", "Build log, behind-the-scenes, or personal experience"),
    ("sunday", "Week Ahead", "list", "List post — tools, lessons, predictions, or curated picks"),
]


def seed_calendar():
    """Seed the content calendar with default 7-day schedule."""
    existing = execute("SELECT COUNT(*) as cnt FROM ops.content_calendar")
    if existing and existing[0].get("cnt", 0) > 0:
        print("  Calendar already seeded — skipping")
        return

    for day, theme, category, description in CALENDAR_SEED:
        execute(
            """INSERT INTO ops.content_calendar (day_of_week, theme, category, description)
               VALUES (%s, %s, %s, %s)""",
            (day, theme, category, description),
            fetch=False,
        )
    print(f"  Seeded calendar with {len(CALENDAR_SEED)} days")


def main():
    print("Initializing content-os database...")

    result = init_db()
    print(f"  Backend: {result['backend']}")
    if result.get("path"):
        print(f"  Database: {result['path']}")

    print("  Tables created successfully")

    # Always seed calendar
    seed_calendar()

    print("\nDatabase ready!")
    print(json.dumps({"success": True, **result}, indent=2))


if __name__ == "__main__":
    main()
