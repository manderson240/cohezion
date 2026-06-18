---
title: Google × Kaggle — 5-Day AI Agents Intensive (Vibe Coding) — capstone prep
date: 2026-06-02
status: ENROLLED (userHasEntered=True) — preparation only, capstone not yet open
reward: Kudos (badge + certificate; top picks get swag + social recognition) — NON-CASH
---

# Google 5-Day AI Agents Intensive (Vibe Coding) — readiness brief

## Facts (verified 2026-06-02)
- **Slug:** `5-day-ai-agents-intensive-vibecoding-course-with-google` (Kaggle, category Featured)
- **Already entered:** yes (kaggle CLI `userHasEntered=True`)
- **Course dates:** June 15–19, 2026 (daily lessons + expert speakers + hands-on)
- **Course-comp deadline shown by CLI:** 2026-06-15 22:59 (enrollment/course gate)
- **Capstone:** opens end of day 5 (~June 19), **due June 30, 2026, 11:59 PM PT**
  (prior iteration was a separate comp `agents-intensive-capstone-project`; CONFIRM the
  exact June-2026 capstone comp slug + deadline once it goes live ~June 19)
- **Submission format:** Kaggle **Writeup** — documented agent + **video explainer** +
  brief rationale + **link to code**. NOT a scored leaderboard; completion-based.
- **Theme:** "vibe coding" — natural language as the primary programming interface;
  build an agent that solves a real problem / improves productivity, integrating tools+APIs;
  "10x agents" via tool/API integration.

## Priority vs the cash portfolio
- This is **Kudos-only** → LOWER priority than Nemotron ($106K, Jun 15) and AGI-Golf ($50K, Jul 15).
- BUT timeline does NOT collide: capstone window is Jun 19–30, after Nemotron's leaderboard close.
- Effort is low: we can feature an EXISTING Cohezion agent. No new infra needed.

## Our unfair advantage
Cohezion is literally a multi-agent orchestration platform. The capstone ("build an agent
that solves a real problem, integrating tools/APIs") maps onto shipped capabilities:
compound executor, swarm/TeamOrchestrator, 87+ MCP tools, local-inference routing
(NPU/iGPU/CPU), A2A + AG-UI, semantic cache. We showcase, not build-from-scratch.

## ACTUAL capstone: "Kaggriculture" (per Kaggle site, 2026-06-02)
> "Apply your agentic workflows in our new capstone challenge, **Kaggriculture** — a farming
> simulation where you'll build and deploy an **autonomous agent to manage resources and
> outperform others in a dynamic environment**. Build your technical portfolio while
> competing for prizes, including Kaggle certificates, badges, and swag. Detailed
> requirements and submission guidelines will be shared during the course."

Implications:
- This is a **competitive agent-in-a-simulation** ("outperform others" → leaderboard-style),
  NOT the open-ended "build any agent + writeup" of 2025 iterations.
- The agent must MANAGE RESOURCES under DYNAMIC conditions → sequential decision-making /
  planning / RL / LLM-policy-in-a-loop. Exact API + env unknown until the course (Jun 15–19).
- Prizes still cert/badge/swag (non-cash), but performance matters now.

## How Cohezion maps onto Kaggriculture (reuse, don't rebuild)
- **Gymnasium envs already exist**: `ManifoldEnv` (19D obs, verifiable rewards), `SwarmEnv`
  (multi-agent) → we know how to wrap an env + train/eval a policy.
- **Agentic decision infra**: CompoundExecutor, swarm orchestration, local-inference routing
  → an LLM-policy agent that plans resource allocation each tick is squarely in our wheelhouse.
- Likely strong play: an LLM-driven planning agent (Gemini, on-theme) with a tool/eval loop,
  optionally backstopped by a cheap local-fleet policy for fast simulation rollouts.

## Open questions to resolve when the env drops (~Jun 15–19)
- Is the agent an LLM-in-a-loop, or a coded/RL policy, or either?
- What's the action/observation API? Submission = notebook that runs the agent in their sim?
- Is scoring a live leaderboard vs other agents, or vs a fixed benchmark?
- Compute limits / allowed libraries / Gemini-API quota?

## Decision (deferred, correctly)
Can't lock the agent design until the Kaggriculture env/API is published during the course.
Prep now = understand prior-course structure + cadence so we move fast Jun 15–19. Lead
candidate when env drops: **Gemini planning agent reusing Cohezion's env+policy patterns.**

## Pre-stage checklist (do during/just-before the course, NOT now)
- [ ] Watch for capstone comp to open (~Jun 19); CONFIRM slug + exact deadline; enter it
- [ ] Lock the project (one of the 3 above)
- [ ] Build/clean the agent notebook (tool use + clear real-world task)
- [ ] Record 3-min video explainer (local screen capture if AMD-fleet involved)
- [ ] Write the Kaggle Writeup (problem, approach, architecture diagram, results, code link)
- [ ] Submit before Jun 30 23:59 PT

## Prior course iterations (researched 2026-06-02) — the pattern
**Gen AI Intensive (2025Q1, Mar 31–Apr 4 2025)** — comp `gen-ai-intensive-course-capstone-2025q1`
- Days: 1 Foundational models + prompt eng · 2 Embeddings/vector DBs · 3 Agents · 4 Domain
  LLMs/fine-tuning · 5 MLOps. Format: daily email = whitepaper + Gemini codelab + NotebookLM
  podcast + Discord + livestream. Capstone = OPEN-ENDED Kaggle Notebook + writeup.
**AI Agents Intensive (Nov 10–14 2025)** — comp `agents-intensive-capstone-project`
- Days: 1 Agents & agentic architectures · 2 Tools & MCP interoperability · 3 Context
  engineering & memory · 4 Quality/logging/eval · 5 Prototype→Production (A2A). Capstone
  launched Nov 14 = OPEN-ENDED "build your agent", completion badge. 160k+ on Discord.

**The change for June 2026:** vibe-coding theme + a STRUCTURED COMPETITIVE capstone
(Kaggriculture). Prior = "build anything, get a badge"; now = "win a simulation."

## Strong hypothesis: Kaggriculture = Kaggle Simulations (`kaggle_environments`)
"Dynamic environment / manage resources / outperform others / deploy an autonomous agent"
is the exact framing of Kaggle Simulations comps (Lux AI, Halite, ConnectX). If so:
- Submit an `agent(observation, configuration) -> action` function in a notebook; Kaggle's
  harness runs episodes vs other agents; ranked by a skill rating (not a static test set).
- Policy can be coded heuristic, RL, OR an LLM-in-the-loop (Gemini, on-theme for vibe coding).
- CONFIRM when env drops (~Jun 15–19): is `kaggle_environments` the harness? action/obs API?

## Pre-stage actions we CAN do now (before env is published)
- [x] `kaggle-environments` installed in the cohezion venv (v1.30.1). Submission mechanics
      drilled + verified end-to-end in `kaggle_sim_reference.py` (ConnectX stand-in):
      agent(obs,cfg) signature, env.run episodes, evaluate/win_rate helper, and — the key
      one — **file-based submission validation** (write `submission.py`, run it AS A FILE via
      `env.run([str(path), opp])`, assert status DONE = how the grader loads it). Includes a
      Gemini-LLM-policy skeleton with the timeout+heuristic-fallback robustness pattern.
      When Kaggriculture opens: change ENV_NAME, adapt obs/action shapes, keep the flow.
- [ ] Skim a prior sim comp's top agent (Lux AI S3 / Halite) for the agent-loop + state mgmt.
- [ ] Map Cohezion reuse: ManifoldEnv/SwarmEnv policy patterns + a Gemini planning loop as the
      Kaggriculture agent; cheap local-fleet policy for fast self-play rollouts.
- [ ] Have a Gemini API key / Google AI Studio ready (course uses Gemini; on-theme for graders).
- [ ] Block Jun 15–19 for daily lessons; capstone opens ~Jun 19, due ~Jun 30 23:59 PT.

## Files (this prep)
- `PREP.md` — this brief
- `kaggle_sim_reference.py` — verified submission-mechanics reference (run with the cohezion venv)
- `submission.py` — generated standalone file-agent (proof the package/validate path works)

## Sources
- Course comp: https://www.kaggle.com/competitions/5-day-ai-agents-intensive-vibecoding-course-with-google
- Google blog: https://blog.google/innovation-and-ai/technology/developers-tools/kaggle-genai-intensive-course-vibe-coding-june-2026/
- Learn guide: https://www.kaggle.com/learn-guide/5-day-agents
- Prior capstone (format reference): https://www.kaggle.com/competitions/agents-intensive-capstone-project/writeups
