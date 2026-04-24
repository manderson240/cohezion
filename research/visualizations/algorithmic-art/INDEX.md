# Algorithmic Art — Cohezion Concepts

Five p5.js generative art pieces visualizing core scientific concepts from Cohezion. Each is a standalone interactive HTML file (CDN-loaded p5.js, seeded for reproducibility, no build step). Open any file directly in a browser.

Generated via the `claude-api:algorithmic-art` skill (Wave D3, synthetic-sniffing-panda polish campaign). Original work — not derived from any artist's existing pieces. Cohezion dark palette: `#0a0e1a` background, `#1e3a8a` deep blue, `#22d3ee` electric cyan, `#e879f9` magenta accent, `#f1f5f9` ink.

## Pieces

### 1. `spin-coherence.html` — Phase Lattice
**Concept**: SPIN coherence = Rotation + Precession. Information units align when phases match.
**Reference**: `CLAUDE.md` § "Design Principles (Compound-Aligned)" — "SPIN Coherence: Information unit = Rotation + Precession. Alignment when phases match."
**Visual**: A field of small spinning-top tokens, each rotating on its own axis and precessing around a tilted vertical. Phase-matched tokens pulse with cyan/magenta halos and gently cluster via attraction. Live coherence percentage HUD.
**Interactive**:
- Token Count (40–220)
- Coherence Target % (0–100) — global phase bias
- Phase Tolerance (radians)
- Coupling Strength (Kuramoto-like)
- Spin Speed
- Precession Speed

### 2. `flume-latent-flow.html` — Latent Currents
**Concept**: FLUME VAE encodes 256-dimensional latent vectors. Encodings flow through latent space, drawn into attractor basins (mode collapse points). Color encodes reconstruction loss.
**Reference**: `CLAUDE.md` § "Architecture at a Glance" — "Flume / FLUME VAE (256D latent space)". Source: `src/cohezion/flume/flume_vae.py`.
**Visual**: Curl-noise particle flow with attractor basins. Color shifts from cyan (low loss / well-encoded) to magenta (high loss / out-of-distribution) as particles consolidate near basins. Mouse drag spawns new encodings.
**Interactive**:
- Encoded Particles (200–3000)
- Attractor Basins (2–14)
- Basin Pull strength
- Flow Curl
- Trail Persistence
- Reconstruction Loss Bias
- Mouse drag: spawn encodings at cursor

### 3. `bioelectric-percolation.html` — HIHO Phase Transition
**Concept**: Levin's bioelectric network — gap-junction percolation triggers HIHO (Half-In-Half-Out) phase transition at ~50% connectivity. Below threshold: fragmented voltage basins. Above: coherent waves sweep the lattice.
**Reference**: `CLAUDE.md` § "Architecture at a Glance" — "Bioelectric: Levin bioelectric network, gap junction percolation, HIHO phase transition". Source: `src/cohezion/physics/bioelectric_model.py`.
**Visual**: Square cellular grid; cells diffuse voltage only across open gap junctions. Junctions stochastically flicker open/closed at the user-set HIHO target. Live readout flips from "subcritical / fragmented" to "above threshold / wave-coherent" at 50%.
**Interactive**:
- Grid Resolution (40–120)
- Gap-Junction % (HIHO threshold)
- Diffusion Rate
- Pacemaker injection rate
- Junction Flicker rate

### 4. `cosmogonic-chain.html` — 10-Step Symmetry Breaking
**Concept**: 10-stage cosmogonic chain — perfect rotational symmetry progressively breaks into increasingly structured forms.
**Reference**: `CLAUDE.md` § "Architecture at a Glance" — "Cosmogony: Cosmogonic chain + SymmetryBreaking". Source: `src/cohezion/physics/cosmogony.py`.
**Visual**: Animated sequence over 10 named stages: (1) Plenum, (2) Polarity, (3) Trinity, (4) Cardinality, (5) Pentad/golden ratio, (6) Hex lattice, (7) L-system branching, (8) Voronoi territories, (9) Recursive subdivision, (10) Coherent multiplicity. Smooth crossfade between stages. Each stage uses a different generative technique (n-gons, L-systems, voronoi sampling, recursive squares).
**Interactive**:
- Stage (1–10) — manual selection
- Auto-Advance Speed (set 0 to freeze)
- Detail / Recursion (controls L-system depth, voronoi cells)
- Asymmetry (jitter / randomness)

### 5. `swarm-mycelium.html` — Ouroboros Bridge
**Concept**: Mycelium network correlates execution patterns; nodes spawn from existing nodes weighted by coherence. As the network grows toward an outer ring, the OuroborosBridge wraps it in self-referential closure (a magenta arc that snakes around to meet its tail).
**Reference**: `CLAUDE.md` § "Architecture at a Glance" — "Ouroboros: Ouroboros bridge + Mycelium network wired into Genesis chain". Source: `src/cohezion/ouroboros/`.
**Visual**: Living branching network slowly rotating; weak edges (low coherence) are pruned; ring-band nodes form a gradually-closing magenta Ouroboros arc with a glowing head and tail-merge point.
**Interactive**:
- Max Nodes (80–600)
- Growth Rate (nodes per frame)
- Coherence Threshold — edges below this are hidden
- Branch Spread (radians)
- Field Rotation (whole-network rotation)
- Ouroboros Pull — biases growth toward the outer ring
