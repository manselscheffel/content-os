---
name: youtube-seo
description: >
  Daily YouTube trend detection and keyword monitoring — identifies rising search
  topics, breakout trends, and high-velocity videos before they peak. Helps time
  content to catch waves early. Use this skill when the user asks to "check YouTube
  trends", "what's trending on YouTube", "find rising topics", "YouTube keyword
  research", "what should I make a video about", "run the SEO check", "YouTube SEO",
  or wants to identify content opportunities based on search demand. Also use when
  feeding trend data into the daily brief or content planning.
user-invocable: true
---

# YouTube SEO Trend Detection

Identify rising YouTube topics before they peak by monitoring three free data sources: YouTube autocomplete suggestions, Google Trends (YouTube filter), and video upload velocity. The goal is to spot what people are searching for *right now* so you can time content to ride the wave.

## Why This Matters

Most creators pick topics by gut feel. This skill replaces guesswork with signal — tracking what YouTube's own autocomplete is surfacing, what Google Trends flags as breakout, and which fresh uploads are getting disproportionate views. A new autocomplete suggestion that wasn't there yesterday means YouTube is seeing rising search volume for that term. That's your window.

## Prerequisites

- `pytrends` installed (`pip3 install pytrends`)
- `requests` installed (`pip3 install requests`)
- `PyYAML` installed (`pip3 install PyYAML`)
- youtube-analytics MCP connected (for rising video detection)
- Database initialized: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/trend_db.py --init-db`

## Seed Keywords

Edit `references/seed_keywords.yaml` to configure which topics to monitor. Start with your core niche terms and expand as you spot patterns.

## Workflow

### Step 1: Verify tables (first run only)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/trend_db.py --init-db
```

### Step 2: Fetch YouTube Autocomplete Suggestions

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/fetch_suggestions.py
```

Hits YouTube's free autocomplete API for each seed keyword (plus prefix variations like "how to [keyword]", "[keyword] tutorial"). Outputs JSON with all suggestions found. Save results:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/trend_db.py --save-suggestions suggestions.json
```

The database tracks when each suggestion was first seen. New suggestions that appeared today but weren't there yesterday are flagged — these represent rising search demand.

### Step 3: Fetch Google Trends Data

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/fetch_trends.py
```

Uses pytrends to pull YouTube-specific search interest for each seed keyword over the last 7 days. Flags terms marked as "BREAKOUT" or rising >100%. Also captures related rising queries.

Save results:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/trend_db.py --save-trends trends.json
```

Note: pytrends can be rate-limited by Google. The script includes exponential backoff, but if you get persistent 429s, wait 10-15 minutes and retry.

### Step 4: Find Rising Videos

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/fetch_rising_videos.py
```

Uses youtube-analytics MCP `search_videos` to find recent uploads (< 3 days old) for each seed keyword. Calculates view velocity (views per hour since upload). Videos with high velocity on a topic you cover = signal that the market wants content on that topic right now.

Save results:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/trend_db.py --save-videos videos.json
```

### Step 5: Score and Rank Opportunities

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/score_opportunities.py
```

Combines all three signals into an opportunity score:
- New autocomplete suggestion: +3 points
- Google Trends breakout: +5 points
- Google Trends rising >200%: +3 points
- High-velocity recent video: +2 points
- Multiple signals on same topic: 1.5x multiplier

Topics with the highest combined scores are your best content opportunities right now.

### Step 6: Generate Report

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/format_report.py
```

Generates a daily trend report saved to `data/youtube_seo/YYYY-MM-DD.md` with:
- Rising Keywords (new autocomplete suggestions)
- Breakout Trends (Google Trends flagged)
- Hot Videos (high velocity recent uploads)
- Top 5 Content Opportunities (scored and ranked with reasoning)

### Quick Run (All Steps)

For a complete run, execute steps 2-6 in sequence. The skill orchestrates this when invoked — run each script, pipe the JSON output into the database save commands, then score and report.

## Day-Over-Day Tracking

The real value comes from running this daily. The database tracks historical suggestions, so after a few days you can see:
- Which suggestions are brand new (rising demand)
- Which suggestions disappeared (fading interest)
- Trend trajectories over time

Check what's new since yesterday:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-seo/scripts/trend_db.py --diff-suggestions
```

## Edge Cases

| Scenario | Handling |
|---|---|
| pytrends rate limited (429) | Exponential backoff, max 3 retries. Log warning, continue with other data. |
| YouTube autocomplete returns empty | Log warning, skip that keyword. May indicate the term is too niche. |
| MCP unavailable | Skip rising videos step. Suggestions + Trends alone are still valuable. |
| No new suggestions today | Normal — not every day has new trends. Report will note "no new signals." |
| First run (no historical data) | All suggestions marked as new. Real diff value starts from day 2. |

## Scheduling

Run daily, ideally in the morning before content planning. Can be triggered manually or integrated into a daily brief cron.
