---
name: linkedin-content
description: >
  LinkedIn content creation pipeline — create categorized posts using writing frameworks
  (contrarian, video drop, PSP, new tool, motivation, story, list), repurpose YouTube videos
  into 3-5 LinkedIn posts, view the themed weekly content calendar with draft/gap status,
  and generate carousel slide decks. Use this skill when the user says "linkedin content",
  "create a linkedin post", "write a post about", "linkedin calendar", "what's my content
  calendar", "repurpose this video for linkedin", "linkedin carousel", "create carousel",
  "what linkedin posts should I write", "draft a post", or wants to create, plan, or manage
  LinkedIn content. Also use when the user asks about content gaps, wants to see what's
  scheduled, or needs to turn a YouTube video into LinkedIn posts.
user-invocable: true
argument-hint: "create <category> <topic> | repurpose <video_url> | calendar | carousel <topic> | statement <topic>"
---

# LinkedIn Content

Your LinkedIn content production pipeline. Creates categorized posts in your voice, repurposes YouTube videos into multiple LinkedIn formats, and tracks everything against a themed weekly calendar.

Shares the `ops.content_items` database with youtube-content — YouTube's post-publish command queues repurpose ideas here, and this skill turns them into actual posts.

## Three Visual Post Formats

Every LinkedIn post you create falls into one of three visual styles:

| Format | When to Use | Visual | Output |
|--------|------------|--------|--------|
| **Statement image** | Bold single-point posts (contrarian, motivation) | 1080x1080 dark gradient + bold text overlay | PNG image + post text |
| **Carousel** | Multi-point educational posts (psp, list, new_tool) | 1080x1350 multi-page slides | PDF document + post text |
| **Video link** | Announcing/referencing a YouTube video (video_drop) | No image — text post with YouTube URL | Post text with embedded link |

When creating a post (Step 1) or repurposing (Step 2), pick the visual format that fits:
- **Statement image** is the default for `contrarian`, `motivation`, `story` categories — single bold claim that stops the scroll
- **Carousel** is the default for `psp`, `list`, `new_tool` categories — multi-point content that rewards swiping
- **Video link** is the default for `video_drop` category — the post text does the work, the video thumbnail handles the visual

These are defaults, not rules. Override when it makes sense (e.g., a contrarian post with 5 supporting points might work better as a carousel).

## Prerequisites

- Supabase tables: `ops.content_items`, `ops.content_calendar` (see `migrations/002_content_tables.sql`)
- Context files populated: `context/my-voice.md`, `context/linkedin/voice.md`, `context/linkedin/frameworks.md`, `context/linkedin/examples.md`
- youtube-analytics MCP connected (for repurpose command — fetching transcripts)
- If output destination is 'notion' (check config): `lib/notion.py` + `NOTION_TOKEN` in `.env` (for pushing content to Content Tracker)

## Commands

Parse the user's input to determine which command to run:
- `create <category> <topic>` → Step 1 (Create Post)
- `repurpose <video_url>` → Step 2 (Repurpose Video)
- `calendar` or no argument → Step 3 (Calendar View)
- `carousel <topic>` → Step 4 (Create Carousel)
- `statement <topic>` → Step 5 (Create Statement Image)

---

## Step 1: Create — Draft a Categorized Post

Takes a category and topic, loads the correct writing framework, and drafts a post in your voice.

### 1a: Determine Category

Valid categories: `contrarian`, `video_drop`, `psp`, `new_tool`, `motivation`, `story`, `list`

If the user doesn't specify a category, infer it from the topic:
- Challenging conventional wisdom → contrarian
- Announcing/referencing a video → video_drop
- Teaching a framework or system → psp
- Reviewing or showcasing a tool → new_tool
- Personal lesson or vulnerability → motivation
- Build log or behind-the-scenes → story
- Numbered items or tips → list

### 1b: Load Context

Read these files for voice and framework:
1. `context/my-voice.md` — Core identity, tone, vocabulary, banned words
2. `context/linkedin/voice.md` — LinkedIn-specific formatting, Hook-Twist-Pitch structure
3. `context/linkedin/frameworks.md` — The specific framework for the chosen category
4. `context/linkedin/examples.md` — Gold standard reference posts

### 1c: Generate the Post

Run the creation script:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/linkedin-content/scripts/create_post.py \
  --category contrarian \
  --topic "Why most AI agents fail in production"
```

The script provides the framework template. Write the actual post by matching the examples in `context/linkedin/examples.md` — those are the quality bar, not the framework structure. The frameworks file describes the natural flow; the examples show what it actually looks like.

Key rules:
- Match the examples' tone: funny, charming, quick to the point
- Never fabricate stories or experiences — use absurd analogies instead
- 400-850 chars. Past 900 means you're over-explaining.
- Not every post needs a video link. Some just land a thought and leave.
- Social links, hashtags, and about text are loaded from `.claude/content-os.local.md`

### 1d: Generate Visual (if applicable)

Based on the category, determine the visual format (see "Three Visual Post Formats" table above):

**Statement image** (contrarian, motivation, story): Extract the single boldest claim from the post — split it into a primary line and accent line. Generate the image via Gemini:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/linkedin-content/scripts/render_statement.py \
  --primary "AI agents are not employees" \
  --accent "they're taxi meters that think"
```

The script uploads the style reference image from the plugin assets as a style guide to Gemini, which generates a new image matching the style with the new text. Same pattern as thumbnail-generator — no HTML templates needed.

**Carousel** (psp, list, new_tool): Follow Step 4 instead — generate slides from the post's key points.

**Video link** (video_drop): No image needed. The YouTube URL generates its own preview card. Post text does the heavy lifting.

### 1e: Save to Database

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-content/scripts/content_db.py \
  --action insert \
  --platform linkedin \
  --content-type post \
  --category contrarian \
  --status draft \
  --title "Post title/hook" \
  --body "Full post text" \
  --source-type manual \
  --metadata '{"char_count": 850, "framework_used": "contrarian", "visual_format": "statement", "image_path": "deliverables/statement-images/..."}'
```

Note: Uses the shared `content_db.py` from youtube-content (it handles both platforms).

For `visual_format`, use one of: `"statement"`, `"carousel"`, `"video_link"`.

### 1f: Present

Output:
1. The full post (formatted as it would appear on LinkedIn)
2. Character count and category
3. Visual format used + image/PDF path (if generated)
4. Which content calendar day this maps to
5. If output destination is 'notion' (check config): Ask "Want me to push this to Notion?"

### 1g: Push to Notion (after user confirms)

If output destination is 'notion' (check config) and the user says yes:

```python
from lib.notion import create_content_page, upload_image_to_page
page = create_content_page(
    title=post_hook_line,
    status="Planning",
    body_markdown=full_post_text,  # The complete LinkedIn post — not a summary
    metadata={"tags": ["AI"]}
)
# If a statement image or carousel PDF was generated:
upload_image_to_page(page["id"], image_path, caption="LinkedIn visual")
```

Creates a page in the Projects database with the **full post text** as page body, and attaches any generated visuals as image blocks.

---

## Step 2: Repurpose — YouTube Video to LinkedIn Posts

Takes a YouTube video URL and generates 3-5 categorized LinkedIn posts from the transcript.

### 2a: Get Transcript

Use youtube-analytics MCP `get_video_transcript` to fetch the transcript.

If a transcript file is provided or the video was recently processed by youtube-content post-publish, check `.tmp/` for cached transcript.

### 2b: Analyze for Angles

Run the repurpose script:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/linkedin-content/scripts/repurpose_video.py \
  --video-url "https://youtube.com/watch?v=abc123" \
  --title "Video Title"
```

The script checks for existing repurpose ideas queued by youtube-content's post-publish command (source_type = 'repurpose' in `ops.content_items`). If found, use those as starting points. If not, analyze the transcript fresh.

### 2c: Generate 3-5 Posts

For each angle identified:

1. Pick the best category (contrarian, video_drop, psp, new_tool, motivation, story, list)
2. Load the framework for that category from `context/linkedin/frameworks.md`
3. Draft the post following voice rules
4. Assign a visual format based on category (see "Three Visual Post Formats" table)

Requirements:
- One post MUST be `video_drop` category (video link format — text + YouTube URL)
- Remaining posts should be standalone — they work without watching the video
- Each post should be a different category (no duplicates)
- Each post should target a different insight from the video
- Generate statement images for contrarian/motivation/story posts
- Generate carousel PDFs for psp/list/new_tool posts (if the content warrants slides)

### 2d: Save All to Database

Save each as a draft in `ops.content_items`:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/youtube-content/scripts/content_db.py \
  --action insert \
  --platform linkedin \
  --content-type post \
  --category video_drop \
  --status draft \
  --title "Post hook" \
  --body "Full post" \
  --source-type repurpose \
  --metadata '{"source_video_url": "...", "source_video_title": "...", "visual_format": "video_link"}'
```

### 2e: Present

Output all posts formatted for review, with:
- Category label and framework used
- Visual format (statement / carousel / video_link)
- Character count
- Image/PDF path (if visual was generated)
- Suggested posting day (based on calendar theme)
- If output destination is 'notion' (check config): Ask "Want me to push these to Notion?"

If the user says yes, create a Notion page for each post using `lib/notion.py` with Format="Written" and the post text as body.

---

## Step 3: Calendar — Weekly Content View

Shows the themed weekly calendar with draft/gap status.

### 3a: Fetch Calendar and Content

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/linkedin-content/scripts/calendar_view.py
```

The script queries:
- `ops.content_calendar` for the 7-day theme template
- `ops.content_items` for recent LinkedIn drafts, scheduled, and published items

### 3b: Present

Output a table showing:

```
| Day       | Theme      | Category   | Status      | Title/Topic              |
|-----------|------------|------------|-------------|--------------------------|
| Monday    | Motivation | motivation | draft       | "Why I almost quit..."   |
| Tuesday   | Tools      | new_tool   | — GAP —     |                          |
| Wednesday | Deep Dive  | psp        | published   | "The ATOM framework..."  |
| Thursday  | Contrarian | contrarian | draft       | "AI agents are broken"   |
| Friday    | Video Drop | video_drop | scheduled   | "New video: Claude Code"  |
| Saturday  | Story      | story      | — GAP —     |                          |
| Sunday    | Week Ahead | list       | — GAP —     |                          |
```

Highlight gaps and suggest topics based on:
- Recent YouTube videos (repurpose candidates)
- Trending AI news from `ops.news_items`
- Calendar theme for that day

---

## Step 4: Carousel — Slide Deck Post

Generate a carousel PDF for LinkedIn. LinkedIn carousels are multi-page PDFs where each page becomes a swipeable slide.

### 4a: Get Slide Structure

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/linkedin-content/scripts/create_carousel.py \
  --topic "5 mistakes AI consultants make" \
  --slides 8
```

The script returns the slide structure template. Fill in real content for each slide:
- **Title slide**: Bold provocative headline + author name (from config)
- **Content slides**: One key point per slide — punchy headline (5-8 words), supporting text (1-2 lines)
- **Summary slide**: "Key Takeaways" + 3-5 bullet recap
- **CTA slide**: Engagement prompt + author info (from config)

### 4b: Write Slide Content

Create a JSON file with the filled-in slide content. Each slide needs:

```json
{
  "topic": "5 things AI code review actually catches",
  "slides": [
    {"type": "title", "primary_text": "5 Things AI Code Review Actually Catches"},
    {"type": "content", "primary_text": "Null Refs You Wrote at Midnight", "supporting_text": "AI catches every unguarded access...", "point_number": 1},
    {"type": "summary", "primary_text": "What It Won't Catch", "takeaways": ["Architecture decisions", "Business logic", "Design patterns"]},
    {"type": "cta", "primary_text": "Want the full breakdown?"}
  ]
}
```

Save to `.tmp/carousel_slides.json`.

### 4c: Render to PDF

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/linkedin-content/scripts/render_carousel.py \
  --input .tmp/carousel_slides.json \
  --preview-html
```

This renders the slides using the branded HTML template (`assets/carousel_template.html`) via Playwright's headless Chromium → PDF. Outputs:
- **PDF** (ready to upload to LinkedIn as a document post)
- **Preview PNG** of the first slide
- **HTML file** (if `--preview-html` flag used, for debugging)

Design specs (configured in the template):
- 1080x1350px portrait (4:5 ratio, optimal for mobile)
- Near-black background (#0a0a0a) with sky blue accents (#38bdf8)
- 52px bold headlines, 28px supporting text, Inter font
- Slide counter (e.g., "3/8") in bottom-right
- Sky blue accent bar at top of each slide
- 15% safe zone from all edges

Optional theme override in the JSON:
```json
{
  "theme": {
    "bg_color": "#0a0a0a",
    "accent_color": "#38bdf8",
    "text_color": "#f8fafc",
    "muted_color": "#94a3b8"
  }
}
```

### 4d: Save and Present

Save to database as content_type = 'carousel' (use `--save` flag on create_carousel.py).

Output the PDF path and preview image for review. The PDF is ready to upload directly to LinkedIn as a document post — each page becomes one swipeable carousel slide.

---

## Step 5: Statement — Single Statement Image

Generate a branded statement image for LinkedIn via Gemini. The script uploads the dark-statement-reference image as a style guide and Gemini generates a new image with your text in the same style. Same approach as thumbnail-generator — no HTML templates or Playwright needed.

### 5a: Write Statement Text

Extract or craft the statement. It needs two lines:
- **Primary line**: The setup or context (light gray text)
- **Accent line**: The punch or twist (brand-color text)

Good statements are bold, concise, and slightly provocative. They should make sense without the accompanying post text.

### 5b: Generate via Gemini

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/linkedin-content/scripts/render_statement.py \
  --primary "AI is not a coding tool" \
  --accent "its modern infrastructure"
```

Or pass a JSON file:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/linkedin-content/scripts/render_statement.py \
  --input .tmp/statement.json
```

The script:
1. Uploads the style reference image from plugin assets
2. Sends a prompt describing the desired text and style
3. Gemini returns a new image matching the dark gradient + bold text style
4. Saves PNG to `deliverables/statement-images/`

Requires `GEMINI_API_KEY` or `GOOGLE_API_KEY` in `.env` (or configured via `lib.config.get_key("gemini")`).

### 5c: Save and Present

Save to database as content_type = 'post' with `visual_format: "statement"` in metadata.

Output the PNG path for review. The image is ready to attach to a LinkedIn post directly.

---

## Scripts Reference

| Script | Location | Purpose |
|--------|----------|---------|
| `create_post.py` | `${CLAUDE_PLUGIN_ROOT}/skills/linkedin-content/scripts/` | Category framework template + post structure |
| `repurpose_video.py` | `${CLAUDE_PLUGIN_ROOT}/skills/linkedin-content/scripts/` | Transcript analysis + multi-post generation |
| `calendar_view.py` | `${CLAUDE_PLUGIN_ROOT}/skills/linkedin-content/scripts/` | Weekly calendar with gap analysis |
| `create_carousel.py` | `${CLAUDE_PLUGIN_ROOT}/skills/linkedin-content/scripts/` | Carousel slide structure + content generation |
| `render_carousel.py` | `${CLAUDE_PLUGIN_ROOT}/skills/linkedin-content/scripts/` | HTML template → Playwright → PDF rendering |
| `render_statement.py` | `${CLAUDE_PLUGIN_ROOT}/skills/linkedin-content/scripts/` | Statement image via Gemini API (reference image + prompt → PNG) |
| `content_db.py` | `${CLAUDE_PLUGIN_ROOT}/skills/youtube-content/scripts/` | Shared CRUD for ops.content_items (both platforms) |

All database access uses `lib/db.py` (`execute()`, `execute_one()`). Everything in the `ops` schema.

## Edge Cases

| Scenario | Handling |
|----------|---------|
| No transcript available | Ask user to paste manually or wait for YouTube processing |
| No repurpose ideas queued | Analyze transcript fresh — don't depend on youtube-content having run first |
| Calendar empty | Run migration to seed ops.content_calendar |
| Category unclear | Infer from topic, or ask user |
| Post too long | LinkedIn optimal is 400-1200 chars. Warn if over 1500. |
| Existing drafts for same day | Show both, let user pick which to use |
