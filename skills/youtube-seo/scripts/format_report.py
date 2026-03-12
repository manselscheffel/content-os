#!/usr/bin/env python3
"""
Tool: YouTube SEO Daily Report Generator
Purpose: Generate a markdown trend report from scored opportunities. Saves to
         data/youtube_seo/YYYY-MM-DD.md and outputs to stdout for piping.

Usage:
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/format_report.py
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/format_report.py --input scored.json
    python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/format_report.py --stdout-only

Dependencies: lib.db (dual-backend: SQLite default, Supabase Postgres optional)

Output: Markdown report file + JSON confirmation
"""

import sys
import os
import json
import argparse
from datetime import date
from pathlib import Path

# Resolve plugin root for portable paths
PLUGIN_ROOT = os.environ.get(
    "CLAUDE_PLUGIN_ROOT",
    str(Path(__file__).resolve().parent.parent.parent)
)
SKILL_DIR = Path(PLUGIN_ROOT) / "skills" / "youtube-seo"
PROJECT_ROOT = Path(PLUGIN_ROOT).parent  # project root
sys.path.insert(0, str(SKILL_DIR / "scripts"))

from trend_db import get_today_data, save_report_meta


def generate_report(scored_data=None, today_data=None):
    """Generate the markdown report."""
    today = date.today()
    date_str = today.isoformat()
    day_name = today.strftime("%A, %B %d, %Y")

    if today_data is None:
        today_data = get_today_data()

    if scored_data is None:
        from score_opportunities import score_opportunities
        scored_data = score_opportunities(today_data)

    opportunities = scored_data.get("opportunities", [])
    new_suggestions = today_data.get("new_suggestions", [])
    trends = today_data.get("trends", [])
    rising_queries = today_data.get("rising_queries", [])
    rising_videos = today_data.get("rising_videos", [])

    # Filter to meaningful data
    breakout_trends = [t for t in trends if t.get("is_breakout")]
    rising_trends = [t for t in trends if (t.get("rising_percent") or 0) > 50 and not t.get("is_breakout")]
    hot_videos = [v for v in rising_videos if v.get("view_velocity", 0) > 0]
    top_opportunities = opportunities[:5]

    lines = []
    lines.append(f"# YouTube SEO Trend Report: {date_str}")
    lines.append(f"\n> {day_name}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **New autocomplete suggestions**: {len(new_suggestions)}")
    lines.append(f"- **Breakout trends**: {len(breakout_trends)}")
    lines.append(f"- **Rising trends (>50%)**: {len(rising_trends)}")
    lines.append(f"- **Rising queries**: {len(rising_queries)}")
    lines.append(f"- **Hot videos spotted**: {len(hot_videos)}")
    lines.append(f"- **Total scored opportunities**: {len(opportunities)}")
    lines.append("")

    # Top Content Opportunities
    if top_opportunities:
        lines.append("## Top Content Opportunities")
        lines.append("")
        for i, opp in enumerate(top_opportunities, 1):
            sources = ", ".join(opp.get("signal_sources", []))
            lines.append(f"### #{i}: {opp['topic']} ({opp['score']:.1f} pts)")
            lines.append(f"**Signal sources**: {sources}")
            lines.append("")
            for sig in opp.get("signals", []):
                lines.append(f"- {sig}")
            lines.append("")
    else:
        lines.append("## Top Content Opportunities")
        lines.append("")
        lines.append("No significant opportunities detected today. This is normal — not every day has breakout trends.")
        lines.append("")

    # Rising Keywords
    if new_suggestions:
        lines.append("## Rising Keywords (New Autocomplete)")
        lines.append("")
        lines.append("| Seed Keyword | New Suggestion |")
        lines.append("|---|---|")
        for sug in new_suggestions[:20]:
            lines.append(f"| {sug.get('seed_keyword', '')} | {sug.get('suggestion', '')} |")
        if len(new_suggestions) > 20:
            lines.append(f"\n*...and {len(new_suggestions) - 20} more*")
        lines.append("")

    # Breakout Trends
    if breakout_trends:
        lines.append("## Breakout Trends")
        lines.append("")
        for t in breakout_trends:
            lines.append(f"- **{t['keyword']}**: Interest {t.get('interest_score', '?')}/100 — BREAKOUT")
        lines.append("")

    # Rising Trends
    if rising_trends:
        lines.append("## Rising Trends")
        lines.append("")
        lines.append("| Keyword | Interest | Change |")
        lines.append("|---|---|---|")
        for t in sorted(rising_trends, key=lambda x: x.get("rising_percent", 0) or 0, reverse=True):
            pct = t.get("rising_percent", 0) or 0
            lines.append(f"| {t['keyword']} | {t.get('interest_score', '?')}/100 | +{pct:.0f}% |")
        lines.append("")

    # Rising Queries
    if rising_queries:
        lines.append("## Rising Related Queries")
        lines.append("")
        lines.append("| From Seed | Query | Value |")
        lines.append("|---|---|---|")
        for rq in rising_queries[:15]:
            lines.append(f"| {rq.get('seed_keyword', '')} | {rq.get('query', '')} | {rq.get('value', '')} |")
        lines.append("")

    # Hot Videos
    if hot_videos:
        lines.append("## Hot Videos (High Velocity)")
        lines.append("")
        for v in hot_videos[:10]:
            lines.append(f"- **{v.get('title', 'Untitled')}**")
            lines.append(f"  - Channel: {v.get('channel', '?')}")
            lines.append(f"  - Views: {v.get('views', 0):,} | Velocity: {v.get('view_velocity', 0):,.0f} views/hr")
            lines.append(f"  - Keyword: {v.get('keyword_match', '?')}")
            lines.append("")

    lines.append("---")
    lines.append(f"*Generated by youtube-seo skill on {date_str}*")

    return "\n".join(lines)


def run(input_file=None, stdout_only=False):
    """Generate and save the report."""
    today_data = get_today_data()

    if input_file:
        with open(input_file) as f:
            scored_data = json.load(f)
    else:
        from score_opportunities import score_opportunities
        scored_data = score_opportunities(today_data)

    report = generate_report(scored_data, today_data)

    if not stdout_only:
        report_dir = PROJECT_ROOT / "data" / "youtube_seo"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"{date.today().isoformat()}.md"
        report_path.write_text(report)

        # Save report metadata to DB
        opps = scored_data.get("opportunities", [])
        top_opp = opps[0]["topic"] if opps else "none"
        new_sug = len(today_data.get("new_suggestions", []))
        breakouts = len([t for t in today_data.get("trends", []) if t.get("is_breakout")])
        hot_vids = len([v for v in today_data.get("rising_videos", []) if v.get("view_velocity", 0) > 0])

        save_report_meta(str(report_path), new_sug, breakouts, hot_vids, top_opp)

        result = {
            "success": True,
            "report_path": str(report_path),
            "report_length": len(report),
            "opportunities_count": len(opps),
            "top_opportunity": top_opp,
        }
        print(json.dumps(result, indent=2))
    else:
        print(report)

    return report


def main():
    parser = argparse.ArgumentParser(description="Generate YouTube SEO daily report")
    parser.add_argument("--input", metavar="FILE", help="Pre-scored opportunities JSON")
    parser.add_argument("--stdout-only", action="store_true", help="Print report to stdout, don't save")

    args = parser.parse_args()
    run(input_file=args.input, stdout_only=args.stdout_only)


if __name__ == "__main__":
    main()
