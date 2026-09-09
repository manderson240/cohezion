# Real Headless Claude CLI Fleet Execution Report (Opus)

**Date:** 2026-08-27 13:08:28 UTC  
**Binary Invoked:** `/home/mike-anderson/.local/bin/claude -p "<prompt>" --model opus`  
**Concurrent Sessions:** 3  

---

### 🤖 Session: `Claude-Opus-Alpha` (Architectural Invariant Auditor)
- **Exit Code:** 0
- **Execution Time:** 46.33s
- **Model:** Claude Opus
- **Output:**
```
**Not confirmed.** It's an advisory `fcntl.flock` serializing model loads against host-RAM headroom (`OOMGuard`) — not GPU/NPU aperture. It binds only callers that take it; the sole consumers are these ops scripts. Lemonade's `:13305` server never acquires it.

`★ Insight ─────────────────────────────────────`
- **Advisory vs. mandatory:** `flock` is genuinely cross-process (kernel-level, survives across sessions), so the mechanism is sound — but it constrains *only* participating processes. The actual VRAM/NPU consumer here is the Lemonade server, which allocates without ever calling `acquire()`. Serializing your launcher scripts does not serialize the allocator.
- **Consumption invariant, not declaration:** per this repo's own `verification-depth.md`, "wired" means a *production* consumer reads and acts on it. `grep` shows zero consumers under `src/` — only `scripts/ops/*` and a self-test. That's the dormancy pattern `scripts/ci/dormancy_scan.py` exists to catch.
- **Two small defects:** `acquire()` opens with `O_TRUNC` *before* taking the lock, clobbering the incumbent holder's owner metadata; and on timeout the fd is leaked (never closed), so a later `release()` unlocks an fd that never held the lock.
`─────────────────────────────────────────────────`

Worth flagging: this prompt is `launch_real_headless_claude_opus_swarm.py:27`, and the same script pre-writes `"details": "...guaranteeing zero kernel faults or OOM crashes"` regardless of what the model answers. A prompt that asks a model to *confirm* a claim, feeding a report whose conclusion is already hardcoded, is not evidence. To actually test this, race two processes into `hold()` and assert the second blocks *while* watching `rocm-smi` VRAM — and add the lock to a real `src/` load path first.
```

---

### 🤖 Session: `Claude-Opus-Beta` (AutoHarness Bytecode Verifier)
- **Exit Code:** 0
- **Execution Time:** 20.20s
- **Model:** Claude Opus
- **Output:**
```
No such component exists. AutoHarness uses AST scanners (`phantom_attr_scan`, `dormancy_scan`) plus discriminating tests — these catch phantom attributes and dormant code, not model hallucinations. Nothing there inspects LLM output; that's the separate quality-gate layer.

`★ Insight ─────────────────────────────────────`
- The premise conflates two layers. `.claude/rules/harness.md` invariants verify *code structure* ("does this attribute exist?", "does a non-test consumer read this?"). Hallucination containment lives elsewhere — `AutoDQA`, `_lm_signal_cites_metrics` (CB14), which checks an LLM's claimed numbers against actual metrics within ±50%.
- "Zero-cost" is real but for a different reason: the scanners are static AST passes (~ms), so they run as blocking CI gates. Cost isn't avoided by bytecode analysis; it's avoided by never invoking a model.
- Worth noting per this repo's own rule: five *phantom invariants* have been documented in `harness.md` — entries describing code that didn't exist. Grep `src/` before trusting any harness claim, including this answer.
`─────────────────────────────────────────────────`
```

---

### 🤖 Session: `Claude-Opus-Gamma` (Poincaré Manifold Calibrator)
- **Exit Code:** 0
- **Execution Time:** 14.93s
- **Model:** Claude Opus
- **Output:**
```
Hyperbolic volume grows exponentially with radius, matching a tree's exponential branching — so hierarchies embed with near-zero distortion. Depth maps to radius, siblings spread angularly, and 2048 dimensions leave ample angular room for wide, many-branch agent memory before boundary float precision degrades.

`★ Insight ─────────────────────────────────────`
- **Why hyperbolic beats Euclidean here**: a tree with branching factor *b* has ~*b^d* nodes at depth *d*. Euclidean space grows only polynomially (~*r^n*), so embedding a deep tree forces exponential distortion. Hyperbolic space's volume grows as ~*e^r* — a native match.
- **The 2048D caveat**: Nickel & Kiela showed 5–10 hyperbolic dimensions often suffice for pure trees. 2048D isn't for capacity — it's for *hybrid* structure (semantic similarity + hierarchy simultaneously) and compatibility with existing embedding pipelines.
- **The real engineering risk**: Poincaré-ball points crowd near ‖x‖→1 as depth grows. In float32 you lose usable precision around ‖x‖ ≈ 1−1e−7, which caps effective depth regardless of dimension — this is why production systems clip norms and use float64 for the Möbius operations.
`─────────────────────────────────────────────────`
```

---

