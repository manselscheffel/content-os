---
name: youtube
description: YouTube content pipeline — ideate video ideas, prep video packages, process published videos, or create cadence posts.
argument-hint: "ideate | prep <idea> | post-publish <video_url> | cadence <topic>"
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

Run the youtube-content skill. Parse the user's argument to determine which command to execute:

- `ideate` or no argument → Generate 5 ranked video ideas from intelligence sources
- `prep <idea>` → Create a full video package (PSP outline, titles, description)
- `post-publish <video_url>` → Process a published video (timestamps, description, LinkedIn repurpose queue)
- `cadence <topic>` → Create a YouTube community tab post

Read the full skill at `${CLAUDE_PLUGIN_ROOT}/skills/youtube-content/SKILL.md` and follow it step by step.

Before running, check if setup is complete by reading `.claude/content-os.local.md`. If it doesn't exist, tell the user to run `/content-setup` first.
