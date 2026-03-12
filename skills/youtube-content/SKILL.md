---
name: youtube-content
description: >
  Complete YouTube content production pipeline — ideate videos from 5 intelligence sources
  (competitor analysis, AI news, YouTube SEO trends, ICP gaps, novel ideas), prep full video
  packages (PSP outline + titles + thumbnails + description), process published videos
  (timestamps + description + LinkedIn repurpose queue), and generate cadence posts
  (carousel slides for community tab/shorts). Use this skill when the user says
  "youtube content", "ideate videos", "video ideas", "prep a video", "post-publish",
  "process my video", "youtube cadence", "community tab post", "what should I make a video about",
  "generate video ideas", "prep video package", or wants to plan, prepare, or process YouTube content.
  Also use when the user asks to check what videos to make next, wants a content package for filming,
  or needs to process a recently uploaded video.
user-invocable: true
argument-hint: "ideate | prep <idea> | post-publish <video_url> | cadence <topic>"
---

# YouTube Content

Your YouTube content production pipeline. Turns intelligence data into video packages you can film, and processes published videos into descriptions + LinkedIn repurpose ideas.

Three intelligence skills run on a schedule and populate Supabase with fresh data:
- **competitor-analysis** → `ops.contrarian_angles`, `ops.processed_videos`, `ops.channels`
- **ai-news-monitor** → `ops.news_items`
- **youtube-seo** → `ops.seo_suggestions`, `ops.seo_trends`, `ops.seo_rising_queries`, `ops.seo_rising_videos`, `ops.seo_reports`

All intelligence data lives in Supabase (`ops` schema). This skill reads from all three plus context files to produce content packages.

## Prerequisites

- youtube-analytics MCP server connected (for transcripts, video data)
- Supabase tables created: `ops.content_items`, `ops.content_calendar` (see `migrations/002_content_tables.sql`)
- Intelligence skills running: competitor-analysis, ai-news-monitor, youtube-seo
- excalidraw-diagram skill configured (for prep command — on-screen visuals)
- thumbnail-generator skill configured (for prep command)
- If Notion is configured (check output destination in config): `lib/notion.py` + `NOTION_TOKEN` in `.env` (for pushing content to Content Tracker)

## Commands

Parse the user's input to determine which command to run:
- `ideate` or no argument → Step 1 (Ideate)
- `prep <idea>` → Step 2 (Prep) — works with ideas from ideate OR ad hoc topics the user brings directly
- `post-publish <url>` → Step 3 (Post-Publish)
- `cadence <topic>` → Step 4 (Cadence)

Ad hoc ideas are first-class. When the user comes with their own video idea (from a conversation, community question, personal experience, etc.), go straight to Step 2 with `source_type = 'manual'`. No scoring needed — the user already decided this is worth making.

---

## Step 1: Ideate — Generate Video Ideas

Generate 5 ranked video ideas from 5 intelligence sources. The goal is to surface the highest-impact video you could make right now based on what's happening in your space.

### 1a: Gather Intelligence

Run the ideation script to pull from all 5 sources:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-content/scripts/ideate.py
```

The script queries:

1. **Competitor angles** — Supabase `ops.contrarian_angles` and `ops.processed_videos` (via `lib/db.py`). Pulls recent angles with risk/reward scores where status = 'new'. These are topics where competitors posted but left gaps you can exploit.

2. **AI news** — Supabase `ops.news_items` (via `lib/db.py`). Pulls items with `relevance_score >= 7` from the last 7 days. High-scoring news means your audience cares about this topic RIGHT NOW.

3. **YouTube SEO trends** — Supabase `ops.seo_suggestions` (new autocomplete terms), `ops.seo_trends` (Google Trends breakout/rising), `ops.seo_rising_videos` (high view velocity), `ops.seo_rising_queries` (related rising queries). Rising search demand = people actively looking for content you could make.

4. **ICP/niche gaps** — Read `context/icp.md` to understand the audience archetypes and their pain points. Cross-reference against what's already been covered (check `ops.content_items` for recent topics). Look for underserved pain points — what your audience needs but nobody in the space is covering.

5. **Novel ideas** — Your original ideas that don't come from external data: your system builds (the content OS itself as content), original frameworks, unique takes, contrarian positions you hold. Read `context/my-business.md` for current priorities and `context/competitive-strategy.md` for positioning.

If any database is empty or unavailable, the script handles it gracefully and reports which sources had data.

### 1b: Score and Rank

Each idea is scored on:
- **Timeliness** (0-3): Is this trending RIGHT NOW? Will it be stale in a week?
- **Audience fit** (0-3): Does this match your ICP pain points? Which archetypes does it serve?
- **Competitive advantage** (0-3): Can you say something others can't? Do you have proof/experience?
- **Pillar coverage** (0-1): Does this fill a gap in your content pillar distribution?

Read `${CLAUDE_PLUGIN_ROOT}/skills/youtube-content/references/ideation_prompt.md` for the full scoring rubric.

Check pillar coverage gaps:
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-content/scripts/content_db.py --action pillar-gaps --platform youtube
```

### 1c: Present Ideas

Output 5 ideas ranked by score. For each idea:

```
## Idea #1: [Title concept] ⭐ Score: 8/10

**Source**: competitor_angle | news_item | seo_trend | icp_gap | novel
**Source detail**: [Where this came from — e.g., "Competitor X posted about Y, 150K views, but missed Z"]
**Content pillar**: Pillar N — [Name]
**Timeliness**: [Why now — what makes this urgent]
**Your angle**: [What makes YOUR take different]
**Title concepts**:
  - [Pattern-based title 1]
  - [Pattern-based title 2]
**Thumbnail concept**: [Brief visual description]
**Serves archetypes**: [Which ICP archetypes this hits]
```

Ask the user which idea they want to prep, or if they want to refine any of them.

---

## Step 2: Prep — Create Video Package

Takes an idea and produces everything needed before filming. The idea can come from:
- **Ideate output** — an idea ranked and scored in Step 1
- **Ad hoc** — the user's own idea from a conversation, community question, audience pain point, or personal experience. Tag as `source_type = 'manual'`. Skip scoring — the user has already decided this matters.

### 2a: Research the Topic

If the idea came from a competitor angle, read the full analysis for deep context. For ad hoc ideas, research the topic fresh:
- Read `context/competitive-strategy.md` for positioning
- Check if competitors have covered this (query `ops.processed_videos` via Supabase)
- Note what's missing from existing coverage

### 2b: Generate PSP Outline

Read `${CLAUDE_PLUGIN_ROOT}/skills/competitor-analysis/references/psp_outline_prompt.md` for the PSP framework.
Read `context/my-voice.md` for core voice and identity, and `context/youtube/voice.md` for YouTube-specific delivery patterns.

Generate a PSP outline following the framework:
- **Problem**: 2-3 hook options, core tension, why now, what others miss
- **Solution**: Core argument, 3-5 talking points, where you differ
- **Path**: Clear next steps, implementation route, what to do first/second/third, detours to avoid

This is TALKING POINTS only. Not a script. Bullet points you can riff on.

### 2c: Generate 3 Titles

Read `${CLAUDE_PLUGIN_ROOT}/skills/competitor-analysis/references/title_patterns.md` for the full pattern library (proven formulas with performance multipliers).

Generate 3 titles:
- **Option A**: Best pattern-based title (highest-fit pattern, with multiplier estimate)
- **Option B**: Second-best pattern (different category from A)
- **Option C**: Freeform curiosity (MUST pass the "would I say this in conversation?" test)

For each: state pattern code, estimated multiplier, word count, char count.

### 2d: Generate YouTube Description

Read `${CLAUDE_PLUGIN_ROOT}/skills/youtube-content/references/description_template.md` for the footer template.

Generate a draft description:
- 2-3 sentence summary of what the video covers
- [Timestamps will be added post-publish]
- Resources mentioned section (tools, links referenced in the outline)
- Footer content (links, about text, hashtags) is loaded from config — see `.claude/content-os.local.md`

### 2e: Save to Database

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-content/scripts/content_db.py \
  --action insert \
  --platform youtube \
  --content-type video \
  --status outline \
  --title "The chosen title" \
  --body "PSP outline as markdown" \
  --source-type competitor_angle \
  --pillar 3 \
  --metadata '{"titles": ["A", "B", "C"], "description_draft": "..."}'
```

### 2f: Present Package and STOP

Output the content package and then **stop and wait for user feedback**:
1. PSP outline
2. Title options table (pattern, multiplier, word/char count)
3. Draft description
4. Filming checklist (key demos to prepare, files to have open, etc.)

**Do NOT generate thumbnails or diagrams yet.** Present the package, then ask the user:
- "Which title do you want to go with?"
- "Want me to generate thumbnails? If so, what's your creative direction — style (electro_black / pixar_style / before_after), what icons/logos, what text on the thumbnail?"
- "Want me to generate on-screen diagrams for the video?"
- "Want me to push this to Notion?" (only if Notion is configured)

Thumbnails and diagrams are collaborative — the user provides creative direction, then you chain into the thumbnail-generator and excalidraw-diagram skills. Never auto-generate these in the background.

### 2g: Generate Thumbnails (after user input)

Only run this after the user gives creative direction. Use the thumbnail-generator skill with the user's specific instructions — style choice, icon placement, text, colors. The reference image is gospel; the user's direction describes what to change.

### 2h: Generate Excalidraw Diagrams (after user input)

Only run this if the user asks for on-screen visuals. Review the PSP outline and identify 2-4 key concepts that benefit from visual explanation. Use the excalidraw-diagram skill:
- **Style**: `sketch` (hand-drawn, approachable — matches YouTube teaching tone)
- **Format**: `slides` (one concept per frame, progressive disclosure during the video)
- **Depth**: Comprehensive/technical — include evidence artifacts (code snippets, real data examples, actual API names)

The resulting `.excalidraw` files go in `deliverables/video-assets/`.

### 2i: Push to Notion (after user confirms)

Only run this if Notion is configured (check output destination in config) and the user said yes to "Push to Notion?" in step 2f.

```python
from lib.notion import create_content_page, upload_image_to_page
page = create_content_page(
    title=chosen_title,
    status="Planning",
    body_markdown=full_psp_outline_md,  # Complete PSP outline — not placeholders
    metadata={"tags": ["AI"], "priority": "High"}
)
# After thumbnails are generated (step 2g):
upload_image_to_page(page["id"], thumbnail_path, caption="Thumbnail v1")
```

This creates a page in the Projects database with the **full PSP outline, title options, and description** as page content. The `body_markdown` must be the complete, formatted content — headings, bullets, numbered lists, code blocks — not a summary. If thumbnails were generated (step 2g), upload the best one as an image block on the page.

---

## Step 3: Post-Publish — Process a Published Video

After you've filmed and uploaded, this command processes the published video. Takes a YouTube video URL or video ID.

### 3a: Fetch Transcript

Use youtube-analytics MCP `get_video_transcript` with the video ID (extract from URL if needed).

If transcript unavailable: wait 1-2 hours after upload for YouTube to generate captions, then retry. If still unavailable, ask user to paste transcript manually.

### 3b: Extract Timestamps

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-content/scripts/extract_timestamps.py --transcript-file .tmp/transcript.txt
```

The script analyzes the transcript for topic transitions and generates a timestamp list. Review and adjust — the script gets you 80% there but you may want to tweak section names.

### 3c: Generate Final Description

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-content/scripts/generate_description.py \
  --title "Video Title" \
  --timestamps-file .tmp/timestamps.json \
  --template ${CLAUDE_PLUGIN_ROOT}/skills/youtube-content/references/description_template.md
```

Read `${CLAUDE_PLUGIN_ROOT}/skills/youtube-content/references/description_template.md` for the footer format.

Output: Complete YouTube description with:
- Summary paragraph
- Timestamps
- Resources mentioned
- Footer content (links, about text, hashtags) is loaded from config — see `.claude/content-os.local.md`

### 3d: Queue LinkedIn Repurpose Ideas

Analyze the transcript and identify 3-5 standalone insights that work as LinkedIn posts. For each, determine the best category (contrarian, video_drop, psp, new_tool, motivation, story, list).

Save each as an idea in the content database:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-content/scripts/content_db.py \
  --action insert \
  --platform linkedin \
  --content-type post \
  --status idea \
  --category video_drop \
  --title "Insight title" \
  --body "Brief description of the angle" \
  --source-type repurpose \
  --metadata '{"source_video_url": "https://...", "source_video_title": "..."}'
```

One of the 3-5 MUST be a `video_drop` category (the announcement post). The others should be standalone insights that work without watching the video.

### 3e: Update Video Status

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-content/scripts/content_db.py \
  --action update-status \
  --id <content_item_id> \
  --status published \
  --metadata '{"video_url": "https://...", "timestamps": [...], "published_at": "..."}'
```

### 3f: Update Notion (if configured and page exists)

If Notion is configured (check output destination in config), check if a Notion page exists for this video (by title match). If found, update it:

```python
from lib.notion import find_content_page, update_content_page
page = find_content_page(video_title)
if page:
    update_content_page(page["id"], {"status": "Complete"})
```

If no page exists, ask: "Want me to create a Notion page for this video?"

### 3g: Present Results

Output:
1. Final YouTube description (ready to paste)
2. Timestamp list
3. Summary of LinkedIn repurpose ideas queued (with categories)
4. Notion status (updated / created / skipped / not configured)
5. Reminder: "Run `/linkedin-content repurpose <url>` to generate the actual LinkedIn posts"

---

## Step 4: Cadence — YouTube Community Posts

Standalone, on-demand command for creating YouTube community tab posts. Not part of the default ideate→prep→post-publish flow — call this separately when you want to maintain channel presence between main video uploads without filming.

Read `${CLAUDE_PLUGIN_ROOT}/skills/youtube-content/references/community_posts.md` for the full best practices reference (post types, specs, algorithm effects, tactical playbook).

### Why This Matters

YouTube evaluates channels across ALL formats (video, Shorts, Posts) for recommendation quality. An inactive Posts tab is a mild negative signal. 2-3 posts per week keeps the channel "alive" between uploads and warms up the audience for the next video.

### 4a: Determine Post Type

Community posts come in several formats. Pick based on the goal:

| Format | When to Use | Engagement |
|--------|-------------|------------|
| **Poll** | Pre-video teaser, opinion gauging, topic selection | Highest (5-7x other formats) |
| **Image carousel** | Key takeaways, data viz, infographics | Medium |
| **Image + text** | Breaking news reaction, behind-the-scenes | Medium |
| **Text discussion** | Contrarian hot take, question for audience | Low-medium |

Polls should be the default 50%+ of the time — they dramatically outperform everything else.

### 4b: Determine Topic

If given a topic string, use it directly.
If given a video URL, fetch the transcript and extract the most shareable insight.
If neither, suggest topics from recent videos or trending news.

### 4c: Generate the Post

**For polls:**
Write the question (hook must land in under 288 characters — that's the "Read more" cutoff), 2-4 poll options (65 chars each max), and optional context text.

**For image carousels:**
```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-content/scripts/create_cadence_post.py \
  --topic "The topic" \
  --slides 6
```
Create 4-8 slides. Each image should be 1080x1080px (square, 1:1 ratio — YouTube crops to square in preview). Dark background + bright accent colors matches tech aesthetic. Up to 10 images per post.

**For text/image posts:**
Write the post text. First 288 characters are the hook (visible before "Read more"). No markdown support — only line breaks for formatting. Keep it punchy, use line breaks as pacing.

### 4d: Community Post Specs

| Spec | Value |
|------|-------|
| Image size | 1080x1080px (square) or 1920x1080px (landscape) |
| Max images | 10 per post (carousel) |
| Text before "Read more" | 288 characters |
| Max text | ~7,700 characters |
| Poll options | Up to 4, 65 chars each |
| Posting frequency | 2-3x/week optimal, max 1-2/day |
| Formats | JPG, PNG (GIF up to 16MB) |

### 4e: Save to Database

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-content/scripts/content_db.py \
  --action insert \
  --platform youtube \
  --content-type cadence_post \
  --status draft \
  --title "Post title or poll question" \
  --body "Full post content" \
  --metadata '{"post_format": "poll|carousel|image|text", "slides": [...], "poll_options": [...], "source_video_url": "..."}'
```

### 4f: Present

Output the post formatted for review:
- For polls: the question + options, ready to paste into YouTube Studio
- For image carousels: slide content with visual hierarchy notes, reminder to render images
- For text posts: the full text with the 288-char hook highlighted

Carousel images can be rendered using the LinkedIn carousel pipeline (`render_carousel.py`) with 1080x1080px dimensions instead of 1080x1350px — the template and renderer work for both.

---

## Scripts Reference

All scripts are in `${CLAUDE_PLUGIN_ROOT}/skills/youtube-content/scripts/`:

| Script | Purpose | Input | Output |
|--------|---------|-------|--------|
| `ideate.py` | Query 5 sources, score, rank | (reads DBs directly) | JSON: ranked ideas |
| `content_db.py` | CRUD for ops.content_items | `--action`, params | JSON: rows |
| `extract_timestamps.py` | Transcript → timestamps | `--transcript-file` | JSON: timestamp list |
| `generate_description.py` | Build full YT description | `--title`, `--timestamps-file` | Markdown: description |
| `post_publish.py` | Orchestrate post-publish flow | `--video-url` | Runs steps 3a-3e |
| `create_cadence_post.py` | Generate carousel slides | `--topic`, `--slides` | JSON: slide content |

All database access uses `lib/db.py` (`execute()`, `execute_one()`) for Supabase Postgres. Everything lives in the `ops` schema.
If Notion is configured (check output destination in config): integration uses `lib/notion.py` (`create_content_page()`, `update_content_page()`, `upload_image_to_page()`, `find_content_page()`).

## Edge Cases

| Scenario | Handling |
|----------|---------|
| Intelligence DBs empty | Report which sources had no data. Still generate ideas from ICP gaps + novel sources. |
| Voice guide missing | Work without it. Note in output: "Voice guide not loaded — check context/my-voice.md and context/youtube/voice.md" |
| Transcript unavailable | Wait for YouTube processing, or accept manual paste |
| No content_items table yet | Prompt user to run migration: `migrations/002_content_tables.sql` |
| Competitor analysis hasn't run | Skip source 1, note it. Other 4 sources still work. |
| Video URL format varies | Accept youtube.com/watch?v=, youtu.be/, or bare video ID |

## Content Pillars

Reference `context/competitive-strategy.md` for the content tier system:
- **Tier 1 (Growth)**: Head-to-head comparisons, contrarian responses — drive views AND subscribers
- **Tier 2 (Depth)**: Deep dives, full builds, series content — build loyalty and community pipeline
- **Tier 3 (Stop Making)**: Business advice, legal content, opinion without builds

The ideate command checks pillar distribution to avoid over-indexing on one type.
