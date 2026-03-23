---
title: Implementation First, Infrastructure Later
date: 2026-02-23
tags: [methodology, compound-engineering, decision, token-efficiency]
related_concepts: [token-efficiency, compound-engineering, meta-learning, token-efficiency-patterns, adversarial-review]
status: active
aspect: knower
neural:
  activation: 0.8
  stage: growing
  synapse_in: 13
  synapse_out: 8
---

# Implementation First, Infrastructure Later

Implementation-first is a core Cohezion development principle: build one working feature and validate it before adding infrastructure, tests, documentation, or scaffolding. The principle was extracted from the Kyutai postmortem, where 61K tokens were spent on API documentation, placeholder tests, and dependency research before any implementation -- producing 0% functional output. The corrective pattern: copy a working template, implement the single most important feature first, validate it manually, then add tests and infrastructure incrementally.

The principle reflects a fundamental asymmetry: infrastructure cost is low if the feature works (adding tests and docs to working code is straightforward), but very high if the feature doesn't work (all infrastructure must be discarded and redone). Validating the implementation first eliminates the high-risk scenario.

## Theoretical Foundations

Implementation-first is a concrete instantiation of several well-established software engineering principles:

**YAGNI (You Aren't Gonna Need It)** -- Coined by Ron Jeffries as part of Extreme Programming (XP), YAGNI states that features should only be added when required. Don't build infrastructure, abstractions, or extension points "just in case." The cost of building something unnecessary is not just the time spent building it, but the ongoing maintenance burden and the complexity it adds to every future change.

**Lean Startup / MVP** -- Eric Ries's build-measure-learn feedback loop mandates building the smallest possible thing that validates a hypothesis. The classic example: Zappos validated online shoe demand by photographing local store inventory and posting it online before building any e-commerce infrastructure. Implementation-first applies the same logic to engineering tasks -- validate the core feature before investing in supporting infrastructure.

**Last Responsible Moment** -- From lean software development: defer decisions until the last responsible moment, when you have the most information. Infrastructure decisions made before the implementation works are based on assumptions. Decisions made after have the benefit of concrete knowledge about what the system actually needs.

## Key Properties

- **Asymmetric risk**: Infrastructure cost is low when the feature works (incremental addition), but very high when it doesn't (total discard). Implementation-first eliminates the high-cost scenario.
- **Validated starting points**: Copy working templates rather than building from scratch. The `cloud-vault-mcp` server is the canonical template for new MCP servers in Cohezion.
- **Incremental infrastructure**: After the feature is validated, add tests, documentation, CI integration, and monitoring incrementally -- each addition is cheap when the foundation is solid.
- **Token efficiency**: In agentic AI sessions, premature infrastructure wastes context tokens on scaffolding that may be discarded. Implementation-first maximizes the ratio of useful output per token spent.

## Anti-Patterns (What To Avoid)

1. **Scaffold-first**: Spending hours setting up project structure, CI/CD, linting, documentation templates before writing a single line of business logic.
2. **Placeholder tests**: Writing test files with `pass` or `TODO` bodies before the implementation exists. These create false confidence and waste tokens.
3. **Dependency research spirals**: Exhaustively researching every possible library and approach before writing any code. Research should be just-in-time, driven by concrete implementation needs.
4. **Premature abstraction**: Creating generic interfaces, plugin systems, or configuration layers before having even one concrete use case.

## Enforcement in Cohezion

In Cohezion sessions, this pattern is enforced via the RequestAlignmentAnalyzer: before executing any significant task, the analyzer checks whether the approach is validated-first or infrastructure-first. The `cloud-vault-mcp` server is explicitly documented as the template to copy when building new MCP servers -- the pre-validated starting point that makes implementation-first tractable.

## Primary Sources

- Ron Jeffries (1998). *You Aren't Gonna Need It*. XP principle. [https://ronjeffries.com/xprog/articles/practices/pracnotneed/](https://ronjeffries.com/xprog/articles/practices/pracnotneed/)
- Eric Ries (2011). *The Lean Startup*. Crown Business. Build-measure-learn feedback loop and MVP methodology.
- Mary Poppendieck and Tom Poppendieck (2003). *Lean Software Development*. Addison-Wesley. "Last responsible moment" decision principle.

## Related
- [[pattern-implementation-first-infrastructure-later]] -- the pattern file with code-level implementation guide
- [[token-efficiency]] -- the economic principle implementation-first serves
- [[token-efficiency-patterns]] -- collection of patterns this is part of
- [[meta-learning]] -- this principle was extracted via meta-learning from the Kyutai postmortem
- [[compound-engineering]] -- implementation-first is one of the core compound engineering principles
- [[concept-testing]] -- validates that implemented features actually work before adding infrastructure
- [[honest-metrics-over-inflated-claims]] -- related principle of measuring real output rather than activity
- [[2026-02-12-phase-0-foundation-complete|Phase 0 Foundation Complete]] -- Phase 0 validates the foundation before scaling infrastructure

## Relevance to Cohezion

Implementation-first is not just a coding principle -- it is the economic foundation of token-efficient agentic work. Every Cohezion session operates under a finite context budget. Spending tokens on infrastructure that may be discarded is a direct cost to the project. By validating the implementation first, agents ensure that every subsequent token spent on tests, documentation, and CI integration produces lasting value rather than throwaway scaffolding.

The principle was extracted through [[meta-learning]] from the Kyutai postmortem incident and codified as one of the core [[compound-engineering]] practices. Its enforcement through the RequestAlignmentAnalyzer makes it a systemic guardrail rather than a suggestion.

## Skills

- FAIL_FAST_PRIME -- Ship minimal viable implementations
