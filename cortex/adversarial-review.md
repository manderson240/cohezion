---
title: Adversarial Review
date: 2026-02-23
tags: [adversarial-review, planning, methodology, compound-engineering]
related_concepts: [compound-engineering, meta-learning, alignment, workflow-orchestration, token-efficiency]
status: active
aspect: knower
neural:
  activation: 0.98
  stage: mature
  synapse_in: 48
  synapse_out: 30
---

# Adversarial Review

Adversarial review is the structured practice of critiquing a plan or design by assuming the proposer is wrong and generating falsifiable counter-hypotheses. Unlike standard review (which looks for obvious errors), adversarial review actively tries to invalidate the proposal — finding hidden assumptions, edge cases, and alternative explanations that the proposer's perspective is blind to.

The economic case for adversarial review is compelling: a 10-minute review investment (5K tokens) can prevent 8+ hours of wasted execution (225K+ tokens) when it catches a fundamental flaw before work begins. The ROI is 45x on a single catch. The [[lesson-adversarial-review-before-execution]] lesson, validated across multiple Cohezion sessions, established adversarial review as a mandatory gate before any significant implementation begins.

In Cohezion's spec workflow, adversarial review is institutionalized through the `plan-challenger` agent: a sub-agent that receives the completed plan and is explicitly instructed to challenge its assumptions, identify risks, and require evidence for key claims. This is the final quality gate before plan approval — the plan-challenger runs in parallel with the plan-verifier, and both must clear before implementation begins.

## Key Properties
- **Assumption inversion**: Assumes the proposer is wrong; requires positive evidence, not absence of objections
- **Counter-hypothesis generation**: Produces specific falsifiable alternative explanations
- **Evidence requirement**: Intuition alone is insufficient; claims must be backed by observable evidence
- **Mandatory gating**: Adversarial review is a blocking gate, not advisory feedback
- **Asymmetric value**: High catch rate on low-probability catastrophic failures justifies fixed review overhead

## Navigation

- [[MOC-safety-alignment]] — Map of Content for AI safety, alignment, adversarial review, and guardrails

## Related
- [[compound-engineering]] — adversarial review is a mandatory phase gate in the compound engineering workflow
- [[meta-learning]] — adversarial review findings are extracted as lessons to prevent future blind spots
- [[alignment]] — adversarial review is an alignment verification mechanism for agent plans
- [[workflow-orchestration]] — the workflow layer that enforces adversarial review as a mandatory checkpoint
- [[lesson-adversarial-review-before-execution]] — the validated lesson formalizing this practice
- [[2026-02-22-recursive-challenger-session-68-autonomous-improvement-loop|Session 68: Recursive Challenger]] — autonomous improvement loop applying recursive adversarial challenge to the compound engineering process itself
- [[2026-02-16-fix-3-reasoning-inference-option-b|Fix #3: Reasoning Inference Option B]] — chose keyword-matching with honest 60% confidence, aligning with adversarial review's transparency principle
- [[2026-02-16-phases-4b-7-master-execution-plan-revised|Phases 4B-7 Master Execution Plan]] — comprehensive adversarial review identified 18 risks, shifted timeline from 6 to 10 weeks, and deferred Phase 5 ML
- [[2026-02-16-phases-4b-7-stakeholder-decision-brief|Phases 4B-7 Stakeholder Decision Brief]] — executive brief presenting three execution options derived from adversarial review findings
- [[2026-02-20-session-58-cosmic-fire-module-retrospective|Session 58: Cosmic Fire Retrospective]] — integration theater detection is a concrete application of adversarial review methodology
- [[2026-02-20-session-59-compound-engineering-complete|Session 59: Compound Engineering Complete]] — adversarial validation resolved integration theater from Session 58
- [[2026-02-11-session-55-pause-push-conduct-retrospective-before-github-deployment|Session 55: Pause Push for Retrospective]] — pausing deployment for retrospective exemplifies adversarial review before irreversible action
- [[2026-02-14-phase-6d-decision-quality-scoring-complete|Phase 6D: Decision Quality Scoring]] — the contradiction component in quality scoring identifies decisions needing adversarial re-examination

## Related Decisions

- [[2026-03-05-separate-cohezion-a-from-cohezion-b|Two Cohezions]] — adversarial review validated internal consistency but missed the "cold reader" test: does the framing make sense to someone outside the system?
- [[2026-02-17-phase-2-service-initialization-gap-discovery]] — adversarial review uncovered the service initialization gap that would have caused Phase 2 integration failure
- [[2026-02-10-operational-forensics-compound-engineering]] — operational forensics as adversarial investigation methodology applied to compound engineering failures
- [[gemini-cli-ai-employees-agent-factory]] — Gemini CLI agent factory demonstrates adversarial review at the agent deployment level

## Related Patterns

- [[pattern-compound-engineering]] — the compound engineering pattern that institutionalizes adversarial review as a mandatory phase gate
- [[implementation-first-infrastructure-later]] — implementation-first reduces the blast radius of adversarial review catches by validating early
- [[private-to-public-rename-drift]] — adversarial review of rename PRs catches missed call sites before they become runtime errors
- [[production-ready-definition-checklist]] — the Session 57 adversarial review that discovered 8 P0 blockers motivated this production readiness checklist
- [[staged-validation-long-horizon-tasks]] — each stage gate uses adversarial review as the validation mechanism for GO/NO-GO decisions

## Missions

- ADVERSARIAL_PORTFOLIO_REVIEW_20260225 — Five-perspective adversarial audit of the Cohezion portfolio
- CONSTITUTION — Integration theater detection and technical honesty principles
- RETROSPECTIVE_ANTHROPIC_PORTFOLIO — Adversarial audit ensuring 100% technical honesty

## Session References

- [[SESSION-44-CONTINUATION-FINAL-STATUS]] — honest status assessment caught inflated claims from multiple teammates
- [[SESSION-44-FINAL-REPORT]] — cost-optimizer's integrity check as adversarial review against inflated metrics
- [[SESSION-44-FINAL-SUMMARY]] — independent verification and quality gate discipline modeled as adversarial review
- [[SESSION-44-HONEST-FINAL-METRICS]] — cost-optimizer's integrity check functioned as adversarial quality gate

## Agent Outputs

- [[adversarial-review]] — Adversarial Review: Compound Engineering Agent Swarm
- ADVERSARIAL_REVIEW — Adversarial Review (specialist infrastructure and full-repo showcase sessions)
- adversarial_assessment — Adversarial Assessment of simulation and benchmarking strategies
- adversarial_audit — Adversarial Audit of implementation quality
- adversarial_audit_plan — Adversarial Audit Plan for token-efficient compound engineering
- adversarial_audit_report — Adversarial Audit Report findings
- adversarial_review_tsunami — Adversarial Review Tsunami (stress-test scenario analysis)
- RECURSIVE_POLISH_REPORT — Recursive polish report
- MULTIAGENT_ADVERSARIAL_REVIEW — Multiagent adversarial review: experience persistence

## Daily References

- [[2026-02-10-adversarial-findings-summary]] — key findings summary from 4 independent Haiku adversarial reviewers: unanimous "DO NOT PROCEED"
- [[2026-02-10-adversarial-review-synthesis]] — synthesis of compound node linking plan vulnerabilities exposed by 4 reviewers

## Skills

- ADVERSARIAL_TESTING_PRIME — Red teaming and adversarial prompting
- democratic_debate — Diverse AI personas for critique
- TESTING_PRIME — Adversarial testing methodology
