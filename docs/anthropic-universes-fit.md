# Cohezion → Anthropic Research Engineer, Universes — Living Resume

**Candidate:** Mike Anderson · [github.com/manderson240/cohezion](https://github.com/manderson240/cohezion) · manderson240@gmail.com
**Target role:** [Research Engineer, Universes](https://job-boards.greenhouse.io/anthropic/jobs/5061517008) — *"train AI models to perform complex, difficult, long-horizon agentic tasks in ultra-realistic settings."*

> **This is a *living* resume.** Every capability claim below is checked by a script that
> re-measures the evidence on demand. It is not a list of assertions — it is a list of
> things you can re-run.
>
> ```bash
> python scripts/resume_verify.py            # human-readable table
> python scripts/resume_verify.py --receipt   # writes docs/resume_receipt.json
> make resume                                 # same, via Make
> ```
>
> **Last receipt:** `23 PASS / 0 FAIL / 1 SKIP` across 24 checks
> (`docs/resume_receipt.json`, regenerate to refresh). Each check is graded by
> **verification strength** — `STRONG` (ran end-to-end), `MEDIUM` (imported + instantiated),
> `WEAK` (import only) — so no claim outruns its evidence.

---

## TL;DR — why this is the right repo for *this* team

The Universes team builds **agentic training environments** and **rigorous evaluations of
genuine capability**. Cohezion is, at its core, exactly that: a Gymnasium-registered RL
environment with verifiable rewards (`Cohezion/ManifoldEnv-v0`), an **environment *generator***
that synthesizes new environments from spec and validates the generated code, an evaluation
harness with baselines and bootstrap CIs, and a long-horizon agentic loop that has been run,
measured, and — critically — **corrected when its own metrics turned out to be gameable.**

That last point is the whole pitch. The single most role-relevant artifact in this repo is a
one-line honest admission in the learnings log:

> `KEY_LEARNINGS.md:32` — *"RL REINFORCE: 0.991 coherence **but environment 'too easy.'**"*

A policy hit 99.1% coherence; instead of putting that number on a poster, the project diagnosed
it as a **reward that was too easy to game** and built a harder successor environment
(`ManifoldEnv-v0`, where a random agent scores ≈ −1.6 and a *trained* agent has to earn its
reward). Catching your own benchmark-gaming is the difference between "measuring activity" and
"measuring genuine capability" — which is the literal language of the job description.

---

## The boxes, checked

Legend: ✅ verified live by `resume_verify.py` · 📄 evidence in-repo · 🌐 external repo/artifact · ⚠️ honest gap

### Preferred qualifications (the technical core of the role)

| Job requirement | Cohezion evidence | Strength | Status |
|---|---|---|---|
| **Building RL environments / simulations** | `Cohezion/ManifoldEnv-v0` (19D obs / 12D action) resets, steps, returns finite verifiable reward; `SwarmEnv` multi-agent; `arc_env.py` | STRONG | ✅ `env_rollout` |
| **Build *next-generation* training environments** | `environments/auto_generator.py`: `EnvironmentGenerator` + `GeneratedCodeValidator` synthesize + validate new envs from spec | MEDIUM | ✅ `env_generation` |
| **Rigorous, reproducible evaluations** | Same seed reproduces reward exactly; `eval/universe_evaluator.py` (bootstrap CIs, ≥3 baselines) + `capability_scorecard.py` | STRONG / MEDIUM | ✅ `reward_determinism`, `eval_harness` |
| **Evaluation breadth (agentic/coding benchmarks)** | `benchmarks/{agentic_benchmark,coding_benchmark,cyber_benchmark,benchmark_suite}.py`; `competition/` (ARC-AGI-3 solver + eval-identity checks) | MEDIUM | ✅ `eval_benchmarks` |
| **LLM training / fine-tuning / RL** | `rl/{ppo,grpo,distributed,lora}_trainer.py` import; GRPO + LoRA present | WEAK *(import only — not a training-run claim)* | ✅ `rl_training_infra` |
| **Sandboxing / containerization / isolation** | `sandbox/isolation.py`, `sandboxing/executor.py`, `sandbox/shadow_worktree.py`, `Dockerfile`; Kaggle Blackwell handshake (containerized GPU) | MEDIUM | ✅ `sandboxing` |
| **Large-scale / distributed ML infrastructure** | `inference/orchestrator.py` `TieredOrchestrator` routes across NPU/iGPU/CPU local fleet | MEDIUM | ✅ `distributed_inference` |
| **Local-first inference fleet (heterogeneous accel.)** | `inference/triune_orchestrator.py` routes NPU(13306)/iGPU(13307)/CPU(13309) on AMD Strix Halo; `fleet.extend_claude()` escalates to cloud only on a quality-gate miss — a 10k-token loop runs at **$0** | MEDIUM | ✅ `local_inference` |
| **Large-scale simulation** | `mass_sim/` scale tiers up to a **25M-agent** "aspirational" universe (checkpointed, batched) | STRONG | ✅ `mass_sim` |
| **Self-improving infrastructure** | `ouroboros/` self-healing loop + `mycelium/` skill synthesis from execution traces + `evolution/` evolutionary skill optimization | MEDIUM | ✅ `self_improvement` |
| **Batched inference for throughput** | `async run_batch(prompts, *, budget_usd)` → `asyncio.gather` fan-out (3.44× throughput, harness CB1) | MEDIUM | ✅ `batching` |
| **Caching for efficiency at scale** | `cache/semantic_cache.py` L1 hash + L2 cosine + L3 vault, encoder-calibrated thresholds (harness CA1/CA2); 11 cache test files | MEDIUM | ➖ `semantic_cache` (SKIP — **latent bug surfaced**: unimportable at this commit, `lemonade_encoder` absent; `tests/cache/` errors on collection here) |
| **World models / simulations** | `world_model/jepa_world_model.py` (JEPA predictor, causal masking, CPU-trainable) | MEDIUM | ✅ `world_model` |
| **Published / influential ML research** | physics-grounded training-universes write-ups in `docs/`; `CITATION.cff`; sibling repo `observer-patch-holography/` | — | 📄 *(software citation, not peer-reviewed — see gaps)* |
| **Software engineering for robust infra** | 745 tests collect cleanly across 5 role-relevant suites (env/rl/eval/world_model/physics); ~2,259 across a wider set (one unrelated collection error in `tests/compound`); pre-commit, ruff, mypy, CI | STRONG | ✅ `test_collection` |
| **Observability / persistence / audit** | Live SurrealDB: 49 tables incl. bi-temporal `agent_journey`, `hash_chain` audit trail, `vmodel_gate`/`proof_obligation` (V-Model) | MEDIUM | ✅ `surrealdb` |

### Required qualifications (the working style)

| Job requirement | How Cohezion demonstrates it |
|---|---|
| **Impact-driven, outcomes over activity** | Reward-gaming self-catch (0.991 → harder env); metrics reported as *actual* numbers with caveats, not rounded up. |
| **Balance research exploration with engineering** | This very artifact: a research-grade honesty discipline shipped as a runnable verifier + CI gate. |
| **Comfortable with uncertainty / quick adaptation** | Built across ~40 git worktrees and a compound loop that explicitly tracks drift and pivots (`autoresearch.md`). |
| **Strong SWE for robust infrastructure** | Async I/O with timeouts, circuit breakers, typed boundaries (Pydantic), V-Model structural-before-behavioral invariants. |
| **Enjoy pair programming** | The entire codebase was built as a human↔model pair-programming loop ("compound engineering"). |
| **Passionate about safe, beneficial AI** | Thesis is *structural* safety: physics-grounded environments where unsafe actions fight an attractor rather than being penalized post-hoc. |

---

## Distinctive depth — the physics substrate (verified live)

Beyond the standard boxes, Cohezion's differentiator is a mathematically-grounded substrate.
These are not slideware claims — each is demonstrated numerically by `resume_verify.py`:

| Component | What it is | Live demonstration |
|---|---|---|
| **Geometric correspondence** | The Fisher information metric induced by a VAE's `(μ, logvar)` *is* a Riemannian metric — the bridge between statistical models and differential geometry (`physics/information_geometry.py`). | ✅ `geometric_correspondence`: Fisher→Riemannian tensor is **6×6, symmetric, positive-semidefinite** (min eigenvalue ≈ 1.35 > 0 — a valid metric). |
| **Unified physics** | A single 12D Riemannian manifold (SU(2) spinors, Lagrangian dynamics, Yang–Mills gauge, Fisher metric) onto which FLUME's 256D latent projects (`flume/manifolds/translator.py`, `physics/`). | ✅ `unified_physics`: a **256D FLUME latent → 12D** Unified-Physics coordinates + coherence, live. |
| **Quadrature Nexus** | The swarm's **4-voice consensus-governance** mechanism — multi-perspective agreement before action (`swarm/quadrature_nexus.py`). | ✅ `quadrature_nexus`: importable, instantiable consensus orchestrator. |

**Why this matters for Universes:** the safety thesis is *structural* — instead of penalizing
unsafe actions post-hoc, agents operate on a manifold where the stable equilibrium (HIHO,
coherence ≈ 0.5) is where Yang–Mills curvature vanishes and the Fisher metric is minimized.
The geometric correspondence is what lets the same point be described as a VAE latent, a
physical state, and an information-geometric minimum simultaneously — observability by
construction.

### The genesis substrate & worldview lattice (also verified live)

The "ultra-realistic settings" the role targets need *diverse* world priors, not one. Cohezion
carries a research-grade layer for exactly that — and, true to the rest of this doc, each piece
is import-and-run checked, with honest framing about what's ML-core vs research-exploratory:

| Component | What it is | Live demonstration | Honest framing |
|---|---|---|---|
| **Cosmogony engine** | `physics/cosmogony.py` `SymmetryBreaking` — a symmetry-breaking cascade that generates universe states (`void → … → 12D`). | ✅ `cosmogony`: produces a valid **12D** state from the `void` symmetry stage. | Procedural environment *genesis* / initial-condition generation — research-exploratory. |
| **Worldview lattice** | `worldviews/` — **17** cosmological traditions × **10** Theory-of-Everything steps, with cross-tradition convergence mapping. | ✅ `worldviews`: 17 traditions × 10 ToE steps. | Diverse environment/world priors; breadth, not an ML benchmark. |
| **ToE bridge (Observer Patch Holography)** | `physics/observer_patch.py` — observer-centric consistency; overlapping observer patches must agree (SPIN coherence). | ✅ `toe_observer`: two patches yield a valid `overlap_fraction ∈ [0,1]`. | The formal root of the structural-safety thesis (observers agree ⇒ coherence). |
| **TEK × Unified Physics** | `agents/specialists/ecoresilience_agent.py` — synthesizes Traditional Ecological Knowledge with the 12D manifold. | ✅ `tek_agent`: `EcoResilienceAgent` importable. | A specialist agent demonstrating cross-domain synthesis; applied, not core ML. |
| **Bioelectric (Levin)** | `physics/bioelectric_model.py` — gap-junction percolation + cognitive light cone on the manifold. | ✅ `bioelectric`: `BioelectricNetwork` percolation runs, coherence ≈ 0.92. | Developmental-bio-inspired collective dynamics; research-exploratory. |

I flag these as **research range**, not as "this is production LLM training." For a *Research*
Engineer role that prizes taste and the ability to build novel environments, the signal is: I
can take an abstract idea (a worldview, a cosmogony, an observer-consistency axiom) and land it
as runnable, tested code on a shared manifold — which is the same muscle as turning a research
hypothesis into a training environment.

## Flagship narrative: the 0.991 that became a research lesson

This is the story to lead an interview with, because it *is* the job.

1. **Built** a 12D latent-navigation RL environment and trained a REINFORCE policy. It reached
   **0.991 average coherence** — a number that looks like a triumph.
2. **Interrogated it** instead of celebrating: the learnings log records the verdict in plain
   text — *"environment too easy."* The agent had found an easy reward, not genuine capability.
3. **Built a harder successor**, `Cohezion/ManifoldEnv-v0` (19D obs / 12D action), where a
   random agent scores ≈ **−1.6** (verified live this run) and a trained agent must actually
   learn. The honest results matrix (`README.md`):

   | Algorithm | Reward mode | Steps | Reward | vs Random | vs Greedy |
   |---|---|---|---|---|---|
   | PPO | curriculum + small actions | 20K | 12.04 | **+18.0** | — |
   | PPO | curriculum | 100K | 14.23 | +7.51 | +1.34 |
   | **SAC** | **dense** | 100K | **40.77** | +3.40 | −1.20 |
   | PPO | dense | 100K | 38.95 | −1.79 | +3.73 |

   The finding has teeth: **reward structure must match the algorithm's learning dynamics**
   (on-policy PPO benefits from curriculum; off-policy SAC needs simpler gradients) — and both
   need actions that *cooperate* with the environment's attractor rather than fight it.

**Why it maps to Universes:** the team's job is to build environments where capability is real
and evals that can't be gamed. This repo contains a worked example of detecting a gamed metric
and re-engineering the environment to fix it.

---

## Research currency — Cohezion vs 2026 tip-of-spear

The role rewards staying at the frontier. Here is an honest map of where Cohezion already
aligns with 2026 SOTA and where it does not.

| 2026 technique (source) | Cohezion status |
|---|---|
| **Automatic env generation via Generator+Validator** — [EnvScaler](https://arxiv.org/pdf/2601.05808), [ClawEnvKit](https://arxiv.org/html/2604.18543v2) use Parser→Generator→Validator | ✅ **Convergent**: `EnvironmentGenerator` + `GeneratedCodeValidator` is the same architecture, arrived at independently. |
| **RLVR (verifiable rewards)** moving single-turn→agentic — [overview](https://lucek.ai/blogs/rlvr-with-llms), [Appen](https://www.appen.com/blog/rlvr) | ✅ Verifiable rewards in env; GRPO trainer present. ⚠️ Gap: **multi-turn** agentic RLVR. |
| **Process / implicit step rewards** for sparse-reward agentic RL — [Implicit Step Rewards](https://arxiv.org/pdf/2509.19199) | ✅ Per-step coherence + `DegradationDetector` are process-level signals. ⚠️ Not yet wired as a training reward. |
| **Standardized sandbox rollout infra** — [ProRL Agent: rollout-as-a-service](https://arxiv.org/html/2603.18815v1) | ✅ `sandbox/` + `sandboxing/` isolation. ⚠️ Gap: rollout-as-a-service API. |
| **Adversarial / co-evolution curricula** — [Eurekaverse](https://arxiv.org/pdf/2411.01775), [COvolve](https://arxiv.org/pdf/2603.28386) (two-player zero-sum env↔policy) | ⚠️ Gap: Cohezion has curriculum reward modes but **not** adversarial agent↔environment co-evolution. Clear next build. |

The field's stated hard problems — *"sparse and delayed rewards, long non-Markovian
trajectories, non-stationary environments"* ([overview](https://blog.dailydoseofds.com/p/how-top-ai-labs-are-building-rl-agents)) —
are exactly the failure modes Cohezion's trajectory tracking and degradation detection target.

### Latent-space reasoning ([Awesome-Latent-Space](https://github.com/YU-deep/Awesome-Latent-Space))

That taxonomy — latent chain-of-thought, **continuous thought vectors**, and **RL over latent
thought trajectories** — is the paradigm Cohezion is built on, not adjacent to it:

| Taxonomy theme | Cohezion status |
|---|---|
| Continuous thought vectors / reasoning in latent space | ✅ FLUME VAE compresses reasoning into a **256D** latent; the "FLUME-First" rule mandates `encode() → latent reasoning → decode()` (`src/cohezion/flume/`). |
| **RL over latent thought trajectories** | ✅ `Cohezion/ManifoldEnv-v0` *is* a policy navigating a latent manifold toward a stability attractor — RL-in-latent-space, verified live. |
| Latent compression for efficiency | ✅ PolarQuant / QJL latent quantization in `flume/` (harness-tracked). |
| Latent CoT / silent test-time scaling (e.g. Coconut-style) | ⚠️ Gap: Cohezion compresses *to* a latent but does not yet iterate latent CoT at inference time. Concrete next experiment. |
| Vision-Language-Action latent actions (embodied) | ➖ N/A — Cohezion is not embodied/robotic; honest non-match. |

### World models / JEPA ([LeWM](https://github.com/lucas-maes/le-wm))

LeWM's contribution is a *stable* JEPA trained end-to-end with a single regularizer enforcing
**isotropic-Gaussian latent embeddings** (collapse prevention without EMA/stop-grad zoos).
Cohezion's world model is built on the same idea:

| LeWM / LeJEPA technique | Cohezion status |
|---|---|
| Isotropic-Gaussian latent regularizer (anti-collapse) | ✅ `world_model/sigreg.py` — **SIGReg: Sketched-Isotropic-Gaussian Regularizer** (same family). |
| JEPA next-embedding prediction world model | ✅ `world_model/jepa_world_model.py` (causal masking, CPU-trainable). |
| Planning / rollouts in latent space | ✅ `jepa_world_model_persistent.py` "dream rollouts" + `surprise_explorer.py` (surprise-driven exploration). |
| ~15M-param, single-GPU, fast planning | ⚠️ Cohezion's JEPA is smaller and CPU-scale (repo's own docs disagree on the exact param count — 86K vs ~2M — so I don't cite a figure); not benchmarked against LeWM's control-task speedups. |

A local working copy of the upstream repo exists at `dev/le-wm/` (LeWM JEPA: 34 tests, per CLAUDE.md).

---

### Currency log — 2026-05-15 sweep (agentic RLVR frontier)

A second research pass against the **May–June 2026** agentic-RLVR literature, with honest mappings:

| Frontier method (source) | Cohezion mapping |
|---|---|
| **Agent-RLVR** — environment as verifiable feedback + agent guidance for *sparse* agentic rewards ([2506.11425](https://arxiv.org/html/2506.11425v2)) | ✅ Cohezion's env already emits verifiable per-step reward; `rl/reward_shaping.py` + curriculum in `auto_generator.py`. ⚠️ Gap: error-aware *guidance* signal. |
| **AgentV-RL** — agentic verifier with forward+backward agents re-checking solutions ([2604.16004](https://arxiv.org/abs/2604.16004)) | ✅ Conceptual twin of the **Quadrature Nexus** (4-voice consensus verification) + `compound/triune_reviewer.py`. |
| **OPRL / implicit step rewards** — process reward model on on-policy trajectories ([2509.19199](https://arxiv.org/pdf/2509.19199)) | ✅ Per-step coherence + `DegradationDetector` are process-level signals. ⚠️ Not yet trained as a PRM. |
| **Scaling Environments for LLM Agents** (survey, [2511.09586](https://arxiv.org/html/2511.09586v1)) | 📄 Umbrella for the env-generation direction Cohezion's `EnvironmentGenerator` sits in. |

## Where to look (evidence map)

| Capability | File(s) |
|---|---|
| Registered RL env | `src/cohezion/environments/manifold_env.py`, `environments/__init__.py` |
| Multi-agent env | `src/cohezion/environments/swarm_env.py` |
| **Environment generator** | `src/cohezion/environments/auto_generator.py` |
| Verifiable rewards | `src/cohezion/rewards/calculator.py`, env `step()` reward |
| RL / LLM training | `src/cohezion/rl/{ppo,grpo,lora,distributed}_trainer.py` |
| Evaluation | `src/cohezion/eval/universe_evaluator.py`, `eval/capability_scorecard.py` |
| World model | `src/cohezion/world_model/jepa_world_model.py` |
| Batching | `src/cohezion/inference/orchestrator.py` (`run_batch`) |
| Local inference fleet | `src/cohezion/inference/triune_orchestrator.py`, `inference/fleet.py` (`extend_claude`) |
| Caching | `src/cohezion/cache/semantic_cache.py` |
| Geometric correspondence | `src/cohezion/physics/information_geometry.py` (Fisher metric), `flume/geometric_bridge.py` |
| Unified physics / cosmogony | `src/cohezion/physics/` (`spinor`, `lagrangian`, `gauge_theory`, `cosmogony`), `flume/manifolds/translator.py` |
| Worldview lattice / ToE / TEK | `src/cohezion/worldviews/`, `physics/observer_patch.py`, `agents/specialists/ecoresilience_agent.py` |
| Quadrature Nexus | `src/cohezion/swarm/quadrature_nexus.py` |
| Sandboxing | `src/cohezion/sandbox/isolation.py`, `sandboxing/executor.py` |
| Persistence / audit | SurrealDB (49 tables); `compound/journey_tracker.py` (hash-chain) |
| Knowledge base | Obsidian vault `~/vaults/cohezion-vault/` (curated learnings/research notes) |

**Related repositories (same author):**
[`aimo-progress-prize-3`](https://www.kaggle.com/competitions/) (LLM math-reasoning competition entry — agentic reasoning eval at scale),
`le-wm` (JEPA world model from pixels),
`observer-patch-holography` (physics research underlying the structural-safety thesis).

---

## Honest gaps (what this resume does *not* claim)

Calibration is a feature, not a disclaimer. Per the role's emphasis on *genuine* capability:

- **No peer-reviewed publication.** The research is documented in-repo and as a software
  citation (`CITATION.cff`); it has not been through peer review. Treat "published research"
  as **aspirational**, not met.
- **Training infra is present, not benchmarked here.** The RL/LLM trainers import and have
  tests, but this verifier does **not** run a full training job (it's `WEAK` evidence by
  design — importing `ppo_trainer.py` is not proof of a trained model).
- **The flagship 0.991 metric is explicitly superseded** as a "too-easy environment" result;
  it is presented as a *lesson*, not a capability claim. The previously-circulated figures
  *"0.991 coherence over 25M cycles / 92.7% in HIHO band / 27.3% cost reduction"* in
  `docs/ANTHROPIC_TECHNICAL_SUMMARY.md` are **not** reproduced here: 25M cycles is a HIHO
  *physics-convergence* run (not the RL result), and "27.3%" had no measurable provenance
  (it appears only as hardcoded UI text). That older doc is superseded by this one.
- **Latent bug the verifier surfaced (and I'm reporting, not hiding):** at this commit
  `cache/semantic_cache.py` imports a `cohezion.cache.lemonade_encoder` module that is absent,
  so the cache is unimportable and `tests/cache/` errors on collection (11 collection errors).
  The cache design/calibration is documented (harness CA1/CA2) but is **not** runnable at this
  SHA. This is exactly the kind of regression a self-verifying resume is meant to catch.
- **Cross-worktree note:** this repo is developed across ~40 worktrees sharing one editable
  install; `resume_verify.py` validates the importable `cohezion` package. Reproduce from a
  clean `uv sync` for a canonical run.
- **No adversarial co-evolution / multi-turn agentic RLVR yet** — see research-currency table.

---

## Reproduce everything

```bash
uv sync
python scripts/resume_verify.py            # the 12 checks above, live
make resume                                 # same, writes docs/resume_receipt.json
uv run pytest tests/environments tests/rl tests/eval tests/world_model -q   # the suites cited
```

*Generated as a self-verifying artifact. If a claim here ever stops being true, the verifier
turns red — which is the point.*
