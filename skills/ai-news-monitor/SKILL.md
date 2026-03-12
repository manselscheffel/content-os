---
name: ai-news-monitor
description: Monitor AI news sources (Hacker News, GitHub Trending, Reddit, Perplexity), score for relevance, alert via Slack (optional), and generate community newsletters. Run with /ai-news-monitor or ask to "check AI news", "run the news monitor", "generate the newsletter", or "what's happening in AI today".
user-invocable: true
---

# AI News Monitor

## Objective

Monitor multiple AI news sources for content relevant to your channel and community, score items for relevance using LLM-as-Judge, optionally alert via Slack for high-priority items, and generate formatted newsletters.

## What Gets Delivered

- **Immediate Slack Alerts** (optional): High-priority items (score >= 8) pushed every 2 hours
- **Daily Digest**: Summary of all relevant items from past 24 hours at 7am
- **Weekly Roundup**: Top 10 content opportunities every Sunday
- **Community Newsletter**: Community-formatted daily newsletter (manual trigger)
- **Intel Brief**: Concise intelligence briefing format
- **Database**: All items tracked for deduplication and analysis

## Inputs Required

- OpenAI API key (`OPENAI_API_KEY`) or Anthropic API key (`ANTHROPIC_API_KEY`) — for LLM scoring
- Slack bot token (`SLACK_BOT_TOKEN`) — optional, for alerts
- Perplexity API key (`PERPLEXITY_API_KEY`) — optional, for extended sources
- Config: `references/news_monitor.yaml` (source settings, thresholds, watchlists)

## Execution Steps

### Step 1: Scrape Sources (parallel where possible)

**Hacker News:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ai-news-monitor/scripts/scrape_hackernews.py --max-stories 50 --min-score 30 --check-new
```
**Input**: `--max-stories`, `--min-score`, `--keywords`, `--check-new` (skip items already in DB)
**Output**: JSON array of stories with title, url, score, comments, author

**GitHub Trending:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ai-news-monitor/scripts/scrape_github_trending.py --since daily --min-stars 50 --check-new
```
**Input**: `--since` (daily/weekly), `--min-stars`, `--topics`, `--language`, `--watchlist-only`
**Output**: JSON array of repos with name, description, stars, language, url

**Reddit:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ai-news-monitor/scripts/scrape_reddit.py --subreddits ClaudeAI,LocalLLaMA,MachineLearning --sort hot --check-new
```
**Input**: `--subreddits` (customize to your niche), `--sort`, `--min-score`, `--max-age-hours`, `--limit-per-sub`
**Output**: JSON array of posts with title, url, score, comments, subreddit

**Perplexity (extended sources):**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ai-news-monitor/scripts/fetch_perplexity_news.py --source all --hours 24
```
**Input**: `--source` (twitter/producthunt/newsletters/all), `--hours`, `--accounts`
**Output**: JSON with aggregated news items from Twitter, Product Hunt, newsletters

### Step 2: Deduplicate Against Database

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ai-news-monitor/scripts/news_db.py --action is-duplicate --source hackernews --source-id 12345
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ai-news-monitor/scripts/news_db.py --action insert --source hackernews --source-id 12345 --title "Title" --url "https://..."
```
**Actions**: `is-duplicate`, `insert`, `update-score`, `get-unalerted`, `mark-alerted`, `list`, `stats`, `daily-digest`

### Step 3: Score Relevance (LLM-as-Judge)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ai-news-monitor/scripts/score_relevance.py --items-file items.json --model haiku
```
**Input**: `--items-file` (JSON), `--title`/`--source`/`--url` (single item), `--model` (gpt4/gpt4-mini/claude/haiku)
**Output**: Scored items with `relevance_score` (1-10), `relevance_tier`, `relevance_reasoning`, `content_angle`, `topics_matched`, `viral_indicators`
**Prompt**: `references/score_relevance.md`

### Step 4: Store Scores in Database

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ai-news-monitor/scripts/news_db.py --action update-score --id 5 --score 8.5 --tier high --reasoning "Relevant because..."
```

### Step 5: Format and Alert

**Slack alerts (only if SLACK_BOT_TOKEN is configured):**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ai-news-monitor/scripts/format_slack_alert.py --type immediate --items-file high_priority.json
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ai-news-monitor/scripts/format_slack_alert.py --type daily --items-file digest.json
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ai-news-monitor/scripts/format_slack_alert.py --type weekly --items-file weekly.json
```

**Community newsletter:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ai-news-monitor/scripts/format_community_newsletter.py --hours 24
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ai-news-monitor/scripts/format_community_newsletter.py --hours 24 --output clipboard
```

**Intel brief:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ai-news-monitor/scripts/format_intel_brief.py --hours 24
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ai-news-monitor/scripts/format_intel_brief.py --hours 24 --output clipboard
```

### Full Pipeline (Orchestrator)

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ai-news-monitor/scripts/batch_news_monitor.py --mode immediate
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ai-news-monitor/scripts/batch_news_monitor.py --mode daily_digest
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ai-news-monitor/scripts/batch_news_monitor.py --mode weekly_roundup
python3 ${CLAUDE_PLUGIN_ROOT}/skills/ai-news-monitor/scripts/batch_news_monitor.py --mode immediate --dry-run
```

## Scoring Criteria

**High Priority (8-10)** — Immediate alert:
- Major model releases (new Claude, GPT, Gemini, open-weight models)
- AI coding tool updates (IDE features, agent frameworks)
- Big industry moves (acquisitions, major hires, company pivots)
- Mind-blowing demos (video gen, voice, wild capabilities)
- New tools/frameworks users can try immediately
- Agentic AI breakthroughs (MCP servers, agent frameworks, multi-agent systems)

**Viral Indicators** (boost score by 1-2):
- Massive engagement, "Wait, that actually works?" factor
- Tool you can try in 5 minutes
- Drama between big players
- "I built X with Y in Z hours" format

**Medium (5-7)** — Daily digest:
- Model comparisons/benchmarks, AI coding tools, open source releases

**Filter Out (1-4)** — Ignore:
- Consumer AI apps, AI art, funding announcements, AI ethics debates (unless directly relevant)

## Edge Cases & Error Handling

### No New Items
- Log "No new items found", don't post to Slack, exit 0

### API Failures
- HN API down: Log warning, exit gracefully
- Scoring fails: Skip item, log error, continue with others
- Slack fails: Items stay in DB as "new", retry next run

### Rate Limits
- HN: 500ms delay between item fetches (built into scraper)
- OpenAI/Anthropic: Standard API limits apply
- Slack: Standard rate limits

## Environment Variables

```bash
OPENAI_API_KEY=sk-proj-...      # For scoring (or use ANTHROPIC_API_KEY)
ANTHROPIC_API_KEY=sk-ant-...    # For scoring (alternative)
SLACK_BOT_TOKEN=xoxb-...        # Optional — for Slack alerts
PERPLEXITY_API_KEY=pplx-...     # Optional — for extended sources
GITHUB_TOKEN=ghp_...            # Optional — for higher GitHub API rate limits
```

## Scheduling (Cron)

```bash
# Every 2 hours (immediate monitoring)
0 */2 * * * python3 ${CLAUDE_PLUGIN_ROOT}/skills/ai-news-monitor/scripts/batch_news_monitor.py --mode immediate

# Daily digest at 7am
0 7 * * 1-5 python3 ${CLAUDE_PLUGIN_ROOT}/skills/ai-news-monitor/scripts/batch_news_monitor.py --mode daily_digest

# Weekly roundup Sunday 6pm
0 18 * * 0 python3 ${CLAUDE_PLUGIN_ROOT}/skills/ai-news-monitor/scripts/batch_news_monitor.py --mode weekly_roundup
```

## Daily Newsletter Workflow

1. Ensure news fetch ran: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/ai-news-monitor/scripts/news_db.py --action stats`
2. Generate newsletter: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/ai-news-monitor/scripts/format_community_newsletter.py --hours 24`
3. Copy output and paste into your community
4. Add personal commentary or highlights
