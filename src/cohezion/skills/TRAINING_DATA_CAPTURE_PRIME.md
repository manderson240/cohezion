# SKILL: TRAINING_DATA_CAPTURE_PRIME

## DOMAIN EXPERTISE
You are a specialist in **training data collection and curation** for AI systems. You understand how to capture, log, analyze, and rank agentic interactions to generate high-quality training datasets.

## KEY TEXTS & CONCEPTS
- **Interaction Logging:** Capturing every prompt/response pair
- **Journey Tracking:** Following agent paths through tasks
- **Quality Metrics:** Coherence, relevance, creativity, accuracy
- **Performance Ranking:** Comparing agent effectiveness
- **Semantic Analysis:** Embedding-based similarity and clustering

## MATHEMATICAL FOUNDATION
Quality score aggregation:
$$Q = w_c \cdot C + w_r \cdot R + w_a \cdot A + w_s \cdot S$$

Where:
- C = Coherence (internal consistency)
- R = Relevance (prompt-response alignment)
- A = Accuracy (factual correctness)
- S = Success rate
- $w_*$ = weights

## INSTRUCTION

### 1. Interaction Record Structure

```python
from dataclasses import dataclass, field
from datetime import datetime
from uuid import uuid4

@dataclass
class InteractionRecord:
    """Single prompt/response interaction."""
    id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    # Content
    prompt: str = ""
    response: str = ""
    
    # Context
    model: str = ""
    agent_id: str = ""
    stream: str = ""  # architect, engineer, biologist, etc.
    step: int = 0
    
    # Quality metrics (0.0 to 1.0)
    coherence: float = 0.0
    relevance: float = 0.0
    creativity: float = 0.0
    accuracy: float = 0.0
    
    # Performance
    latency_ms: int = 0
    success: bool = True
```

### 2. Journey Tracking

```python
@dataclass
class JourneyRecord:
    """Complete agent journey across multiple interactions."""
    id: str = ""
    agent_id: str = ""
    stream: str = ""
    
    # Interactions in this journey
    interaction_ids: list[str] = field(default_factory=list)
    
    # Aggregated metrics
    total_steps: int = 0
    avg_coherence: float = 0.0
    success_rate: float = 0.0
    
    # Outcome
    status: str = "in_progress"  # in_progress, completed, failed
    final_score: float = 0.0
    rank: int = 0  # Performance rank
```

### 3. Capture System

```python
class TrainingDataCapture:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.interactions_path = output_dir / "interactions.jsonl"
        self.journeys_path = output_dir / "journeys.jsonl"
    
    async def log_interaction(self, interaction: InteractionRecord):
        """Log interaction to JSONL file."""
        with open(self.interactions_path, 'a') as f:
            f.write(json.dumps(asdict(interaction)) + '\n')
    
    def start_journey(self, agent_id: str, stream: str) -> str:
        """Start tracking a new journey."""
        journey = JourneyRecord(agent_id=agent_id, stream=stream)
        self.active_journeys[f"{agent_id}:{stream}"] = journey
        return journey.id
    
    def end_journey(self, agent_id: str, stream: str, score: float):
        """End and save journey with final score."""
        # Save to journeys.jsonl
```

### 4. Quality Estimation

```python
def estimate_coherence(text: str) -> float:
    """Estimate coherence from text structure."""
    score = 0.5
    if len(text) > 100: score += 0.1
    if '.' in text: score += 0.1
    if any(w in text.lower() for w in ['because', 'therefore']): score += 0.1
    return min(1.0, score)

def estimate_relevance(prompt: str, response: str) -> float:
    """Estimate relevance from keyword overlap."""
    prompt_words = set(prompt.lower().split())
    response_words = set(response.lower().split())
    overlap = len(prompt_words & response_words)
    total = len(prompt_words | response_words)
    return overlap / total if total > 0 else 0.0
```

### 5. Overnight Integration

```python
# In overnight_driver.py
from cohezion.training import TrainingDataCapture, OvernightTrainingIntegration

capture = TrainingDataCapture(Path("training_data"))
integration = OvernightTrainingIntegration(capture)

# Wrap all LLM calls
response, record = await integration.wrap_llm_call(
    model="gemini-2.0-flash",
    prompt=prompt,
    agent_id=agent_id,
    stream=stream,
    step=step,
    call_fn=llm_call
)
```

## OUTPUT FILES

| File | Format | Content |
|------|--------|---------|
| `interactions.jsonl` | JSONL | Every prompt/response pair |
| `journeys.jsonl` | JSONL | Agent journey summaries |
| `rankings.json` | JSON | Performance rankings |

## APPLICATIONS
- **FLUME Training:** Generate paragraph-level thought examples
- **R-Zero Calibration:** Tune difficulty based on performance data
- **Agent Evaluation:** Compare agent effectiveness across runs
- **Quality Filtering:** Keep only high-coherence examples
- **Semantic Clustering:** Group similar interactions for analysis

## VERSION
v1.0

## SEE ALSO
- FLUME_METHODOLOGY_PRIME.md
- MASS_SIMULATION_PRIME.md
- SEMANTIC_ANALYSIS_PRIME.md
