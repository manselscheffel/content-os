---
name: competitor-analysis
description: Daily competitor YouTube monitoring — find new videos, analyze transcripts, mine contrarian angles, research topics, and generate PSP video outlines with click-worthy titles. Run with /competitor-analysis or ask to "check competitors", "what are competitors posting", "run the competitor check", or "any new competitor videos".
user-invocable: true
---

# Competitor Analysis

Monitor YouTube competitors daily. When they post a new video: grab the transcript, find where they're wrong or weak, research the topic deeply, and generate a PSP video outline with titles that'll outperform theirs.

## Prerequisites

- youtube-analytics MCP server connected
- Database initialized: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/competitor-analysis/scripts/check_new_videos.py --init-db`
- Edit `references/competitors.yaml` with your own competitor channels

## Workflow

### Step 0: Load State and Context

1. Read `references/competitors.yaml` to get the competitor channel list and settings.
2. Read `context/competitive-strategy.md` for strategic positioning (if it exists).
3. Run `python3 ${CLAUDE_PLUGIN_ROOT}/skills/competitor-analysis/scripts/check_new_videos.py --status` to see last-checked timestamps and processed video counts.
4. Note today's date — ALL research must be grounded to today's date. State "as of [today's date]" in research sections.

### Step 1: Check Each Competitor for New Videos

For each competitor channel in `competitors.yaml`:

1. Use youtube-analytics MCP `get_recent_videos` with the channel handle to fetch videos from the last 3-7 days (use `default_lookback_days` from settings, or since `last_checked` if available).
2. For each video returned, run: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/competitor-analysis/scripts/check_new_videos.py --is-processed VIDEO_ID`
3. Skip any already-processed videos.
4. Skip Shorts (< 60 seconds) unless they have unusually high engagement.
5. After checking a channel, update its timestamp: `python3 ${CLAUDE_PLUGIN_ROOT}/skills/competitor-analysis/scripts/check_new_videos.py --set-last-checked "@handle"`

If NO new videos found across any channel: report "No new competitor content since last check" and stop.

If new videos found: list them for the user, then proceed to Step 2 for each.

### Step 2: Analyze Each New Video

Run the following pipeline for each new video. Process one video at a time.

#### Step 2a: Fetch Transcript

Use youtube-analytics MCP `get_video_transcript` with the video ID.

If transcript is unavailable: log warning, do title-only analysis using the video title and description. Note the limitation in the output.

#### Step 2b: Analyze the Video

Read `references/analysis_prompt.md` for the analysis framework.

Analyze the transcript to extract:
- Topic summary (what is this video fundamentally about?)
- Key claims made (explicit advice, tool recommendations, results claims)
- Methodology assessment (did they SHOW or just CLAIM? demo vs production?)
- Tools mentioned
- Content pillar mapping (which of the 7 pillars from `references/content_pillars.md`)
- What the competitor's audience will take away from this

#### Step 2c: Find Weaknesses and Contrarian Angles

Read `references/contrarian_prompt.md` for the analysis framework.

Cross-reference the video analysis against:
- The competitor's known weaknesses from `competitors.yaml`
- Your strategic positioning from `context/competitive-strategy.md` (if available)

Find:
- Where the competitor is factually wrong
- Where they oversimplified or skipped important nuance
- Where they showed a demo but implied production readiness
- Where they made unvalidated claims
- Contrarian angles with genuine merit (classify as debunker/whistleblower/contrarian/reformer)
- Risk/reward assessment for each angle

#### Step 2d: Deep Research

Research the video's topic using your own knowledge, grounded to today's date.

Cover:
- Current state of the topic (what's actually true as of today)
- Recent developments or changes
- Expert consensus vs. common misconceptions
- Practical realities that demos don't show
- What most people get wrong about this

If Reddit threads, forum discussions, or niche sources are needed: use Firecrawl MCP `firecrawl_search` or `firecrawl_scrape` to access them.

IMPORTANT: Always state "as of [today's date]" when presenting research findings. Never present outdated information as current.

#### Step 2e: Education Phase

Break the concept down at two levels so you truly understand it before creating content:

**ELI5**: Simple explanation anyone can understand. Use an analogy.

**Expert View**: Nuanced technical depth — edge cases, trade-offs, implementation realities, what the competitor left out.

#### Step 2f: Generate PSP Outline

Read `references/psp_outline_prompt.md` for the framework.
Read `references/voice_guide.md` for tone and vocabulary.

Generate:
- **Problem**: 2-3 hook options, core tension, why it matters now, what the competitor missed
- **Solution**: Core argument, 3-5 talking points, where your take differs from competitor
- **Proof**: Personal experience reference, specific results, counter-example, vivid analogy

This is TALKING POINTS ONLY. Not a script. Bullet points you can riff on.

#### Step 2g: Generate Titles

Read `references/title_patterns.md` for the full pattern library.

Generate 3 title options:
- **Option A**: Best pattern-based title (highest-fit pattern, with multiplier estimate)
- **Option B**: Second-best pattern (different category from A)
- **Option C**: Freeform curiosity (MUST pass the "would I say this in conversation?" test)

For each title: state the pattern code, estimated multiplier, word count, char count.

Consider the competitor's original title — your title should capture THEIR audience's attention (people searching for or watching similar content).

### Step 3: Save Output

Create directory: `data/competitor_analyses/YYYY-MM-DD/` (today's date).

Save one markdown file per analyzed video: `{channel_handle}_{video_id}.md`

Use this format:

```markdown
# Competitor Analysis: [Video Title]

> **Creator**: @handle | **Published**: YYYY-MM-DD | **Views**: N
> **Analyzed**: YYYY-MM-DD | **Content Pillar**: Pillar X - Name

---

## What They Said
[Summary of key claims, methodology, tools mentioned]

## Where They're Wrong / Weak
[Specific weaknesses, oversimplifications, missing depth — with transcript quotes]

## Contrarian Angles
[Each angle with archetype, reasoning, risk/reward, execution tips]

## Research: The Full Picture (as of [today's date])

### ELI5
[Simple explanation with analogy]

### Expert View
[Nuanced technical depth, edge cases, trade-offs]

### What Most People Get Wrong
[Common misconceptions this competitor reinforced or failed to address]

## Your Video: PSP Outline

### Hook Options
1. [Hook 1]
2. [Hook 2]
3. [Hook 3]

### Problem
- Core pain: ...
- What they think: ...
- What's actually true: ...
- Why now: ...

### Solution
- Core argument: ...
- Point 1: ...
- Point 2: ...
- Point 3: ...
- Competitor contrast: ...

### Proof
- Experience proof: ...
- Numbers: ...
- Counter-example: ...
- Analogy: ...

### Close
- Key takeaway: ...
- CTA: ...

## Title Options

| # | Title | Pattern | Est. Multiplier | Words | Chars |
|---|-------|---------|-----------------|-------|-------|
| A | ... | P2 | 1.2-1.9x | 8 | 54 |
| B | ... | C4 | 1.4-2.2x | 7 | 48 |
| C | ... | FREEFORM | Variable | 6 | 38 |

**Recommended**: [A/B/C] — [Why this one wins]

## Thumbnail Concept
[Brief concept that synergizes with recommended title — visual description, text overlay, layout]
```

### Step 4: Update State

For each processed video:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/competitor-analysis/scripts/check_new_videos.py \
  --mark-processed VIDEO_ID \
  --channel "@handle" \
  --title "Video Title" \
  --path "data/competitor_analyses/YYYY-MM-DD/handle_videoid.md" \
  --pillar "Pillar N"
```

For each strong contrarian angle found:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/competitor-analysis/scripts/check_new_videos.py \
  --add-angle \
  --video-id VIDEO_ID \
  --angle "The contrarian take text" \
  --risk medium \
  --reward high
```

### Step 5: Report Summary

Print a summary:
- How many channels checked
- How many new videos found (per channel)
- For each analyzed video: title, creator, top contrarian angle, recommended title
- Any errors or skipped videos (and why)

If multiple videos were analyzed, also create a summary file:
`data/competitor_analyses/YYYY-MM-DD/_summary.md`

## Edge Cases

| Scenario | Handling |
|---|---|
| Transcript unavailable | Title-only analysis. Note limitation in output. |
| MCP tool fails | Log error, continue with other channels. Don't update last_checked for failed channels. |
| No new videos | Report cleanly and stop. |
| Video is a Short (< 60s) | Skip unless unusually high engagement. |
| Already-processed video | Skip silently. |
| Very long transcript (> 30K words) | Analyze first 30K words with note about truncation. |
| Conflicting research findings | Flag explicitly. Let user decide which angle to take. |

## Scheduling

Run daily. Recommended: morning check so outlines are ready for content creation.

To check accumulated contrarian angles across all sessions:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/competitor-analysis/scripts/check_new_videos.py --angles --filter-status new
```
