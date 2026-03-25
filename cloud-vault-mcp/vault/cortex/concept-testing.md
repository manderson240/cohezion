---
title: "Concept Testing"
date: 2026-02-19
tags: [concept, compound-engineering, knowledge-graph-systems, adversarial-review]
related_concepts: [concept-validation, adversarial-review, knowledge-graph-systems, compound-engineering]
aspect: knower
neural:
  activation: 0.99
  stage: mature
  synapse_in: 61
  synapse_out: 80
---
## Definition

Concept testing in Cohezion refers to the practice of validating that a knowledge concept is correctly captured, accurately described, and genuinely useful before it becomes a permanent node in the knowledge graph. A concept note that contains incorrect information or misleading descriptions compounds negatively — it gets injected into agent contexts, biases decisions, and generates downstream errors that are hard to trace back to the faulty source.

The key testing practices are: checking the concept definition against primary sources (does it accurately represent the paper or pattern it describes?), verifying wiki-links point to existing notes (no broken links), confirming the `related_concepts` frontmatter matches actual relationships, and validating that the concept is self-contained enough to be useful when retrieved without the full graph. The [[adversarial-review]] pattern applies here — assume the concept note is wrong and verify it.

In Cohezion's compound engineering workflow, concepts are tested as part of the vault enrichment process. Newly created or auto-generated stub notes are reviewed for accuracy, expanded with verified content, and cross-linked to related notes. The SurrealDB import pipeline validates concept metadata against schema before ingestion, acting as a programmatic concept test.

## Key Properties

- **Accuracy verification**: Concept definitions checked against primary sources
- **Link validation**: Wiki-links verified to point to existing, correctly named notes
- **Self-containment check**: Concept useful in isolation without requiring linked notes
- **Schema validation**: Frontmatter fields (tags, related_concepts, date) match expected types
- **Cross-link consistency**: If A links to B, B should know about A (bidirectional awareness)

## Related Papers

- [[2026-02-09-lessons-integration-complete]]
- [[ai_for_good]]
- [[benchmarking]]
- [[conclusion]]
- [[data_engineering]]
- [[dl_primer]]
- [[dnn_architectures]]
- [[efficient_ai]]
- [[frameworks]]
- [[frontiers]]
- [[hw_acceleration]]
- [[introduction]]
- [[lesson-01-agent-has-great-content-but-claude-code-only-auto-reads]]
- [[lesson-02-ruff-auto-formats-on-save-re-read-files-before-editing-ha]]
- [[lesson-03-critical]]
- [[lesson-04-surgery-lesson]]
- [[lesson-05-surrealdb]]
- [[lesson-06-ollama-latency]]
- [[lesson-07-gtt-carveout-illusion]]
- [[lesson-08-import-graph]]
- [[lesson-09-ruff-hook-fights]]
- [[lesson-10-gitlab-ci-runner]]
- [[lesson-11-team-agent-efficiency]]
- [[lesson-12-layered-validation]]
- [[lesson-13-8-6m-file-incident]]
- [[lesson-14-cleanup-is-multi-pass]]
- [[lesson-15-system-lockup-2026-01-27]]
- [[lesson-16-pre-commit-hooks-stage-override]]
- [[lesson-17-stale-branch-mining]]
- [[lesson-18-mock-live-services-in-tests]]
- [[lesson-19-session-awareness-protocol]]
- [[lesson-20-ci-scope-discipline]]
- [[lesson-21-runtime-json-pollution]]
- [[lesson-22-gitignore-ordering]]
- [[lesson-23-stash-branch-switch-hazard]]
- [[lesson-24-yaml-folded-scalar-trap]]
- [[lesson-25-uv-venv-contention]]
- [[lesson-26-never-print-credentials]]
- [[lesson-27-hook-file-revert]]
- [[lesson-28-non-critical-tracking-pattern]]
- [[lesson-29-batch-cache-two-phase]]
- [[lesson-30-holographic-projection-fallback]]
- [[lesson-31-operation-specific-modulation]]
- [[lesson-32-concurrent-pytest-contention]]
- [[lesson-33-skill-keyword-matching-is-broad]]
- [[lesson-34-test-hang-unmocked-live-service]]
- [[lesson-35-non-blocking-observability-pattern-new]]
- [[lesson-36-mcp-configuration-requires-end-to-end-test-new]]
- [[lesson-37-experience-guided-execution-works-new]]
- [[lesson-38-singleton-executor-for-sessions-new]]
- [[ml_systems]]
- [[ondevice_learning]]
- [[ops]]
- [[optimizations]]
- [[privacy_security]]
- [[responsible_ai]]
- [[robust_ai]]
- [[sustainable_ai]]
- [[training]]
- [[workflow]]

## Related Concepts

- [[concept-validation]] — the formal validation process for concept accuracy
- [[adversarial-review]] — the review pattern applied to concept definitions
- [[knowledge-graph-systems]] — the graph that tested concepts form nodes in
- [[compound-engineering]] — the methodology concept testing serves
- [[2026-02-09-phase-5b-production-readiness-validation|Phase 5B Production Readiness Validation]] — 955+ tests with 100% pass rate demonstrating comprehensive testing across 5 production components

## Related Decisions

- [[2026-02-17-phase-2-service-initialization-gap-discovery]] — adversarial review of Phase 2 discovered untested service initialization gaps; concept testing would have caught this earlier

## Key Lesson Links

- [[lesson-18-mock-live-services-in-tests]] — all external service calls in unit tests MUST be mocked; integration tests run separately
- [[lesson-34-test-hang-unmocked-live-service]] — unmocked live services cause indefinite test hangs; set explicit timeouts as a safety net
- [[lesson-32-concurrent-pytest-contention]] — parallel pytest workers sharing resources cause flaky tests; use worker-unique resource identifiers

- [[test-isolation-via-singleton-reset]] — singleton reset is a specific testing technique for isolating tests that depend on shared singleton services
- [[DecisionHealthDashboard]] — decision health monitoring applies concept testing principles (staleness detection, consequence validation) to decisions

## Related Patterns

- [[MockPattern]] — mock pattern using vector similarity for testing semantic search components
- test_routing_pattern — test routing pattern for validating request routing in agent pipelines
- [[ADOPTION_CHECKLIST]] — applies analogous quality-gate methodology to code pattern adoption across teams
- [[test-mocking-pattern]] — analogous testing methodology for code; both ensure correctness before integration
- [[agent-logs-schema-validation]] — validation checklist pattern applied to agent log structure
- [[2026-02-22-post-crash-venv-recovery-pytest-missing-despite-pyprojecttoml|Post-Crash Venv Recovery]] — venv recovery is a prerequisite for running concept and integration tests
- [[2026-02-23-one-coherent-model-beats-two-partial-implementations|One Coherent Model]] — conflicting test fixtures from dual models demonstrate how architectural ambiguity breaks test infrastructure

## Related from Patterns

- [[sanitize-env-var-path-components]] — validating sanitized components is a form of concept correctness testing applied to security
- [[private-to-public-rename-drift]] — rename validation is analogous to concept testing: verify all references point to the correct target after changes
- [[production-ready-definition-checklist]] — production readiness checks apply concept testing rigor to deployment artifacts
- [[staged-validation-long-horizon-tasks]] — stage gate criteria use the same evidence-gated validation principle

## Missions

- REPOSITORY_HEALTH_PRIME — Automated detection thresholds and CI/CD governance checks

## Agent Outputs

- **TDD Compound Engineering** — `Agents/Antigravity/1fe20157-e5b9-4b89-bde5-6ba19bdf00b7/task.md`
- **Concurrency and Reliability Patterns** — `Agents/Antigravity/56ccc7b5-420d-4fa7-bffe-50170bab9888/task.md`
- **Validate VLIW Optimization Solution** — `Agents/Antigravity/ae6acabc-a484-4e15-833b-207833b158e4/task.md`
- **Package and Review Anthropic Challenge Results** — `Agents/Antigravity/95a4975b-2b7b-427a-9625-1c2e1d95b815/task.md`

## Relevance to Cohezion

Concept testing is integral to vault quality. Auto-generated stub notes are created with placeholder content; concept testing is the process of replacing placeholders with verified, accurate definitions. The vault enrichment sessions (like the one generating this content) are concept testing sessions in practice — reading primary sources and lessons, verifying accuracy, and updating notes with substantiated definitions. Quality concepts are what make `vault_find_relevant_context` reliable rather than misleading.

## Session References

- [[SESSION-46-COMPLETE]] — independent verification confirming Phase 6.2 completeness via test execution
- [[session-46-test-isolation-and-phase-2-security]] — test suite stabilization from 98.3% to 99.0% via systematic isolation fixes

## Skills

- ADVERSARIAL_TESTING_PRIME — Systematic testing at scale
- code_standards — Static analysis and type checking
- FAIL_FAST_PRIME — Early testing and rapid iteration
- MYCELIUM_PRIME — Autonomous test synthesis
- pre_flight_validation — Systematic dependency checking
- REPOSITORY_HEALTH_PRIME — Pre-commit hooks and automated monitoring
- RIGOROUS_EVALUATION_PRIME — Objective physics-grounded benchmarks
- TESTING_PRIME — Python pytest patterns and coverage
- visual_validation — Visual UI validation automation
- test_automation — Watchdog-based test framework for monitoring and validating automated processes
