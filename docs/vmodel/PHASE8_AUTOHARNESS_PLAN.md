# V-Model Phase 8 — AutoHarness Verification Spec

**Workstream:** feat/autoharness-vmodel-wave1
**Date:** 2026-05-02
**Pairs with:** `scripts/validation/vmodel/phase8_autoharness_harness.py`, `scripts/ci/validate_skills.py`

## 1. Requirement

Ensure generated agent stubs, config dataclasses, and skill descriptions are structurally valid
before they enter the compound session pipeline. The TemplateEngine (`src/cohezion/core/template_engine.py`)
emits Python source code from PRIME skill `.md` definitions — any regression here produces silent
runtime failures in downstream agents.

## 2. Invariants

### P1 — Valid Python Stubs (existing)

**Claim:** All 225 skills generate valid Python agent stubs.
**Status:** Currently true (verified by `scripts/ci/validate_skills.py`).
**Verification:** `compile()` each stub in `"exec"` mode; count syntax errors.

### P2 — Valid Registry Paths (existing)

**Claim:** All 125 registry entries have valid file paths.
**Status:** Currently true (verified by `scripts/ci/validate_registry.py`).
**Verification:** Cross-check registry JSON keys against `src/cohezion/skills/*.md` glob.

### P3 — Agent Stubs Compile for All Generated Skill Agents (NEW)

**Claim:** Both agent stub variants (`generate_agent_stub` and `generate_executable_agent`)
compile without syntax error for every skill.
**Status:** Not yet verified — `validate_skills.py` only checks `generate_agent_stub`.
**Risk:** `generate_executable_agent` has a more complex code path with `InstructionExpander`,
plan serialization, and quoting — a regression here is undetected.

**Verification method:**
1. Parse all skills via `TemplateEngine.parse_all()`.
2. For each `SkillSpec`, call `engine.generate_executable_agent(spec)`.
3. `compile()` the output in `"exec"` mode.
4. Report each failure with skill name and SyntaxError details.

### P4 — Config Dataclasses Have No Duplicate Field Names (NEW)

**Claim:** Every generated `@dataclass` config class has unique field names.
**Status:** Not yet verified.
**Risk:** The `_concept_name_to_field()` function normalizes concept names (lowercase, collapse
underscores). Two distinct concept names like "Max Tokens" and "MAX_TOKENS" both map to
`max_tokens` — the dataclass silently overwrites the first field.

**Verification method:**
1. For each `SkillSpec`, call `engine.generate_config_class(spec)`.
2. Parse the generated source to extract `@dataclass` field annotations.
3. Check for duplicate field names via a set comparison.
4. Report each duplicate with the skill name and offending fields.

### P5 — Skill Descriptions Don't Exceed 500 Chars (NEW)

**Claim:** No skill `domain_expertise` description exceeds 500 characters.
**Status:** Not yet verified.
**Risk:** Runaway generation or poorly formatted `.md` files can produce multi-thousand-character
domain strings. These bloat `SYSTEM_PROMPT` constants in generated agents, inflating token costs
and potentially causing context-window failures.

**Verification method:**
1. For each `SkillSpec`, measure `len(spec.domain_expertise)`.
2. Flag any skill where it exceeds 500 characters.
3. Report the skill name and actual length.

## 3. Harness Integration

The verification harness (`scripts/validation/vmodel/phase8_autoharness_harness.py`) accepts
a target file argument and delegates to the CI validation scripts. Output format:

```json
{
  "passed": true,
  "file": "scripts/ci/validate_skills.py",
  "checks": [
    {"check": "p1_valid_stubs", "passed": true, "elapsed_s": 0.1, "detail": "225/225 compiled"},
    {"check": "p3_executable_agents", "passed": true, "elapsed_s": 0.3, "detail": "225/225 compiled"},
    {"check": "p4_unique_fields", "passed": true, "elapsed_s": 0.2, "detail": "0 duplicates found"},
    {"check": "p5_description_length", "passed": true, "elapsed_s": 0.1, "detail": "0 over 500 chars"}
  ],
  "elapsed_s": 0.7
}
```

## 4. Verification Gates

- **Gate G1:** `scripts/validation/vmodel/phase8_autoharness_harness.py scripts/ci/validate_skills.py` exits 0.
- **Gate G2:** All five invariants (P1–P5) report `"passed": true`.
- **Gate G3:** Harness output is valid JSON parseable by CI pipeline.
