#!/usr/bin/env python3
"""
Tool: Community Newsletter Formatter
Purpose: Generate Skool-ready newsletter from AI news database

Usage:
    python tools/news_monitor/format_community_newsletter.py --hours 24
    python tools/news_monitor/format_community_newsletter.py --hours 48 --output clipboard
    python tools/news_monitor/format_community_newsletter.py --hours 24 --output file --file newsletter.txt

Dependencies:
    - psycopg2
    - lib.db (shared Supabase connection)
    - pyperclip (optional, for clipboard output)

Output:
    Formatted newsletter text ready to paste into Skool
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


def get_items(hours: int = 24, min_score: float = None) -> list:
    """Fetch news items from database."""
    query = '''
        SELECT
            id, source, title, url, summary,
            relevance_score, relevance_tier, content_angle,
            topics_matched, created_at,
            drift_total, drift_verdict, drift_reasoning
        FROM ops.news_items
        WHERE created_at > NOW() - INTERVAL '%s hours'
    '''
    params = [hours]

    # Always exclude unscored items — they haven't been vetted
    query += ' AND relevance_score IS NOT NULL'

    if min_score is not None:
        query += ' AND relevance_score >= %s'
        params.append(min_score)

    query += ' ORDER BY relevance_score DESC, created_at DESC'

    rows = execute(query, params)
    return [dict(row) for row in rows]


def _deduplicate(items: list) -> list:
    """Remove duplicate stories covering the same topic."""
    import re
    from urllib.parse import urlparse

    seen_urls = set()
    seen_entities = []  # list of entity sets per kept item
    unique = []

    # Extract key entities from title for deduplication
    def extract_entities(title: str) -> set:
        title_lower = title.lower()
        entities = set()
        # Match model+version (require at least one digit: "qwen3.5", "gpt-5.2", not bare "gpt")
        for m in re.finditer(r'(qwen|gemini|gpt|claude|llama|mistral|opus|codex|seedance|kling|sora|minimax|glm|step)[\s\-]?\d[\d.]*', title_lower):
            entities.add(re.sub(r'[\s\-]+', '', m.group()).strip('.'))
        # Match specific product names (openclaw, unsloth, etc.)
        for product in ['openclaw', 'unsloth', 'fastgpt']:
            if product in title_lower:
                entities.add(product)
        # Match repo-style names (owner/repo)
        for m in re.finditer(r'\b(\w+/\w+)\b', title):
            entities.add(m.group().lower())
        return entities

    for item in items:
        # URL dedup: strip query params
        url = item.get('url', '')
        parsed = urlparse(url)
        url_key = f"{parsed.netloc}{parsed.path}".rstrip('/')

        if url_key in seen_urls:
            continue

        # Entity overlap dedup: if >50% of entities match a kept item, skip
        title = item.get('title', '')
        ents = extract_entities(title)
        is_dupe = False
        if ents:
            for prev_ents in seen_entities:
                overlap = ents & prev_ents
                if overlap and len(overlap) >= max(1, min(len(ents), len(prev_ents)) * 0.5):
                    is_dupe = True
                    break

        if is_dupe:
            continue

        seen_urls.add(url_key)
        if ents:
            seen_entities.append(ents)
        unique.append(item)

    return unique


def categorize_items(items: list) -> dict:
    """Categorize items into newsletter sections for builders & vibe coders."""

    # Deduplicate first — many sources cover the same story
    items = _deduplicate(items)

    big_news = []
    tools = []
    cool_stuff = []
    quick_hits = []

    # Big players — news about these goes in BIG NEWS
    big_players = [
        'openai', 'anthropic', 'claude', 'chatgpt', 'gpt-4', 'gpt-5', 'gpt4', 'gpt5',
        'google', 'gemini', 'deepmind', 'meta ai', 'llama 3', 'llama 4', 'mistral',
        'microsoft', 'copilot', 'midjourney', 'runway', 'eleven labs', 'elevenlabs',
        'stability', 'cohere', 'hugging face', 'huggingface', 'nvidia',
        'sam altman', 'dario amodei', 'sundar', 'satya nadella',
        'qwen', 'minimax', 'xai', 'grok'
    ]

    # Major media coverage = big news regardless
    big_media = [
        'new yorker', 'nytimes', 'new york times', 'wsj', 'wall street journal',
        'bloomberg', 'reuters', 'techcrunch', 'the verge', 'wired',
        'breaking:', 'exclusive:', 'just in:'
    ]

    # Tools/repos builders can actually use
    tool_keywords = [
        'no-code', 'nocode', 'low-code', 'lowcode',
        'workflow', 'template', 'cursor', 'bolt', 'v0', 'replit',
        'zapier', 'make.com', 'n8n', 'flowise', 'langflow',
        'chatbot', 'mcp', 'claude code',
        'extension', 'chrome', 'open source', 'open-source',
        'framework', 'library', 'sdk', 'cli', 'plugin'
    ]

    # Cool/wild demos (show "look what's possible")
    fun_keywords = [
        ' play ', 'plays ', 'playing ', 'played ',
        ' game', 'gaming', 'simcity', 'minecraft', 'doom', 'chess', 'pokemon',
        'music', ' art ', 'creative', 'weird', 'crazy', 'wild', 'insane',
        'meme', 'funny', 'hilarious', 'wtf',
        'robot', 'humanoid', 'dancing', 'drawing',
        'deepfake', 'anime', 'cartoon',
        'seedance', 'kling', 'sora ', 'veo ',
        'video generation', 'voice clone', 'text to video', 'image generation',
        'pen plotter', 'masterpiece'
    ]

    # Skip these (too academic for builders)
    skip_keywords = [
        'arxiv', 'paper:', '[r]', '[d]', 'phd', 'research scientist',
        'mlops', 'kubernetes', 'terraform',
        'rlhf', 'perplexity score'
    ]

    # User discussions — not actual news
    user_discussion_patterns = [
        'i gave ', 'i found ', 'i made ', 'i built ', 'i created ',
        'i asked ', 'i tried ', 'i used ', 'i got ', 'i want ', 'i ran ',
        'my experience', 'my workflow', 'my setup',
        'does anyone', 'has anyone', 'can anyone',
        'help me', 'how do i', 'why does', 'why is',
        'rant:', 'unpopular opinion', 'hot take',
        'explained to me', 'told me', 'helped me',
        'anyone else', 'am i the only',
        'what\'s your', 'how do you', 'how i ',
        'claude completely changed', 'changed my life'
    ]

    # Claude ecosystem keywords — these always get priority
    claude_keywords = [
        'claude', 'anthropic', 'dario amodei',
        'openclaw', 'zeptoclaw', 'claw',
        'agent harness', 'ultrathink',
        'mcp server', 'model context protocol',
    ]

    for item in items:
        score = item.get('relevance_score')
        source = item.get('source', '')
        title = item.get('title', '').lower()

        # Skip academic stuff
        if any(kw in title for kw in skip_keywords):
            continue

        # Check categories
        has_big_player = any(bp in title for bp in big_players)
        has_big_media = any(bm in title for bm in big_media)
        is_claude_ecosystem = any(kw in title for kw in claude_keywords)
        is_user_discussion = any(pat in title for pat in user_discussion_patterns)
        is_tool = any(kw in title for kw in tool_keywords)
        is_fun = any(kw in title for kw in fun_keywords)

        # Big news: high score + about a big player/media, NOT user discussions
        # Exception: Claude ecosystem content is ALWAYS big news if score >= 7
        is_big_news = (has_big_player or has_big_media) and not is_user_discussion

        # Categorize (priority: claude ecosystem, github->tools, big news, cool stuff, tools, quick hits)
        if is_claude_ecosystem and score and score >= 7:
            big_news.append(item)
        elif source == 'github':
            tools.append(item)
        elif is_user_discussion and not is_claude_ecosystem:
            quick_hits.append(item)
        elif score and score >= 8 and is_big_news:
            big_news.append(item)
        elif is_big_news and score and score >= 7:
            big_news.append(item)
        elif is_fun:
            cool_stuff.append(item)
        elif is_tool:
            tools.append(item)
        elif score and score >= 7:
            quick_hits.insert(0, item)
        else:
            quick_hits.append(item)

    # Mix sources in cool_stuff for variety
    cool_mixed = []
    cool_by_source = {}
    for item in cool_stuff:
        src = item.get('source', 'unknown')
        if src not in cool_by_source:
            cool_by_source[src] = []
        cool_by_source[src].append(item)

    while len(cool_mixed) < 5:
        added = False
        for src in ['hackernews', 'reddit', 'github']:
            if src in cool_by_source and cool_by_source[src]:
                cool_mixed.append(cool_by_source[src].pop(0))
                added = True
                if len(cool_mixed) >= 5:
                    break
        if not added:
            break

    return {
        'big_news': big_news[:5],
        'tools': tools[:5],
        'cool_shit': cool_mixed,
        'quick_hits': quick_hits[:6]
    }


def get_mixed_highlights(items: list, limit: int = 5) -> list:
    """Get highlights with source diversity (prioritize HN, then mix others)."""
    # Group by source
    by_source = {}
    for item in items:
        src = item.get('source', 'unknown')
        if src not in by_source:
            by_source[src] = []
        by_source[src].append(item)

    # Priority order: HN first (higher quality), then GitHub, then Reddit
    priority = ['hackernews', 'github', 'reddit', 'perplexity', 'twitter', 'newsletter']

    highlights = []
    # First pass: take top item from each source in priority order
    for src in priority:
        if src in by_source and by_source[src]:
            highlights.append(by_source[src].pop(0))
            if len(highlights) >= limit:
                break

    # Second pass: fill remaining slots round-robin
    while len(highlights) < limit:
        added = False
        for src in priority:
            if src in by_source and by_source[src]:
                highlights.append(by_source[src].pop(0))
                added = True
                if len(highlights) >= limit:
                    break
        if not added:
            break

    return highlights


def to_unicode_bold(text: str) -> str:
    """Convert ASCII text to Unicode Mathematical Bold for platforms that don't support markdown."""
    bold_map = {}
    # Uppercase A-Z
    for i, c in enumerate('ABCDEFGHIJKLMNOPQRSTUVWXYZ'):
        bold_map[c] = chr(0x1D5D4 + i)
    # Lowercase a-z
    for i, c in enumerate('abcdefghijklmnopqrstuvwxyz'):
        bold_map[c] = chr(0x1D5EE + i)
    # Digits 0-9
    for i, c in enumerate('0123456789'):
        bold_map[c] = chr(0x1D7EC + i)
    return ''.join(bold_map.get(c, c) for c in text)


def format_source_badge(source: str) -> str:
    """Format source as badge."""
    badges = {
        'hackernews': 'HN',
        'github': 'GitHub',
        'reddit': 'Reddit',
        'perplexity': 'Web',
        'twitter': 'X',
        'newsletter': 'Newsletter'
    }
    return badges.get(source, source.title())


def shorten_title(title: str, max_len: int = 50) -> str:
    """Shorten title for preview bullets."""
    # Remove common prefixes
    prefixes = ['Show HN: ', 'Launch HN: ', '[D] ', '[R] ', '[P] ']
    for prefix in prefixes:
        if title.startswith(prefix):
            title = title[len(prefix):]
            break

    if len(title) <= max_len:
        return title
    return title[:max_len-3].rsplit(' ', 1)[0] + '...'


def generate_preview(categorized: dict) -> list:
    """Generate preview bullets for top of newsletter."""
    preview = []

    # Take top items from each category
    if categorized['big_news']:
        preview.append(shorten_title(categorized['big_news'][0]['title']))
    if categorized['tools'] and len(preview) < 5:
        preview.append(shorten_title(categorized['tools'][0]['title']))
    if categorized['cool_shit'] and len(preview) < 5:
        preview.append(shorten_title(categorized['cool_shit'][0]['title']))
    if categorized['quick_hits'] and len(preview) < 5:
        for item in categorized['quick_hits'][:2]:
            if len(preview) < 5:
                preview.append(shorten_title(item['title']))

    return preview


def format_newsletter(items: list, date: str = None) -> str:
    """Format items into Skool-ready newsletter.

    Skool community posts are plain text only — no markdown, no HTML,
    no native bullets or bold. Best practices:
    - Unicode bold for headers (renders everywhere)
    - Dashes for list items (standard Skool convention)
    - Flat structure (no indentation — Skool ignores it)
    - Generous blank lines between items
    - Bare URLs on own line (auto-link in Skool)
    - Emoji sparingly for section markers
    """
    if not date:
        date = datetime.now().strftime('%B %d, %Y')

    categorized = categorize_items(items)

    # Collect DRIFT ACT NOW items (across all items, before categorization)
    act_now_items = [i for i in items if i.get('drift_verdict') == 'act_now'][:3]

    lines = []

    # Header
    lines.append(f"{to_unicode_bold('AI DAILY DIGEST')} - {date}")
    lines.append("")

    # SHOULD YOU CARE? section (DRIFT ACT NOW items)
    if act_now_items:
        lines.append(f"\U0001f3af {to_unicode_bold('SHOULD YOU CARE?')}")
        lines.append("These passed the DRIFT test — they actually matter for builders right now.")
        lines.append("")
        for i, item in enumerate(act_now_items, 1):
            title = item['title']
            if len(title) > 80:
                title = title[:77] + '...'
            lines.append(f"{i}. {to_unicode_bold(title)}")
            if item.get('drift_reasoning'):
                lines.append(item['drift_reasoning'])
            lines.append(item.get('url', ''))
            lines.append("")

    # Big News
    if categorized['big_news']:
        lines.append(f"\U0001f534 {to_unicode_bold('BIG NEWS')}")
        lines.append("")
        for i, item in enumerate(categorized['big_news'], 1):
            title = item['title']
            if len(title) > 80:
                title = title[:77] + '...'
            lines.append(f"{i}. {to_unicode_bold(title)}")
            if item.get('content_angle'):
                lines.append(item['content_angle'])
            lines.append(item['url'])
            lines.append("")

    # Tools You Can Use
    if categorized['tools']:
        lines.append(f"\U0001f6e0 {to_unicode_bold('TOOLS YOU CAN USE')}")
        lines.append("")
        for item in categorized['tools']:
            title = item['title']
            if len(title) > 80:
                title = title[:77] + '...'
            lines.append(f"- {to_unicode_bold(title)}")
            lines.append(item['url'])
            lines.append("")

    # Cool Stuff
    if categorized['cool_shit']:
        lines.append(f"\u26a1 {to_unicode_bold('COOL STUFF')}")
        lines.append("")
        for item in categorized['cool_shit']:
            title = item['title']
            if len(title) > 80:
                title = title[:77] + '...'
            lines.append(f"- {title}")
            lines.append(item['url'])
            lines.append("")

    # Quick Hits
    if categorized['quick_hits']:
        lines.append(f"\u26a1 {to_unicode_bold('QUICK HITS')}")
        lines.append("")
        for item in categorized['quick_hits']:
            title = item['title']
            if len(title) > 80:
                title = title[:77] + '...'
            lines.append(f"- {title}")
            lines.append(item['url'])
            lines.append("")

    # Footer
    lines.append("What caught your eye? Drop a comment \U0001f447")
    lines.append("")

    return '\n'.join(lines)


def copy_to_clipboard(text: str) -> bool:
    """Copy text to clipboard if pyperclip is available."""
    try:
        import pyperclip
        pyperclip.copy(text)
        return True
    except ImportError:
        return False


def main():
    parser = argparse.ArgumentParser(description='Generate community newsletter from AI news')
    parser.add_argument('--hours', type=int, default=24, help='Hours to look back (default: 24)')
    parser.add_argument('--min-score', type=float, help='Minimum relevance score to include')
    parser.add_argument('--output', choices=['stdout', 'clipboard', 'file'], default='stdout',
                        help='Output destination (default: stdout)')
    parser.add_argument('--file', type=str, help='Output file path (required if --output file)')
    parser.add_argument('--date', type=str, help='Date string for header (default: today)')

    args = parser.parse_args()

    # Validate
    if args.output == 'file' and not args.file:
        print("Error: --file required when --output is 'file'", file=sys.stderr)
        sys.exit(1)

    # Get items
    items = get_items(hours=args.hours, min_score=args.min_score)

    if not items:
        print(f"No items found in the last {args.hours} hours", file=sys.stderr)
        sys.exit(0)

    # Format newsletter
    newsletter = format_newsletter(items, date=args.date)

    # Output
    if args.output == 'stdout':
        print(newsletter)
    elif args.output == 'clipboard':
        if copy_to_clipboard(newsletter):
            print(f"Newsletter copied to clipboard! ({len(items)} items)", file=sys.stderr)
        else:
            print("pyperclip not installed. Install with: pip install pyperclip", file=sys.stderr)
            print("Outputting to stdout instead:\n", file=sys.stderr)
            print(newsletter)
    elif args.output == 'file':
        Path(args.file).write_text(newsletter)
        print(f"Newsletter saved to {args.file} ({len(items)} items)", file=sys.stderr)


if __name__ == '__main__':
    main()
