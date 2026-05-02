---
name: kaggle-compound-prime
description: "Systematic approach to entering and winning Kaggle competitions using the Cohezion Compound Loop, Ouroboros failure recovery, and Mycelium test coverage."
---

# SKILL: KAGGLE_COMPOUND_PRIME

## DOMAIN EXPERTISE
Systematic approach to entering and winning Kaggle competitions using the Cohezion Compound Loop, Ouroboros failure recovery, and Mycelium test coverage.

## KEY TEXTS & CONCEPTS
- **Alignment Gate First**: Check competition alignment (deadline, prize size, team count, skill match) before committing resources.
- **Experience-Driven Selection**: Use journey tracker data from past competitions to inform strategy.
- **Ouroboros Monitoring**: Detect submission failures and synthesize healing patches.
- **Mycelium Coverage**: Generate tests for submission code before shipping.
- **V-Model Engineering**: Requirements → Design → Architecture → Implementation → Unit Test → Integration Test → System Test → Validation.

## INSTRUCTION
1. **Alignment Gate**: Score competition by `prize / (teams * weeks_remaining * effort_estimate)`. Proceed only if `alignment_score > 0.5`.
2. **Requirements Phase**: Define acceptance criteria (e.g., "notebook runs on Kaggle CPU in <60s", "uses allowed models only").
3. **Design Phase**: Pick the Compound Loop components to apply (Crisis Response, ARC Solver, etc.).
4. **Architecture Phase**: Use mycelium to scaffold testable modules. Use ouroboros to plan failure modes.
5. **Implementation Phase**: Build with `uv run` locally, then package for Kaggle.
6. **Unit Test Phase**: Mycelium generates tests for each primitive/function.
7. **Integration Test Phase**: Run full notebook pipeline end-to-end.
8. **System Test Phase**: Validate on Kaggle Kernel environment (no internet, no GPU if not requested).
9. **Validation Phase**: Check output format, metrics, and narrative quality.
10. **Submission**: Push via `kaggle kernels push`. Monitor with Ouroboros for failure analysis.

## ACCEPTANCE CRITERIA CHECKLIST
- [ ] Notebook imports run without `ModuleNotFoundError`
- [ ] No internet-dependent calls in final cell
- [ ] Output file matches competition format exactly
- [ ] README/blog post explains compound engineering angle
- [ ] Skill refinement loop is demonstrated (not just described)
- [ ] Visual metrics dashboard included

## VERSION
v1.0 — Derived from Gemma-4-Good session

## SEE ALSO
- COMPOUND_ENGINEERING_PRIME
- SYSTEMS_ENGINEERING_VMODEL
- OUROBOROS_LOOP_PRIME
- MYCELIUM_COVERAGE_PRIME
