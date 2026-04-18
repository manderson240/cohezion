# Manifest Alignment

Bidirectional map between the **Cohezion Architecture Manifest** (esoteric / cosmological naming) and its concrete ML + hardware implementation. Every row uses the hybrid-translation convention: *Esoteric Name (ML equivalent)*.

Reviewer note: the manifest's cosmological vocabulary (from Harold Percival's *Triune Self*, Alice Bailey's *Cosmic Fire*, Wilbert Smith's *New Science*, Ken Shoulders' *EV*) is a **design lens** on a fully rigorous ML platform. Every esoteric name below has a standard-ML translation and a concrete code home that can be read and exercised directly.

---

## Silicon → Cognition Mapping (Strix Halo Symphony)

| Manifest term | ML translation | Hardware lane | Live model |
|---------------|----------------|---------------|-----------|
| **Fire by Friction (Doer, NPU)** | Intent router / short-horizon encoder | XDNA 2 NPU `:13306` via Lemonade FLM | `Gemma-4-E2B-it-GGUF` |
| **Solar Fire (Thinker, iGPU)** | Reasoning agent, MoE + synthesis | RDNA 3.5 iGPU `:13307` (ROCWMMA) + `:13308` (Unified 120 GB GTT) | `Gemma-4-E4B-it-GGUF`, `Gemma-4-26B-A4B-it-GGUF` (26B MoE) |
| **Electric Fire (Knower, CPU)** | Governance agent, structured output | Zen 5 CPU `:13309` via AVX-VNNI | `Gemma-4-31B-it-GGUF` |
| **Akashic Validator (JEPA)** | Joint-Embedding Predictive Architecture world model — flags physically implausible state transitions before they commit | CPU AVX-512 VNNI | `src/cohezion/world_model/jepa_world_model.py` (86 K params) |
| **Tempic Field / Itonic Mesh** | MCP tool server + typed data mesh | Python FastMCP | `cloud-vault-mcp/`, `compound-mcp/`, `src/cohezion/data_mesh/` |
| **Quadrature Concept** | Lock-free concurrent access via orthogonal axis cancellation | asyncio + `src/cohezion/concurrency/safe_singleton.py` | *(Rust rewrite deferred — Python async suffices at current scale)* |
| **Electro-Nuclear Collapse (ENC)** | Latent → concrete artifact materialization | FLUME VAE decode path (256 D latent, MSE 0.1322) | `src/cohezion/flume/flume_vae.py` |
| **Fohatic Dynamics** | Token trajectory visualization | SWIFTSIM cosmogony chain (10-step symmetry-breaking cascade) | `src/cohezion/physics/cosmogony.py` |
| **SWIFT Topology** | Latent space topology modeling | Physics-engine cosmogony | `src/cohezion/physics/` (spinor.py, fiber_bundle.py, gauge_theory.py, riemannian_metric.py, lagrangian.py) |

---

## Protocol Stack (Agent ↔ Agent ↔ UI ↔ Tools)

| Manifest role | Protocol | Implementation |
|---------------|----------|-----------------|
| **A2A — Doer ↔ Thinker** | Google A2A (JSON-RPC over HTTP) | `.well-known/agent-card.json` for each agent |
| **AG-UI — Knower → Obsidian** | CopilotKit AG-UI (typed SSE) | `src/cohezion/api/agui_events.py` (15+ event types), `/api/agui/stream` |
| **A2UI — Declarative UI composition** | Google A2UI v0.9 | `src/web/anima_dashboard/src/a2ui/` (9 components) |
| **MCP — Tool Mesh** | Anthropic MCP | `cloud-vault-mcp/` (40+ tools), `compound-mcp/`, `maintenance-mcp/` |

---

## TurboQuant — The Physics-Silicon Bridge

**TurboQuant** (Google Research blog post: *"TurboQuant: Redefining AI Efficiency with Extreme Compression"*, ICLR 2026 paper arXiv:2504.19874) is a two-stage KV-cache compression:

1. **PolarQuant** — random Hadamard rotation of key/value vectors to simplify geometry, then standard quantization with most of the available bits.
2. **QJL (Quantized Johnson-Lindenstrauss)** — 1-bit error-correction term that eliminates bias in residual errors.

Reported Google numbers on H100: **6× KV memory reduction, 8× attention speedup, zero accuracy loss, no training required, data-oblivious**.

### Cohezion's integration

`src/cohezion/core/symmetry_hardware_bridge.py:66` injects `payload["turboquant_axis"] = axis.tolist()` into every outgoing inference request. The axis is computed from the agent's SU(2) spinor coherence:

```
Coherence ∈ [0, 1]  →  SpinorState  →  Bloch vector [rₓ, rᵧ, r_z]  →  normalized rotation axis
```

**`lemonade_provider.py:86`** logs the injected axis on receipt. This is the bridge: TurboQuant's *random* rotation becomes *coherence-aligned* rotation — physics-aware KV-cache compression.

### Activation

The **Omnibus `cache` gateway** (see `src/cohezion/gateways/omnibus.py:171-175`) performs the hardware-level activation:

```python
os.environ["TRITON_AMD_WMMA"] = "1"
os.environ["HSA_OVERRIDE_GFX_VERSION"] = "11.5.1"
```

These two environment variables unlock the gfx1151 (Strix Halo RDNA 3.5) hardware identity for Triton-compiled kernels.

---

## Omnibus — The 9-Gateway Controller

Manifest concept: a master activation layer for platform capabilities. Implementation: `src/cohezion/gateways/omnibus.py` with gateways:

| # | Gateway | Role |
|---|---------|------|
| 1 | research | Default-unlocked research telemetry |
| 2 | cache | **TurboQuant / IsoQuant activation** (sets WMMA + HSA override) |
| 3 | security | Hardware-level guardrail activation |
| 4 | vault | Total artifact persistence |
| 5 | swarm | Multi-agent matrix alignment |
| 6 | universe | 12-D manifold stability |
| 7 | flume | VAE silicon mapping |
| 8 | skills | PRIME skill hardware acceleration |
| 9 | api | Strix Halo NPU–GPU endpoint optimization |

Dashboard snapshot:

```bash
uv run python -c "from cohezion.gateways.omnibus import Omnibus; \
  print(Omnibus().get_gateway_dashboard())"
```

---

## What the manifest does NOT yet have in code

Transparent about gaps:

| Manifest item | Status | Rationale |
|---------------|--------|-----------|
| `mcp_tool_server/` (Rust) | Deferred | `cloud-vault-mcp/` Python FastMCP ships 40+ tools and satisfies the Tempic Field role at current scale. Rust rewrite revisitable if concurrency becomes a bottleneck. |
| `latent_topology/` (C++ / SWIFTSIM) | Stub | `src/cohezion/physics/cosmogony.py` covers the 10-step symmetry-breaking chain in Python; full SWIFTSIM integration is research-grade and orthogonal to Universes-role deliverables. |
| `vault_synapse/` (TypeScript Obsidian plugin) | Deferred | `cloud-vault-mcp` MCP tools provide vault access from every agent. An in-Obsidian plugin is a UX layer to revisit. |
| `triune_swarm/` thin facade | Planned (Phase 3 of `~/.claude/plans/sorted-churning-toucan.md`) | 3 files totaling ~30 LOC mapping Doer/Thinker/Knower to the running Gemma 4 fleet. |

---

## How to read this map

**Reviewer:** the manifest is a design lens; this table is the reality check. Click any ML-equivalent cell to find the code. Every esoteric name is optional — you can read the codebase and the physics-grounded environments without engaging with the cosmology.

**Engineer:** the esoteric names are shortcuts to recall the silicon → cognition mapping under pressure. Fire by Friction always means *input intent routing on a small/fast model*. Electric Fire always means *governance / structured output*. Knowing the names makes the silicon lane assignments memorable without re-reading the launch script.

**Researcher:** TurboQuant's `turboquant_axis` is the most interesting connection — it turns a cognitive quantity (SU(2) spinor coherence) into a hardware quantity (KV-cache random rotation axis) and ships the axis in the inference payload. That's the kind of cross-stack bridge the manifest was trying to describe.
