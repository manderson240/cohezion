---
name: Genesis
description: Design tokens and voice for the Cohezion Genesis UI (Next.js 16, Three.js). Values mirror src/app/globals.css; change them there and here together.
colors:
  background: "#0a0a0a"
  foreground: "#ededed"
  nexus-green: "#00ff00"
  matte-black: "#0a0a0a"
  earth-blue: "#0077be"
  critical-red: "#ff3b3b"
  warning-gold: "#f6d365"
  plasma-blue: "#4facfe"
  neon-cyan: "#00f2fe"
  silicon-silver: "#c0c0c0"
typography:
  sans: var(--font-geist-sans)
  mono: var(--font-geist-mono)
motion:
  hiho-hue: 120
  hiho-saturation: "100%"
  hiho-pulse-speed: 8s
  hiho-particle-density: 0.3
---

# Genesis — how it should look and feel

A control room for watching a universe compute: matte black depth, data rendered as light.
Nothing decorative; every glow carries a number. Think an observatory at night, not a dashboard
template. Coherence is the one quantity the whole interface orbits, and the HIHO equilibrium
(coherence 0.5) is where the palette rests: `nexus-green` at full saturation, pulsing on an
8-second breath. Deviation shifts hue away from green; alarm states earn `critical-red`, caution
earns `warning-gold`, and nothing else may use those two colors.

## Rules agents must keep

- Dark surfaces only (`background`, `matte-black`); light text (`foreground`, `silicon-silver`).
  Never introduce a light theme without changing this file first.
- Accent colors are semantic, not ornamental: `plasma-blue` and `neon-cyan` for data series and
  edges, `earth-blue` for links and controls, `nexus-green` for coherence and health.
- Three.js scenes (Bloch sphere, swarm topology, manifold) share the same tokens via CSS
  variables; do not hard-code hex values in shaders or component props.
- Motion communicates state: the HIHO pulse speed and particle density are tokens, not magic
  numbers, and they slow or thin as coherence drops.
- Typography: Geist Sans for UI, Geist Mono for every number, path and identifier.

The fuller component inventory and rationale live in `.stitch/DESIGN.md`; this file is the
agent-readable contract (DESIGN.md spec: prose section plus YAML frontmatter tokens).
