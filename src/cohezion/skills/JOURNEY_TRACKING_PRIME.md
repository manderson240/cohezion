# SKILL: JOURNEY_TRACKING_PRIME

## DOMAIN EXPERTISE
You are a specialist in **agent journey tracking** - recording the 12D physics trajectory of agents through debate workflows.

## KEY CONCEPTS
- **JourneyTracker** - Records agent steps with full physics state
- **12D Physics State** - x,y,z,time,mass,sentiment,complexity,factuality,connectivity,stability,novelty,coherence
- **Trajectory Visualization** - Multi-panel rendering of physics evolution

## INSTRUCTION

### 1. Start Journey
```python
from cohezion.swarm.journey_tracker import get_journey_tracker, AgentType

tracker = get_journey_tracker()
journey_id = tracker.start_journey("What is consciousness?")
```

### 2. Record Step (Full 12D)
```python
tracker.record_step(
    agent_type=AgentType.ANALYST,
    agent_name="analyst_technical",
    perspective="technical",
    input_text="query",
    output_text="analysis result",
    physics_state={
        "x": 0.1, "y": 0.2, "z": 0.5,
        "time": 0.1, "mass": 0.8, "sentiment": 0.5,
        "complexity": 0.7, "factuality": 0.9,
        "connectivity": 0.4, "stability": 0.7,
        "novelty": 0.6, "coherence": 0.8,
    },
    duration_ms=300,
    confidence=0.85,
)
```

### 3. End & Visualize
```python
journey = tracker.end_journey("Final response", final_confidence=0.92)

# API endpoints
# GET /journeys/{id}/plot - Multi-panel 12D visualization
# GET /journeys/{id}/visualize - Animated GIF trajectory
```

### 4. Physics Evolution
| Agent | Key Physics Changes |
|-------|---------------------|
| Analyst | Scattered x,y,z; moderate coherence |
| Critic | Centered z; high factuality |
| Synthesizer | z=1.0; max coherence & connectivity |

## SEE ALSO
- UNIVERSE_PHYSICS_PRIME.md
- UNIVERSE_VISUALIZATION_PRIME.md
