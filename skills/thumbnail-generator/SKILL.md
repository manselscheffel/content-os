---
name: thumbnail-generator
description: Generate YouTube thumbnail variations from a video concept through a collaborative design process with human creative direction. Use when user says "generate thumbnails", "make a thumbnail", or "thumbnail for [concept]". Run with /thumbnail-generator. Also triggered automatically during youtube-content prep.
argument-hint: "video concept description"
---

# Thumbnail Generator

Generate production-ready YouTube thumbnails (1280x720) through a collaborative creative process. The reference images do the heavy lifting — Gemini can see them. Your prompt is just the diff.

## Core Principle

**The reference image is gospel.** We upload a reference thumbnail and tell Gemini: "Recreate this exactly, but change X." Gemini can see the lighting, composition, colors, 3D rendering style, everything. We don't describe any of that in words — we only describe what's different.

This is how you'd use Gemini directly: drop in a reference image and say "use this but swap the left logo for Claude with an orange glow." Short, specific, just the changes.

## Environment Variables

- `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) — Google AI API key (required)

Keys are loaded via `lib.config.get_key("gemini")`.

## Execution Steps

### Step 1: Understand the Video

Before recommending anything, understand what the thumbnail is for. Collect:

- **Video title** (or working title) — thumbnail text must complement, not repeat, the title
- **What the video covers** — 1-2 sentence core message
- **Key tools/products** — which logos would viewers recognize?
- **Target emotion** — curiosity, FOMO, shock, aspiration?

If coming from youtube-content prep, you already have the PSP outline, title options, and audience info. Use them.

If the user gives a bare concept, ask these questions before proceeding.

### Step 2: Pick a Thumbnail Style

Ask the user to pick a thumbnail style. Each style has reference images in `assets/reference-thumbnails/` — the reference IS the style. No need to describe it.

| Style | When to Use |
|---|---|
| `electro_black` | Dark, dramatic, neon glows — tech reveals, AI tools, comparisons |
| `pixar_style` | 3D rendered, clay/plastic, warm — tutorials, builds, friendly content |
| `before_after` | Split layout, red/green contrast — transformations, comparisons |

Present a recommendation based on the video concept:

```
## Thumbnail Style

Based on your video about [topic], I'd recommend:

**electro_black** — dark and dramatic, matches the "power tool" energy of the video.

Other options:
- **pixar_style** — warmer, more approachable (good for tutorials)
- **before_after** — split comparison layout (good for vs content)

Which style do you want?
```

The user picks one. That selects the reference image.

### Step 3: Present Concept & Get Creative Direction

Read `references/prompt-system.md` for logo selection rules and text patterns.

Present a recommended concept to give the user a starting point:

```
## My Recommendation for "[Video Title]"

**Text**: "GOD MODE"
**Left logo**: github
**Right logo**: claude-color
**Rationale**: Title tells them what you built, thumbnail tells them what it GIVES them.

This is just a starting point. Tell me what you want changed on the reference:
- Which logos go where (left/right)
- What colors/glows behind each logo
- What text to put on it
- Anything else you want different from the reference

Think of it like dropping the reference into Gemini and saying "use this but change..."
```

The user gives creative direction — just the changes they want from the reference. Could be:
- "Claude on the left with orange glow, GitHub on the right with blue glow, text says GOD MODE"
- "Same as your recommendation but swap the logos"
- "Just change the text to say UNLOCKED"

### Step 4: Build 3 Short Prompts

Take the user's creative direction and create 3 variations. Each prompt is SHORT — just the changes from the reference. The reference image does the rest.

- **Variation 1**: User's direction executed with the chosen style reference
- **Variation 2**: Same direction but with a different style reference image (gives a different mood)
- **Variation 3**: Same style as variation 1 but with an alternative text option

**Good prompt** (short, just the diff):
```
Recreate this thumbnail exactly. Same style, lighting, composition. Only change:
- Top-left icon: use the provided GitHub logo with a blue glow behind it
- Top-right icon: use the provided Claude logo with an orange glow behind it
- Person: use the provided face photo, centered
- Text at bottom: "GOD MODE" in bold white with black outline
```

**Bad prompt** (describes the entire visual — Gemini can already SEE the reference):
```
Create a YouTube thumbnail, 1280x720. Dark cinematic background with dramatic lighting — deep purples and blacks. Put the GitHub logo on the top-left with a blue/purple glow radiating behind it...
```

Save the prompts to `.tmp/thumbnails/[slug]/prompts.json`:

```json
[
  {
    "prompt": "Recreate this thumbnail exactly. Same style, lighting, composition. Only change:\n- Top-left icon: use the provided GitHub logo with a blue glow behind it\n- Top-right icon: use the provided Claude logo with an orange glow behind it\n- Person: use the provided face photo, centered\n- Text at bottom: \"GOD MODE\" in bold white with black outline",
    "archetype": "electro_black",
    "text_on_image": "GOD MODE",
    "logos_used": ["github", "claude-color"],
    "user_direction": "GitHub left with blue glow, Claude right with orange glow, text GOD MODE"
  }
]
```

### Step 5: Generate Images

Run the generation script:

```bash
python3 ${CLAUDE_PLUGIN_ROOT}/skills/thumbnail-generator/scripts/generate.py \
  --prompts-file .tmp/thumbnails/[slug]/prompts.json \
  --output-dir .tmp/thumbnails/[slug]
```

The script:
1. Loads prompts.json
2. Auto-fetches product icons from lobe-icons CDN (cached in `assets/logos/`)
3. Sends requests to Gemini with reference thumbnail + face photo + icons + your short prompt
4. Gemini sees the reference, recreates it, applies only the changes you specified
5. Saves thumbnails to the output directory

### Step 6: Review Together

Show the generated thumbnails to the user. Ask:
- Does this match what you had in mind?
- Want to adjust anything — text, colors, logo placement?

If they want changes, go back to Step 3 — get new direction, rebuild the prompt, regenerate.

Common issues and fixes:
- **Text garbled**: Gemini text accuracy ~90%. Regenerate that variation.
- **Colors off**: Be more explicit about the color change in the prompt
- **Style drifted from reference**: Make the prompt shorter — less description = less drift from reference

### When Called from youtube-content prep

During `/youtube-content prep`, this skill runs as part of a larger workflow. The flow is the same — pick style, get creative direction, generate. Don't skip Step 3.

## CLI Options

```
--prompts-file PATH    Pre-made prompts.json
--variations N         Number of variations (default: 3)
--no-face              Generate without face/person
--style STYLE          Force a specific style (electro_black, pixar_style, before_after)
--output-dir PATH      Custom output directory
```

## Icons

Auto-fetched from [lobe-icons](https://lobehub.com/icons) CDN by slug name. Cached in `assets/logos/`. See `references/prompt-system.md` for the slug table.

## Reference Files

| File | When to Read |
|---|---|
| `references/prompt-system.md` | **Before Step 3.** Logo selection rules, text patterns, concept triangle. |
| `references/best-practices.md` | When you need deeper thumbnail design theory |
| `references/brand-kit.yaml` | Loaded automatically by the script |

## Cost

- ~$0.05-0.15 per thumbnail via Gemini API
- **Total per video**: depends on iterations. Typically 2-4 generations = $0.10-0.60

## Files

| File | Purpose |
|---|---|
| `SKILL.md` | This file |
| `references/brand-kit.yaml` | Brand config |
| `references/prompt-system.md` | Text patterns, concept design rules, logo slugs |
| `references/best-practices.md` | Thumbnail design theory |
| `scripts/generate.py` | Image generation (icon fetch + Gemini API) |
| `scripts/compose.py` | PIL-based deterministic compositor (fallback) |
| `scripts/setup_brand.py` | Brand kit setup |
| `assets/base-face.jpg` | Your base photo |
| `assets/logos/` | Auto-cached icons |
| `assets/reference-thumbnails/` | Style references by archetype |
