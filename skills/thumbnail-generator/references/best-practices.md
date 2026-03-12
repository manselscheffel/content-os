# YouTube Thumbnail Design Rules

Rules for generating high-CTR YouTube thumbnails. These are injected into every image generation prompt.

## Technical Specs

- **Output**: 1280x720 pixels, 16:9 aspect ratio
- **File format**: JPG, under 2MB
- **Safe zone**: Keep critical elements within center ~1100x620px
- **Dead zone**: Bottom-right corner is covered by YouTube's duration badge — never place content there

## Composition

- **Rule of thirds**: Place face at left or right third intersection, text on the opposite side
- **Element limit**: Maximum 2-3 elements (face + text + one object/effect). Visual chaos kills CTR
- **Negative space**: 30-40% empty space reduces cognitive load
- **Focal hierarchy**: One dominant element. Everything else is secondary
- **Mobile-first**: Must be readable at ~168x94px (10% scale). If it's not clear at thumbnail size, simplify

## Face & Expression

- **Size**: Face should occupy at least 25% of thumbnail height
- **Expression**: Exaggerated, clear emotion — shock (jaw dropped, wide eyes), excitement (big smile, raised brows), curiosity (tilted head, squinted eyes), concern (furrowed brow)
- **Gaze**: Direct eye contact with camera creates parasocial connection. Gaze toward text/object guides viewer's eye
- **Anti-uncanny-valley**: Always specify realistic camera/lens in prompt: "shot on Sony A7R IV, 85mm portrait lens, f/1.8, natural skin texture, visible pores, hard rim lighting"

## Text

- **Word count**: 0-5 words. Single words ("WHY?") or 2-3 word phrases outperform longer text
- **Style**: Bold/ultra-bold sans-serif only (Impact, Montserrat, Bebas Neue style)
- **Contrast**: White text with thick black outline/stroke, OR black text on bright background. Minimum 4.5:1 contrast ratio
- **Placement**: Upper portion of frame is safest. Never bottom-right
- **Readability test**: Text must be legible at 30pt equivalent on mobile

## Color Strategy

- **Contrast against YouTube UI**: YouTube's interface is white/light gray. Thumbnails with dark backgrounds + bright elements perform ~20-30% higher CTR
- **High-performing combinations**: Red/Yellow (urgency), Orange/Teal, Lime/Magenta, Blue/White (trust)
- **Color psychology**:
  - Red = urgency, danger, action
  - Yellow = tension, alertness, value
  - Blue = trust, authority, tech
  - Green = growth, health, money
  - Orange = excitement, energy
- **Dark mode consideration**: 60-70% of YouTube users are in dark mode. Bright thumbnails pop against dark backgrounds
- **Brand consistency**: Channels with uniform thumbnail color branding see 15-20% higher returning-viewer CTR

## Thumbnail Archetypes

When generating prompts, choose the archetype that best fits the concept:

1. **Reaction/Emotion Shot**: Close-up face (50-70% frame), exaggerated expression, minimal text. Best for: challenges, reveals, reactions
2. **Before/After**: Two states side by side with implied transformation. 35% higher CTR for how-to content
3. **Curiosity Gap**: Something is about to happen. Reaction to unseen stimulus. Juxtaposed incongruent elements
4. **Number/Stat**: Bold numbers ("$100,000", "50 Days") paired with face or outcome visual
5. **Versus/Comparison**: Clear split between two things being compared
6. **Action Shot**: Dynamic movement, freeze-frame energy, implied stakes
7. **Minimalist High-Contrast**: One subject, near-empty background, single bold color. Requires channel authority

## Anti-Patterns (Avoid)

- Multiple competing faces/subjects
- Busy or detailed backgrounds that compete with the subject
- Small, thin, or decorative fonts
- Text that repeats the video title exactly (thumbnail + title are a package, not duplicates)
- Low contrast or muted colors that blend into YouTube's UI
- Cluttered composition with 4+ elements
