#!/usr/bin/env python3
"""
Tool: Personal Intel Brief
Purpose: Full dump of scored AI news, organized by what matters for content creation,
         community growth, and staying ahead in the Claude Code / AI builder space.

No truncation. No cute categories that drop items. Just signal, grouped by priority.

Usage:
    python3 .claude/skills/ai-news-monitor/scripts/format_intel_brief.py --hours 24
    python3 .claude/skills/ai-news-monitor/scripts/format_intel_brief.py --hours 48 --min-score 6
    python3 .claude/skills/ai-news-monitor/scripts/format_intel_brief.py --hours 24 --output clipboard

Output:
    Full intel brief to stdout, clipboard, or file
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Resolve plugin root for lib imports
import os
PLUGIN_ROOT = os.environ.get(
    "CLAUDE_PLUGIN_ROOT",
    str(Path(__file__).resolve().parent.parent.parent)
)
sys.path.insert(0, PLUGIN_ROOT)
from lib.db import execute

# --- Priority buckets (checked in order, first match wins) ---

CLAUDE_ECOSYSTEM = [
    'claude', 'anthropic', 'dario amodei', 'ultrathink',
    'openclaw', 'zeptoclaw', 'claw',
    'agent harness', 'claude code', 'claude skill', 'claude hook',
    'mcp server', 'model context protocol',
]

MODEL_RELEASES = [
    'gpt-5', 'gpt5', 'gpt-4', 'gpt4', 'gpt 5', 'gpt 4',
    'gemini', 'llama 4', 'llama4', 'qwen', 'mistral',
    'opus', 'sonnet', 'haiku',
    'open-weight', 'open weight', 'new model', 'model release',
    'phi-4', 'phi4', 'codex', 'yuan',
]

INDUSTRY_MOVES = [
    'openai', 'google ai', 'deepmind', 'microsoft', 'nvidia',
    'meta ai', 'xai', 'grok', 'sam altman', 'satya',
    'acquisition', 'acquires', 'hires', 'leaves', 'joins',
    'funding', 'valuation', 'revenue', 'ipo',
]


def get_items(hours: int = 24, min_score: float = 5) -> list:
    """Fetch scored items from database."""
    rows = execute('''
        SELECT
            id, source, title, url, summary,
            relevance_score, relevance_tier, content_angle,
            relevance_reasoning, created_at,
            drift_total, drift_verdict, drift_reasoning
        FROM ops.news_items
        WHERE created_at > NOW() - INTERVAL '%s hours'
          AND relevance_score IS NOT NULL
          AND relevance_score >= %s
        ORDER BY relevance_score DESC, created_at DESC
    ''', (hours, min_score))

    return [dict(row) for row in rows]


def classify(title: str) -> str:
    """Classify an item into a priority bucket."""
    t = title.lower()
    if any(kw in t for kw in CLAUDE_ECOSYSTEM):
        return 'claude'
    if any(kw in t for kw in MODEL_RELEASES):
        return 'models'
    if any(kw in t for kw in INDUSTRY_MOVES):
        return 'industry'
    return 'other'


def source_tag(source: str) -> str:
    return {'hackernews': 'HN', 'github': 'GH', 'reddit': 'RD',
            'perplexity': 'PX', 'twitter': 'X'}.get(source, source[:2].upper())


def format_item(item: dict) -> str:
    """Format a single item — full title, no truncation."""
    score = item.get('relevance_score', 0)
    src = source_tag(item.get('source', ''))
    title = item['title']
    url = item.get('url', '')
    angle = item.get('content_angle', '')
    reasoning = item.get('relevance_reasoning', '')

    lines = [f"  [{score:.0f}] [{src}] {title}"]
    lines.append(f"       {url}")
    if angle:
        lines.append(f"       > {angle}")
    if reasoning:
        lines.append(f"       Why: {reasoning}")
    # DRIFT verdict
    drift_verdict = item.get('drift_verdict')
    if drift_verdict:
        drift_total = item.get('drift_total', '?')
        drift_label = {"act_now": "ACT NOW", "watch": "WATCH", "ignore": "IGNORE"}.get(drift_verdict, drift_verdict.upper())
        drift_line = f"       DRIFT: {drift_label} ({drift_total}/10)"
        drift_reason = item.get('drift_reasoning', '')
        if drift_reason:
            drift_line += f" — {drift_reason}"
        lines.append(drift_line)
    return '\n'.join(lines)


def format_brief(items: list, hours: int) -> str:
    """Build the full intel brief."""
    now = datetime.now()
    date_str = now.strftime('%B %d, %Y %H:%M')

    # Classify all items
    buckets = {'claude': [], 'models': [], 'industry': [], 'other': []}
    for item in items:
        bucket = classify(item['title'])
        buckets[bucket].append(item)

    # Collect ACT NOW items across all buckets
    act_now_items = [i for i in items if i.get('drift_verdict') == 'act_now']

    lines = []
    lines.append(f"{'='*60}")
    lines.append(f"  INTEL BRIEF — {date_str}")
    lines.append(f"  Last {hours}h | {len(items)} items scored 5+")
    lines.append(f"{'='*60}")
    lines.append("")

    # Section 0: ACT NOW (DRIFT test passed)
    if act_now_items:
        lines.append(f"{'─'*60}")
        lines.append(f"  ACT NOW — PASSED DRIFT TEST ({len(act_now_items)} items)")
        lines.append(f"{'─'*60}")
        lines.append("")
        for item in act_now_items:
            lines.append(format_item(item))
            lines.append("")

    # Section 1: Claude / Anthropic Ecosystem
    if buckets['claude']:
        lines.append(f"{'─'*60}")
        lines.append(f"  CLAUDE / ANTHROPIC ECOSYSTEM ({len(buckets['claude'])} items)")
        lines.append(f"{'─'*60}")
        lines.append("")
        for item in buckets['claude']:
            lines.append(format_item(item))
            lines.append("")

    # Section 2: Model Releases & Benchmarks
    if buckets['models']:
        lines.append(f"{'─'*60}")
        lines.append(f"  MODEL RELEASES & BENCHMARKS ({len(buckets['models'])} items)")
        lines.append(f"{'─'*60}")
        lines.append("")
        for item in buckets['models']:
            lines.append(format_item(item))
            lines.append("")

    # Section 3: Industry Moves
    if buckets['industry']:
        lines.append(f"{'─'*60}")
        lines.append(f"  INDUSTRY MOVES ({len(buckets['industry'])} items)")
        lines.append(f"{'─'*60}")
        lines.append("")
        for item in buckets['industry']:
            lines.append(format_item(item))
            lines.append("")

    # Section 4: Tools, Repos & Everything Else
    if buckets['other']:
        lines.append(f"{'─'*60}")
        lines.append(f"  TOOLS, REPOS & OTHER ({len(buckets['other'])} items)")
        lines.append(f"{'─'*60}")
        lines.append("")
        for item in buckets['other']:
            lines.append(format_item(item))
            lines.append("")

    lines.append(f"{'='*60}")

    return '\n'.join(lines)


def copy_to_clipboard(text: str) -> bool:
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except ImportError:
        return False


def main():
    parser = argparse.ArgumentParser(description='Personal AI intel brief')
    parser.add_argument('--hours', type=int, default=24, help='Hours to look back (default: 24)')
    parser.add_argument('--min-score', type=float, default=5, help='Minimum score to include (default: 5)')
    parser.add_argument('--output', choices=['stdout', 'clipboard', 'file'], default='stdout')
    parser.add_argument('--file', type=str, help='Output file path')

    args = parser.parse_args()

    if args.output == 'file' and not args.file:
        print("Error: --file required when --output is 'file'", file=sys.stderr)
        sys.exit(1)

    items = get_items(hours=args.hours, min_score=args.min_score)

    if not items:
        print(f"No items scored {args.min_score}+ in the last {args.hours} hours", file=sys.stderr)
        sys.exit(0)

    brief = format_brief(items, args.hours)

    if args.output == 'stdout':
        print(brief)
    elif args.output == 'clipboard':
        if copy_to_clipboard(brief):
            print(f"Copied to clipboard ({len(items)} items)", file=sys.stderr)
        else:
            print("pyperclip not installed, printing to stdout:", file=sys.stderr)
            print(brief)
    elif args.output == 'file':
        Path(args.file).write_text(brief)
        print(f"Saved to {args.file} ({len(items)} items)", file=sys.stderr)


if __name__ == '__main__':
    main()
