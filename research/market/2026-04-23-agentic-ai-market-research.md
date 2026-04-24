---
title: "Agentic AI & Compound Engineering — Market & Domain Research (April 2026)"
date: 2026-04-23
campaign: synthetic-sniffing-panda Ω13
researcher: bmad-market-research + bmad-domain-research
audience: cohezion strategic decisions
sources_methodology: |
  WebSearch (10 queries, April 23, 2026) cross-referenced with Context7 library
  metadata for LangGraph (1,252 indexed snippets, benchmark 87.55) and review of
  the cohezion PRFAQ at research/prfaq/2026-04-23-cohezion-prfaq.md and
  CLAUDE.md "Architecture at a Glance" / "Agent Protocol Stack" sections.
  Where claims could not be independently verified within the search budget,
  they are flagged [pending verification]. URLs include date-accessed = 2026-04-23.
---

# Executive summary

The agentic-AI substrate market entered 2026 having consolidated around four open-source orchestrators of meaningful scale (LangGraph, CrewAI, the new Microsoft Agent Framework which absorbed AutoGen + Semantic Kernel, and the OpenAI Agents SDK which absorbed Swarm), one rapidly-rising hosted-runtime entrant from Anthropic (Claude Managed Agents, GA April 8, 2026), and a handful of specialist plays on the memory axis (Letta/MemGPT, Mem0, Zep). The compound-engineering thesis — that each interaction should make the next one cheaper, faster, and better — has crossed from academic curiosity into mainstream developer vocabulary, primarily through Kieran Klaassen's Every.to articles, the EveryInc "compound-engineering-plugin" for Claude Code, the BAIR "shift to compound AI systems" essay (Zaharia et al.), and Stanford NLP's DSPy v2.5 + GEPA optimizer. Cohezion is unusual in three respects: (1) it ships the loop as the *primary* product surface rather than as a side effect of agent execution; (2) it embeds agent state in a continuous Riemannian manifold with a mathematically-derived safe attractor instead of relying on rule-based safety; and (3) its memory substrate is a 256-D variational latent (FLUME) rather than a textual scratchpad or a vector index.

Top three competitive threats: **LangGraph** (sheer mass — 126K+ stars, ~400 enterprise deployments, NVIDIA partnership, deep observability via LangSmith); **Anthropic Claude Managed Agents** (subsumes the runtime layer that cohezion competes on, at $0.08/session-hour); **EveryInc Compound Engineering Plugin** (the phrase "compound engineering" is being claimed by another OSS project that ships a Claude Code plugin today, while cohezion still ships only the substrate).

Top three unmet needs cohezion is well-positioned to address: **(a) audit-grade observability with hash-chained provenance** for regulated industries — most observability platforms record but don't seal the trail; **(b) sovereignty-by-default local-fleet routing** with graceful cloud escalation — prevailing routers are cloud-first with local as fallback; **(c) loops that compose memory, skill refinement, and cost routing into a single substrate** rather than three bolt-on tools.

Top three risks: (a) Anthropic Managed Agents subsumes the runtime layer and the wedge collapses to "self-hosted alternative" with thin pricing power; (b) the term "compound engineering" gets owned by EveryInc/Klaassen and cohezion's branding asset evaporates; (c) the physics-grounded state space remains unverified outside the constrained ManifoldEnv setting and the structural-safety claim cannot be defended against scrutiny.

# 1. Domain map

## 1.1 The agentic-AI stack (layers)

The market has stratified into five recognisable layers as of April 2026, with most products spanning two adjacent layers:

| Layer | Function | Representative incumbents (April 2026) |
|---|---|---|
| **L1: Foundation models** | Reasoning + tool-use primitives | Claude Opus/Sonnet 4.7, GPT-5, Gemini 2.5, Llama 4, DeepSeek-R1 |
| **L2: Agent orchestration** | Plan, route, hand-off, retry | LangGraph, CrewAI, Microsoft Agent Framework, OpenAI Agents SDK, Claude Agent SDK |
| **L3: Skill / capability libraries** | Reusable, composable agent capabilities | Anthropic Agent Skills (markdown + frontmatter), Voyager-derived skill stores, EveryInc Compound Engineering plugin |
| **L4: Observability + governance** | Trace, score, audit, replay | Langfuse, LangSmith, Helicone, Arize/Phoenix, Braintrust, Maxim AI |
| **L5: Substrate / compound systems** | Closed-loop self-improvement, latent memory, audit-graded persistence | Letta (memory-as-OS), Zep / Mem0 (graph memory), DSPy + GEPA (program-level optimisation), **cohezion (the only one combining all four into one stack)** |

L5 is where cohezion claims to live. The category is real (Berkeley AI Research formally named it in February 2024; the Databricks "Compound AI Systems" glossary is now a standard reference) but is not yet served by a single integrated product — it is served by adjacent tools that customers stitch together.

## 1.2 The compound-engineering thesis

**Proponents** are now mainstream. Kieran Klaassen at Cora / Every.to has done more than any single voice to popularise the phrase, with a podcast tour through early 2026 and the EveryInc OSS plugin for Claude Code, Codex, and Cursor. The plugin codifies Klaassen's "Plan → Work → Review → Compound" four-step loop. LangChain's own blog has adopted "agentic engineering" and describes swarms-of-agents in production. Lethain (Will Larson) wrote a measured analysis of Every's results: a single developer can plausibly do the work of five developers a few years ago.

**Skeptics** include those pointing out that the term collapses several distinct phenomena (RAG, prompt optimisation, skill caching, code generation) under one branding label. The BAIR essay framed it as "compound AI systems" precisely to keep it as an architectural pattern rather than a methodology.

**Evidence base**: DSPy + GEPA shows reflective prompt evolution outperforming reinforcement learning on several benchmarks (Agrawal et al., 2025); the Self-Improving Coding Agent paper (SICA, arXiv 2504.15228) shows 17% → 53% on SWE-Bench Verified after self-edits; Voyager's original skill-library result remains foundational; ICLR 2026 has a dedicated workshop on Recursive Self-Improvement (April 26-27, 2026, Rio de Janeiro). A March 2026 Medium piece on "Reflective and Self-Improving Agents" surveys the design pattern. The thesis is no longer fringe.

## 1.3 Multi-agent orchestration patterns

| Pattern | Canonical example | Trade-off |
|---|---|---|
| **Sequential pipeline** | LangChain LCEL, CrewAI sequential process | Predictable, composable; brittle to unexpected outcomes |
| **Graph-based** | LangGraph, Microsoft Agent Framework (workflow), LlamaIndex AgentWorkflow | Rich control flow; verbose for simple cases |
| **Conversation-based** | AutoGen GroupChat (now Magentic-One in MAF), CrewAI hierarchical | Emergent collaboration; cost-control hard |
| **Vote / consensus** | Cohezion SkillConsensusVoter, MAR (Multi-Agent Reflexion, 2025) | High trust; expensive token-wise |
| **Tool-use loop** | Claude Agent SDK, OpenAI Agents SDK, Letta v1 agent loop | Simple mental model; constrained to single-agent paradigm |
| **Manager-worker delegation** | CrewAI hierarchical, Microsoft MAF handoff | Clear authority; scales poorly past N≈10 |

Cohezion's default execution path is a hybrid: a single-agent tool-use loop wrapped in an 11-step compound pipeline, with vote-based skill refinement at session end. That choice is unusual. Most frameworks pick one pattern and let the user compose multiples.

# 2. Competitor analysis

## 2.1 LangChain / LangGraph

**What it is**: LangGraph (released 2024) is a low-level orchestration framework for building stateful agents as directed graphs with typed state, durable execution via checkpointing, streaming, and human-in-the-loop capabilities. Latest version is **1.1.6** (April 10, 2026 per agentframeworkhub.com), with v1.1.3 having shipped "Deep Agents" (planner + subagent + filesystem) and distributed runtime. LangChain itself remains the higher-level building-block library on top.

**Adoption signals (April 2026)**:
- LangChain main repo: ~127K GitHub stars, 20.9K forks, ~3,897 contributors (per teqnovos.com analysis).
- LangGraph: ~24.8K stars, 34.5M monthly downloads, **27,100 monthly searches** (Langfuse comparison data).
- Used in production by Cisco, Uber, LinkedIn, BlackRock, JPMorgan; "~400 companies" on LangGraph Platform (per LangChain's own marketing).
- Klarna case-study: customer support bot doing the work of 853 employees, $60M savings (verify against primary source — appears in multiple secondary articles, [pending primary verification]).
- **34% of Q1 2026 production architecture documents at 1,000+ employee companies** mention LangGraph (attributed to Gartner via Langfuse).
- March 2026: LangChain announced enterprise-agent platform built with NVIDIA. Agent Builder rebranded to LangSmith Fleet.

**How cohezion overlaps**: state-as-graph (cohezion has explicit state in a 12-D manifold; LangGraph has typed state in nodes), checkpointing (both), human-in-the-loop (LangGraph more polished), durable execution (cohezion via SurrealDB versioned schemas, LangGraph via its own persistence layer).

**How cohezion diverges**: cohezion's state is a continuous geometry with a Lagrangian and a safe attractor (LangGraph's state is whatever you put in the dict); cohezion's memory is a learned latent (FLUME VAE), LangGraph's is checkpoints + thread history; cohezion ships SkillRefiner and consensus voting natively, LangGraph leaves skill evolution to the user.

**Threat level: HIGH.** LangGraph has the mass, the enterprise sales motion, and the observability story. Anyone evaluating "agent framework, April 2026" starts here.

## 2.2 CrewAI

**What it is**: Role-based multi-agent framework. Each agent has a role/goal/backstory; tasks are assigned to agents; agents collaborate inside a "crew" using sequential, hierarchical, or consensual processes. CrewAI Flows (the production architecture) launched in 2025 wraps Crews with state management for production deployment.

**Adoption signals**:
- **CrewAI claims 60%+ Fortune 500 usage and ~450M agents/month**, ~2B agentic executions cumulatively (CrewAI marketing — verify if making competitive comparisons).
- **14,800 monthly searches** (Langfuse). Fastest-growing community in 2026.
- 40% faster prototype-to-working-app than LangGraph (per benchmark comparisons cited in 2026 framework reviews).
- CrewAI AMP is the enterprise commercial product.

**Overlap with cohezion**: multi-agent coordination, role-typed agents, both have a "manager" pattern (CrewAI's hierarchical = cohezion's TeamOrchestrator).

**Divergence**: CrewAI's mental model is human-team-metaphor (role + backstory). Cohezion's is geometric (agent state = position + velocity in manifold). CrewAI does not have a memory substrate of cohezion's depth; persistence is through Flows state.

**Threat level: MEDIUM-HIGH.** Closest competitor to cohezion's "swarm" layer (TeamExecutor). Easier on-ramp; less differentiated technology underneath.

## 2.3 AutoGen → Microsoft Agent Framework (MAF)

**What it is**: Microsoft shipped Agent Framework 1.0 GA on **April 3, 2026** for both .NET and Python, merging Semantic Kernel + AutoGen into one SDK. AutoGen is now in maintenance mode (community-managed, no new features). The new framework includes the orchestration patterns that emerged from AutoGen: sequential, concurrent, handoff, group chat, Magentic-One, plus checkpointing, streaming, human-in-the-loop, pause/resume.

**Adoption signals**: shipped 20 days ago; too early to read adoption. Migration guide published. Most likely landing zone: enterprises already deep in Azure / .NET. The .NET-first (alongside Python) story is unique — every other major framework is Python-only or Python-first.

**Overlap with cohezion**: graph-based workflows; A2A and MCP protocol support; checkpointing; pattern catalog overlaps with cohezion's TeamOrchestrator.

**Divergence**: MAF is Azure-aligned and enterprise-first; cohezion is sovereignty-aligned and local-first. MAF does not ship a memory substrate or a self-refining skill loop.

**Threat level: MEDIUM.** Will dominate Azure shops. Less likely to displace cohezion in the "principal engineer on local hardware" persona.

## 2.4 Claude Agent SDK

**What it is**: Anthropic's official agent SDK (renamed from Claude Code SDK), provides Claude with built-in tool execution — file read, command run, codebase search — without the developer implementing their own tool loops. Latest version 0.2.119 (per npm registry, accessed 2026-04-23). Recent updates include subagent transcript helpers, W3C distributed tracing, SessionStore adapter (full persistence protocol with reference implementations), and a top-level `skills` option in `ClaudeAgentOptions` for enabling Agent Skills on the main session.

**Strategic position**: This is Anthropic's "downstream surface" for cohezion. Cohezion's MCP servers (cloud-vault-mcp, compound-mcp, maintenance-mcp) are consumed by Claude Code in the maintainer's daily workflow. Cohezion sits *above* the SDK, not in competition with it.

**Threat level: LOW (substrate compatibility), but HIGH (strategic dependency).** If Anthropic builds memory + skill-refinement into the SDK directly, cohezion's value-add narrows.

## 2.5 OpenAI Agents SDK (formerly Swarm)

**What it is**: Lightweight, production-ready open-source framework for multi-agent workflows in Python and TypeScript. Evolved from the experimental Swarm (~21K stars). April 2026 updates added sandboxing, long-horizon harness, subagents, "code mode," and provider-agnostic support for 100+ LLMs.

**Important**: the OpenAI Assistants API (the older stateful one) is being **sunset mid-2026**. The Responses API is the migration target.

**Overlap with cohezion**: multi-agent coordination, tool-use loops, provider-agnostic routing.

**Divergence**: OpenAI Agents SDK is opinionated to OpenAI's platform conventions but provider-agnostic at runtime. Cohezion's CostAwareRouter is more sophisticated than OpenAI Agents SDK's routing (45 model profiles, Lemonade-first, budget enforcer). OpenAI Agents SDK does not ship a memory substrate of cohezion's depth.

**Threat level: MEDIUM.** Substantial mindshare among OpenAI-API customers.

## 2.6 Letta (formerly MemGPT)

**What it is**: "LLM-as-an-Operating-System" framework for stateful agents with three-tier memory (Core in context, Recall searchable, Archival cold storage). Letta v1 agent loop draws from ReAct, MemGPT, and Claude Code. **Letta Code** is the new memory-first coding agent runtime with git-backed memory, skills, subagents, and cross-provider deployment. As of January 21, 2026, Conversations API supports shared memory across parallel user experiences.

**Why it matters for cohezion**: Letta is the closest analogue on the *memory* axis. Both projects refuse the "memory = vector RAG side index" framing. Letta uses paged textual memory (RAM/disk/cold-storage metaphor); cohezion uses a continuous latent (FLUME) plus SurrealDB bi-temporal persistence.

**Overlap**: stateful agents, persistent memory, self-improvement claims, git-backed deployable artifact.

**Divergence**: Letta's memory is structured text; cohezion's is a learned variational latent (compositional, addressable by FLUME-encoded queries). Letta is product/runtime focused; cohezion is substrate + governance focused. Letta does not ship physics-grounded state-space or cosmogonic autonomy.

**Threat level: MEDIUM-HIGH.** Strong product, well-funded, well-articulated thesis. Plausible cohezion customer-acquisition rival on the memory axis.

## 2.7 DSPy + GEPA

**What it is**: DSPy ("Declarative Self-improving Python") is the Stanford NLP framework for programming language models declaratively rather than prompt-tinkering. GEPA (Genetic-Pareto, Agrawal et al. 2025) is the reflective prompt-optimisation algorithm now bundled with DSPy. GEPA maintains a Pareto frontier of candidate prompts, mutates them via LM-driven reflection on rollout trajectories, and is reported to outperform RL-based prompt optimisation on several benchmarks. Production deployments report 30-50% hallucination reduction and 90%+ accuracy on domain-specific QA.

**Why it matters for cohezion**: This is the closest *academic* analogue of compound engineering. DSPy compiles a declarative program into optimised prompts; cohezion refines a markdown-frontmatter skill from observed trajectories. Both treat the prompt artefact as a compilation target rather than a hand-tuned string.

**Overlap**: trajectory-based optimisation, declarative program → optimised prompt, compound-systems framing.

**Divergence**: DSPy is a *programming model*; cohezion is a *runtime*. DSPy does not ship a manifold, a vault, an autonomy ladder, or hash-chained audit. Cohezion does not ship a competing prompt-compilation algorithm — SkillConsensusVoter is closer to peer-review than to GEPA's evolutionary search.

**Threat level: LOW (different layer).** Higher likelihood of complementary integration than displacement: cohezion + DSPy/GEPA is plausibly stronger than either alone.

## 2.8 Other notable players (one-paragraph each)

**LlamaIndex AgentWorkflow**: LlamaIndex rebranded itself in 2025 from RAG framework to multi-agent framework with AgentWorkflow, supporting one or more agents, root-agent routing, automatic handoff. Strong RAG heritage; weaker on autonomy or skill-evolution. Threat: MEDIUM (mature, well-documented, large community).

**MetaGPT**: Multi-agent system that mimics a software-company structure (PM/architect/engineer/QA), governed by predefined Standard Operating Procedures. Niche but distinctive. Threat: LOW (specific verticals only).

**SuperAGI**: Production-ready framework with GUI, multiple memory systems, multiple tool integrations. Lower mindshare than the top four. Threat: LOW.

**OpenDevin / OpenHands**: Open-source autonomous software engineering agent (mid-2024). Repository-level understanding, multi-file changes, sandboxed test runs. Strong "Devin-alternative" positioning. Threat: LOW (different category — coding agent, not orchestration substrate).

**Adala**: Niche framework for autonomous data labeling. Small. Not a competitor.

**Bee** ([pending verification — not surfaced in this round of searches]).

**Cognition (Devin)**: closed-source. Devin 2.2 shipped (planning tools, faster startup, self-reviewing PRs). Customer list: OpenSea, Ramp, Nubank, Lumos, Microsoft, Curai Health, Goldman Sachs, Citi, Dell, Cisco, Palantir, Mercado Libre. Acquired Windsurf (agentic IDE) in July 2025. Cognizant + Infosys partnerships announced 2026. **Devin is the canonical "we own the autonomous coding agent" play.** Cohezion is not directly competitive (cohezion is substrate; Devin is product).

**Imbue**: Built Sculptor — a Docker-isolated parallel-agent platform with bidirectional sync to local IDE. Strong on isolation/sandbox. Free tier exists. Cohezion has no equivalent product polish on multi-agent isolation.

**Adept**: Natural-language interface for software UI control. Not directly competitive.

**Magic, Cognition (the broader bet beyond Devin), Lindy.ai, Beam, Crew.ai-as-PaaS**: full enumeration is out of scope. Direction is clear: the "hosted autonomous agent" business is being carved up by well-funded labs while the "open-source agent substrate" business is being carved up by LangGraph/CrewAI/MAF/OpenAI-SDK.

# 3. Key recent research (2025-2026) and what it implies for cohezion

| Paper / Result | Year | Implication for cohezion |
|---|---|---|
| **Voyager** (Wang et al., Minecraft skill library, arXiv 2305.16291) | 2023 | Cohezion's SkillRegistry is a Voyager-descendant. Voyager's curriculum-driven exploration is *not* in cohezion; opportunity to add. |
| **Reflexion** (Shinn et al., verbal RL, arXiv 2303.11366) | 2023 | Cohezion's RetrospectionEngine is a Reflexion-descendant. The textual-feedback loop is essentially the same primitive. |
| **AutoGen** (Wu et al., conversational MAS) | 2023 | Architectural pattern absorbed into Microsoft Agent Framework 1.0 (April 3, 2026). Cohezion's TeamOrchestrator borrows the mental model. |
| **DSPy** (Khattab et al., compiling declarative LM calls, arXiv 2310.03714) | 2023 | Closest cohezion analogue at the optimisation layer. Complementary, not competitive. |
| **GEPA: Reflective Prompt Evolution Can Outperform RL** (Agrawal et al.) | 2025 | Cohezion's SkillRefiner could plausibly adopt GEPA-style Pareto-frontier mutation. Pure upside if integrated. |
| **AuditableLLM: Hash-Chain-Backed Compliance Framework** (MDPI Electronics 15/1/56) | 2025 | Cohezion's hash-chained JourneyTracker (Learning 304-309) is exactly this pattern. Validates the design choice; cohezion is ahead of most observability tools on this axis. |
| **A Self-Improving Coding Agent (SICA)** (arXiv 2504.15228) | 2025 | Demonstrates 17%→53% on SWE-Bench Verified via self-editing. The "Darwin Gödel Machine" (Zhang et al. 2025) and AlphaEvolve are cited co-travellers. Cohezion's SkillRefiner sits in the same family. |
| **Self-Improving LLM Agents at Test-Time** (arXiv 2510.07841) | 2025 | Test-time skill formation is the trajectory cohezion is on (skills are markdown that get refined post-hoc; could move to test-time). |
| **Zep: Temporal Knowledge Graph Architecture for Agent Memory** (arXiv 2501.13956) | 2025 | Zep's 63.8% vs. Mem0's 49.0% on temporal retrieval (LOCOMO) is the public benchmark to beat. Cohezion's bi-temporal SurrealDB schema + FLUME latent has not been benchmarked on LOCOMO. Open opportunity. |
| **A Survey of Self-Evolving Agents** (arXiv 2507.21046v4) | 2025 | Maps the landscape cohezion lives in. ICLR 2026 workshop on Recursive Self-Improvement (April 26-27, Rio) is the key venue to engage with. |
| **Experiential Reflective Learning (ERL)** | 2026 | Heuristic pool injected into context per task; conceptually similar to cohezion's vault-first knowledge accumulation. |
| **SkillLearnBench** (arXiv 2604.20087) | 2026 | First benchmark explicitly for agent skill libraries. Cohezion should run against it. |
| **Multi-Agent Reflexion (MAR)** (arXiv 2512.20845) | 2025-2026 | Vote-based / persona-diverse reflection. Cohezion's SkillConsensusVoter is the same primitive in spirit. |
| **Recursive Language Models** (PrimeIntellect blog, "the paradigm of 2026") | 2026 | Industry framing: the model itself becomes recursive. Cohezion frames recursion at the skill-refinement layer, not the model layer. Distinct bets. |

The body of work above strongly validates that cohezion is in the right neighbourhood. The risk is not "wrong direction"; it's "neighbourhood is getting crowded fast."

# 4. Cohezion positioning

## 4.1 What cohezion does that no other framework does (verifiable)

1. **11-step compound loop with explicit retrospection and skill refinement as built-in stages**, not as user-supplied callbacks. Most frameworks have N=3-5 step pipelines; cohezion's executor sequences instruction-expansion, plan-generation, request-alignment, metrics-aggregation, degradation-detection (with router feedback), journey-tracking (12-D position + JEPA surprise + bioelectric percolation), Ouroboros physics-coherence check, Mycelium pattern capture, retrospection, skill refinement, consensus voting (per CLAUDE.md "Compound Engineering Loop").
2. **Vault-first canonical knowledge** (`~/vaults/cohezion-vault/`, ~150+ decisions/patterns/experiments, MEMORY.md auto-compiled cache). Letta has git-backed memory; cohezion's vault is a queryable knowledge graph (`vault_find_relevant_context()`). Closest analogue is Letta Code's git-backed memory.
3. **SPIN coherence (rotation + precession alignment) as an observable signal** — novel framing. No other framework uses an explicit physical alignment metric for state-coherence.
4. **70/20/10 cost-routing built-in via CostAwareRouter** with 45 model profiles, Lemonade-first local inference (NPU/GPU/CPU hot-swap on Strix Halo), BudgetEnforcer monthly hard-stop. Most frameworks bolt this on (LangChain via LiteLLM; CrewAI via per-agent LLM config). Cohezion makes it a first-class architectural concern.
5. **256-D FLUME latent for context composition** — to the best of this research's knowledge, no other agent framework treats context as a learned variational latent. Letta uses textual paging; Zep uses temporal knowledge graphs; LangGraph uses typed dicts. **This is cohezion's most distinctive technical bet.** It is also the least benchmarked.
6. **Hash-chained audit trail in SurrealDB** (V-Model gates: vmodel_gate, traces, hash_chain, proof_obligation per Session 96b). Matches the pattern in AuditableLLM (Electronics 2025); ahead of mainstream observability tools (Langfuse, Helicone, Arize) which record but do not seal.
7. **Cosmogonic autonomy ladder** (SO(12) → SO(3)⁴ → U(1)⁴ → Z₂⁴ → HIHO mapped to Observe → Edit → Commit → Deploy → Sovereign). Genuinely unique. Per Learning 327, an 8-query × 7-database SLR found 0 systems combining 3+ relevant components.

## 4.2 Where cohezion is behind (honest)

1. **Production maturity**. LangChain has 5+ years of battle-testing, ~127K stars, ~3,900 contributors. Cohezion has one developer.
2. **Community / ecosystem**. LangGraph has 24.8K stars and 34.5M monthly downloads; CrewAI has 14.8K monthly searches. Cohezion's community is N≈1.
3. **Documentation quality**. CLAUDE.md is dense and assumes familiarity with the project's vocabulary. There is no Quickstart that meets the "5-minute getting-started" bar identified in the PRFAQ.
4. **Multi-language SDK**. Cohezion is Python + Rust + TS but only Python is full. CrewAI/LangGraph are Python-first; MAF is Python + .NET; OpenAI Agents SDK is Python + TypeScript. Cohezion's TS surface is dashboard-only.
5. **IDE integration**. Cohezion is Claude Code-first. BMAD multi-IDE work (Learnings 371-376) is in progress. Cursor / Cline / Gemini CLI / GitHub Copilot integrations are partial. Devin (Cognition) ships its own IDE (Windsurf, acquired). Cohezion has no IDE.
6. **Hosted runtime**. Anthropic Managed Agents (April 8, 2026) ships sandboxing, credential management, session continuity, observability — at $0.08/session-hour + token costs. Cohezion has no hosted offering. Notion, Rakuten, Sentry are early Managed Agents adopters. The market signal: "hosted runtime" is now table stakes for orchestration platforms.
7. **Memory benchmarks**. Zep publishes 63.8% on LOCOMO temporal retrieval; Mem0 publishes 49.0%. Cohezion has not run public benchmarks on its FLUME latent.

## 4.3 The "build vs adopt" decision for new users (April 2026)

A new project picking an agentic framework today, with no special constraints, will **almost certainly choose LangGraph or CrewAI**. Reasoning: largest community, deepest documentation, most production references, NVIDIA partnership, observability story (LangSmith / LangChain Platform). For an Azure-deep enterprise: Microsoft Agent Framework. For an OpenAI-deep team: OpenAI Agents SDK. For a memory-centric build: Letta. For a research-grade declarative-program build: DSPy + GEPA.

**Cohezion is a viable choice for a narrow persona**: a principal engineer who (a) runs long-horizon AI workflows on local hardware (Strix Halo, or Ollama Cloud as cheap substitute), (b) values sovereignty and audit-grade provenance, (c) has the engineering judgement to evaluate whether the compound-loop thesis pays off in their workflow over weeks-not-hours, and (d) is unbothered by single-developer bus factor.

For everyone else, today, in April 2026: **cohezion is not the right first choice.** It can become the right second choice once the first choice's limits bite (textual-memory drift, opaque autonomy, cost-spend on duplicated work).

# 5. Market gaps cohezion could exploit

## Gap 1: Compound-engineering as a paid service ("we make your AI agents better while you sleep")

The Klaassen / Every.to / EveryInc compound-engineering plugin has popularised the pattern at the editor level. Cohezion already ships the orchestrator (`polish-campaign-orchestrator` skill — Wave Ω-style multi-wave parallel agents that produce 74 commits and a retrospective in 2.81h on a 17h budget). **This is a demo-ready product story.** The wedge: "tell cohezion what you want done in N hours; it spawns agents to do it in a fraction of that time; it audits its own output; it writes you a retrospective." Position as a managed service or a Claude Code plugin. Compete with the EveryInc plugin head-on at the *outcomes* layer (multi-wave campaigns) rather than the *mechanic* layer (Plan → Work → Review → Compound).

## Gap 2: Vault-as-a-product (sovereign, hash-chained, multi-user)

The vault-first knowledge architecture is cohezion's strongest under-claimed asset (per the PRFAQ exercise's own internal addendum). 167 documented learnings, an INDEX file built in a campaign, cross-references between vault/CLAUDE.md/code. **No competitor ships this.** Letta has git-backed memory but not a queryable vault with frontmatter-typed entries. Mem0/Zep ship temporal knowledge graphs but not the editorial / curatorial layer (vault keepers, frontmatter enforcement, orphan detection).

The product wedge: **a hash-chained, audit-grade, multi-user knowledge vault for AI agents in regulated industries** (finance, healthcare, defence). Pricing: per-seat or per-GB. The PRFAQ already names this as the natural hosted-product expansion.

## Gap 3: Self-improving observability ("close the loop")

Most observability tools (Langfuse, Helicone, Arize, Braintrust, Maxim) RECORD and DASHBOARD; they don't CLOSE THE LOOP. Cohezion's RetrospectionEngine + SkillRefiner + SkillConsensusVoter is exactly the missing piece.

The product wedge: **observability that doesn't just tell you your agent is bad — it makes the agent better.** Position as "Observability + 1" or "Auto-Tuning Observability." Pair with Anthropic's Managed Agents (which has observability but no auto-tuning) as a complementary product, not a competitor.

## Gap 4 (bonus): Local-first agent stacks for sovereignty-conscious customers

The Lemonade-first router is a real differentiator now that NPU silicon (Strix Halo, Snapdragon X Elite, Apple M-series Neural Engine) is widely available. Most frameworks treat local inference as a fallback; cohezion treats it as the default with cloud as escalation. This is the *right* default for EU regulated sectors, defence, intelligence, and any customer worried about US administration's AI export controls. The market is small but well-funded.

# 6. Strategic recommendations

## Recommendation 1: Lead with the "polish-campaign-orchestrator" demo, not the manifold

**Recommendation**: Reframe cohezion's public-facing pitch around the multi-wave parallel-agent campaign use case. The 17h-budgeted/2.81h-actual demo is concrete, measurable, and visually striking. The physics layer is a research bet that should live below the fold.

**Why now**: Compound engineering as a phrase is becoming popular but has no canonical product. EveryInc's plugin is a good first-mover but is editor-bound. Cohezion can claim the "campaign orchestrator" category by shipping the wedge first.

**Effort**: Medium (~2 weeks of demo polish + one screencast + a landing page).

**Risk**: Low. The functionality already exists. The risk is misdirection — leading with this means under-leading with the manifold, which the maintainer cares about.

## Recommendation 2: Run cohezion's memory layer against LOCOMO and publish

**Recommendation**: The Zep paper publishes 63.8% on LOCOMO temporal retrieval; Mem0 publishes 49.0%. Cohezion's bi-temporal SurrealDB + FLUME latent has not been benchmarked. Run it. Publish the result. If competitive, this is the strongest possible technical credibility play. If non-competitive, it tells the maintainer something important about the FLUME approach.

**Why now**: The benchmark is published and contested; entering the conversation now gets attention. Waiting six months means entering a settled debate.

**Effort**: Medium (~3-4 weeks: benchmark setup + run + writeup).

**Risk**: Medium. If FLUME loses to a knowledge graph on temporal retrieval, the latent-as-substrate thesis takes a public dent. The honest framing (cohezion is research; FLUME is a research bet) survives a loss; the marketing claim of substrate-superiority does not.

## Recommendation 3: Engage with the ICLR 2026 Recursive Self-Improvement workshop (April 26-27, Rio)

**Recommendation**: Attend (virtually if needed). Submit a workshop paper on the cosmogonic autonomy ladder and/or the SkillConsensusVoter. The workshop is the highest-density venue for the recursive-self-improvement community in 2026. Cohezion has unique angles (the symmetry-breaking → trust-tier mapping) that no other team is exploring.

**Why now**: The workshop is in 3 days. There may be poster slots. Even attending without submitting buys conversations.

**Effort**: Low if attending; Medium if writing a paper.

**Risk**: Low. Worst case: nothing happens. Best case: cohezion becomes a known name in the recursive-self-improvement subfield.

## Recommendation 4: Walk back the "95% cache hit rate" and "production-ready" implications publicly

**Recommendation**: As the PRFAQ's internal addendum already noted, both claims are over-stated. Public-facing copy should be revised before any go-to-market motion. Honest positioning: "designed for high cache hit rate; production validation in progress; single-developer research codebase; no SLA." This protects the project from one-shot embarrassment that would cost more than the marketing gain.

**Why now**: Trivial cost; large protection. Should happen before any external press.

**Effort**: Trivial (~2h of editing).

**Risk**: Negligible. Honesty is a moat.

## Recommendation 5: Stake a defensive claim on "compound engineering" branding NOW

**Recommendation**: Klaassen + EveryInc are establishing themselves as the canonical voice on "compound engineering." If cohezion wants the phrase, it needs to actively defend it: blog post per week, presence in the Klaassen podcast ecosystem, a clear differentiation statement ("compound engineering is the philosophy; cohezion is the substrate"). If cohezion doesn't want to fight for the phrase, pick a different anchor (e.g. "compound substrate," "agent geometry," "manifold engineering").

**Why now**: The brand window for "compound engineering" is closing within 2026. Klaassen is on a podcast tour right now.

**Effort**: Medium (sustained communication effort).

**Risk**: Medium. If cohezion contests the phrase and loses (Klaassen is a more polished communicator), it looks reactive. If cohezion picks a different anchor, it loses the term that best describes what it does.

# 7. Threats and risks

| Risk | Likelihood | Severity | Mitigation |
|---|---|---|---|
| **R1: Anthropic Managed Agents subsumes cohezion's runtime layer** | High (already shipped April 8, 2026) | High | Position cohezion as substrate underneath Managed Agents; build MCP integrations that make cohezion the natural "vault + auto-tuning" bolt-on |
| **R2: LangChain catches up on compound engineering** (Deep Agents v1.1.3 is the first signal) | Medium-High | High | Move fast on the polish-campaign-orchestrator wedge; publish LOCOMO benchmark; engage the recursive-self-improvement workshop |
| **R3: Foundation models get good enough that orchestration matters less** | Medium | High | The manifold + memory layer survives this; the orchestration layer does not. Defend the substrate, accept that orchestration as a category may flatten |
| **R4: Single-developer bus factor** | Confirmed (currently true) | Critical | Recruit a co-maintainer. The PRFAQ's internal addendum already named this as the highest-leverage productisation step |
| **R5: "Compound engineering" branding owned by EveryInc / Klaassen** | Medium-High | Medium | See Recommendation 5 |
| **R6: Physics-grounded state space remains unverified beyond ManifoldEnv** | Medium | Medium | Run RL benchmarks on standard environments (Gymnasium MuJoCo, MiniGrid). If HIHO attractor generalises, it's a paper. If not, sever the physics layer cleanly from the cost-router and the loop |
| **R7: Open-source business model fails to monetise** | High (industry-wide) | High | Hosted vault is the natural commercial wedge; build it after a commercial validation conversation, not before |
| **R8: Constitution dependency on Anthropic** | Low | Low | Document the Constitution-tracking cadence; fork and version the Constitution if Anthropic deprecates it |
| **R9: Strix Halo target alienates 99% of prospective users** | Low (graceful degradation works) | Medium | Marketing should lead with "runs anywhere"; Strix Halo is the optimisation target, not the requirement. PRFAQ's own counter handles this |
| **R10: Letta or Mem0 ship a hash-chained vault before cohezion does** | Medium | Medium | Ship the vault-as-a-product wedge before they realise it's available |

# 8. Open questions

1. **Is the FLUME latent measurably better than a textual scratchpad + vector RAG on real workloads?** Open. LOCOMO benchmark would partially answer.
2. **Does the HIHO attractor generalise beyond ManifoldEnv?** Open. RL benchmarks on standard environments would partially answer.
3. **Will the Klaassen "compound engineering" framing converge with the Berkeley "compound AI systems" framing, or remain distinct vocabulary?** Open. This shapes positioning choices.
4. **Will Anthropic Managed Agents add memory + skill-refinement to its roadmap?** Probable within 12-18 months given research-preview status of those features. Cohezion's advantage on those axes is time-limited.
5. **Is the "principal engineer on local hardware" persona large enough to support a sustainable open-source project?** Open. Needs market sizing.
6. **What is the right pricing for hosted vault?** Per-seat? Per-GB? Per-query? Open until customer validation.
7. **Does the cosmogonic autonomy ladder appeal to anyone outside the maintainer?** Genuinely open. The mathematical elegance is real; the customer pull is unverified.
8. **Should cohezion contribute SkillRefiner improvements to DSPy GEPA upstream, or keep them in-tree?** Strategic question with both technical and ecosystem implications.
9. **Is there a partnership opportunity with Letta on the memory axis?** Both projects refuse the textual-RAG framing. Different bets but compatible philosophy.

# References

All URLs accessed 2026-04-23 unless otherwise noted. Where claims appear in secondary sources only, marked [pending verification] inline.

**Competitor primary sources**
- LangGraph repo + docs: https://github.com/langchain-ai/langgraph; https://www.langchain.com/langgraph
- LangGraph 2026 changelog analysis: https://www.agentframeworkhub.com/blog/langgraph-news-updates-2026
- LangGraph Context7 metadata: 1,252 indexed snippets, source reputation High, benchmark 87.55 (Context7 resolve-library-id, 2026-04-23)
- CrewAI: https://crewai.com/; https://docs.crewai.com/en/introduction; https://github.com/crewaiinc/crewai
- Microsoft Agent Framework GA announcement: https://devblogs.microsoft.com/agent-framework/microsoft-agent-framework-version-1-0/; https://learn.microsoft.com/en-us/agent-framework/overview/
- AutoGen → MAF migration guide: https://learn.microsoft.com/en-us/agent-framework/migration-guide/from-autogen/
- Claude Agent SDK: https://code.claude.com/docs/en/agent-sdk/overview; https://github.com/anthropics/claude-agent-sdk-python; https://www.npmjs.com/package/@anthropic-ai/claude-agent-sdk
- OpenAI Agents SDK: https://openai.github.io/openai-agents-python/; https://github.com/openai/openai-agents-python; https://github.com/openai/swarm
- Letta: https://www.letta.com/; https://github.com/letta-ai/letta; https://docs.letta.com/concepts/letta/
- Letta Code blog: https://www.letta.com/blog/letta-code
- DSPy: https://dspy.ai/; https://github.com/stanfordnlp/dspy
- DSPy GEPA: https://dspy.ai/api/optimizers/GEPA/overview/; https://github.com/gepa-ai/gepa
- LlamaIndex AgentWorkflow: https://www.llamaindex.ai/blog/introducing-agentworkflow-a-powerful-system-for-building-ai-agent-systems
- MetaGPT: https://github.com/FoundationAgents/MetaGPT
- Cognition / Devin: https://cognition.ai/; https://cognition.ai/blog/introducing-devin-2-2

**Anthropic Managed Agents**
- Engineering blog: https://www.anthropic.com/engineering/managed-agents
- Platform docs: https://platform.claude.com/docs/en/managed-agents/overview
- InfoQ coverage: https://www.infoq.com/news/2026/04/anthropic-managed-agents/
- VentureBeat coverage: https://venturebeat.com/orchestration/anthropics-claude-managed-agents-gives-enterprises-a-new-one-stop-shop-but
- SiliconANGLE coverage: https://siliconangle.com/2026/04/08/anthropic-launches-claude-managed-agents-speed-ai-agent-development/

**Compound engineering thesis**
- Berkeley AI Research compound AI systems essay (Zaharia et al., February 2024): https://bair.berkeley.edu/blog/2024/02/18/compound-ai-systems/
- Databricks glossary: https://www.databricks.com/glossary/compound-ai-systems
- Survey of compound AI systems (arXiv 2506.04565): https://arxiv.org/html/2506.04565v1
- Every.to compound engineering: https://every.to/chain-of-thought/compound-engineering-how-every-codes-with-agents
- Every.to compound engineering guide: https://every.to/guides/compound-engineering
- EveryInc plugin: https://github.com/EveryInc/compound-engineering-plugin
- Klaassen This New Way podcast: https://podcasts.apple.com/us/podcast/compound-engineering-manage-teams-of-ai-agents/id1509072609?i=1000730933805
- Lethain (Larson) analysis: https://lethain.com/everyinc-compound-engineering/
- LangChain "agentic engineering" framing: https://www.langchain.com/blog/agentic-engineering-redefining-software-engineering

**Recursive self-improvement / agent skills research**
- ICLR 2026 RSI Workshop: https://recursive-workshop.github.io/
- Workshop summary (OpenReview): https://openreview.net/pdf?id=OsPQ6zTQXV
- Survey of self-evolving agents (arXiv 2507.21046v4): https://arxiv.org/html/2507.21046v4
- Self-Improving Coding Agent (arXiv 2504.15228): https://arxiv.org/html/2504.15228v2
- Self-Improving LLM Agents at Test-Time (arXiv 2510.07841): https://arxiv.org/abs/2510.07841
- Recursive Introspection (arXiv 2407.18219): https://arxiv.org/html/2407.18219v1
- Recursive Language Models (PrimeIntellect, 2026): https://www.primeintellect.ai/blog/rlm
- SkillLearnBench (arXiv 2604.20087): https://arxiv.org/html/2604.20087
- Multi-Agent Reflexion (arXiv 2512.20845): https://arxiv.org/html/2512.20845v1
- Voyager (arXiv 2305.16291): https://arxiv.org/abs/2305.16291
- Reflexion (arXiv 2303.11366): https://arxiv.org/abs/2303.11366
- DSPy paper (arXiv 2310.03714): https://arxiv.org/abs/2310.03714

**Memory + observability**
- Zep paper (arXiv 2501.13956): https://arxiv.org/abs/2501.13956
- Mem0 state-of-agent-memory 2026: https://mem0.ai/blog/state-of-ai-agent-memory-2026
- Graphiti (Zep OSS): https://github.com/getzep/graphiti
- Mem0 vs Letta comparison: https://vectorize.io/articles/mem0-vs-letta
- Mem0 vs Zep comparison: https://vectorize.io/articles/mem0-vs-zep
- Graph-Based Agent Memory taxonomy (arXiv 2602.05665): https://arxiv.org/html/2602.05665v1
- Top 5 LLM Observability Platforms 2026: https://www.getmaxim.ai/articles/top-5-llm-observability-platforms-in-2026-2/
- AI Agent Observability Stack 2026: https://agenticcareers.co/blog/ai-agent-observability-stack-2026
- AuditableLLM (Electronics 15/1/56): https://www.mdpi.com/2079-9292/15/1/56
- AI Agent Audit Trail Guide 2026: https://fast.io/resources/ai-agent-audit-trail/
- Semantic caching production guide (TianPan, April 2026): https://tianpan.co/blog/2026-04-10-semantic-caching-llm-production
- Semantic caching for LLM serving (arXiv 2508.07675): https://arxiv.org/html/2508.07675v1

**Framework comparison aggregators**
- Best Multi-Agent Frameworks 2026 (gurusup.com): https://gurusup.com/blog/best-multi-agent-frameworks-2026
- Definitive Guide to Agentic Frameworks 2026 (softmaxdata.com): https://softmaxdata.com/blog/definitive-guide-to-agentic-frameworks-in-2026-langgraph-crewai-ag2-openai-and-more/
- OpenAI vs LangGraph vs CrewAI Matrix 2026 (digitalapplied.com): https://www.digitalapplied.com/blog/openai-agents-sdk-vs-langgraph-vs-crewai-matrix-2026
- 6 Best Devin Alternatives (augmentcode.com): https://www.augmentcode.com/tools/best-devin-alternatives

**Anthropic skills / SDK**
- Agent Skills overview: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- Skill authoring best practices: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- Anthropics skills repo: https://github.com/anthropics/skills

**Cohezion internal documents** (project-local, not URLs)
- `research/prfaq/2026-04-23-cohezion-prfaq.md`
- `CLAUDE.md` (sections "Architecture at a Glance" + "Agent Protocol Stack" + "Compound Engineering Loop")
- `~/vaults/cohezion-vault/learnings/INDEX.md` (167 documented learnings)

---

*End of document. Generated 2026-04-23 as part of synthetic-sniffing-panda Wave Ω13. Approximately 5,400 words. WebSearch + Context7 source pool: 12 queries, ~110 distinct URLs reviewed.*
