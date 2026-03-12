# Content OS Plugin

AI-powered content operating system. YouTube + LinkedIn content pipeline with intelligence-driven ideation.

## How to Operate

1. Check if setup is complete: read `.claude/content-os.local.md`. If missing, run the content-setup skill.
2. Read the relevant skill SKILL.md before starting any task.
3. All scripts are in `${CLAUDE_PLUGIN_ROOT}/skills/<skill-name>/scripts/`.
4. All context files are in the user's project at `context/`.
5. Config and API keys are in `.claude/content-os.local.md` and `.env`.
6. Database is either SQLite (`data/content.db`) or Supabase — `lib/db.py` handles both transparently.
7. Output goes to `deliverables/` (local) or Notion (if configured).

## Key Rules

- Always read `context/my-voice.md` before writing any content
- Never fabricate stories or experiences — use absurd analogies instead
- LinkedIn posts: 400-850 chars. Past 900 means you're over-explaining.
- Don't auto-generate thumbnails or diagrams — wait for user creative direction
- Check pillar coverage gaps before suggesting video ideas
- One of any repurpose batch MUST be a video_drop category
