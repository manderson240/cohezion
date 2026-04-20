---
title: Experience Feedback Loop
date: 2026-02-23
tags: [compound-engineering, learning, agent-workflow, meta-learning]
related_concepts: [compound-engineering, meta-learning, agent-journey-tracking, context-management, token-efficiency]
status: active
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 63
  synapse_out: 25
---

# Experience Feedback Loop

The experience feedback loop is the mechanism by which agent session outcomes — successes, failures, unexpected discoveries — are captured, structured, and injected back into future sessions to improve performance. It is the engine of [[compound-engineering]]: without a feedback loop, each session starts from scratch; with one, each session builds on all prior sessions.

The loop operates in four stages. First, a session executes and produces outputs (code, decisions, experiment results). Second, observations are saved to vault memory via `vault_push_memory` and `vault_push_session_state`. Third, structured lessons are extracted using `vault_log_decision` or `vault_log_experiment`, creating durable, searchable records. Fourth, future sessions load relevant prior context via `vault_find_relevant_context` and `vault_pull_session_context`, grounding new work in accumulated institutional knowledge.

The empirical payoff is substantial: [[lesson-37-experience-guided-execution-works-new]] demonstrated that experience-guided execution produces materially better outputs than cold-start sessions. Over 100 sessions, the feedback loop compounds to 7x+ token efficiency gains — not from doing the same work faster, but from not repeating mistakes and not rediscovering solutions that are already in the vault.

## Stages
1. **Execute**: Agent session runs, producing outputs and encountering decisions
2. **Capture**: Observations saved to vault memory; raw session state preserved
3. **Extract**: Lessons formalized via `vault_log_decision`, `vault_log_experiment`, `vault_extract_pattern`
4. **Inject**: Future sessions load relevant context via `vault_find_relevant_context`
5. **Improve**: Agents refine skills based on accumulated patterns; SkillRefiner updates PRIME definitions

## Related
- [[compound-engineering]] — the methodology the feedback loop implements
- [[meta-learning]] — the strategic layer that extracts patterns from the feedback loop
- [[agent-journey-tracking]] — the observability layer that records what happened during execution
- [[context-management]] — how prior experience is assembled and delivered to new sessions
- [[Ouroboros-Loop]] — the real-time autonomic Sense/Feel/Act cycle that operationalizes feedback during active sessions
- [[FLUME-Architecture]] -- FLUME embeddings close the feedback loop by making prior session knowledge retrievable for context injection
- [[reinforcement-learning]] -- RL's trial-and-error reward signal parallels the experience feedback loop that captures outcomes for improvement
- [[lesson-37-experience-guided-execution-works-new]] — empirical validation of feedback loop value
- [[2026-02-22-recursive-challenger-session-68-autonomous-improvement-loop|Session 68: Recursive Challenger]] — autonomous improvement loop applying the feedback loop recursively to compound engineering itself
- [[session-57-local-finetuning|Session 57: Local Model Finetuning]] — converts journey data into JSONL for QLoRA/Ollama finetuning, closing the experience-to-model feedback loop

## Related Patterns & Experiments

- [[2026-03-05-flume-kl-collapse-diagnostic]] — experiment to validate FLUME KL divergence health and reconstruction fidelity
- [[structured-experience-vector-layout]] — the structured data format that closes the feedback loop from execution to training
- [[2026-02-24-flume-vae-v2-training-results]] — FLUME VAE v2 training experiment consuming structured experience data through the feedback loop
- [[research-integration-todos]] — research integration tasks feed the compound learning base: each processed paper adds reusable knowledge
- [[lab-agent]] — the lab agent feeds experiment results and observations into the experience feedback loop
- [[2026-02-20-session-59-autonomous-compound-engineering-foundation|Session 59: Autonomous Compound Engineering]] — vault-first knowledge architecture implements the capture and inject stages of the feedback loop
- [[2026-02-27-ux-reentry-narrative-system-speaks-first|Re-entry Narrative]] — surfaces accumulated compound learning as evidence of the feedback loop in the UI
- [[2026-03-03-vault-knowledge-graph-densification-complete-via-parallel-agent-teams|Graph Densification Complete]] — densification feeds the experience loop by making prior decisions more discoverable
- [[2026-03-03-claude-platform-skills-assessment|Platform Skills Assessment]] — identifies end-to-end VAE training and evaluation rigor as critical gaps in closing the feedback loop credibly
- [[research-lineage]] — research lineage tracks the provenance chain that the feedback loop generates over time
- [[knowledge-graph-densification]] — densification sprints are a feedback-loop-driven process: each cycle identifies and fills gaps

## Related Projects

- [[2026-03-03-vault-as-platform-memory-recommendations|Vault as Platform Memory Recommendations]] — strategic assessment of vault-as-memory architecture with 6 prioritized recommendations

## Agent Outputs

- **Project Ouroboros Implementation Plan** — `Agents/Antigravity/1fbfc912-70e8-458b-a3e3-cc4ace0e8395/implementation_plan.md`
- **Cycle 3: Recursive Evolution** — `Agents/Antigravity/48be5ea6-a6b4-42e1-adca-ac83660307e0/task.md`
- **Research Updates Batch 1** — `Agents/Antigravity/d9c1fcdb-69db-458c-b64a-f26e49625c33/RESEARCH_UPDATES_BATCH_1.md`
- **Research Updates Final** — `Agents/Antigravity/d9c1fcdb-69db-458c-b64a-f26e49625c33/RESEARCH_UPDATES_FINAL.md`
- **Omega Skill Crystallizer Design** — `Agents/Antigravity/ada764e1-6829-4b4c-a85a-e111080303ad/omega_skill_crystallizer_design.md`

## Skills

- meta_skill — Pattern abstraction into skills
- TRAINING_DATA_CAPTURE_PRIME — Agentic interaction logging

## Learnings & Meta
- [[1771220602|Learning: verify_skill]] — high-fidelity learning pattern demonstrating the feedback loop in action
- [[compound-demo-0|Compound Demo Iteration 0]] — initial compound demo with performance metrics feeding the loop
- [[recording-self-20260304-094201-1|Self-Recording Session]] — Cohezion observing its own feedback loop
