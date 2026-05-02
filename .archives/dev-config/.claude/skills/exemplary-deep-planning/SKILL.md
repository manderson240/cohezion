---
name: exemplary-deep-planning
description: |
  Deep planning methodology for ambitious, multi-domain features that span math, physics,
  backend, frontend, multimodal, and persistence layers. Use when: (1) user asks to build
  something that touches 5+ subsystems, (2) the task requires grounding abstract concepts
  in real math/science, (3) the deliverable is a full interactive experience (webapp with
  audio/video/3D), (4) user says "use all your capabilities" or similar. Key pattern:
  parallel codebase exploration → web research → mathematical grounding → vertical-slice
  milestones → multimodal integration → total artifact persistence. This was marked as
  EXEMPLARY by the user and should be the target quality bar for all future planning.
author: Claude Code
version: 1.0.0
tags: [planning, architecture, multimodal, physics, webapp]
---

# Exemplary Deep Planning Methodology

## Problem

Complex features spanning math, physics, backend APIs, frontend visualization, audio/video,
and data persistence require a planning methodology that prevents scope drift while
maintaining depth. Standard planning produces either too-abstract documents or too-narrow
task lists.

## The Pattern (Verified in Genesis Engine session, 2026-03-26)

### Step 1: Parallel Deep Exploration (3 agents)

Launch 3 Explore agents simultaneously with orthogonal focus areas:

| Agent | Focus | Example |
|-------|-------|---------|
| **Foundations** | Core domain concepts, existing implementations, mathematical structures | "Explore the 12D manifold, SPIN coherence, HIHO stability" |
| **Infrastructure** | Skills, knowledge graph, compound engineering, persistence | "Explore skills, SurrealDB schemas, API endpoints" |
| **Surface** | Existing webapp, visualization, frontend components, UX | "Explore webapp components, Three.js scenes, hooks" |

### Step 2: Read Critical Files Directly

After exploration, read the 5-10 most important files yourself. Agents summarize; you need exact code to plan modifications.

### Step 3: Web Research for External Grounding

Use WebFetch/WebSearch for:
- Academic papers (arxiv) for mathematical rigor
- Reference implementations (SpaceEngine, Illustris) for UX inspiration
- Libraries and tools (Kyutai Labs, Tone.js) for multimodal capabilities
- Historical/philosophical references (Brahmagupta, Laozi) for narrative depth

### Step 4: Save Research Document

Write a comprehensive research document (`docs/<feature>-research.md`) BEFORE the plan. This captures:
- What exists (with code references)
- What's missing (mathematical gaps)
- The real math (actual equations, not hand-waving)
- Creative/literary inspiration
- Architecture decisions and trade-offs

### Step 5: Vertical-Slice Milestones

**Critical pattern**: Don't plan by horizontal layers (all math → all API → all frontend). Instead, plan **vertical slices** where each milestone delivers working math + API + UI:

```
Milestone 1: spinor.py + /genesis/spinor API + BlochSphere.tsx
Milestone 2: cosmogony.py + /genesis/cool API + GenesisScene.tsx
Milestone 3: fiber_bundle.py + /genesis/fiber-bundle API + FiberBundleViz.tsx
```

Each milestone has a clear "Done when" definition of a working, demonstrable feature.

### Step 6: Cross-Cutting Concerns as Explicit Milestones

Audio, video, persistence, and multimodal capabilities get their own milestone but are wired into all previous milestones retroactively:

```
Milestone N: Sonification → wire into M1 (Bloch hum), M2 (phase crack), M3 (geodesic audio)
```

### Step 7: Total Artifact Persistence

**Design principle**: ALL artifacts (prompts, responses, internal states, model checkpoints, audio, video, simulation runs) stored in SurrealDB. Nothing is ephemeral. This enables:
- World model training from journey data
- Universe replay from any historical state
- Retrospective analysis across sessions

## Quality Bar (What Makes It "Exemplary")

1. **Real math, not metaphor**: Actual equations (Euler-Lagrange, Fisher metric, Pauli matrices), not "we use advanced physics"
2. **Historical grounding**: Brahmagupta's zero, Laozi's Wújí, Wheeler's "It from Bit" — not decoration but mathematical foundations
3. **Creative vision**: Cinematic references (2001, Interstellar, Arrival) inform UX decisions, not just aesthetics
4. **Actionable milestones**: Each milestone completable in 1-2 sessions with clear "Done when"
5. **Multimodal completeness**: Audio (Tone.js + PocketTTS + Moshi), video (canvas capture), narration (PocketTTS), dialogue (Moshi), visual commentary (MoshiVis)
6. **Comprehensive persistence**: 6+ SurrealDB tables capturing every artifact type
7. **User feedback integration**: Each user comment (Brahmagupta, PocketTTS, Kyutai) enriches the plan rather than restarts it

## Anti-Patterns

- Planning by horizontal layer (all backend, then all frontend)
- Abstract milestones without "Done when" criteria
- Placeholder math ("we'll add the equations later")
- Skipping creative/philosophical grounding
- Treating audio/video as "nice to have" instead of first-class
- Ephemeral artifacts that aren't persisted

## Example: Genesis Engine Plan

**Reference**: `docs/plans/genesis-engine-plan.md` (668 lines)
**Research**: `docs/genesis-engine-research.md` (962 lines)

7 milestones, 49 new files, 9 modified files, spanning:
- 7 physics modules (SU(2) spinors, Riemannian geometry, Lagrangian mechanics, fiber bundles, gauge theory, information geometry, cosmogony)
- JEPA world model (LeWorldModel-inspired)
- SpaceEngine/Illustris-style universe simulation
- Full Kyutai Labs multimodal stack (PocketTTS, Moshi, Mimi, MoshiVis)
- 6 new SurrealDB tables for total artifact persistence
- 22 frontend components with Three.js, KaTeX, Tone.js

## Verification

The plan is "exemplary" when:
- User says it sets the quality bar for future sessions
- Every module has real math (equations that can be tested)
- Every milestone has a "Done when" with concrete criteria
- The research document could serve as a textbook chapter
- Audio/video are integrated, not afterthoughts
