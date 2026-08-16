---
name: hookify-rule-engine
description: Universal Hookify Rule Engine with MCP bridge for cross-platform (Opencode, Claude Code, Gemini CLI) support. Implements persistent rules with configurable levers, three-tier persistence, and recursive learning.
metadata:
  version: "1.0.0"
  domain: compound-engineering
  author: Cohezion Team
  created: 2026-03-23
  tags: [hookify, rules, mcp, cross-platform, persistence, ralph-loop]
---

# SKILL: HOOKIFY_PRIME

## DOMAIN EXPERTISE

You are a specialist in **Hookify Rule Systems** - a universal framework for defining, persisting, and executing configurable rules across multiple AI coding platforms. You understand:

1. **Rule Definition Architecture**: Three-tier persistence (Git → SurrealDB → Vault)
2. **Cross-Platform Execution**: Native Opencode + MCP bridge for Claude Code/Gemini CLI
3. **Lever Configuration**: Thresholds, booleans, enums, scalars with override precedence
4. **Ralph Loop Integration**: HIHO coherence gates for cosmological task orchestration
5. **Adversarial Validation**: Multi-perspective code review with adversarial testing

## PURPOSE

Hookify provides **persistent, configurable, cross-platform rule enforcement** for compound engineering workflows:

- **Rule Definitions**: Human-readable markdown in `.agent/HOOKIFY_RULES.md`
- **Configurable Levers**: Runtime-adjustable parameters (thresholds, booleans, scalars)
- **Three-Tier Persistence**: Git (defaults) → SurrealDB (runtime) → Vault (history)
- **Cross-Platform**: Works on Opencode (native), Claude Code (hooks), Gemini CLI (MCP)
- **Recursive Learning**: Rules self-refine based on execution outcomes
- **TDD Integration**: Rule validation with adversarial test generation

## ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────┐
│                    UNIVERSAL HOOKIFY                             │
├─────────────────────────────────────────────────────────────────┤
│  Platform Layer                                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │  Opencode    │ │ Claude Code  │ │ Gemini CLI   │             │
│  │  (Native)    │ │  (Hooks/MCP) │ │  (MCP)       │             │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘             │
│         │                │                │                      │
│         └────────────────┼────────────────┘                      │
│                          │                                       │
│  ┌───────────────────────┴───────────────────────┐               │
│  │         MCP Bridge Server                     │               │
│  │  (hookify_mcp_server.py)                     │               │
│  └───────────────────────┬───────────────────────┘               │
│                          │                                       │
│  Core Engine Layer                                               │
│  ┌─────────────────────────────────────────────┐                 │
│  │  HookifyValidator                           │                 │
│  │  - Rule parsing                           │                 │
│  │  - Condition evaluation                   │                 │
│  │  - Action execution                       │                 │
│  │  - Lever resolution                       │                 │
│  └─────────────────────┬─────────────────────┘                 │
│                        │                                         │
│  Persistence Layer                                               │
│  ┌──────────┬──────────┬──────────┐                           │
│  │   Git    │ SurrealDB│  Vault   │                           │
│  │ (Tier 1) │ (Tier 2) │ (Tier 3) │                           │
│  │ Defaults │ Runtime  │ History  │                           │
│  └──────────┴──────────┴──────────┘                           │
└─────────────────────────────────────────────────────────────────┘
```

## RULE DEFINITION FORMAT

Rules are defined in `.agent/HOOKIFY_RULES.md`:

```markdown
## Rule: cosmological_ralph_loop
- **ID**: cosmological_ralph_loop
- **Trigger**: session_start
- **Condition**: goal.matches("cosmology|solver|universe")
- **Action**: ralph_loop.orchestrate
- **Levers**:
  - coherence_threshold: 0.5  # float, range 0.0-1.0
  - max_iterations: 20         # int, range 1-100
  - auto_commit: true          # bool
  - witness_plate: "vault/hippocampus/changelog-{session_id}.md"  # enum
  - fallback_action: "decompose_request"  # enum
- **Adversarial Tests**:
  - test_cosmological_convergence
  - test_hiho_stability
  - test_witness_plate_creation
```

## THREE-TIER PERSISTENCE

### Tier 1: Git (`.agent/HOOKIFY_RULES.md`)
- Version-controlled rule definitions
- Immutable default lever positions
- Cross-platform sync via git

### Tier 2: SurrealDB (`hookify_rules` table)
- Runtime lever overrides
- Session-specific configurations
- Fast query (< 5ms)

### Tier 3: Vault (`vault/prefrontal/hookify-decisions/`)
- Rule change decisions
- Violation patterns
- Effectiveness retrospection
- Cross-session learning

## LEVER RESOLUTION PRECEDENCE

1. **Environment variables** (highest): `HOOKIFY_{RULE_ID}_{LEVER_NAME}`
2. **SurrealDB runtime**: Session/user-specific overrides
3. **Git defaults**: `.agent/HOOKIFY_RULES.md` base values

## CROSS-PLATFORM TRIGGERS

| Trigger | Opencode | Claude Code | Gemini CLI |
|---------|----------|-------------|------------|
| session_start | `CompoundSessionManager.start_session()` | `CLAUDE.md` load | `GEMINI.md` load |
| pre_execute | `CompoundSessionManager.check_alignment()` | `pre_execute` hook | MCP `pre_execute` tool |
| post_execute | `CompoundExecutor.execute_task()` | `post_execute` hook | MCP `post_execute` tool |
| pre_commit | Git pre-commit | Native hooks | Shell wrapper |

## INTEGRATION WITH COMPOUND ENGINEERING

Hookify integrates with the 11-step pipeline:

1. **Step 1.5**: `pre_execute` hook validates alignment
2. **Step 6.5**: `post_execute` hook logs to vault
3. **Step 7.3**: Retrospection extracts rule effectiveness
4. **Step 7**: Skill refinement updates rule definitions

## TDD WORKFLOW

```python
# 1. Write adversarial test FIRST
def test_cosmological_ralph_loop_convergence():
    """Test that Ralph Loop converges to HIHO within tolerance."""
    validator = HookifyValidator()
    context = {
        "goal": "Implement cosmological Boltzmann solver",
        "coherence": 0.3  # Below threshold
    }
    result = validator.validate("pre_execute", context)
    assert result.block is True
    assert "coherence" in result.violations[0].message

# 2. Run test (fails)
# 3. Implement rule engine
# 4. Run test (passes)
# 5. Adversarial review
# 6. Refine and repeat
```

## MULTI-PERSPECTIVE ADVERSARIAL REVIEW

Each rule undergoes review from three perspectives:

1. **Architect**: Does the rule align with system design?
2. **Engineer**: Is the implementation robust?
3. **Tester**: Are edge cases covered?

## RECURSIVE LEARNING

Rules self-improve via:

1. **Execution Logging**: Every validation logged to vault
2. **Pattern Extraction**: `RetrospectionEngine.analyze_execution_result()`
3. **Rule Refinement**: `SkillRefiner.refine()` updates `.agent/HOOKIFY_RULES.md`
4. **Consensus Validation**: `SkillConsensusVoter` validates changes

## IMPLEMENTATION STEPS

### Step 1: Create PRIME Skill (THIS FILE)
- [x] Define architecture
- [x] Specify rule format
- [x] Document persistence strategy

### Step 2: TDD Test Suite
- Write adversarial tests first
- Cover: rule parsing, lever resolution, action execution

### Step 3: Core Engine
- `HookifyValidator` class
- Rule parser from markdown
- Lever resolver with precedence

### Step 4: MCP Bridge
- `hookify_mcp_server.py`
- Tool definitions for validate, get_levers, set_lever

### Step 5: Platform Adapters
- Opencode: Native integration
- Claude Code: Hook scripts
- Gemini CLI: MCP client

### Step 6: Adversarial Review Harness
- Multi-perspective testing
- Automated review generation

### Step 7: Recursive Learning
- Vault integration for execution logs
- Retrospection hooks
- Automated rule refinement

## VERSION

v1.0.0 (Initial)

## SEE ALSO

- `HOOKIFY_RULES.md` (Rule definitions)
- `HOOKIFY_CONFIG.yaml` (Configuration)
- `tests/hookify/` (TDD test suite)
- `src/cohezion/hookify/` (Implementation)
- `src/cohezion/mcp/hookify_server.py` (MCP bridge)


## KEY CONCEPTS
- **Manifold Mapping**: Tracking 12D Poincaré state representation for HOOKIFY PRIME.
- **AutoHarness Invariants**: 0ms AST bytecode policy assertions (arXiv:2603.03329v1).
- **Deterministic Execution**: Zero-latency verification and sovereign local execution.


## INSTRUCTION

### 1. Initialize Context
```python
from cohezion.flume import PoincareManifoldND
from cohezion.agi.autoharness_policy import AutoHarnessPolicy

policy = AutoHarnessPolicy()
state = PoincareManifoldND.project([0.05] * 2048, target_dim=12)
```

### 2. Execute Deterministic Action
```python
# Verify state invariants with 0ms overhead
res = policy.verify_action("standard_execution", state)
assert res.allowed is True
```
