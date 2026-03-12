---
name: content-setup
description: >
  Initial configuration wizard for the content-os plugin. Walks through business info,
  platform selection, voice calibration from writing samples, competitor analysis,
  API key collection, and social link setup. Generates all context files and config
  needed for the content pipeline to work. Use when user says "content setup",
  "set up content os", "configure content pipeline", "initialize", or when
  .claude/content-os.local.md doesn't exist. Also triggered by SessionStart hook
  if setup is incomplete.
user-invocable: true
argument-hint: "(no arguments — runs the full guided setup)"
---

# Content OS Setup Wizard

One guided flow that configures everything the content pipeline needs. Run this once when first installing the plugin, or re-run to update any section.

## Prerequisites Check

Before starting, verify the user has:
1. A working directory with a `.claude/` folder (or create one)
2. Python 3.9+ installed
3. At minimum, a clear idea of their business/niche and target audience

## The Setup Flow

Run all 7 steps in sequence as a single conversation. Use `AskUserQuestion` for each step to collect input, then generate files.

---

### Step 1: Business Basics

Ask the user:
- "What's your business or brand name?"
- "What's your niche? (e.g., 'AI automation for solopreneurs', 'fitness coaching for busy professionals')"
- "Describe your target audience in 2-3 sentences — who are they, what do they struggle with?"
- "What are you building/selling? (community, courses, consulting, SaaS, etc.)"

Generate: `context/my-business.md` from `${CLAUDE_PLUGIN_ROOT}/context-templates/my-business.md` template, filled with their answers.

---

### Step 2: Platform Selection

Ask:
- "Which platforms do you create content for? (YouTube / LinkedIn / Both)"
- "Which is your primary platform?"

Store in config. This determines which skills are active and which context files get generated.

---

### Step 3: Voice Calibration

This is the most important step. Ask:
- "Paste 3-5 examples of content you've written that you're proud of — posts, emails, video scripts, anything in YOUR voice. The more examples, the better the calibration."

After they paste samples, analyze them to extract:
- **Primary tone** (blunt, warm, technical, casual, etc.)
- **Sentence structure** (short and punchy? long and flowing? mixed?)
- **Vocabulary patterns** (power words they gravitate to, words they avoid)
- **Humor style** (sarcasm, self-deprecating, absurd analogies, none)
- **Rhetorical devices** (questions, lists, stories, analogies, data)
- **Profanity level** (none, strategic, casual)
- **Signature patterns** (specific recurring phrases, structures, or habits)

Generate: `context/my-voice.md` from the template, filled with extracted patterns.

If LinkedIn is selected: Also generate `context/linkedin/voice.md` with LinkedIn-specific adaptations of their voice. Copy `${CLAUDE_PLUGIN_ROOT}/context-templates/linkedin/frameworks.md` to `context/linkedin/frameworks.md`. Save their best examples to `context/linkedin/examples.md`.

If YouTube is selected: Also generate `context/youtube/voice.md` with YouTube-specific delivery patterns adapted to their style.

---

### Step 4: Competitive Landscape

Ask:
- "Who are your top 3-5 competitors? (YouTube channels, LinkedIn creators, or both — paste names or URLs)"
- "What does each competitor do well? What do they miss?"
- "What's YOUR unfair advantage — what can you say or show that they can't?"

Generate: `context/competitive-strategy.md` from template with:
- Competitor map table
- Unfair advantages
- Content strategy tiers (Growth / Depth / Stop Making)
- Positioning statement

Also generate ICP from the combination of business info + audience description + competitive landscape:
Generate: `context/icp.md` with audience archetypes, pain points, and discovery paths.

---

### Step 5: Content Pillars

Based on all the context gathered so far, propose 5-7 content pillars:
- Present them as a numbered table with name and description
- Ask user to confirm or adjust

These pillars map to the `pillar` integer field in the database and are used for coverage gap analysis.

Add the final pillars to `context/competitive-strategy.md`.

---

### Step 6: API Keys & Integrations

Present the prerequisites checklist based on what they need:

**Required for all users:**
- None (SQLite works out of the box)

**Required for YouTube content (if platform = youtube):**
- youtube-analytics MCP server — "Do you have the youtube-analytics MCP server connected? (This gives us access to transcripts and video data)"

**Required for thumbnails and statement images:**
- Gemini API key — "Do you have a Google AI / Gemini API key? Get one free at https://aistudio.google.com/apikey"

**Optional upgrades:**
- Supabase — "Want to use Supabase instead of SQLite? (Better for multi-device access and larger datasets). If yes, paste your SUPABASE_DB_URL"
- Notion — "Want content pushed to Notion? If yes, paste your NOTION_TOKEN and the database ID of your Projects database"
- OpenAI — "The AI news monitor can use OpenAI for relevance scoring. Paste your OPENAI_API_KEY if you have one"
- Slack — "Want Slack alerts for high-priority news? Paste your SLACK_BOT_TOKEN"
- Perplexity — "The news monitor uses Perplexity for extended research. Paste your PERPLEXITY_API_KEY if you have one"

For each key they provide, validate the format (check prefix patterns like `sk-`, `gsk_`, etc.) but don't test the API — just store it.

---

### Step 7: Social Links & Footer

Ask:
- "What social links should appear in your YouTube descriptions and LinkedIn posts?"
  - LinkedIn URL
  - Twitter/X URL
  - Community link (Skool, Discord, etc.)
  - Newsletter link
  - Any other links
- "Write a 2-3 sentence 'About' blurb for your YouTube description footer — who you are and what your channel is about"
- "What base hashtags should go on every post? (e.g., #AI #Automation #YourBrand)"

---

## Generate Config Files

After collecting all inputs, generate the following:

### 1. `.claude/content-os.local.md`

```markdown
---
business_name: "[from step 1]"
niche: "[from step 1]"
platforms:
  - youtube
  - linkedin
database:
  backend: sqlite
  supabase_db_url: "[if provided]"
api_keys:
  gemini: "[if provided]"
  openai: "[if provided]"
  notion: "[if provided]"
  slack: "[if provided]"
  perplexity: "[if provided]"
social_links:
  linkedin: "[URL]"
  twitter: "[URL]"
  community: "[URL]"
  newsletter: "[URL]"
output:
  destination: local
  notion_database_id: "[if provided]"
hashtags: "[from step 7]"
about_text: "[from step 7]"
---

# Content OS Configuration

Generated by content-setup wizard on [date].
Business: [name] | Niche: [niche] | Platforms: [list]
```

### 2. `.env` (append, don't overwrite)

Add any API keys provided to the `.env` file. If `.env` doesn't exist, create it. If keys already exist, don't overwrite.

```
GEMINI_API_KEY=...
OPENAI_API_KEY=...
NOTION_TOKEN=...
SLACK_BOT_TOKEN=...
PERPLEXITY_API_KEY=...
SUPABASE_DB_URL=...
```

### 3. Context files (from steps 3-5)

- `context/my-business.md`
- `context/my-voice.md`
- `context/icp.md`
- `context/competitive-strategy.md`
- `context/linkedin/voice.md` (if LinkedIn selected)
- `context/linkedin/frameworks.md` (if LinkedIn selected)
- `context/linkedin/examples.md` (if LinkedIn selected)
- `context/youtube/voice.md` (if YouTube selected)

### 4. Initialize database

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/scripts/init_db.py
```

This creates the SQLite database (or Supabase tables) and seeds the content calendar.

### 5. Create directory structure

```bash
mkdir -p context/linkedin context/youtube data deliverables/.tmp
```

---

## Present Summary

After generating everything, present:

```
Content OS Setup Complete!

Business: [name]
Niche: [niche]
Platforms: [YouTube, LinkedIn]
Database: SQLite (data/content.db)
Output: Local (deliverables/)

Context files generated:
  ✓ context/my-voice.md
  ✓ context/my-business.md
  ✓ context/icp.md
  ✓ context/competitive-strategy.md
  ✓ context/linkedin/ (voice, frameworks, examples)
  ✓ context/youtube/ (voice)

API keys configured:
  ✓ Gemini (thumbnails + statement images)
  ✗ Notion (not configured — using local output)
  ✓ youtube-analytics MCP (transcripts)

Next steps:
  1. Run /youtube ideate — to generate your first video ideas
  2. Run /linkedin create contrarian "your topic" — to draft a LinkedIn post
  3. Run /content-calendar — to see your weekly content schedule
```

---

## Re-running Setup

If the user runs setup again after initial configuration:
- Read existing config and pre-fill answers
- Ask "Want to update [section] or keep current?" for each step
- Only regenerate files for sections they changed
- Never delete existing content — merge updates
