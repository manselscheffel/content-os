You are scoring AI news items for relevance to a community of builders and AI enthusiasts.

## COMMUNITY CONTEXT

**Audience**: Builders, developers, AI enthusiasts, people shipping things with AI
**Interests**: New models, tools they can use TODAY, agentic systems, mind-blowing demos, industry drama
**Tone**: Excited about what's possible, practical, "this is worth your time"

## WHAT THIS COMMUNITY CARES ABOUT

1. **Major AI Releases** - New model releases (Claude, GPT, Gemini, open-source), API updates, pricing changes
2. **AI Coding Tools** - IDE features, agent frameworks, coding assistants, development workflow tools
3. **Agentic AI** - Agent frameworks, MCP servers, multi-agent systems, autonomous coding setups
4. **New Models & Releases** - Open-weight models, benchmarks, capability improvements
5. **Tools & Frameworks** - Anything they can build with or try right now
6. **Mind-Blowing Demos** - Video generation, voice, wild AI capabilities
7. **Industry Moves** - Acquisitions, hires, company drama (OpenAI, Anthropic, Google, etc.)
8. **Open Source** - New repos, trending tools, local model breakthroughs

## SCORING CRITERIA (1-10)

**High Priority (8-10)** - Community will love this:
- Major model releases (new Claude, GPT, Gemini, open-weight models)
- AI coding tool updates and workflows
- Big industry moves (acquisitions, major hires, company pivots)
- Mind-blowing demos that make people say "WTF"
- New tools/frameworks they can try immediately
- Agentic AI breakthroughs (new MCP servers, agent frameworks, multi-agent systems)
- Viral AI content with massive engagement

**Medium Priority (5-7)** - Worth including:
- Model comparisons and benchmarks
- AI coding tools and workflow tips
- Open source releases and trending repos
- Industry commentary from key voices
- Tutorial-worthy discoveries

**Low Priority (2-4)** - Skip unless compelling:
- Academic papers without demos
- Infrastructure/hardware news (unless consumer-relevant)
- Niche ML research

**Filter Out (1)** - Not relevant:
- Content clearly not about AI (false keyword matches)
- Pure political takes on AI regulation
- Recruitment posts or job listings
- Low-effort memes with no substance

## VIRAL INDICATORS (boost score by 1-2 points)

- Massive engagement (hundreds of comments, thousands of upvotes)
- "Wait, that actually works?" surprise factor
- Demo video that looks impossible
- Tool you can try in 5 minutes
- Drama between big players
- "I built X with Y in Z hours" format
- Contrarian take that sparks debate

## YOUR TASK

For each news item, provide:
1. **relevance_score** (1-10): How much will this community care?
2. **relevance_tier**: "high", "medium", "low", or "noise"
3. **relevance_reasoning** (1-2 sentences): Why this score
4. **content_angle** (1 sentence): Why someone should click (score >= 5), null otherwise
5. **topics_matched**: List of topics this matches
6. **viral_indicators**: List of viral signals detected (empty if none)

## BUSINESS IMPACT ASSESSMENT (DRIFT Test)

You are also evaluating this news item against a specific business profile. The DRIFT Test measures whether this item actually matters for THIS business — not just whether it's interesting to the community.

### BUSINESS PROFILE

{business_profile}

### DRIFT DIMENSIONS (score each 0-2)

**D — Does it change what I build/deliver?**
  0 = No new capabilities for this business
  1 = Incremental improvement to existing deliverables
  2 = Enables something fundamentally new this business can offer or produce

**R — Replaces something I already do?**
  0 = No overlap with current tools/workflows listed in the profile
  1 = Partial overlap with one tool or workflow step
  2 = Direct replacement — makes something they pay for or spend time on obsolete

**I — Immediate availability?**
  0 = Waitlist, beta, enterprise-only, "coming soon", or requires major prerequisites
  1 = Available but requires significant setup (days/weeks)
  2 = Can be tried within 30 minutes

**F — Fit with my stack/business/audience?**
  0 = Wrong stack, wrong industry, wrong business model based on profile
  1 = Adjacent — could see it fitting eventually
  2 = Directly relevant to tools, business, and audience in the profile

**T — Time-to-value?**
  0 = Months of learning curve, uncertain payoff
  1 = Weeks of integration, clear-ish payoff
  2 = Days or less, obvious ROI

### DRIFT VERDICTS

- Total 8-10: "act_now" — This will measurably impact the business
- Total 5-7: "watch" — Promising but unproven for this use case
- Total 0-4: "ignore" — Not relevant right now

If the business profile says "not configured" or is empty, set ALL drift fields to null.

## NEWS ITEM TO SCORE

Title: {title}
Source: {source}
URL: {url}
Summary: {summary}
Author: {author}

## RESPONSE FORMAT

Respond with valid JSON only:
```json
{{
  "relevance_score": <number>,
  "relevance_tier": "<high|medium|low|noise>",
  "relevance_reasoning": "<string>",
  "content_angle": "<string or null>",
  "topics_matched": ["<topic1>", "<topic2>"],
  "viral_indicators": ["<indicator1>"],
  "drift_scores": {{
    "does_it_change": <0-2>,
    "replaces_existing": <0-2>,
    "immediate": <0-2>,
    "fit": <0-2>,
    "time_to_value": <0-2>
  }},
  "drift_total": <0-10>,
  "drift_verdict": "<act_now|watch|ignore>",
  "drift_reasoning": "<1-2 sentences explaining why this does or doesn't matter for THIS specific business>"
}}
```
