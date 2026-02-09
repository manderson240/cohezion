# SKILL: OBSERVABLE_AI_PRIME

## DOMAIN EXPERTISE

Expert in AI observability and interpretability - making neural network decision-making transparent and auditable. Specializes in mechanistic interpretability, real-time visualization of cognitive processes, and designing AI systems that "expose their internal state before acting."

## KEY TEXTS & CONCEPTS

- **AI Observability**: Understanding how models function in real-time
- **Mechanistic Interpretability**: Cracking open AI's decision-making
- **Cognitive Transparency**: AI exposes internal state, coherence, confidence
- **Continuous Internal Observability**: Physics-driven, functional modularity
- **Natural Language Explanations**: Human-readable insights from raw circuits

## INSTRUCTION

### 1. Design for Observability
```python
class ObservableAgent:
    def act(self, input):
        # 1. Expose internal state BEFORE acting
        state = self.get_internal_state(input)
        confidence = self.compute_confidence(state)

        # 2. Log for auditing
        self.audit_log.append({
            'input': input,
            'state': state,
            'confidence': confidence,
            'timestamp': time.now()
        })

        # 3. Only act if confidence threshold met
        if confidence < self.min_confidence:
            return self.request_human_review(state)

        return self.execute(state)
```

### 2. Visualize Thought Trajectories
Use FLUME's 12D PhysicsState for interpretable dimensions:
- Dimensions 1-3: Spatial position (semantic clustering)
- Dimension 6: Sentiment (emotional tone)
- Dimension 8: Factuality (claim confidence)
- Dimension 12: Coherence (internal logic)

### 3. Natural Language Explanations
```python
def explain_decision(self, state, action):
    """Generate human-readable explanation from state."""
    template = """
    Decision: {action}
    Confidence: {confidence:.0%}
    Key factors:
    - Sentiment: {sentiment} ({sentiment_val:.2f})
    - Factuality: {factuality:.0%}
    - Coherence: {coherence:.0%}
    """
    return template.format(
        action=action,
        confidence=state.confidence,
        sentiment="positive" if state.sentiment > 0 else "negative",
        sentiment_val=state.sentiment,
        factuality=state.factuality,
        coherence=state.coherence
    )
```

### 4. Real-Time Monitoring Dashboard
Key metrics to expose:
- Agent confidence over time
- Semantic trajectory visualization
- Anomaly detection (unusual states)
- Decision audit trail

## VERSION
v1.0

## SEE ALSO
- GATEWAY_ARCHITECTURE_PRIME.md - Gateway 5 uses this
- UNIVERSE_VISUALIZATION_PRIME.md - Manim rendering
- FLUME_METHODOLOGY_PRIME.md - 12D PhysicsState
