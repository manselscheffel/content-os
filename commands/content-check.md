---
name: content-check
description: Check content-os prerequisites — verify API keys, database, context files, and MCP connections are configured.
argument-hint: "(no arguments)"
allowed-tools:
  - Read
  - Bash
  - Glob
  - Grep
---

Run a health check on the content-os installation. Verify:

1. **Config file exists**: `.claude/content-os.local.md`
2. **Context files generated**: `context/my-voice.md`, `context/my-business.md`, `context/icp.md`, `context/competitive-strategy.md`
3. **Database initialized**: Check if `data/content.db` exists (SQLite) or Supabase connection works
4. **API keys**: Check which keys are configured in `.env`:
   - GEMINI_API_KEY (for thumbnails + statement images)
   - OPENAI_API_KEY (for news scoring)
   - NOTION_TOKEN (for Notion output)
   - SLACK_BOT_TOKEN (for alerts)
5. **MCP servers**: Check if youtube-analytics MCP is available
6. **Platform context**: If LinkedIn enabled, check `context/linkedin/` files exist. If YouTube, check `context/youtube/`.
7. **Deliverables directory**: Check `deliverables/` exists

Present results as a checklist:
```
Content OS Health Check
=======================
✓ Config file (.claude/content-os.local.md)
✓ Voice profile (context/my-voice.md)
✓ Business context (context/my-business.md)
✓ ICP (context/icp.md)
✓ Competitive strategy (context/competitive-strategy.md)
✓ Database (SQLite — data/content.db)
✓ Gemini API key
✗ Notion (not configured)
✗ OpenAI API key (news scoring disabled)
✓ YouTube analytics MCP
✓ LinkedIn context files
✓ YouTube context files
```

If any critical items are missing, suggest running `/content-setup`.
