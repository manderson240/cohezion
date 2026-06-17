---
name: vmodel-sr1-integration-test-pattern
description: |
  V-model SR1 integration test pattern: use the REAL class under test with only the
  external I/O boundary mocked. Gives genuine math/logic coverage at integration level.
  Use when: (1) building SR1/AD1 right-side V-model tests for compound components,
  (2) the class under test has real computation (math, sorting, MGPO weights) that must
  be exercised — NOT mocked, (3) only the vault/DB/network I/O boundary needs stubbing.
  Canonical example: SkillRefiner with real mgpo_weight()/prioritized_skills() + mocked
  VaultNeuronWriter.get_instance() → exercises the MGPO bell curve and sort order for real.
  Discriminating test: assert which skill is refined FIRST, not merely that refine() was called.
author: Claude Code
version: 1.0.0
---

# V-Model SR1 Integration Test Pattern

## Problem

MD-level unit tests (all mocks) prove wiring but not computation. If you mock `SkillRefiner`
entirely, a broken MGPO formula still passes every mock-based test. You need SR1-level
tests that run the real implementation to catch formula bugs, wrong sort order, or
accumulator mis-wiring — while keeping tests fast and deterministic.

## Pattern

**Layer 1 (real):** The class under test with its actual logic intact.
**Layer 2 (mocked):** The external I/O boundary (vault, DB, network, file system).

```python
def test_boundary_skill_refined_first():
    mock_vnw = MagicMock()
    mock_vnw.query_category_success_rate.side_effect = {
        "boundary_skill": 0.50,
        "mastered_skill": 1.00,
    }.get

    with patch(
        "cohezion.compound.skill_refiner.VaultNeuronWriter.get_instance",
        return_value=mock_vnw,
    ):
        refiner = SkillRefiner(mcp_client=None)   # REAL SkillRefiner
        refine_calls = []
        refiner.refine = lambda skill_name, **kwargs: refine_calls.append(skill_name)

        ex = CompoundExecutor(
            mcp_client=None,
            skill_refiner=refiner,        # REAL refiner injected
            enable_skill_refinement=True,
            enable_guardrails=False,
        )
        ex._recent_skill_names = ["boundary_skill"] * 5 + ["mastered_skill"] * 5
        ex._batch_mgpo_refine(top_k=2)

    assert refine_calls[0] == "boundary_skill"  # DISCRIMINATING: first, not just called
```

## Discriminating Test Requirement

A test that only checks `refine.call_count > 0` passes even with a broken MGPO sort.
The discriminating assertion is: **which skill appears at index 0** in the call list.
Any plausible wrong implementation (alphabetical, random, LIFO) would fail this check.

## Patch Target for ClassMethod Singletons

Patching a classmethod on the class object itself works regardless of import site:
```python
# Both of these patch the same object — pick the import site in the consumer module
patch("cohezion.compound.skill_refiner.VaultNeuronWriter.get_instance", ...)
patch("cohezion.learning.vault_neuron_reader.VaultNeuronWriter.get_instance", ...)
```

## When NOT to Use

- MD-level unit tests where you want to isolate one method: use full MagicMock
- Tests that hit CLR gate on toy content: see `clr-gate-test-isolation` skill instead
- Tests that need real DB: use pytest fixtures with real SurrealDB connection

## Reference Implementation

`tests/compound/test_mgpo_system_integration.py` — 9 SR1 tests, all pass in <1s.
Covers: weight computation, symmetry, sort order, top-K refine, accumulator drain,
threshold firing.
