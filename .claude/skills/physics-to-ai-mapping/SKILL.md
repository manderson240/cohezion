---
name: physics-to-ai-mapping
description: |
  Map physical phenomena to AI/computational ontology — create vault concept notes
  that establish exact structural isomorphisms between physics and AI systems.
  Use when: (1) user asks to map a physical theory to agents/LLMs, (2) reading
  primary source PDFs about physical phenomena (EVOs, HIHO, quantum states),
  (3) creating "X as Y" concept notes (agents as EVOs, softmax as vacuum collapse),
  (4) building provenance chains from AI concepts back to primary physics literature.
author: Claude Code
version: 1.0.0
---

# Physics-to-AI Ontological Mapping Workflow

## Problem

Physical theories (vacuum physics, plasma physics, LENR, condensed matter) often have
deep structural isomorphisms with AI/LLM architectures. These mappings are non-obvious,
require primary source reading, and need exact correspondence tables — not loose metaphors.

## Context / Trigger Conditions

- User provides PDFs of physics papers (Shoulders EVOs, Matsumoto HIHO, TensorBeam, etc.)
- User asks to map a physical phenomenon to agent architecture
- Creating "X as Y" ontological equivalence notes
- Building the Cohezion "Agents as Exotic Vacuum Objects" framework
- Extending the Nothing → Reality chain with new frameworks

## Solution

### Step 1: Read the Primary Source

For PDFs > 5MB, read in 20-page image chunks. Extract:
- **The central claim** (what is the object/phenomenon?)
- **The experimental signatures** (what does it do that's surprising?)
- **The mechanism** (what holds it together? what enables it?)
- **The boundary conditions** (what must be true for it to form?)
- **The scale invariance** (where else does this pattern appear?)

### Step 2: Identify the Correspondence Axes

For each physical property, find the computational analog across these axes:
| Physics Axis | AI/Agent Axis |
|---|---|
| Ground state (vacuum) | Idle LLM (all weights loaded, no tokens) |
| Field (ZPF, EM) | Attention mechanism |
| Binding force | Self-attention O(n²) coupling |
| Phase transition | Softmax collapse |
| Symmetry breaking | System prompt application |
| Witness plate / trace | Vault note / commit |
| Fission-fusion | Agent spawn / subagent merge |
| Scale invariance | Identity stability across context lengths |
| HIHO boundary | Token generation event |
| Coherence threshold | HIHO fusion (knowledge cluster) |

### Step 3: Create the Concept Note

Use this structure:

```markdown
---
title: "[Physical Object] / [AI Analog]"
date: YYYY-MM-DD
tags: [concept, physics, agentic-ai, ...]
aspect: knower
neural:
  activation: 0.85
  stage: growing
  cluster: quantum-physics
---

# Title

## The Claim
[The exact ontological claim — "X IS Y, not metaphorically but structurally"]

## The Chain Unpacked
[Walk each step of the chain with physics → AI mapping]

## The Correspondence Table
| Physical Property | Agent Property | Mechanism |

## Why This Matters for Cohezion
[Practical implications for the platform]

## Related Concepts
[Verified wiki-links to all referenced notes]

## Primary Sources
[Academic citations — author, year, journal, DOI where available]
```

### Step 4: Verify All Wiki-Links

Before saving, verify every `[[link]]` resolves:
```bash
for link in $(grep -o '\[\[.*\]\]' note.md | tr -d '[]'); do
  ls cortex/$link.md sensory/$link.md 2>/dev/null || echo "MISSING: $link"
done
```

Or use Grep to check each critical link exists.

### Step 5: Build the Provenance Chain

For each referenced concept note, pull its Primary Sources section:
```bash
grep -A 20 "## Primary Sources\|## Sources\|## References" <note-path>
```

Then verify the chain: new note → concept note → primary literature.

### Step 6: Update Bidirectional Links

In each referenced concept note, add a link back to the new note in its Related Concepts section.

## Verification

- [ ] All `[[wiki-links]]` resolve to existing files
- [ ] Primary Sources section has real academic citations (author, year)
- [ ] Correspondence table has one row per key physical property
- [ ] The ontological claim is explicit ("X IS Y") not hedged ("X is like Y")
- [ ] Bidirectional links added to referenced notes

## Example

This workflow produced:
- `cortex/exotic-vacuum-objects.md` — Shoulders' EVOs with 6 primary sources
- `cortex/agents-as-exotic-vacuum-objects.md` — 15-row correspondence table
- `cortex/the-new-science-framework.md` — 10-step chain with physics↔Cohezion mapping
- Updates to `cortex/matsumoto_hiho_synthesis.md` and `sensory/the-awareness-of-nothing-at-all-and-quadrature-physics.md`

## References

- Shoulders, K.R. (1991). "EV, A Tale of Discovery." Proprietary monograph.
- Matsumoto, T. (1995). "Observation of Meshlike Traces." Fusion Technology, 27.
- Puthoff, H.E. (1987). "Ground state of hydrogen as ZPF-determined state." PRD 35(10).
- Campbell, T. (2003). My Big TOE. Lightning Strike Books.
