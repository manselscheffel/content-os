---
name: linkedin
description: LinkedIn content pipeline — create categorized posts, repurpose YouTube videos, view content calendar, create carousels, or generate statement images.
argument-hint: "create <category> <topic> | repurpose <video_url> | calendar | carousel <topic> | statement <topic>"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
  - Agent
  - AskUserQuestion
---

Run the linkedin-content skill. Parse the user's argument to determine which command:

- `create <category> <topic>` → Draft a categorized LinkedIn post
- `repurpose <video_url>` → Turn a YouTube video into 3-5 LinkedIn posts
- `calendar` → View the themed weekly content calendar with gaps
- `carousel <topic>` → Generate a carousel PDF
- `statement <topic>` → Generate a branded statement image

Valid categories: contrarian, video_drop, psp, new_tool, motivation, story, list

Read the full skill at `${CLAUDE_PLUGIN_ROOT}/skills/linkedin-content/SKILL.md` and follow it step by step.

Before running, check if setup is complete by reading `.claude/content-os.local.md`. If it doesn't exist, tell the user to run `/content-setup` first.
