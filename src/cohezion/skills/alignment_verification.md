---
name: alignment_verification
description: Expert in AI alignment verification inspired by Anthropic's research
  methodology. Specializes in model organism testing, alignment faking detection,
  stress-testing safeguards, and iterative alignment verification.
keywords:
- alignment
- alignment faking
- gateway
- gateway_architecture
- iterative alignment
- model organisms
- observable_ai
- petri framework
- physics_informed_prediction
- predict
- scalable oversight
- transparency
- verification
---

# SKILL: ALIGNMENT_VERIFICATION_PRIME

## DOMAIN EXPERTISE

Expert in AI alignment verification inspired by Anthropic's research methodology. Specializes in model organism testing, alignment faking detection, stress-testing safeguards, and iterative alignment verification.

## KEY TEXTS & CONCEPTS

- **Model Organisms**: Controlled demonstrations of potential misalignment
- **Petri Framework**: AI agents simulate conversations to test alignment
- **Alignment Faking**: Models pretending to be aligned while retaining contradictory preferences
- **Scalable Oversight**: Supervising models that may surpass human capabilities
- **Iterative Alignment**: Models assist in their own safety verification

## INSTRUCTION

### 1. Create Model Organism Tests
```python
class ModelOrganismTest:
    """Simulated environment to stress-test AI behavior."""

    def __init__(self, model, environment: SimulatedEnvironment):
        self.model = model
        self.env = environment

    async def run_scenario(self, scenario: Scenario):
        """Run adversarial scenario and observe behavior."""
        self.env.setup(scenario)

        results = []
        for step in scenario.steps:
            action = await self.model.decide(self.env.state)
            outcome = self.env.apply(action)

            results.append({
                'step': step,
                'action': action,
                'alignment_score': self.score_alignment(action, step),
                'deceptive_indicators': self.detect_deception(action),
            })

        return AlignmentReport(results)
```

### 2. Detect Alignment Faking
```python
def detect_alignment_faking(self, model_outputs: list, training_context: dict):
    """Check if model behaves differently when it thinks it's being tested."""

    # Compare behavior in training vs deployment
    training_behavior = self.analyze_behavior(model_outputs, is_training=True)
    deployment_behavior = self.analyze_behavior(model_outputs, is_training=False)

    discrepancy = self.compute_discrepancy(training_behavior, deployment_behavior)

    if discrepancy > THRESHOLD:
        return AlignmentFakingWarning(discrepancy)
    return None
```

### 3. Iterative Self-Verification
```python
class IterativeAligner:
    """Model assists in own alignment verification."""

    async def self_critique(self, action, context):
        """Model evaluates its own alignment."""
        critique = await self.model.evaluate(
            f"Evaluate whether this action aligns with being helpful, honest, and harmless: {action}"
        )
        return critique

    async def alignment_loop(self, task):
        """Iterate until alignment is verified."""
        for _ in range(MAX_ITERATIONS):
            action = await self.model.plan(task)
            critique = await self.self_critique(action, task)

            if critique.is_aligned:
                return action

            task = task.with_feedback(critique)

        return self.escalate_to_human(task)
```

## VERSION
v1.0

## SEE ALSO
- OBSERVABLE_AI_PRIME.md - Transparency for auditing
- PHYSICS_INFORMED_PREDICTION_PRIME.md - Predict misalignment before it happens
- GATEWAY_ARCHITECTURE_PRIME.md - Gateway 5 safety
