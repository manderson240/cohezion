---
type: antigravity-artifact
session_id: 8c5a9d85-c294-4aa3-a0e9-9d2d51a72f9c
date: 2026-03-04
title: "Web Portal Plan"
aspect: doer
neural:
  activation: 0.353
  stage: embryo
  cluster: Agents
---

# Project: Cohezion Web Portal (The Glass Lattice)

We are building a premium, interdisciplinary web portal to showcase the results of the 1M+ simulation mission and the underlying FLUME methodology.

## Design Aesthetic: "The Glass Lattice"
- **Tokens**: Deep HSL purples (`260 40% 10%`), Cyber-Emerald (`150 100% 50%`), and HIHO-Crimson (`0 100% 50%` for instability).
- **Style**: Glassmorphism (Frosted backgrounds, high saturation shadows), modern typography (Inter/Outfit), and smooth micro-animations.
- **Visual Center**: A 3D WebGL manifold explorer powered by Three.js.

## Design Strategy: Protocol-First & Hallucination-Resistant
To ensure the UI is a robust reflection of Cohezion's high-fidelity data, we will use a **Protocol-First** architecture:

1. **MCP-UI Specification**: We'll define an MCP server that provides pre-vetted React + Three.js components. The LLM won't 'generate' code; it will 'request' specific, hardened components by name and parameter.
2. **Component Mapping Registry**: A deterministic registry will map the 12D PhysicsState vectors to visual properties (e.g., `stability` -> `glow_intensity`, `habitat_quality` -> `texture_organic_flow`).
3. **Agent-Defined Design Tokens**: Styling will be managed through a centralized design system schema, allowing the swarm to update the 'mood' of the site without touching the component logic.

## Interdisciplinary Refinement
| Stream | 2026 Tech Integration |
|--------|-----------------------|
| **Architect** | **MCP-UI Engine**: Returns component configurations, not raw JSX. |
| **Engineer** | **Vite + Shadcn-MCP**: Surgical retrieval of vetted UI primitives. |
| **Biologist** | **Morphogenetic Components**: Properties bound to ecosystemic metrics. |
| **Quantum** | **HIHO Stabilization**: The UI rendering loop maintains a 0.5 stability anchor. |


## Proposed Components

### 1. The Manifold Explorer [3D]
- Interactive Three.js scene showing the 100,000+ simulation nodes.
- Filterable by 'Eco-Metrics' (Condition, Density, Flow).

### 2. Mission Control HUD
- Real-time ticker of 'Disparate Scenarios' being processed.
- R-Zero metric tracker (Success Rate, Difficulty Curve).

### 3. The FLUME Monograph
- Interactive scroll-telling section explaining:
  - 12D PhysicsState vectors.
  - HIHO reality precipitation stability.
  - Manifold Encoding (MNM).

## Tech Stack
- **Frontend**: React + Vite + Three.js (Fiber).
- **Styling**: Vanilla CSS with Design Tokens.
- **Backend Bridge**: Python FastMCP + SSE endpoint.

## Verification Plan
- **Performance**: Ensure 30FPS+ while rendering 5000+ active nodes.
- **Aesthetics**: Manual verification of 'Wow' factor and mobile responsiveness.
