#!/usr/bin/env python3
"""Query 5 intelligence sources and output ranked video ideas as JSON.

Sources:
  1. Competitor angles (ops.contrarian_angles)
  2. AI news (ops.news_items)
  3. YouTube SEO trends (ops.seo_*)
  4. ICP/niche gaps (context files + ops.content_items)
  5. Novel ideas (context files)

Output: JSON with ranked ideas from each source, plus metadata for scoring.
Claude handles the final scoring and ranking using references/ideation_prompt.md.
"""

import json
import os
import sys
from pathlib import Path
from datetime import datetime, timezone

# Plugin root: scripts/ -> youtube-content/ -> skills/ -> content-os root
PLUGIN_ROOT = os.environ.get("CLAUDE_PLUGIN_ROOT", str(Path(__file__).resolve().parent.parent.parent))
sys.path.insert(0, PLUGIN_ROOT)
from lib.db import execute


def fetch_competitor_angles():
    """Source 1: Recent contrarian angles with high reward potential."""
    try:
        rows = execute(
            """SELECT ca.id, ca.video_id, ca.angle, ca.risk_level, ca.reward_potential, ca.created_at,
                      pv.title as video_title, pv.channel_handle as channel
               FROM ops.contrarian_angles ca
               LEFT JOIN ops.processed_videos pv ON ca.video_id = pv.video_id
               WHERE ca.created_at > NOW() - INTERVAL '14 days'
               ORDER BY
                   CASE ca.reward_potential
                       WHEN 'very_high' THEN 4
                       WHEN 'high' THEN 3
                       WHEN 'medium' THEN 2
                       ELSE 1
                   END DESC
               LIMIT 10"""
        )
        return {
            "source": "competitor_angle",
            "count": len(rows),
            "items": [_serialize(r) for r in rows],
        }
    except Exception as e:
        return {"source": "competitor_angle", "count": 0, "items": [], "error": str(e)}


def fetch_ai_news():
    """Source 2: High-scoring news items from the last 7 days."""
    try:
        rows = execute(
            """SELECT id, title, source, url, relevance_score, relevance_tier,
                      summary, created_at
               FROM ops.news_items
               WHERE relevance_score >= 7
                 AND created_at > NOW() - INTERVAL '7 days'
               ORDER BY relevance_score DESC, created_at DESC
               LIMIT 10"""
        )
        return {
            "source": "news_item",
            "count": len(rows),
            "items": [_serialize(r) for r in rows],
        }
    except Exception as e:
        return {"source": "news_item", "count": 0, "items": [], "error": str(e)}


def fetch_seo_trends():
    """Source 3: Rising search terms, breakout trends, high-velocity videos."""
    results = {"source": "seo_trend", "items": [], "count": 0}

    try:
        # New autocomplete suggestions (first seen today or yesterday)
        new_suggestions = execute(
            """SELECT seed_keyword, suggestion, first_seen
               FROM ops.seo_suggestions
               WHERE first_seen >= CURRENT_DATE - INTERVAL '2 days'
                 AND is_new = TRUE
               ORDER BY first_seen DESC
               LIMIT 10"""
        )

        # Breakout trends from Google Trends
        breakout_trends = execute(
            """SELECT keyword, interest_score, rising_percent, date
               FROM ops.seo_trends
               WHERE date >= CURRENT_DATE - INTERVAL '3 days'
                 AND (is_breakout = TRUE OR rising_percent > 200)
               ORDER BY rising_percent DESC NULLS LAST
               LIMIT 10"""
        )

        # Rising related queries
        rising_queries = execute(
            """SELECT seed_keyword, query, value, date
               FROM ops.seo_rising_queries
               WHERE date >= CURRENT_DATE - INTERVAL '3 days'
               ORDER BY date DESC
               LIMIT 10"""
        )

        # High-velocity recent videos
        hot_videos = execute(
            """SELECT video_id, title, channel, views, view_velocity, keyword_match
               FROM ops.seo_rising_videos
               WHERE first_spotted >= CURRENT_DATE - INTERVAL '3 days'
                 AND view_velocity > 100
               ORDER BY view_velocity DESC
               LIMIT 10"""
        )

        items = []
        for s in new_suggestions:
            items.append({
                "type": "new_suggestion",
                "keyword": s["seed_keyword"],
                "suggestion": s["suggestion"],
                "first_seen": str(s["first_seen"]),
            })
        for t in breakout_trends:
            items.append({
                "type": "breakout_trend",
                "keyword": t["keyword"],
                "interest_score": t["interest_score"],
                "rising_percent": float(t["rising_percent"]) if t["rising_percent"] else None,
            })
        for q in rising_queries:
            items.append({
                "type": "rising_query",
                "seed_keyword": q["seed_keyword"],
                "query": q["query"],
                "value": q["value"],
            })
        for v in hot_videos:
            items.append({
                "type": "hot_video",
                "title": v["title"],
                "channel": v["channel"],
                "views": v["views"],
                "velocity": float(v["view_velocity"]) if v["view_velocity"] else None,
                "keyword": v["keyword_match"],
            })

        results["items"] = items
        results["count"] = len(items)

    except Exception as e:
        results["error"] = str(e)

    return results


def fetch_content_coverage():
    """Source 4 helper: What pillars/topics have been covered recently."""
    try:
        recent = execute(
            """SELECT title, pillar, source_type, content_type, created_at
               FROM ops.content_items
               WHERE platform = 'youtube'
                 AND created_at > NOW() - INTERVAL '30 days'
               ORDER BY created_at DESC
               LIMIT 20"""
        )

        pillar_counts = execute(
            """SELECT pillar, COUNT(*) as count
               FROM ops.content_items
               WHERE platform = 'youtube' AND pillar IS NOT NULL
                 AND created_at > NOW() - INTERVAL '30 days'
               GROUP BY pillar
               ORDER BY pillar"""
        )

        distribution = {i: 0 for i in range(1, 8)}
        for r in pillar_counts:
            if r["pillar"] in distribution:
                distribution[r["pillar"]] = r["count"]

        return {
            "recent_titles": [r["title"] for r in recent if r["title"]],
            "pillar_distribution": distribution,
            "gaps": [p for p, c in distribution.items() if c == 0],
        }
    except Exception:
        return {"recent_titles": [], "pillar_distribution": {}, "gaps": list(range(1, 8))}


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
    sources = {}

    # Fetch from all 5 sources
    sources["competitor_angles"] = fetch_competitor_angles()
    sources["ai_news"] = fetch_ai_news()
    sources["seo_trends"] = fetch_seo_trends()
    sources["content_coverage"] = fetch_content_coverage()

    # Sources 4 & 5 (ICP gaps + novel ideas) are context-file-driven.
    # We provide the data; Claude reads context/icp.md and context/competitive-strategy.md
    # to generate gap and novel ideas using this data as input.
    sources["context_files"] = {
        "icp_path": "context/icp.md",
        "competitive_strategy_path": "context/competitive-strategy.md",
        "business_path": "context/my-business.md",
        "note": "Claude reads these files to generate ICP gap and novel ideas. "
                "Cross-reference against content_coverage.recent_titles to avoid duplicates.",
    }

    # Summary
    total_signals = sum(
        s.get("count", 0) for s in sources.values() if isinstance(s.get("count"), int)
    )

    output = {
        "success": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_signals": total_signals,
        "sources": sources,
    }

    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
