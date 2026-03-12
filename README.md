# Content OS

AI-powered content operating system for YouTube and LinkedIn. A Claude Code plugin that turns intelligence data into video packages, LinkedIn posts, and a structured content pipeline.

## What It Does

- **YouTube Pipeline**: Ideate videos from 5 intelligence sources → prep full video packages (PSP outline + titles + thumbnails + description) → process published videos (timestamps + LinkedIn repurpose queue) → cadence posts for community tab
- **LinkedIn Pipeline**: Create categorized posts (7 frameworks) → repurpose YouTube videos into 3-5 posts → carousel PDFs → branded statement images → weekly content calendar
- **Intelligence Layer**: Competitor monitoring, AI news scoring, YouTube SEO trend detection
- **Visual Generation**: Thumbnails and statement images via Gemini API, Excalidraw diagrams for on-screen visuals

## Quick Start

1. Install the plugin:
   ```bash
   claude plugin add /path/to/content-os
   ```

2. Run the setup wizard:
   ```
   /content-setup
   ```
   This walks you through business info, voice calibration, competitor analysis, API keys, and generates all config files.

3. Start creating:
   ```
   /youtube ideate          # Generate video ideas
   /youtube prep "topic"    # Create a video package
   /linkedin create contrarian "topic"  # Draft a LinkedIn post
   /content-calendar        # View your weekly schedule
   ```

## Prerequisites

**Required:**
- Claude Code (latest version)
- Python 3.9+

**Optional (based on features you use):**
- `youtube-analytics` MCP server — for video transcripts and analytics
- Gemini API key — for thumbnail and statement image generation
- Supabase account — upgrade from SQLite for multi-device access
- Notion integration — push content to a Notion database
- OpenAI API key — for news relevance scoring
- Slack bot token — for high-priority news alerts

## Commands

| Command | Purpose |
|---------|---------|
| `/content-setup` | Configure the plugin for your business |
| `/youtube` | YouTube content pipeline (ideate, prep, post-publish, cadence) |
| `/linkedin` | LinkedIn content pipeline (create, repurpose, calendar, carousel, statement) |
| `/content-calendar` | View weekly content calendar with gaps |
| `/content-check` | Health check — verify all prerequisites |

## Database

**SQLite (default)** — zero configuration, database at `data/content.db`. Works immediately after setup.

**Supabase (upgrade)** — set `SUPABASE_DB_URL` in `.env` and change `database.backend` to `supabase` in `.claude/content-os.local.md`. Better for multi-device access and larger datasets.

## Project Structure

After setup, your project will have:

```
your-project/
├── .claude/
│   └── content-os.local.md    # Your config (API keys, links, settings)
├── .env                        # API keys
├── context/
│   ├── my-voice.md            # Your calibrated voice profile
│   ├── my-business.md         # Business context
│   ├── icp.md                 # Ideal customer profile
│   ├── competitive-strategy.md # Positioning and tactics
│   ├── linkedin/              # LinkedIn-specific voice and frameworks
│   └── youtube/               # YouTube-specific voice guide
├── data/
│   └── content.db             # SQLite database (if using SQLite)
└── deliverables/              # Generated content (thumbnails, carousels, etc.)
```

## Skills

| Skill | Purpose |
|-------|---------|
| content-setup | Onboarding wizard |
| youtube-content | Full YouTube pipeline |
| linkedin-content | Full LinkedIn pipeline |
| competitor-analysis | Monitor competitor channels |
| ai-news-monitor | Track AI news across sources |
| youtube-seo | Detect rising YouTube trends |
| thumbnail-generator | Generate thumbnails via Gemini |
| excalidraw-diagram | Create on-screen visual diagrams |

## License

MIT
