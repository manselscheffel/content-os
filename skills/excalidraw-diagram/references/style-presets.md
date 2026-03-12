# Style Presets

Style presets control the overall visual feel of a diagram. Each preset defines element-level defaults that get applied to every shape, arrow, and text element.

**These presets override the base values in `color-palette.md` for the properties they define.** Semantic colors (start/end/decision/etc.) still come from the color palette — presets control the rendering style, not the meaning.

---

## How to Use

When generating a diagram, apply the preset values to every element. For example, if using the `sketch` preset, every rectangle gets `roughness: 1`, `fillStyle: "hachure"`, etc.

Properties not listed in a preset fall back to their defaults from `element-templates.md`.

---

## Preset: `formal`

Clean, corporate, technical. Best for architecture diagrams, system documentation, presentations to stakeholders.

| Property | Value |
|----------|-------|
| `roughness` | `0` |
| `fontFamily` | `3` (Cascadia/monospace) |
| `fillStyle` | `"solid"` |
| `strokeWidth` | `2` (shapes), `1` (lines/dividers) |
| `strokeStyle` | `"solid"` |
| `roundness` | `{"type": 3}` (rounded corners) |
| Canvas `viewBackgroundColor` | `"#ffffff"` |

**Text hierarchy:**
- Titles: fontSize `24-36`, color `#1e40af`
- Subtitles: fontSize `18-20`, color `#3b82f6`
- Body: fontSize `14-16`, color `#64748b` or `#374151`

**When to recommend:** Architecture docs, system overviews, technical specs, investor decks, anything that needs to look polished and precise.

---

## Preset: `sketch`

Hand-drawn, approachable, human. Best for YouTube explainers, blog illustrations, conceptual teaching, anything that needs to feel informal and engaging.

| Property | Value |
|----------|-------|
| `roughness` | `1` |
| `fontFamily` | `1` (Virgil/Excalifont — hand-drawn) |
| `fillStyle` | `"hachure"` |
| `strokeWidth` | `2` (shapes), `2` (arrows) |
| `strokeStyle` | `"solid"` |
| `roundness` | `null` (sharp corners — feels more hand-drawn) |
| Canvas `viewBackgroundColor` | `"#faf9f6"` (warm off-white) |

**Text hierarchy:**
- Titles: fontSize `28-36`, color `#1e1e1e`
- Subtitles: fontSize `20`, color `#495057`
- Body: fontSize `16`, color `#495057`

**Color adjustments:** Use slightly warmer/softer versions of the semantic colors:

| Semantic Purpose | Fill | Stroke |
|------------------|------|--------|
| Primary/Neutral | `#a5d8ff` | `#1971c2` |
| Secondary | `#d0bfff` | `#7950f2` |
| Start/Trigger | `#b2f2bb` | `#2f9e44` |
| End/Success | `#a5d8ff` | `#1971c2` |
| Warning/Reset | `#ffc9c9` | `#e03131` |
| Decision | `#ffec99` | `#f08c00` |

**When to recommend:** YouTube video overlays, blog post illustrations, explaining concepts to non-technical audiences, anything where "approachable" matters more than "precise."

---

## Preset: `whiteboard`

Very rough, brainstorm-y, spontaneous. Best for ideation sessions, quick sketches, "thinking out loud" diagrams, napkin-back planning.

| Property | Value |
|----------|-------|
| `roughness` | `2` |
| `fontFamily` | `1` (Virgil/Excalifont) |
| `fillStyle` | `"cross-hatch"` |
| `strokeWidth` | `3` (shapes), `2` (arrows) |
| `strokeStyle` | `"solid"` |
| `roundness` | `null` |
| Canvas `viewBackgroundColor` | `"#f8f0e3"` (warm parchment) |

**Text hierarchy:**
- Titles: fontSize `32-40`, color `#1e1e1e`
- Subtitles: fontSize `22`, color `#495057`
- Body: fontSize `18`, color `#495057`

**Color adjustments:** Bolder, higher-contrast colors:

| Semantic Purpose | Fill | Stroke |
|------------------|------|--------|
| Primary/Neutral | `#74c0fc` | `#1864ab` |
| Secondary | `#b197fc` | `#6741d9` |
| Start/Trigger | `#69db7c` | `#2b8a3e` |
| Warning/Reset | `#ff8787` | `#c92a2a` |
| Decision | `#ffd43b` | `#e67700` |

**When to recommend:** Brainstorming, ideation, early-stage planning, anything where polish would actually hurt (too formal = looks "done" when it's still a draft).

---

## Preset: `minimal`

Clean, understated, modern. Best for landing pages, product diagrams, design-focused contexts where less is more.

| Property | Value |
|----------|-------|
| `roughness` | `0` |
| `fontFamily` | `2` (Helvetica/sans-serif) |
| `fillStyle` | `"solid"` |
| `strokeWidth` | `1` (shapes), `1` (arrows) |
| `strokeStyle` | `"solid"` |
| `roundness` | `{"type": 3}` |
| Canvas `viewBackgroundColor` | `"#ffffff"` |

**Text hierarchy:**
- Titles: fontSize `24-32`, color `#1e1e1e`
- Subtitles: fontSize `16-18`, color `#868e96`
- Body: fontSize `14`, color `#868e96`

**Color adjustments:** Muted, desaturated palette:

| Semantic Purpose | Fill | Stroke |
|------------------|------|--------|
| Primary/Neutral | `#e9ecef` | `#495057` |
| Secondary | `#f1f3f5` | `#868e96` |
| Start/Trigger | `#ebfbee` | `#40c057` |
| End/Success | `#e7f5ff` | `#339af0` |
| Warning/Reset | `#fff5f5` | `#ff6b6b` |
| Decision | `#fff9db` | `#fab005` |

**When to recommend:** Product documentation, landing page visuals, design system docs, anything where the diagram should feel integrated into a clean UI.

---

## Embedding Images

For illustrative diagrams that include actual images/icons (not just shapes), use the `image` element type with base64 data in the `files` object.

### Image Element

```json
{
  "type": "image",
  "id": "img_1",
  "x": 100, "y": 100,
  "width": 200, "height": 200,
  "angle": 0,
  "strokeColor": "transparent",
  "backgroundColor": "transparent",
  "fillStyle": "solid",
  "strokeWidth": 1,
  "roughness": 0,
  "opacity": 100,
  "fileId": "abc123def456...40chars",
  "status": "saved",
  "scale": [1, 1],
  "crop": null,
  "groupIds": [],
  "boundElements": [],
  "version": 1,
  "versionNonce": 123456,
  "isDeleted": false,
  "seed": 987654
}
```

### Files Object

```json
"files": {
  "abc123def456...40chars": {
    "mimeType": "image/png",
    "id": "abc123def456...40chars",
    "dataURL": "data:image/png;base64,iVBORw0KGgo...",
    "created": 1700000000000,
    "lastRetrieved": 1700000000000
  }
}
```

**Key facts:**
- `fileId` is a 40-character SHA-1 hash of the file contents
- `dataURL` is `data:{mimeType};base64,{encodedData}` — fully self-contained
- `status` should be `"saved"` for pre-embedded images
- `scale` is `[1, 1]` by default; negative values flip
- Images work with any preset — they render independently of roughness/fillStyle
