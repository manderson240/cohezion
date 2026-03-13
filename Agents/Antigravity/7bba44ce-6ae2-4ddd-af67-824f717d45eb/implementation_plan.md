---
type: antigravity-artifact
session_id: 7bba44ce-6ae2-4ddd-af67-824f717d45eb
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.67
  stage: embryo
  synapse_in: 0
  synapse_out: 2
---

# Implementation Plan - Phase 11: Holographic Command Center

# Goal Description
Replace the flat web interface with a **"Minority Report" inspired Holographic HUD**. The user wants the application to look like a futuristic "Universe Simulation" controller.
**Key Aesthetics:** Translucency, Depth (Z-Axis), Neon Green data on dark glass, 3D background visualization.

## User Review Required
> [!IMPORTANT]
> **Performance Impact**: This design introduces a 3D WebGL context (`@react-three/fiber`) on the landing page. This will increase GPU usage.
> **Tailwind v4 Migration**: We are fully migrating the theme to CSS Variables in `index.css`, abandoning `tailwind.config.js` to ensure the build is robust.

## Proposed Changes

### Styling Engine (Tailwind v4)
#### [MODIFY] [index.css](file:///home/mike-anderson/dev/cohezion/apps/webapp/src/index.css)
- **Action**: Remove `@config` dependency.
- **Action**: Define `@theme` block directly in CSS.
- **Action**: Add custom utility classes for "Holographic Glass" (`.glass-panel`, `.neon-text`).
- **Variables**:
    - `--color-nexus-green`: `#00FF00` (The Soul).
    - `--color-void-black`: `#0A0A0A` (The Background).
    - `--glass-border`: `rgba(0, 255, 0, 0.2)`.

### Audio & Immersion
#### [NEW] [components/Audio/Narrator.tsx](file:///home/mike-anderson/dev/cohezion/apps/webapp/src/components/Audio/Narrator.tsx)
- **Feature**: "Pocket TTS" integration for Agentic Journeys.
- **Trigger**: Narrates high-entropy events from the thought stream.
- **Tech**: Web Speech API or local TTS endpoint context.

### 3D Architecture (Logo-Centric)
#### [NEW] [components/Universe/HologramField.tsx](file:///home/mike-anderson/dev/cohezion/apps/webapp/src/components/Universe/HologramField.tsx)
- **Concept**: "The Singularity".
- **Behavior**: Scene starts with the **Cohezion Logo** (Glass Cube) at center.
- **Animation**: The Swarm *emerges* from the logo, expanding into the lattice. The logo remains the "Anchor" of the UI.
- **Effect**: Uses `PostProcessing` (Bloom) if performance permits.

### Edge Case Resilience
- **No WebGL / Low Power**: Fallback to static "Holographic Blueprint" background image.
- **Mobile View**: "Datapad Mode" - Stacks panels vertically, disables 3D rotation, keeps the Logo fixed at top.
- **Offline**: If SSE disconnects, UI shifts to "Red/Warning" state with "Reconnecting..." pulse.

### UI Components
#### [MODIFY] [components/LandingPage.tsx](file:///home/mike-anderson/dev/cohezion/apps/webapp/src/components/LandingPage.tsx)
- **Action**: Convert to a full-screen HUD layout.
- **Structure**:
    - **Background**: `<HologramField />` (z-index: 0).
    - **Foreground**: `div.grid` (z-index: 10) with glass panels.

#### [NEW] [components/ui/GlassCard.tsx](file:///home/mike-anderson/dev/cohezion/apps/webapp/src/components/ui/GlassCard.tsx)
- **Style**: `bg-black/40 backdrop-blur-md border border-white/10 rounded-xl`.

## Verification Plan

### Automated Tests
- Build verification (`npm run dev`).

### Automated Tests (Fast Local Loop)
- **Tool**: Playwright (Firefox) + Local Ollama (Vision).
- **Script**: `scripts/verify_ui_local.ts`.
- **Flow**:
    1. Playwright captures screenshot of `localhost:5173`.
    2. Script sends image to local `minicpm-v` or `llava` via Ollama.
    3. Vision model responds YES/NO to "Is the text Neon Green?".
- **Benefit**: Removes network latency and utilizes user's "128GB Local Machine".

### Manual Verification
- **Visual Check**:
    - Does it look like "Minority Report"? (Dark, Glowing, Floating).
    - Is the text visibly **#00FF00**?
    - Is the background a 3D scene, not a flat color?

## Related Vault Notes

- [[cohezion]]
- [[universe-simulation]]
