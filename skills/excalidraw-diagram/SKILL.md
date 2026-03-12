---
name: excalidraw-diagram
description: Create Excalidraw diagram JSON files that make visual arguments. Use when the user wants to visualize workflows, architectures, or concepts.
---

# Excalidraw Diagram Creator

Generate `.excalidraw` JSON files that **argue visually**, not just display information.

**Setup:** If the user asks you to set up this skill (renderer, dependencies, etc.), see `README.md` for instructions.

## Customization

**Colors:** `references/color-palette.md` — semantic shape colors, text hierarchy, evidence artifacts. The single source of truth for all color choices.

**Style presets:** `references/style-presets.md` — four visual presets (formal, sketch, whiteboard, minimal) that control roughness, font, fill style, stroke width, and canvas background. Presets override base rendering properties while semantic colors still come from the color palette.

**Image embedding:** `references/style-presets.md` also documents how to embed actual images/icons into diagrams using the `files` object and `image` element type.

To customize for your brand, edit `color-palette.md` for colors and `style-presets.md` for rendering style.

---

## Core Philosophy

**Diagrams should ARGUE, not DISPLAY.**

A diagram isn't formatted text. It's a visual argument that shows relationships, causality, and flow that words alone can't express. The shape should BE the meaning.

**The Isomorphism Test**: If you removed all text, would the structure alone communicate the concept? If not, redesign.

**The Education Test**: Could someone learn something concrete from this diagram, or does it just label boxes? A good diagram teaches—it shows actual formats, real event names, concrete examples.

---

## Depth Assessment (Do This First)

Before designing, determine what level of detail this diagram needs:

### Simple/Conceptual Diagrams
Use abstract shapes when:
- Explaining a mental model or philosophy
- The audience doesn't need technical specifics
- The concept IS the abstraction (e.g., "separation of concerns")

### Comprehensive/Technical Diagrams
Use concrete examples when:
- Diagramming a real system, protocol, or architecture
- The diagram will be used to teach or explain (e.g., YouTube video)
- The audience needs to understand what things actually look like
- You're showing how multiple technologies integrate

**For technical diagrams, you MUST include evidence artifacts** (see below).

---

## Research Mandate (For Technical Diagrams)

**Before drawing anything technical, research the actual specifications.**

If you're diagramming a protocol, API, or framework:
1. Look up the actual JSON/data formats
2. Find the real event names, method names, or API endpoints
3. Understand how the pieces actually connect
4. Use real terminology, not generic placeholders

Bad: "Protocol" -> "Frontend"
Good: "AG-UI streams events (RUN_STARTED, STATE_DELTA, A2UI_UPDATE)" -> "CopilotKit renders via createA2UIMessageRenderer()"

**Research makes diagrams accurate AND educational.**

---

## Evidence Artifacts

Evidence artifacts are concrete examples that prove your diagram is accurate and help viewers learn. Include them in technical diagrams.

**Types of evidence artifacts** (choose what's relevant to your diagram):

| Artifact Type | When to Use | How to Render |
|---------------|-------------|---------------|
| **Code snippets** | APIs, integrations, implementation details | Dark rectangle + syntax-colored text (see color palette for evidence artifact colors) |
| **Data/JSON examples** | Data formats, schemas, payloads | Dark rectangle + colored text (see color palette) |
| **Event/step sequences** | Protocols, workflows, lifecycles | Timeline pattern (line + dots + labels) |
| **UI mockups** | Showing actual output/results | Nested rectangles mimicking real UI |
| **Real input content** | Showing what goes IN to a system | Rectangle with sample content visible |
| **API/method names** | Real function calls, endpoints | Use actual names from docs, not placeholders |

**Example**: For a diagram about a streaming protocol, you might show:
- The actual event names from the spec (not just "Event 1", "Event 2")
- A code snippet showing how to connect
- What the streamed data actually looks like

**Example**: For a diagram about a data transformation pipeline:
- Show sample input data (actual format, not "Input")
- Show sample output data (actual format, not "Output")
- Show intermediate states if relevant

The key principle: **show what things actually look like**, not just what they're called.

---

## Multi-Zoom Architecture

Comprehensive diagrams operate at multiple zoom levels simultaneously. Think of it like a map that shows both the country borders AND the street names.

### Level 1: Summary Flow
A simplified overview showing the full pipeline or process at a glance. Often placed at the top or bottom of the diagram.

*Example*: `Input -> Processing -> Output` or `Client -> Server -> Database`

### Level 2: Section Boundaries
Labeled regions that group related components. These create visual "rooms" that help viewers understand what belongs together.

*Example*: Grouping by responsibility (Backend / Frontend), by phase (Setup / Execution / Cleanup), or by team (User / System / External)

### Level 3: Detail Inside Sections
Evidence artifacts, code snippets, and concrete examples within each section. This is where the educational value lives.

*Example*: Inside a "Backend" section, you might show the actual API response format, not just a box labeled "API Response"

**For comprehensive diagrams, aim to include all three levels.** The summary gives context, the sections organize, and the details teach.

### Bad vs Good

| Bad (Displaying) | Good (Arguing) |
|------------------|----------------|
| 5 equal boxes with labels | Each concept has a shape that mirrors its behavior |
| Card grid layout | Visual structure matches conceptual structure |
| Icons decorating text | Shapes that ARE the meaning |
| Same container for everything | Distinct visual vocabulary per concept |
| Everything in a box | Free-floating text with selective containers |

### Simple vs Comprehensive (Know Which You Need)

| Simple Diagram | Comprehensive Diagram |
|----------------|----------------------|
| Generic labels: "Input" -> "Process" -> "Output" | Specific: shows what the input/output actually looks like |
| Named boxes: "API", "Database", "Client" | Named boxes + examples of actual requests/responses |
| "Events" or "Messages" label | Timeline with real event/message names from the spec |
| "UI" or "Dashboard" rectangle | Mockup showing actual UI elements and content |
| ~30 seconds to explain | ~2-3 minutes of teaching content |
| Viewer learns the structure | Viewer learns the structure AND the details |

**Simple diagrams** are fine for abstract concepts, quick overviews, or when the audience already knows the details. **Comprehensive diagrams** are needed for technical architectures, tutorials, educational content, or when you want the diagram itself to teach.

---

## Container vs. Free-Floating Text

**Not every piece of text needs a shape around it.** Default to free-floating text. Add containers only when they serve a purpose.

| Use a Container When... | Use Free-Floating Text When... |
|------------------------|-------------------------------|
| It's the focal point of a section | It's a label or description |
| It needs visual grouping with other elements | It's supporting detail or metadata |
| Arrows need to connect to it | It describes something nearby |
| The shape itself carries meaning (decision diamond, etc.) | Typography alone creates sufficient hierarchy |
| It represents a distinct "thing" in the system | It's a section title, subtitle, or annotation |

**Typography as hierarchy**: Use font size, weight, and color to create visual hierarchy without boxes. A 28px title doesn't need a rectangle around it.

**The container test**: For each boxed element, ask "Would this work as free-floating text?" If yes, remove the container.

---

## Style Selection (Do This BEFORE Designing)

Before generating any diagram, you MUST present style options to the user. Read `references/style-presets.md` for the full preset definitions.

### The Workflow

1. **Assess the content** — Read what's being diagrammed. Consider:
   - What is the content about? (architecture, concept, workflow, comparison, etc.)
   - Who is the audience? (developers, YouTube viewers, stakeholders, brainstorming session)
   - What's the context? (documentation, video overlay, blog post, internal planning)

2. **Recommend a style** — Present the four presets with your recommendation:

   > **Style options for this diagram:**
   >
   > | Style | Feel | Best for |
   > |-------|------|----------|
   > | **formal** | Clean, corporate, precise | Architecture docs, system specs, stakeholder decks |
   > | **sketch** | Hand-drawn, approachable | YouTube explainers, blog illustrations, teaching |
   > | **whiteboard** | Rough, spontaneous, brainstorm-y | Ideation, planning, draft concepts |
   > | **minimal** | Understated, modern, quiet | Product docs, landing pages, design contexts |
   >
   > **My recommendation: `sketch`** — this is a YouTube explainer about [topic], and the hand-drawn style will feel more engaging and approachable than a formal diagram.
   >
   > Which style would you like?

3. **Ask about format** — After recommending a style, also ask about layout format:

   > **Format options:**
   > - **Single canvas** — One comprehensive diagram showing everything (best for architecture overviews, reference docs)
   > - **Slides** — Multiple frames/pages, one concept per slide (best for teaching, YouTube, presentations)
   >
   > **My recommendation: `slides`** — this is teaching content, and progressive disclosure will be more effective than one dense diagram.

4. **Wait for user selection** — Do not proceed until the user picks a style AND format.

5. **Apply the preset** — Load the selected preset from `style-presets.md` and apply its values to every element you generate. This means every shape, arrow, and text element uses the preset's `roughness`, `fontFamily`, `fillStyle`, etc. If slides were chosen, follow the Multi-Page / Slide Mode section for frame-based layout.

### When to Skip Style Selection

- If the user explicitly requests a style (e.g., "make it hand-drawn" or "formal diagram"), use that style directly — no need to ask.
- If this is a follow-up diagram in the same session and a style was already chosen, reuse it unless the user asks for something different.

---

## Design Process (Do This BEFORE Generating JSON)

### Step 0: Assess Depth Required
Before anything else, determine if this needs to be:
- **Simple/Conceptual**: Abstract shapes, labels, relationships (mental models, philosophies)
- **Comprehensive/Technical**: Concrete examples, code snippets, real data (systems, architectures, tutorials)

**If comprehensive**: Do research first. Look up actual specs, formats, event names, APIs.

### Step 1: Understand Deeply
Read the content. For each concept, ask:
- What does this concept **DO**? (not what IS it)
- What relationships exist between concepts?
- What's the core transformation or flow?
- **What would someone need to SEE to understand this?** (not just read about)

### Step 2: Map Concepts to Patterns
For each concept, find the visual pattern that mirrors its behavior:

| If the concept... | Use this pattern |
|-------------------|------------------|
| Spawns multiple outputs | **Fan-out** (radial arrows from center) |
| Combines inputs into one | **Convergence** (funnel, arrows merging) |
| Has hierarchy/nesting | **Tree** (lines + free-floating text) |
| Is a sequence of steps | **Timeline** (line + dots + free-floating labels) |
| Loops or improves continuously | **Spiral/Cycle** (arrow returning to start) |
| Is an abstract state or context | **Cloud** (overlapping ellipses) |
| Transforms input to output | **Assembly line** (before -> process -> after) |
| Compares two things | **Side-by-side** (parallel with contrast) |
| Separates into phases | **Gap/Break** (visual separation between sections) |
| Narrows or filters progressively | **Funnel** (stacked trapezoids narrowing down) |
| Has two dimensions of trade-offs | **Matrix/Quadrant** (2x2 grid with labeled axes) |
| Has layered importance/foundations | **Pyramid** (stacked sections, widest at bottom) |
| Focuses on a core goal | **Target/Bullseye** (concentric circles) |
| Weighs pros vs cons | **Scale/Balance** (fulcrum with weighted sides) |
| Shows levels, thresholds, health | **Gauge/Meter** (arc with colored zones) |

### Step 3: Ensure Variety
For multi-concept diagrams: **each major concept must use a different visual pattern**. No uniform cards or grids.

### Step 4: Sketch the Flow
Before JSON, mentally trace how the eye moves through the diagram. There should be a clear visual story.

### Step 5: Generate JSON
Only now create the Excalidraw elements. **See below for how to handle large diagrams.**

### Step 6: Render & Validate (MANDATORY)
After generating the JSON, you MUST run the render-view-fix loop until the diagram looks right. This is not optional — see the **Render & Validate** section below for the full process.

---

## Large / Comprehensive Diagram Strategy

**For comprehensive or technical diagrams, you MUST build the JSON one section at a time.** Do NOT attempt to generate the entire file in a single pass. This is a hard constraint — Claude Code has a ~32,000 token output limit per response, and a comprehensive diagram easily exceeds that in one shot. Even if it didn't, generating everything at once leads to worse quality. Section-by-section is better in every way.

### The Section-by-Section Workflow

**Phase 1: Build each section**

1. **Create the base file** with the JSON wrapper (`type`, `version`, `appState`, `files`) and the first section of elements.
2. **Add one section per edit.** Each section gets its own dedicated pass — take your time with it. Think carefully about the layout, spacing, and how this section connects to what's already there.
3. **Use descriptive string IDs** (e.g., `"trigger_rect"`, `"arrow_fan_left"`) so cross-section references are readable.
4. **Namespace seeds by section** (e.g., section 1 uses 100xxx, section 2 uses 200xxx) to avoid collisions.
5. **Update cross-section bindings** as you go. When a new section's element needs to bind to an element from a previous section (e.g., an arrow connecting sections), edit the earlier element's `boundElements` array at the same time.

**Phase 2: Review the whole**

After all sections are in place, read through the complete JSON and check:
- Are cross-section arrows bound correctly on both ends?
- Is the overall spacing balanced, or are some sections cramped while others have too much whitespace?
- Do IDs and bindings all reference elements that actually exist?

Fix any alignment or binding issues before rendering.

**Phase 3: Render & validate**

Now run the render-view-fix loop from the Render & Validate section. This is where you'll catch visual issues that aren't obvious from JSON — overlaps, clipping, imbalanced composition.

### Section Boundaries

Plan your sections around natural visual groupings from the diagram plan. A typical large diagram might split into:

- **Section 1**: Entry point / trigger
- **Section 2**: First decision or routing
- **Section 3**: Main content (hero section — may be the largest single section)
- **Section 4-N**: Remaining phases, outputs, etc.

Each section should be independently understandable: its elements, internal arrows, and any cross-references to adjacent sections.

### What NOT to Do

- **Don't generate the entire diagram in one response.** You will hit the output token limit and produce truncated, broken JSON. Even if the diagram is small enough to fit, splitting into sections produces better results.
- **Don't use a coding agent** to generate the JSON. The agent won't have sufficient context about the skill's rules, and the coordination overhead negates any benefit.
- **Don't write a Python generator script.** The templating and coordinate math seem helpful but introduce a layer of indirection that makes debugging harder. Hand-crafted JSON with descriptive IDs is more maintainable.

---

## Multi-Page / Slide Mode

For teaching content and presentations, split diagrams across multiple slides instead of one long canvas. This is especially useful for YouTube video overlays, tutorials, and step-by-step explanations where revealing information progressively is more effective than showing everything at once.

### When to Use Slides vs Single Canvas

| Use Slides When... | Use Single Canvas When... |
|---------------------|--------------------------|
| Teaching step-by-step (YouTube, tutorials) | Architecture overview (one big picture) |
| Content should be revealed progressively | Relationships between ALL parts matter |
| Each concept needs space to breathe | The viewer needs to see everything at once |
| Presentation / slideshow format | Reference documentation |
| Complex topic that needs chunking | Simple topic that fits one view |

### Approach: Frame-Based Slides (Single File)

Use Excalidraw `type: "frame"` elements to define slide boundaries within one `.excalidraw` file. Each frame acts as a slide viewport that clips its children.

**Standard slide dimensions:** `1280 x 720` (16:9) or `1200 x 800`

**JSON structure:**

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [
    // Slide 1 children (MUST come before their frame)
    { "id": "s1_title", "type": "text", "frameId": "frame_1", "x": 50, "y": 30, ... },
    { "id": "s1_rect",  "type": "rectangle", "frameId": "frame_1", "x": 50, "y": 100, ... },
    // Slide 1 frame (MUST come after its children)
    { "id": "frame_1", "type": "frame", "x": 0, "y": 0, "width": 1280, "height": 720, "name": "Slide 1 - Introduction", "strokeColor": "#bbb" },

    // Slide 2 children
    { "id": "s2_title", "type": "text", "frameId": "frame_2", "x": 1380, "y": 30, ... },
    // Slide 2 frame
    { "id": "frame_2", "type": "frame", "x": 1380, "y": 0, "width": 1280, "height": 720, "name": "Slide 2 - Core Concept", "strokeColor": "#bbb" }
  ],
  "appState": { "viewBackgroundColor": "#ffffff", "gridSize": 20 },
  "files": {}
}
```

**Critical rules:**
1. **Ordering**: All children of a frame MUST appear *before* their parent frame element in the `elements` array. Out-of-order elements render/clip incorrectly.
2. **frameId**: Every child element inside a slide must have `"frameId": "frame_N"` referencing its parent frame.
3. **Positioning**: Child element `x`/`y` coordinates are absolute (canvas coordinates), not relative to the frame. So a child at `x: 50` inside a frame at `x: 1380` should be at `x: 1430`.
4. **Spacing**: Place frames side-by-side with a 100px gutter between them (e.g., frame 1 at x:0, frame 2 at x:1380, frame 3 at x:2760 for 1280px wide frames).
5. **Naming**: Use descriptive `name` values (e.g., `"Slide 3 - Memory Architecture"`) — these appear as labels in the Excalidraw UI and aid navigation.

**Canvas layout zones within each slide:**

| Zone | Y Range (relative to frame) | Purpose |
|------|---------------------------|---------|
| Header | 30-100 | Title bar, slide number |
| Main Content | 110-600 | Primary diagram content |
| Footer | 620-700 | Callouts, key takeaways, tips |

### Approach: Multiple Files

Generate separate `.excalidraw` files per slide when:
- Each slide is complex enough to be its own comprehensive diagram
- You want each slide independently renderable to PNG
- The slides don't share cross-referencing arrows

**Naming convention:** `{topic}_slide_{N}_{title}.excalidraw`
Example: `ai_os_slide_1_overview.excalidraw`, `ai_os_slide_2_memory.excalidraw`

Each file is a standard single-canvas `.excalidraw` file — no frames needed.

### Slide Content Planning

When splitting a topic into slides, follow these principles:

1. **One concept per slide** — Each slide should teach ONE thing. If you need more than ~6 elements to explain it, it might need two slides.
2. **Progressive disclosure** — Order slides so each builds on the previous. Start with the big picture, then zoom into details.
3. **Visual continuity** — Use the same style preset, color palette, and visual patterns across all slides. Repeated elements (e.g., a system name that appears on multiple slides) should look identical.
4. **Slide 1 is always the overview** — Start with a simplified summary of the entire topic. Subsequent slides zoom into specific parts.
5. **Recap/summary slide at the end** — For 5+ slide decks, the last slide should tie everything together.

### Building Slides Section-by-Section

The section-by-section build strategy still applies within each slide. For frame-based slides:

1. **Create the base file** with the JSON wrapper and the first frame + its children.
2. **Add one frame (slide) per edit pass.** Build all children for that frame, then add the frame element at the end.
3. **Render after every 2-3 slides** to catch layout issues early. The render script will show all frames side-by-side on the canvas.

### Style Presets with Slides

All style presets work with slides. The preset's `viewBackgroundColor` applies to the canvas background (visible between frames). For frame-based slides, the frame itself is transparent — the slide background comes from a full-size rectangle as the first child element of each frame:

```json
{
  "id": "s1_bg", "type": "rectangle", "frameId": "frame_1",
  "x": 0, "y": 0, "width": 1280, "height": 720,
  "backgroundColor": "#faf9f6", "strokeColor": "transparent",
  "fillStyle": "solid", "roughness": 0, "opacity": 100
}
```

Use the preset's `viewBackgroundColor` value as this rectangle's `backgroundColor`.

### Presentation Playback

- **Excalidraw+ (paid)**: Native presentation mode — treats frames as slides with navigation, laser pointer, QR remote control
- **Excalidraw Smart Presentation (free)**: Open-source fork with animated transitions between frames. Elements sharing the same `name` across consecutive frames are smoothly interpolated
- **Obsidian Excalidraw Plugin**: Slideshow script that navigates between frames
- **Manual**: In standard Excalidraw, zoom to each frame manually (frames are visible on canvas as labeled regions)

---

## Visual Pattern Library

### Fan-Out (One-to-Many)
Central element with arrows radiating to multiple targets. Use for: sources, PRDs, root causes, central hubs.
```
        o
       /
  [] -> o
       \
        o
```

### Convergence (Many-to-One)
Multiple inputs merging through arrows to single output. Use for: aggregation, funnels, synthesis.
```
  o \
  o -> []
  o /
```

### Tree (Hierarchy)
Parent-child branching with connecting lines and free-floating text (no boxes needed). Use for: file systems, org charts, taxonomies.
```
  label
  +-- label
  |   +-- label
  |   +-- label
  +-- label
```
Use `line` elements for the trunk and branches, free-floating text for labels.

### Spiral/Cycle (Continuous Loop)
Elements in sequence with arrow returning to start. Use for: feedback loops, iterative processes, evolution.
```
  [] -> []
  ^      |
  [] <- []
```

### Cloud (Abstract State)
Overlapping ellipses with varied sizes. Use for: context, memory, conversations, mental states.

### Assembly Line (Transformation)
Input -> Process Box -> Output with clear before/after. Use for: transformations, processing, conversion.
```
  ooo -> [PROCESS] -> [][]
  chaos              order
```

### Side-by-Side (Comparison)
Two parallel structures with visual contrast. Use for: before/after, options, trade-offs.

### Gap/Break (Separation)
Visual whitespace or barrier between sections. Use for: phase changes, context resets, boundaries.

### Funnel (Narrowing/Filtering)
Stacked trapezoids narrowing downward. Use for: conversion funnels, filtering processes, sales pipelines.
Build with rectangles of decreasing width, stacked vertically. Use color intensity to show volume (lighter = less).

### Matrix/Quadrant (2x2 Analysis)
Four zones with labeled axes. Use for: trade-off analysis, positioning maps, priority grids.
Build with two perpendicular lines (axes) + four rectangles (quadrants) + axis labels as free-floating text.

### Pyramid (Hierarchy/Layers)
Stacked horizontal sections, widest at bottom. Use for: hierarchies, foundations, priority stacks.
Build with rectangles of increasing width stacked bottom-up, or use trapezoid shapes via line elements.

### Target/Bullseye (Focus/Priority)
Concentric circles with center emphasis. Use for: goals, prioritization, focus areas.
Build with concentric ellipses of decreasing size. Center = highest priority (strongest color).

### Scale/Balance (Trade-offs)
Triangle fulcrum with weighted elements on each side. Use for: ROI analysis, trade-offs, cost/benefit.

### Gauge/Meter (Levels/Progress)
Arc shape with colored zones and an indicator. Use for: health scores, thresholds, progress tracking.

### Lines as Structure
Use lines (type: `line`, not arrows) as primary structural elements instead of boxes:
- **Timelines**: Vertical or horizontal line with small dots (10-20px ellipses) at intervals, free-floating labels beside each dot
- **Tree structures**: Vertical trunk line + horizontal branch lines, with free-floating text labels (no boxes needed)
- **Dividers**: Thin dashed lines to separate sections
- **Flow spines**: A central line that elements relate to, rather than connecting boxes

Lines + free-floating text often creates a cleaner result than boxes + contained text.

---

## Shape Meaning

Choose shape based on what it represents—or use no shape at all:

| Concept Type | Shape | Why |
|--------------|-------|-----|
| Labels, descriptions, details | **none** (free-floating text) | Typography creates hierarchy |
| Section titles, annotations | **none** (free-floating text) | Font size/weight is enough |
| Markers on a timeline | small `ellipse` (10-20px) | Visual anchor, not container |
| Start, trigger, input | `ellipse` | Soft, origin-like |
| End, output, result | `ellipse` | Completion, destination |
| Decision, condition | `diamond` | Classic decision symbol |
| Process, action, step | `rectangle` | Contained action |
| Abstract state, context | overlapping `ellipse` | Fuzzy, cloud-like |
| Hierarchy node | lines + text (no boxes) | Structure through lines |

**Rule**: Default to no container. Add shapes only when they carry meaning. Aim for <30% of text elements to be inside containers.

---

## Color as Meaning

Colors encode information, not decoration. Every color choice should come from `references/color-palette.md` — the semantic shape colors, text hierarchy colors, and evidence artifact colors are all defined there.

**Key principles:**
- Each semantic purpose (start, end, decision, AI, error, etc.) has a specific fill/stroke pair
- Free-floating text uses color for hierarchy (titles, subtitles, details — each at a different level)
- Evidence artifacts (code snippets, JSON examples) use their own dark background + colored text scheme
- Always pair a darker stroke with a lighter fill for contrast

**Do not invent new colors.** If a concept doesn't fit an existing semantic category, use Primary/Neutral or Secondary.

---

## Modern Aesthetics

Element-level rendering is controlled by the selected style preset (see `references/style-presets.md`). The preset determines roughness, font, fill style, and stroke width. Below is a reference for what each property does:

### Roughness
- `roughness: 0` — Clean, crisp edges. Used by `formal` and `minimal` presets.
- `roughness: 1` — Hand-drawn, organic feel. Used by `sketch` preset.
- `roughness: 2` — Very sketchy, spontaneous. Used by `whiteboard` preset.

**Default is set by the selected preset.** Do not override unless you have a specific reason.

### Stroke Width
- `strokeWidth: 1` — Thin, elegant. Good for lines, dividers, subtle connections.
- `strokeWidth: 2` — Standard. Good for shapes and primary arrows.
- `strokeWidth: 3` — Bold. Use sparingly for emphasis (main flow line, key connections).

### Opacity
**Always use `opacity: 100` for all elements.** Use color, size, and stroke width to create hierarchy instead of transparency.

### Small Markers Instead of Shapes
Instead of full shapes, use small dots (10-20px ellipses) as:
- Timeline markers
- Bullet points
- Connection nodes
- Visual anchors for free-floating text

---

## Layout Principles

### Hierarchy Through Scale
- **Hero**: 300x150 - visual anchor, most important
- **Primary**: 180x90
- **Secondary**: 120x60
- **Small**: 60x40

### Whitespace = Importance
The most important element has the most empty space around it (200px+).

### Flow Direction
Guide the eye: typically left->right or top->bottom for sequences, radial for hub-and-spoke.

### Connections Required
Position alone doesn't show relationships. If A relates to B, there must be an arrow.

---

## Text Rules

**CRITICAL**: The JSON `text` property contains ONLY readable words.

```json
{
  "id": "myElement1",
  "text": "Start",
  "originalText": "Start"
}
```

Settings: `fontSize: 16`, `fontFamily: 3`, `textAlign: "center"`, `verticalAlign: "middle"`

---

## JSON Structure

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [...],
  "appState": {
    "viewBackgroundColor": "#ffffff",
    "gridSize": 20
  },
  "files": {}
}
```

## Element Templates

See `references/element-templates.md` for copy-paste JSON templates for each element type (text, line, dot, rectangle, arrow). Pull colors from `references/color-palette.md` based on each element's semantic purpose.

---

## Render & Validate (MANDATORY)

You cannot judge a diagram from JSON alone. After generating or editing the Excalidraw JSON, you MUST render it to PNG, view the image, and fix what you see — in a loop until it's right. This is a core part of the workflow, not a final check.

### How to Render

```bash
cd ${CLAUDE_PLUGIN_ROOT}/skills/excalidraw-diagram/references && uv run python render_excalidraw.py <path-to-file.excalidraw>
```

This outputs a PNG next to the `.excalidraw` file. Then use the **Read tool** on the PNG to actually view it.

### The Loop

After generating the initial JSON, run this cycle:

**1. Render & View** — Run the render script, then Read the PNG.

**2. Audit against your original vision** — Before looking for bugs, compare the rendered result to what you designed in Steps 1-4. Ask:
- Does the visual structure match the conceptual structure you planned?
- Does each section use the pattern you intended (fan-out, convergence, timeline, etc.)?
- Does the eye flow through the diagram in the order you designed?
- Is the visual hierarchy correct — hero elements dominant, supporting elements smaller?
- For technical diagrams: are the evidence artifacts (code snippets, data examples) readable and properly placed?

**3. Check for visual defects:**
- Text clipped by or overflowing its container
- Text or shapes overlapping other elements
- Arrows crossing through elements instead of routing around them
- Arrows landing on the wrong element or pointing into empty space
- Labels floating ambiguously (not clearly anchored to what they describe)
- Uneven spacing between elements that should be evenly spaced
- Sections with too much whitespace next to sections that are too cramped
- Text too small to read at the rendered size
- Overall composition feels lopsided or unbalanced

**4. Fix** — Edit the JSON to address everything you found. Common fixes:
- Widen containers when text is clipped
- Adjust `x`/`y` coordinates to fix spacing and alignment
- Add intermediate waypoints to arrow `points` arrays to route around elements
- Reposition labels closer to the element they describe
- Resize elements to rebalance visual weight across sections

**5. Re-render & re-view** — Run the render script again and Read the new PNG.

**6. Repeat** — Keep cycling until the diagram passes both the vision check (Step 2) and the defect check (Step 3). Typically takes 2-4 iterations. Don't stop after one pass just because there are no critical bugs — if the composition could be better, improve it.

### When to Stop

The loop is done when:
- The rendered diagram matches the conceptual design from your planning steps
- No text is clipped, overlapping, or unreadable
- Arrows route cleanly and connect to the right elements
- Spacing is consistent and the composition is balanced
- You'd be comfortable showing it to someone without caveats

### First-Time Setup
If the render script hasn't been set up yet:
```bash
cd ${CLAUDE_PLUGIN_ROOT}/skills/excalidraw-diagram/references
uv sync
uv run playwright install chromium
```

---

## Quality Checklist

### Depth & Evidence (Check First for Technical Diagrams)
1. **Research done**: Did you look up actual specs, formats, event names?
2. **Evidence artifacts**: Are there code snippets, JSON examples, or real data?
3. **Multi-zoom**: Does it have summary flow + section boundaries + detail?
4. **Concrete over abstract**: Real content shown, not just labeled boxes?
5. **Educational value**: Could someone learn something concrete from this?

### Conceptual
6. **Isomorphism**: Does each visual structure mirror its concept's behavior?
7. **Argument**: Does the diagram SHOW something text alone couldn't?
8. **Variety**: Does each major concept use a different visual pattern?
9. **No uniform containers**: Avoided card grids and equal boxes?

### Container Discipline
10. **Minimal containers**: Could any boxed element work as free-floating text instead?
11. **Lines as structure**: Are tree/timeline patterns using lines + text rather than boxes?
12. **Typography hierarchy**: Are font size and color creating visual hierarchy (reducing need for boxes)?

### Structural
13. **Connections**: Every relationship has an arrow or line
14. **Flow**: Clear visual path for the eye to follow
15. **Hierarchy**: Important elements are larger/more isolated

### Technical
16. **Text clean**: `text` contains only readable words
17. **Preset applied**: All elements use the selected style preset's `fontFamily`, `roughness`, `fillStyle`, `strokeWidth`
18. **Preset consistent**: No accidental mixing of preset values (e.g., roughness:0 on one element, roughness:1 on another — unless intentional for emphasis)
19. **Opacity**: `opacity: 100` for all elements (no transparency)
20. **Container ratio**: <30% of text elements should be inside containers

### Visual Validation (Render Required)
21. **Rendered to PNG**: Diagram has been rendered and visually inspected
22. **No text overflow**: All text fits within its container
23. **No overlapping elements**: Shapes and text don't overlap unintentionally
24. **Even spacing**: Similar elements have consistent spacing
25. **Arrows land correctly**: Arrows connect to intended elements without crossing others
26. **Readable at export size**: Text is legible in the rendered PNG
27. **Balanced composition**: No large empty voids or overcrowded regions
