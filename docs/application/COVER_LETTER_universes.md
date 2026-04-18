# Cover Letter — Research Engineer, Universes

**Mike Anderson**
Ithaca, NY — remote-ready with 25% NYC office capacity (1 h flight)
manderson240@gmail.com
github.com/manderson240/cohezion

**Position:** Research Engineer, Universes (Job ID 5061517008)

---

Dear Anthropic Hiring Team,

I'm applying for the Research Engineer role on the Universes team because the work you do — **building the next generation of agentic training environments** — is the same work I've been doing for 18 months on Cohezion, my self-funded research platform. I'd like to show it to you through three concrete artifacts, each directly aligned with a Universes-team responsibility.

### 1. Agentic environments with world-model-validated safety

`src/cohezion/environments/manifold_env.py` is a Gymnasium-compatible RL environment where agents navigate a 12-dimensional Riemannian manifold governed by Lagrangian mechanics and the HIHO stability principle. Instead of learning safety from reward signals that can be gamed, agents operate in physics that **structurally** resists unsafe behavior: large action magnitudes fight the attractor, so reward hacking becomes self-correcting. The environment is OpenEnv-compatible and registered via `gym.make('Cohezion/ManifoldEnv-v0')`. A companion `SwarmEnv` supports multi-agent gauge-field coupling (PettingZoo parallel API). Every transition is validated by a 86 K-parameter JEPA world model (`src/cohezion/world_model/jepa_world_model.py`) that flags physically implausible moves before they commit — mechanistic interpretability through continuous monitoring rather than post-hoc analysis.

### 2. Sandboxed execution for every agent rollout

`src/cohezion/sandbox/isolation.py` provides COW filesystem snapshots (BTRFS/LVM/overlay), Linux namespace isolation (PID/mount/UTS/IPC), and veth/bridge/iptables network isolation. Every agent episode runs in a fresh boundary with a `CleanupRegistry` guaranteeing teardown even on abnormal exit. This is the keyword match for your preferred-qualifications "sandboxing, containerization, VMs" — built from primitives, tested against the multi-agent harness, and composed with `JourneyTracker` so every episode's 12-D trajectory is replayable from a checkpoint.

### 3. Local inference fleet that extends Claude availability — latency first, cost second

This is the differentiator I'd most like to discuss. Universes-scale training means 10³ env-eval cycles per iteration, each typically containing one or more LLM calls. The headline constraint isn't cost — it's **wall-clock time**. A 5-step reasoning chain at 1 s Claude API TTFT takes 5 s minimum per rollout; the same chain on my local NPU lane at measured **63 ms best-case warm latency** takes 750 ms. That's **6.7× faster training iteration** — and unlike cost, you can't buy more wall-clock time. Cost is the second-order win: a 1000-call batch that would cost ~$25 at Sonnet rates costs $0 on the local fleet. I built a **Turboquant-accelerated Gemma 4 fleet** that runs on AMD Strix Halo (128 GB unified memory, XDNA 2 NPU, RDNA 3.5 iGPU, AVX-VNNI CPU) and orchestrates all four Gemma 4 variants across the silicon:

- **NPU (:13306)** — Gemma-4-E2B via FLM — sensing, routing, short-horizon
- **iGPU ROCWMMA (:13307)** — Gemma-4-E4B — governance, structured output
- **iGPU Unified (:13308)** — Gemma-4-26B-A4B (MoE) — reasoning, code synthesis
- **CPU AVX-VNNI (:13309)** — Gemma-4-31B — architect, safety review

One unified Python API (`cohezion.inference.route()`) dispatches across the lanes with task-affine model selection, budget gating, health-probe-backed fallback, and transparent escalation to `claude-haiku-4-5` → `claude-sonnet-4-6` → `claude-opus-4-7` only when the local fleet's quality gate fails. **All Anthropic calls in the fleet are headless `claude` CLI invocations** — `claude -p <prompt> --model <id> --output-format json --max-budget-usd X` — not raw API calls, so budget gating and usage telemetry come for free. Gemini uses the same CLI-subprocess pattern. For concurrent Ollama cloud calls, a `HarnessPool` with three slots (`pi`, `opencode`, `hermes`) sustains **3× parallel dispatch** over the per-client rate limit. Google Research's **TurboQuant** (ICLR 2026, arXiv:2504.19874) is wired in through Cohezion's `SymmetryHardwareBridge`: the SU(2) spinor coherence of the active agent becomes the random-rotation axis for KV-cache quantization — making TurboQuant's PolarQuant algorithm physics-aware. `extend_claude(prompt, claude_model="claude-sonnet-4-6")` is a drop-in wrapper that tries local first.

End-to-end verified 2026-04-18 via streaming dispatch: 5 sequential `route(..., stream=True)` calls to NPU Gemma-4-E2B-it-GGUF measured **TTFT p50 = 80 ms (range 80-86 ms), full-response ~200 ms for 16 tokens, $0 cost** — versus 500-1500 ms Claude API TTFT and $0.003 for the same batch. That is a **6-19× TTFT speedup** sustained across the whole 5-call batch with a 6-millisecond spread. Reproduce with `make demo-universes` and `make health-fleet`.

### Why I want to work on Universes specifically

Your team's focus on **capability evaluations** is where my platform has put in the most hours. Cohezion has validated its architecture in three live competitions — Kaggle Measuring AGI, Luma AMD Speedrun, BlueQubit Quantum — and has shipped 5 200+ tests across 13 CI/CD configurations. But the interesting signal for a Universes role isn't the competitions; it's the **evaluation harness behind them**: `UniverseEvaluator` with bootstrap CIs and 3+ baselines, `DegradationDetector` predicting coherence collapse 10 steps ahead, `benchmark_fleet.py` comparing local-vs-cloud throughput on a held-out workload. The Gemma 4 fleet exists in service of this harness — I need to run 10⁴ evaluation cycles without asking permission from a rate limiter.

My 10 years of data engineering at Nielsen/Claritas (250 M record ETL, 99.95% uptime) give me the operational base for large-scale ML infrastructure work. My physics/philosophy background gave me the lens that led to the manifold-based environments. The 18-month Cohezion investment sits at the intersection. I'd like to bring that intersection to Anthropic.

**Repository:** https://github.com/manderson240/cohezion
**Reviewer one-pager:** `SHOWCASE.md` in the repo root

I understand the 25 % in-office requirement and can accommodate travel from Ithaca (1 h flight to NYC) with advance scheduling. Open to relocation if it suits the team's collaboration cadence.

Thank you for your consideration,

**Mike Anderson**

---

*Attachments: resume, technical summary, reviewer showcase, live demo recording (on request).*
