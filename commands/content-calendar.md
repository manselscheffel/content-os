---
name: content-calendar
description: View the weekly content calendar with draft/gap status across YouTube and LinkedIn.
argument-hint: "(no arguments)"
allowed-tools:
  - Read
  - Bash
  - Glob
  - Grep
---

Show the themed weekly content calendar. This runs the calendar view from the linkedin-content skill.

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/linkedin-content/scripts/calendar_view.py
```

Present as a table showing:
- Day of week + theme
- Category
- Status (draft / scheduled / published / GAP)
- Title/topic for any existing content

Highlight gaps and suggest topics based on recent activity and trending news.

Before running, check if setup is complete by reading `.claude/content-os.local.md`. If it doesn't exist, tell the user to run `/content-setup` first.
