---
title: Concept Validation
date: 2026-02-23
tags: [methodology, testing, compound-engineering, knowledge-graph-systems]
related_concepts: [concept-testing, adversarial-review, knowledge-graph-systems, compound-engineering]
status: active
aspect: knower
neural:
  activation: 0.94
  stage: growing
  synapse_in: 40
  synapse_out: 16
---

# Concept Validation

Concept validation is the process of verifying that a concept note accurately, completely, and usefully represents the underlying knowledge it describes. Where [[concept-testing]] checks structural properties (links work, schema is valid), concept validation verifies semantic accuracy: does the definition match what the primary sources actually say? Are the key properties correct? Would an expert in the domain recognize the description as accurate?

Validation matters because the vault is not just a reference document — it is injected into agent contexts to ground execution decisions. An inaccurate concept note is worse than no note: it actively misleads agents, biasing their reasoning toward incorrect assumptions. Validation serves as the quality gate that keeps the [[knowledge-graph-systems]] trustworthy as it grows.

The validation process in Cohezion mirrors the software TDD cycle: a concept is a "test" of the underlying knowledge, and validation is confirming the test is actually testing the right thing. Adversarial review (assume the definition is wrong, find counter-evidence) is the most effective validation technique for concepts with non-obvious definitions.

## Related
- [[adversarial-review]]
- [[lesson-12-layered-validation]] — layered validation is the architectural pattern that makes concept validation reliable across system boundaries
- [[lesson-36-mcp-configuration-requires-end-to-end-test-new]] — configuration validation requires end-to-end client tests; unit tests miss protocol negotiation failures
- [[circleci-ai-cicd-validation]] — CI/CD autonomous validation agents implement concept validation as automated pipeline gates
- [[concept-validation]] validates concepts before they enter the knowledge graph, parallel to how testing patterns validate code before deployment
- [[2026-02-09-phase-5b-production-readiness-validation|Phase 5B Production Readiness Validation]] — applied layered validation with 4 independent reviewers converging on identical findings
- [[agent-logs-schema-validation]] — applies this validation methodology to agent log frontmatter and content structure
- [[2026-02-14-phase-6d-decision-quality-scoring-complete|Phase 6D: Decision Quality Scoring]] — quality scoring is a form of concept validation applied to decision records

## Related Patterns

- [[production-ready-definition-checklist]] — production readiness validation applies the same evidence-gated verification principle as concept validation
- [[staged-validation-long-horizon-tasks]] — stage gate criteria use the same evidence-gated validation methodology for GO/NO-GO decisions

## Missions

- ADVERSARIAL_PORTFOLIO_REVIEW_20260225 — Programmatic verification of portfolio claims against evidence
- REPOSITORY_HEALTH_PRIME — Pre-commit hooks and size threshold validation patterns

## Session References

- [[SESSION-44-CONTINUATION-FINAL-STATUS]] — independent verification confirming actual vs claimed project state
- [[SESSION-44-FINAL-REPORT]] — verified file existence and test results as evidence-gated validation
- [[SESSION-44-FINAL-SUMMARY]] — SessionPersistence gap identified through file existence verification
- [[SESSION-44-HONEST-FINAL-METRICS]] — verification methodology: run tests, check files, report actual numbers

## Skills

- api_patterns — Pydantic validation patterns
- pre_flight_validation — Pre-flight system validation
- self_evaluation — Automated quality evaluation
- visual_validation — UX auditing and integrity checks
