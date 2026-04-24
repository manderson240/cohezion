---
title: "Cohezion — PRFAQ"
date: 2026-04-23
exercise_type: working-backwards (NOT an actual launch announcement)
status: internal-discussion-document
audience: founder, technical-cofounder, first-engineering-hire, first-customer
campaign: synthetic-sniffing-panda (Wave Ω8)
generated_by: bmad-prfaq skill, autonomous mode
sources:
  - /home/mike-anderson/dev/cohezion/CLAUDE.md
  - /home/mike-anderson/dev/cohezion/.worktrees/nemotron-june/.agent/CONSTITUTION.md
  - /home/mike-anderson/vaults/cohezion-vault/learnings/INDEX.md
  - /home/mike-anderson/.claude/plans/synthetic-sniffing-panda.md
  - research/papers/physics-grounded-training-universes.md
  - research/manuscripts/2026-04-23-flume-vae-compositional-latent.md
disclaimer: |
  This document is a Working-Backwards exercise generated as a forcing
  function for product clarity. Cohezion is currently a single-developer
  research codebase. Nothing herein constitutes an offer, a roadmap
  commitment, a public announcement, or pricing guidance. The "press
  release" framing is hypothetical. The "Internal-only addendum" is the
  true output of the exercise.
---

# PRESS RELEASE

## Cohezion launches today: a physics-grounded compound-engineering substrate for self-improving AI agents

**FOR IMMEDIATE RELEASE — 2026-04-23 (HYPOTHETICAL)**

Cohezion, a research project incubated on a single AMD Strix Halo workstation, today released the first public version of its compound-engineering platform: an end-to-end agent runtime that treats every interaction as a point in a continuous latent geometry, governs agent autonomy through a graduated cosmogonic trust ladder, and refines its own skill library between requests. Cohezion is built for engineers who run long-horizon AI workflows on local hardware, who are tired of agent frameworks that forget everything between sessions, and who want a system that gets demonstrably better the more they use it — not one that costs more for the same answer next month.

What Cohezion ships:

- A **compound execution loop** in which every completed request encodes its context into a 256-dimensional FLUME VAE latent, deposits it into a SurrealDB-backed semantic cache, and uses it to short-circuit similar future requests; the project reports a 95%-plus L2 cache hit rate on its internal benchmark.
- A **physics-grounded agent state space** — a 12-dimensional Riemannian manifold with Lagrangian dynamics, Yang-Mills gauge coupling, and a single attractor at 0.5 coherence (the "HIHO" point) where six independent mathematical frameworks converge. Agent unsafe behaviour is suppressed structurally rather than by post-hoc rule, because reward-hacking the manifold means violating conservation laws.
- A **cosmogonic autonomy ladder** that maps the SO(12) → SO(3)⁴ → U(1)⁴ → Z₂⁴ → HIHO symmetry-breaking chain to five graduated agent trust tiers (Observe → Edit → Commit → Deploy → Sovereign), each gated on five consecutive coherence checks above its threshold and demoted on three failures.
- A **70/20/10 cost-routing fleet** built on Lemonade-first local inference (NPU/GPU/CPU hot-swap on Strix Halo), with budget enforcement, model-quality classification, and a documented escalation path through Ollama Cloud, Anthropic Sonnet, and Anthropic Opus when the local fleet's quality gates fail.
- A **Constitution-bound governance layer** that adopts the January 2026 Anthropic Constitution as its baseline and overlays compound-engineering directives — total artifact persistence, idempotent abstractions, journey persistence, structural-before-behavioural verification — through a hash-chain audit trail in SurrealDB.

"What I wanted was a development environment in which the AI tooling stops forgetting what we did yesterday," said the project's sole maintainer in an internal note. "What I built is a substrate where every prior conversation, every refined skill, and every diagnostic trace lives in the same continuous geometry that the agent reasons over today. The point of the FLUME latent isn't to generate text — autoregressive transformers already do that. The point is to give the agent a *shape* for its own history."

Three concrete use cases visible in the public commit history:

- **Multi-wave parallel-agent polish campaigns.** A 17-hour-budgeted code-quality campaign ("synthetic-sniffing-panda") completed in 2.81 wall-clock hours by orchestrating 5 waves of 3-6 parallel sub-agents under hard inter-wave verification gates. Output: 74 commits, ~100 GB of disk reclaim staged for user approval, lint and bare-except counts cut in half on the targeted modules, a learnings INDEX consolidating 167 documented learnings across 4 source files, and a final retrospective written to vault. The orchestrator pattern itself was extracted into a reusable skill at session end — a literal compound-engineering loop closure.
- **Kernel-optimisation exploration on AMD MI355X.** Cohezion's compound loop wrapped the Luma AMD Speedrun competition workflow: the K-Search planner generates Triton/HIP kernel candidates, the Popcorn submission harness benchmarks them, results feed back as Learning records (L244-L269 in the public learnings index), and the next iteration's planner reads those learnings as context. Twenty-five distinct learnings were extracted from 87 development sessions in this loop alone.
- **Physics-grounded RL agent training.** The ManifoldEnv (Gymnasium-compatible, 19D observation) and SwarmEnv environments reproducibly demonstrate that random agents converge toward HIHO 20% of the time with no learned policy — the manifold itself guides them — while PPO with action scale matched to the dynamics timescale (small actions, [-0.1, 0.1]) reaches reward 12.04 versus a random baseline of -6, on the 7-run diagnostic loop reported in the project's training-universes paper.

"Compound engineering is the bet that the right substrate accumulates value with use, instead of decaying with it," said the project's research lead (also the maintainer; the project is currently a one-person outfit, an honesty caveat carried through this entire document). "Cohezion is a working hypothesis about what that substrate looks like: a continuous latent for context, a physical manifold for state, a graduated autonomy ladder for trust, and a self-extending skill library for capability."

Getting started: Cohezion is open-source under a permissive licence on GitHub (`manderson240/cohezion`), runs end-to-end on a single AMD Strix Halo workstation (Ryzen AI MAX+ 395, 128 GiB unified memory, Radeon 8060S iGPU), and exposes its compound loop through a documented FastAPI surface (92 route handlers, 45 model profiles, six FLUME endpoints). The project does not currently offer a hosted product, professional support, or an SLA. It does offer a ~6,100-test test suite, a documented 11-step executor pipeline, and a complete vault-first knowledge accumulation system that is itself the most concrete demonstration of the platform's compound-engineering thesis.

---

# FAQ

## For users / customers

### Q: What does Cohezion do?

A: Cohezion is the runtime, the memory, and the governance layer for AI agents that run long-horizon engineering workflows. Concretely: it takes a request (a prompt, a skill invocation, a user instruction), encodes it into a 256-dimensional FLUME latent, checks a three-tier semantic cache for a matching prior, executes through an 11-step orchestrator if no hit, persists the entire trajectory (request, plan, tool calls, outputs, internal state, model-routing decision, cost) to SurrealDB, refines the responsible skill from the trajectory's outcome, and updates the latent population with the new point. The next request that lands inside that latent's neighbourhood reuses the prior work. The system that has handled a thousand requests is structurally different from — and demonstrably more capable than — the system that has handled ten.

### Q: How is this different from LangChain, CrewAI, AutoGen, or other agent frameworks?

A: Three differences carry most of the weight.

**Compound state.** LangChain, CrewAI, and AutoGen orchestrate calls. Cohezion is a substrate: every call deposits structured state into a continuous geometry that the next call reads from. They treat memory as a textual scratchpad or vector-RAG side index. Cohezion treats memory as an addressable latent whose *shape* the executor reasons over.

**Physical structure for safety.** Competing frameworks use rule-based safety (deny-lists, filters, classifiers) or post-hoc evaluation. Cohezion embeds agent state in a manifold whose attractor is, by mathematical construction, the safe equilibrium. An agent cannot reward-hack the Lagrangian; equations of motion are determined by the metric, not the policy. This is a structural layer underneath other safety layers, not a replacement for them.

**Cosmogonic autonomy.** Most frameworks bind permissions statically. Cohezion gates capability promotion on coherence-stability statistics — five consecutive checks above threshold to advance, three failures to demote. Agents earn commit/deploy/sovereign rights through demonstrated stability, not a config flag. Enforced by AutonomyEngine, observable in JourneyTracker's bi-temporal SurrealDB schema.

### Q: Why "compound engineering"?

A: The phrase comes from a single design principle, codified as Compound Engineering Principle #1 in the Constitution: *every feature created makes every new feature easier to achieve*. Compound engineering is what you get when you take that principle seriously and build an execution loop around it. The FLUME latent is a compound artifact (each deposit improves nearest-neighbour retrieval). The skill library is a compound artifact (each refinement improves the next refinement). The Learning index is a compound artifact (each L-number cited makes the next session faster to onboard). The phrase compresses what would otherwise be a long list of concretely compounding subsystems.

### Q: What's the pricing model?

A: For this exercise we propose a three-tier model — but be aware no version of this is presently offered, this is not a roadmap commitment, and the project's actual present state is "single-developer research repo on GitHub." The notional tiers:

- **Open-source core** (free, MIT-style): the executor, FLUME VAE, ManifoldEnv/SwarmEnv, the cost-aware router, the SurrealDB schema, the FastAPI surface. Run it on your own hardware. Nothing is held back.
- **Hosted vault** (paid, per-seat or per-GB): managed SurrealDB persistence, hosted FLUME endpoints, automatic vault sync across machines. The motivation is that the compound-engineering value comes from the accumulated latent population; making that durable and team-shareable is the natural service.
- **Support and integration tier** (paid, custom): help integrating Cohezion into an existing engineering organisation, custom skill development, custom MCP server bring-up, on-premise deployment assistance.

The honest answer is that no pricing has been validated against any prospective customer. This is a forcing-function exercise.

### Q: What hardware do I need?

A: Cohezion is designed end-to-end for **AMD Strix Halo** (Ryzen AI MAX+ 395, 16C/32T, integrated Radeon 8060S iGPU, 128 GiB unified memory). The hardware truth-anchor doc is explicit that the entire compound loop, including FLUME training, must fit inside this envelope — datacentre-class accelerators are **excluded** as a hard constraint.

It also runs on standard x86_64 Linux with any PyTorch-supported GPU, or CPU-only (FLUME and JEPA are both small enough). Performance differs. Cost routing degrades gracefully: Lemonade-first local is the optimisation; Ollama Cloud (~$20/mo) and the Anthropic API are documented fallbacks.

### Q: How long until I see value?

A: First benefit (semantic-cache hits on near-duplicate requests): within the first dozen interactions. Second (skill refinement from observed trajectories): a day or two of moderate use. Third (physics-grounded RL policies that generalise beyond reward-only training): a research investment, not an out-of-the-box win.

Honest framing: Cohezion is a substrate that compounds. Day one looks like every other agent framework. Day thirty, if the substrate is working as designed, looks meaningfully different.

### Q: Can I use my own models?

A: Yes. The CostAwareRouter in `src/cohezion/swarm/cost_aware_router.py` is YAML-profile-driven (45 model profiles in the snapshot under study) and supports Lemonade local-inference (with NPU/GPU/CPU hot-swap on Strix Halo via `LemonadeAdapter`), Ollama Cloud, the Anthropic API, and any OpenAI-compatible HTTP endpoint. The 70/20/10 split (70% simple to local/free, 20% medium to Sonnet, 10% hard to Opus) is a default tier curve, not a hard wiring.

### Q: Does Cohezion work with Claude Code, Cursor, Cline, or other IDEs?

A: Cohezion exposes capabilities through MCP servers (`cloud-vault-mcp`, `compound-mcp`, `maintenance-mcp`) and is consumed by Claude Code in the maintainer's daily workflow. Cursor, Cline, GitHub Copilot, and Gemini CLI integrations are partial (BMAD multi-IDE work, Learnings 371-376); production-ready cross-IDE is roadmap, not shipped.

## For engineers

### Q: What's the architecture?

A: A compound execution loop around a typed agent state space, persisted in a temporal database, governed by a graduated autonomy ladder, instrumented end-to-end.

**Loop**: 11 steps in `src/cohezion/compound/executor.py` — instruction expansion, plan generation, request alignment, metrics aggregation, degradation detection (with router feedback), journey tracking (12-D position + JEPA surprise + bioelectric percolation), Ouroboros physics-coherence check, Mycelium pattern capture, retrospection, skill refinement, consensus voting. Each step is observable, idempotent, SurrealDB-persisted.

**State space**: 12-D Riemannian manifold, metric `g = diag(1.0×3, 0.7×3, 0.5×3, 0.3×3)` across space/field/control/precipitation fabrics. Euler-Lagrange dynamics under a HIHO Gaussian attractor; symplectic Störmer-Verlet integration.

**Persistence**: SurrealDB on SurrealKV (port 8001, localhost-only, `?versioned=true` for temporal queries). Bi-temporal schemas on neurons/journey/universe_node. V-Model gate tables (vmodel_gate, traces, hash_chain, proof_obligation) for audit.

**Cost**: CostAwareRouter (45 profiles, Lemonade-first), BudgetEnforcer (monthly hard-stop), ModelQualityClassifier. Cheap-first, escalate on quality-gate failure.

**Web**: Next.js 16 + Three.js + Tone.js (`src/web/anima_dashboard`); `/genesis` route renders the manifold, FLUME latent (PCA-3D), swarm topology, journey trajectories.

### Q: Is this production-ready?

A: No. Honestly: no.

The project has approximately 6,133 collected tests. The full suite completes without crash. Coverage on the 5 highest-stakes files was lifted to 50% or above as part of Wave 3 of the synthetic-sniffing-panda campaign (April 23, 2026). Lint count was cut by approximately 40% in the same campaign. Bare-except violations were cut by more than 50%. mypy is now installed and a baseline error count exists, with a strict carve-out list maintained in `pyproject.toml`.

These are real numbers from a real cleanup. They are not the numbers of a production system. The project is a single-developer research codebase. There is no SLA. There is no support contract. There is no commercial offering. There is no second engineer reviewing pull requests. The CLAUDE.md project file is explicit about this and the constitution prioritises honesty above helpfulness.

Use Cohezion if you want to study a working compound-engineering substrate, contribute to one, or fork one. Do not use Cohezion if you need a vendor relationship and a phone number.

### Q: Open source?

A: Yes. Repo at `github.com:manderson240/cohezion` (Git LFS active, 182 MB bundle, 46 LFS-tracked binaries). Licence intended to be permissive (MIT or Apache 2.0) — verify against the actual `LICENSE` file before redistribution; this exercise asserts no specific text. Several integrated components carry their own licences (Apache 2.0 for `observer-patch-holography`, A2UI, AG-UI; CC0 for the Anthropic Constitution baseline), credited in CLAUDE.md.

### Q: How do you handle prompt injection?

A: A `prompt-injection-guard` skill wraps externally-sourced text (GitHub issues, PR bodies, web fetches, user content) in delimiters before LLM interpolation; the LLM treats delimiter-wrapped content as data, not instruction. Verification-before-completion rules require running the agent against adversarial inputs on any prompt-construction change. The Constitution adds a layer: agents prioritise broadly-safe behaviour above operator instruction and refuse instructions originating from untrusted text masquerading as operator input. Both layers are partial. We do not claim to have solved prompt injection.

### Q: How do you control cost at scale?

A: Three layered mechanisms. (1) The **70/20/10 tier curve** in `CostAwareRouter`: 70% of requests to Lemonade local (free, 3-slot NPU/GPU/CPU hot-swap), 20% to Sonnet (~$3/M), 10% to Opus (~$15/M). Per-profile override. (2) The **BudgetEnforcer** logs token usage by skill/agent/tier and refuses (not falls back) on monthly budget crossing. (3) The **degradation feedback loop**: `DegradationDetector` CRITICAL alerts force the next N queries up a tier via router callback. Spend more when quality is failing, less when it isn't.

### Q: What's the data model?

A: SurrealDB with bi-temporal schemas. Six "Genesis tables" added in Session 74: `journey_transitions`, `universe_snapshots`, `prompt_artifacts`, `model_artifacts`, `simulation_artifacts`, `internal_state_snapshots`. V-Model audit tables added in Session 96b: `vmodel_gate`, `traces`, `hash_chain`, `proof_obligation`. Hash-chain audit trail in JourneyTracker mitigates the OLIF (observable-lineage-integrity-failure) class of attacks documented in Learning 304-309.

Total Artifact Persistence is Compound Engineering Principle #8: nothing is ephemeral. Prompts, responses, internal states, model checkpoints, simulation runs, all written to SurrealDB. The cache replay protocol guarantees that on SurrealDB reconnect after offline, all cached writes from the local fallback store replay deterministically.

### Q: How do skills work?

A: A skill is a markdown file with PRIME-format frontmatter, indexed by the SkillRegistry. Snapshot: 235 in `src/cohezion/skills/` (215 PRIME), plus mirrors in `~/.claude/skills/` (44) and the vault (~246 PRIME). Wave 4C of synthetic-sniffing-panda produced `skills/CONSOLIDATION_REPORT.md` with per-skill keep/merge/delete decisions awaiting approval.

Skills invoke through the executor. Trajectories record; at session end, SkillRefiner proposes an updated definition; SkillConsensusVoter validates against multiple agents before commit. This is the inner compound loop. The registry is vault-first — the canonical source for any skill is the vault copy; project copies are derived.

## For investors / decision makers

### Q: What's the market?

A: Engineering orgs spending on AI agent infrastructure. Three signals.

(1) **Agent frameworks** (LangChain/CrewAI/AutoGen/Semantic Kernel) — paid demand for runtime orchestration. Cohezion competes here as a substrate, not a framework. (2) **Local AI inference** (Ollama, Lemonade, llama.cpp) — enterprise demand for sovereignty + cost control. The Lemonade-first router is built for that customer. (3) **AI observability/governance** (Arize, W&B, Helicone) — demand for trajectory recording + audit. Hash-chained SurrealDB persistence is built for that customer.

Honest framing: Cohezion has not validated demand in any of these markets directly. The exercise is to identify the strongest wedge.

### Q: What's the moat?

A: Three candidates, in decreasing order of confidence.

**Most defensible — the compound-engineering loop itself.** A semantic cache that grows with every interaction, a self-refining skill library, a 167-entry learnings index across 87 sessions: not a feature competitors can ship in a month. Forking gets you the substrate, not the accumulated state. Running it 30 days produces a different system from the one you started with.

**Second — the physics-grounded state space.** The HIHO attractor on a 12-D Riemannian manifold is a research bet; in-tree results hold for ManifoldEnv/SwarmEnv. If it generalises, structural safety competitors cannot reproduce. If not, the loop and cost router survive — the physics layer is severable.

**Most speculative — the cosmogonic autonomy ladder.** Mapping symmetry-breaking stages to graduated trust is genuinely novel: an 8-query × 7-database SLR found 0 systems combining 3+ of the relevant components (Learning 327). Whether customers value it is unproven.

### Q: Who's the customer?

A: The candidate persona that fits the present codebase most cleanly: the **principal engineer running long-horizon AI workflows on local hardware**, who is already running Claude Code or equivalent and is hitting two specific frustrations — cost spend on duplicated work, and capability decay across sessions because the AI tooling forgets context. This person is technically able to install and operate Cohezion, has the hardware to run the local fleet (Strix Halo or equivalent, or willingness to use Ollama Cloud as a substitute), and has enough engineering judgement to evaluate whether the compound-loop thesis is paying off in their workflow.

The candidate persona that does NOT fit: the engineering manager looking to roll out AI tooling to a 50-person team. Cohezion is not packaged for that. The vault sharing model, the multi-user authentication story, and the centralised cost controls are not built.

### Q: What's the competition?

A: Direct: LangChain, LlamaIndex, CrewAI, AutoGen, Semantic Kernel. All are agent frameworks; all treat memory as either textual scratchpad or vector-RAG side index. None of them, to our knowledge, ship a compositional latent VAE as the addressable substrate.

Adjacent: MemGPT (virtual-memory paging of textual context), Generative Agents (reflection-summarised text memory), Voyager (executable skill library indexed by natural-language description), ReAct, Reflexion. Distinct designs for the agent-memory problem; none use a continuous latent geometry.

Local-inference adjacent: Ollama, Lemonade, llama.cpp + LangChain stacks. Cohezion uses Lemonade as its preferred local backend and is not a competitor — it sits above.

Hosted-agent platform adjacent: OpenAI Assistants, Anthropic Workbench, Google Vertex AI Agents. These are managed services; Cohezion is presently a self-hosted substrate. Different category of buyer.

### Q: Risks?

A:

1. **Single maintainer.** The project has one developer. Bus factor is one. There is no second engineer reviewing pull requests, and the volume of code, documentation, and architectural commitment is large for one person to defend long-term.
2. **Hardware concentration.** End-to-end design targets AMD Strix Halo. Most prospective customers do not have Strix Halo. Cloud and CPU fallbacks exist but are second-class.
3. **The physics layer is a research bet.** If HIHO does not generalise beyond the constrained ManifoldEnv setting, the marketing-claim about "structural safety" weakens. The compound loop and cost router survive the physics layer being wrong; the differentiation story does not.
4. **Branding.** "Cohezion" is the codebase name. Whether it is also the product name is unresolved. The phrase "compound engineering" is the strongest branding asset; "Cohezion" itself is unfamiliar and easily confused with "Coherence" or "Cohesion-with-an-S".
5. **Open-source business model risk.** Open-core models are difficult to monetise without aggressively gating critical features. The proposed hosted-vault tier needs validation against real customer willingness-to-pay.
6. **Constitution dependency.** Cohezion adopts the January 2026 Anthropic Constitution as a baseline. If Anthropic changes that document, downstream Cohezion governance text needs to track. This is solvable but is a non-trivial maintenance commitment.

---

# Internal-only addendum

## Hardest objections (steel-manned)

### 1. "This is just a research project with delusions of grandeur."

**Steel-manned**: A 6,100-test test suite, a 92-route FastAPI surface, and a documented 11-step executor do not by themselves constitute a product. Many research codebases have impressive surface areas and zero customers. The compound-engineering loop is plausibly a real innovation, but a real innovation buried in a research codebase is not an asset until someone outside the maintainer can run it and benefit.

**Counter**: The honest counter is partial. Yes — Cohezion is a research codebase. The PRFAQ is intentionally framed as a hypothetical launch. The point of the exercise is to identify what would have to be true for the codebase to *become* a product. The compound-engineering loop, the FLUME latent, the cost router, and the SurrealDB persistence are real, working subsystems with test coverage; the productisation work is largely packaging, documentation, and finding the wedge customer. The accumulated learnings (167 documented L-numbers) and the 87-session execution history are themselves the most concrete demonstration that the substrate compounds — that's not a delusion, that's a measurable artifact in the vault.

### 2. "Compound engineering is a vague term — what's the user actually doing?"

**Steel-manned**: "Every feature makes future features easier" is an aspirational statement, not a UX. Users do not see "compound engineering"; they see prompts and responses. If the term cannot survive translation into a concrete user-facing workflow, it is marketing.

**Counter**: The concrete user-facing workflow is: run an agent loop against Cohezion, observe that the second time you ask a similar question, the cost and latency drop because the FLUME latent matched a prior; observe that skills used during your first session are refined automatically before your second session; observe that learnings extracted from your debugging trail are available as cited references in subsequent sessions. None of this requires the user to know the phrase "compound engineering." That phrase is the explanation of *why* the workflow has these properties, not the workflow itself. The objection is fair as a marketing critique. The reframe: lead with the observable outcomes (lower cost over time, retained context across sessions, self-refining skills), keep "compound engineering" as the technical-buyer story.

### 3. "Why should I trust an agent that 'evolves' itself?"

**Steel-manned**: Self-modifying agents are an alignment hazard. The SkillRefiner that updates its own skill definitions is precisely the surface area where an agent could drift away from operator intent without anyone noticing.

**Counter**: Three structural mitigations are already built. First, the Constitution sits above the SkillRefiner; refined skills cannot violate hard constraints without being rejected by the SkillConsensusVoter. Second, the SkillConsensusVoter requires multi-agent agreement before a refinement commits — an adversarial review layer, not a single-agent self-edit. Third, the cosmogonic autonomy ladder gates the SkillRefiner's effective authority on coherence-stability statistics — a refiner whose recent work has destabilised coherence is automatically demoted before it can do further damage. None of this is a perfect defence. It is a layered one.

### 4. "The hardware constraints (Strix Halo) are a non-starter for most users."

**Steel-manned**: A product whose default deployment requires a specific AMD workstation that costs ~$3,000 and is not available everywhere is a niche product by construction. The total addressable market is small.

**Counter**: The Strix Halo target is a design constraint of the maintainer's actual hardware, not a marketing requirement of the platform. Cohezion runs end-to-end on commodity x86 with any PyTorch-supported GPU, on CPU only (the FLUME and JEPA models are intentionally small enough), or on Ollama Cloud (~$20/month). The Strix Halo target is the *optimisation* surface; the cost router degrades gracefully. The marketing claim should be "designed for sovereignty on local hardware, runs anywhere"; the Strix Halo specifics belong in a hardware-tuning appendix, not on the homepage.

### 5. "Open-source frameworks already do most of this."

**Steel-manned**: LangChain has 80,000+ stars. CrewAI has growing adoption. AutoGen has Microsoft behind it. Whatever Cohezion does, the prospective customer's reasonable first move is "can I do this with LangChain?" If the answer is "mostly yes plus some glue code," the differentiation collapses.

**Counter**: The honest comparison: LangChain orchestrates agent calls; Cohezion is the substrate underneath the orchestration. You can run LangChain on top of Cohezion (the cost router and the SurrealDB persistence would be useful); you can not get the FLUME latent, the physics-grounded state space, or the cosmogonic autonomy ladder out of LangChain at all. The relevant question is whether the prospective customer values those three additions enough to take on a less-mature substrate. For most customers today, the answer is no. For the customer who is hitting the limits of LangChain — who is feeling the pain of textual-memory drift, of cost-spend on near-duplicate work, of opaque agent autonomy — the answer might be yes. The wedge is narrow; that is also where products start.

## Decisions to make before a real launch

1. **Licence model.** MIT vs Apache 2.0 vs custom. Pick one and write it into `LICENSE`. The current `LICENSE` file should be audited explicitly before any "open source" claim is made publicly.
2. **Hosted vs self-hosted-only.** Building a hosted vault doubles the engineering surface area. Decide whether it is the v1 wedge or a v2 add-on. Most likely v2.
3. **Branding.** Is the product name "Cohezion" (codebase) or something else? "Compound" is taken; "Coherence" is taken; "Anima" is the dashboard name and is unclaimed and arguably a stronger consumer name. This needs a brand-design pass.
4. **First persona / first wedge.** The principal-engineer-on-Strix-Halo persona is the most natural first customer (it is, after all, the maintainer's own profile). But it is also a market of N≈1 unless broadened. Decide whether to broaden to "principal engineer running local AI agents on any hardware" (larger market, weaker differentiation against Ollama+LangChain stacks) or stay narrow.
5. **Constitution-tracking commitment.** Document the cadence at which Cohezion governance text will track Anthropic Constitution updates. Without this commitment, the safety-claim has unclear shelf life.
6. **Multi-IDE story.** BMAD multi-IDE coordination (Learnings 371-376) is in progress. Decide whether v1 ships with Claude Code only (cleanest), or attempts cross-IDE (broader reach, much larger surface area).

## What this PRFAQ exercise revealed

### 3 things about Cohezion that are UNDER-claimed

1. **The vault-first knowledge accumulation system is itself the strongest demonstration of the compound-engineering thesis, and it is buried in CLAUDE.md as a footnote.** 167 documented learnings, an INDEX file built in a 2.81-hour campaign, cross-references between vault/CLAUDE.md/code — this is not a side-effect of the platform, this *is* the platform working on its own development. The product story should lead with "we used Cohezion to build Cohezion and here is the compounding artifact" instead of mentioning it in passing.
2. **The 7-run training-diagnostic loop in the Universes paper is a complete reproducible result that contradicts a default RL assumption.** Random agents converging 20% of the time on a Riemannian manifold *because of the manifold*, not because of policy, is a publishable finding. The PRFAQ buries this in a use-case bullet. It should be the headline feature for the safety story.
3. **The 17-hour-budgeted campaign that completed in 2.81 hours via parallel-agent orchestration is a demo-ready product story.** "Tell Cohezion what you want done in N hours, it spawns agents to do it in a fraction of that time, it audits its own output, it writes you a retrospective." That is a product. It is also already implemented (`polish-campaign-orchestrator` skill). It is not currently positioned as one.

### 3 things that are OVER-claimed (need walking back before going public)

1. **"95%+ semantic cache hit rate"** — this number appears in CLAUDE.md but the FLUME VAE manuscript is explicit that quantitative validation is pending. The 95% figure is reported from the SemanticCache test suite's own narrow benchmark, not from end-to-end production traffic. Public claim should be "designed for high cache hit rate; validation against production workloads in progress."
2. **"Production-ready" implication anywhere in the press release.** The honest position from the Internal FAQ is "single-developer research codebase, no SLA, no support contract, no second reviewer." The press-release framing flirts with implying more than that. Either explicitly carry the research caveat into the press release, or do not write the press release until the system is productised.
3. **The "structural safety" claim from the physics layer.** The HIHO attractor convergence is real for the ManifoldEnv setting; the *generalisation* to arbitrary agent tasks is unproven. CLAUDE.md and the Constitution claim "safety emerges from structure"; the manuscripts are more honest, noting that "the compound engineering loop has been validated in software engineering tasks; generalization to other domains is an open question." Public claims should track the manuscripts, not the marketing.

### 3 things that are MISSING (would need to build before launch)

1. **A 5-minute getting-started experience.** A new user cloning the repo and running `make install && make demo` should hit a working FLUME-cached agent loop within five minutes. The current bring-up requires reading CLAUDE.md (~26 KB), installing Lemonade, configuring SurrealDB, understanding the Compound Loop, and authoring a first PRIME skill. That is a research-codebase onboarding experience, not a product onboarding experience.
2. **A second engineer reviewing pull requests.** The bus factor is one. Recruiting, hiring, or partnering to bring in a second person who can defend the codebase is the single highest-leverage productisation step. Without it, every other commitment in this PRFAQ is fragile.
3. **A multi-user / team-collaboration model for the vault.** The vault-first knowledge architecture is the strongest compound-engineering demonstration but it is single-user by construction. Two engineers running Cohezion against the same codebase today have two parallel vaults that never merge. A merge-aware vault (or a hosted vault that handles the merge) is the natural product expansion and is presently unbuilt.

---

*End of document. ~4,970 words. Generated 2026-04-23 as part of the synthetic-sniffing-panda Wave Ω8 PRFAQ exercise. Not an actual launch announcement.*
