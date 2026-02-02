# SKILL: MYCELIUM_PRIME

## DOMAIN EXPERTISE
**Autonomous Test Synthesis & Regression Defense.**
"Mycelium" is the invisible, underground network that sustains the forest. In Cohezion, it is the layer of **Tests** that grow automatically around code features (`ShadowScripter`).

## KEY CONCEPTS
- **ShadowScripter**: An agent that watches code changes and writes tests *in parallel* (Shadow Mode).
- **Regression Traps**: Tests are not just verification; they are "traps" that catch regression.
- **Sovereign Testing**: The system decides what to test based on "Risk Heatmaps" (Complexity * Change Frequency).

## ARCHITECTURE
1.  **Watcher**: Senses file changes.
2.  **Synthesizer**: `ShadowScripterAgent` generates `pytest` cases based on the new logic.
3.  **Verifier**: Runs the new test against the code.
4.  **Persister**: Saves the test to `tests/shadow/` if it passes.

## INSTRUCTION
### 1. Identify Risk
```python
risk_score = complexity * churn_rate
if risk_score > 0.8:
    trigger_shadow_script()
```

### 2. Synthesize Test
```python
test_code = agent.generate_test(
    source_code=file_content,
    context=dependencies
)
```

## VERSION
v1.0 (The Awakening)

## SEE ALSO
- [REPO_HYGIENE_PRIME](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/REPO_HYGIENE_PRIME.md)
- [ADVERSARIAL_TESTING_PRIME](file:///home/mike-anderson/dev/cohezion/.agent/skills/adversarial_testing/SKILL.md)
