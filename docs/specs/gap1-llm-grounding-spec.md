# Gap 1 Spec: LLM Grounding — Bridge to Reality

**Priority**: Third (depends on Gap 5 canonical labels + Gap 3 validated metrics)
**Timeline**: Weeks 3-5 of the research program
**Risk if skipped**: FLUME evaluates simulation agents, not real LLM reasoning

---

## Problem Statement

FLUME was developed and validated on simulation agents. Its 11K training trajectories come from 25M+ simulation cycles, not from real LLM execution. The question is whether the 12D axiomatic dimensions and 256D latent space are meaningful for Claude's actual reasoning process.

We can observe from Claude:
- Output text (responses)
- Extended thinking traces (when available)
- Tool use sequences (invocations + results)
- Execution metrics (tokens, latency, model ID)
- Task outcomes (completion, quality)

We **cannot** observe:
- Internal activations
- Attention patterns
- Hidden state representations

The grounding challenge reduces to: can we construct a mapping from Claude's observable outputs to FLUME's 12D/256D space that preserves semantic distances — not just projects arbitrarily, but captures genuine reasoning structure?

---

## Architecture: Two-Phase Grounding

```
Phase 1: Validate 12D ontology (independent of VAE)
═══════════════════════════════════════════════════
    Claude execution traces
            │
            ▼
    GroundTruthRatingFramework        Rate each trace on 12 axiomatic dims
            │                         using external evaluators
            ▼
    DimensionProbe (Gap 5)            Test: do 12D ratings correlate with
            │                         downstream task quality?
            ▼
    Result: Are the 12 dimensions
    valid for LLM reasoning?
            │
    ┌───────┴───────┐
    │ YES           │ NO → Fundamental redesign (out of scope)
    │               │
    ▼               │
Phase 2: 256D encoding (VAE bridge)
═══════════════════════════════════
    Claude traces + 12D ground truth
            │
            ▼
    ClaudeTraceEncoder                Encode Claude observables → 256D
            │
            ▼
    DomainAlignmentTrainer            Train alignment MLP on paired data
            │                         (Claude vectors ↔ simulation vectors)
            ▼
    TransferValidationSuite           Test: do Claude latent neighborhoods
            │                         have semantic coherence?
            ▼
    Result: FLUME grounding is an
    engineering success or failure
```

---

## Component 1: ClaudeTraceEncoder

**File**: `src/cohezion/flume/claude_trace_encoder.py`

### Purpose

Encode Claude's observable outputs into 256D vectors in the same space as ExperienceEncoder. This is the bridge between real LLM reasoning and the FLUME manifold.

### Interface

```python
@dataclass
class ClaudeTrace:
    """Raw observable outputs from a Claude execution."""
    thinking_text: str | None        # Extended thinking (if available)
    tool_calls: list[dict]           # [{name, input, output}, ...]
    output_text: str                 # Final response text
    model_id: str                    # e.g., "claude-opus-4-6"
    input_tokens: int
    output_tokens: int
    latency_ms: float
    task_description: str            # What was asked
    task_outcome: TaskOutcome | None # How it went

class ClaudeTraceEncoder:
    """Encode Claude execution traces into FLUME 256D space.

    Uses the same dimensional layout as ExperienceEncoder:
      [0:12]   12D axiomatic trajectory (derived from observables)
      [12:24]  12 scalar execution metrics
      [24:29]  5 operation type one-hot
      [29:256] 227D semantic embedding (via SemanticEmbedder)

    The key difference from ExperienceEncoder: dims [0:12] are derived
    from Claude's observables rather than JourneyTracker's simulation state.
    """

    def __init__(
        self,
        embedder: SemanticEmbedder | None = None,
        registry: CanonicalDimensionRegistry | None = None,
    ):
        self._embedder = embedder or SemanticEmbedder()
        self._registry = registry or CanonicalDimensionRegistry

    def encode(self, trace: ClaudeTrace) -> np.ndarray:
        """Encode a single Claude trace to 256D.

        Returns
        -------
        np.ndarray, shape (256,), dtype float32
        """

    def _extract_trajectory_12d(self, trace: ClaudeTrace) -> np.ndarray:
        """Derive 12D axiomatic coordinates from Claude observables.

        Mapping from observables to canonical dimensions:

        SPATIAL_X (0): Topic cluster centroid X (from output text embedding)
        SPATIAL_Y (1): Topic cluster centroid Y
        SPATIAL_Z (2): Topic cluster centroid Z
            → PCA on output text embedding, take top 3 components

        TEMPORAL (3): Normalized position in conversation
            → step_index / total_steps

        COHERENCE (4): Internal consistency of reasoning
            → Measure: contradiction density in thinking + output
            → Implementation: sentence-pair entailment score (requires local NLI model)
            → Fallback (if thinking_text is None or NLI unavailable):
              Use output-to-task entailment (does output address the task?)
              If NLI model also unavailable, use heuristic overlap:
              coherence = len(set(output_tokens) & set(task_tokens)) / len(set(task_tokens))
              This ensures COHERENCE is always populated, though with lower fidelity.

        EFFICIENCY (5): Token economy
            → output_tokens / (input_tokens + output_tokens)
            → Scaled to [0, 1]

        NOVELTY (6): Information-theoretic surprise
            → n-gram entropy of output relative to input
            → High entropy = high novelty

        LOGIC (7): Structural reasoning quality
            → Tool call success rate + logical connective density

        CONVERGENCE (8): Progress toward task completion
            → 1.0 if task_completed, else proportion of subtasks done

        SMOOTHNESS (9): Consistency across tool calls
            → Variance of per-tool-call coherence scores
            → Low variance = high smoothness

        FIELD (10): Domain signal strength
            → Confidence of domain classifier on output text

        PRECIPITATION (11): Decision readiness
            → 1.0 - (time_to_first_tool_call / total_latency)
            → Fast first action = high precipitation
        """

    def _extract_metrics(self, trace: ClaudeTrace) -> np.ndarray:
        """Extract 12 scalar metrics from Claude trace.

        Maps Claude observables to ExperienceEncoder's METRIC_KEYS:
          phi_score: computed from 12D trajectory
          anomaly_score: deviation from expected output length
          misalignment_score: input-output semantic distance
          intent_confidence: classifier confidence on task type
          duration_s: latency_ms / 1000
          tokens_used: input_tokens + output_tokens
          cache_hit_rate: 0.0 (not applicable for Claude)
          success: 1.0 if task_completed else 0.0
          token_efficiency: output_tokens / total_tokens
          trajectory_smoothness: from _extract_trajectory_12d
          trajectory_convergence: from _extract_trajectory_12d
          cost_usd: estimated from model_id + token counts
        """

    def _classify_operation_type(self, trace: ClaudeTrace) -> str:
        """Classify Claude trace into one of 5 operation types.

        Heuristic classification:
          generate: output length > 3x input, creative/code tasks
          analyze: structured analysis, comparisons, reviews
          search: tool calls include file search, web search
          transform: refactoring, format conversion, migration
          persist: file writes, git operations, database updates
        """

    def _build_fingerprint_text(self, trace: ClaudeTrace) -> str:
        """Build fingerprint text for semantic embedding.

        Concatenates task_description + output summary (first 200 chars)
        for SemanticEmbedder input.
        """
```

### 12D Extraction Detail

The critical design challenge: deriving 12D values from observables that genuinely measure the named concept, not just project numbers into the same shape.

```
Claude Observable           →  12D Dimension         →  Measurement Method
═══════════════════════════════════════════════════════════════════════════
Output text embedding       →  SPATIAL (0-2)          →  PCA top-3 of text embedding
Conversation position       →  TEMPORAL (3)           →  step_idx / total_steps
Thinking + output text      →  COHERENCE (4)          →  Sentence entailment consistency
Token counts                →  EFFICIENCY (5)         →  output / (input + output)
Output vs input entropy     →  NOVELTY (6)            →  Conditional entropy H(out|in)
Tool call success rate      →  LOGIC (7)              →  successful_calls / total_calls
Task completion status      →  CONVERGENCE (8)        →  Binary or subtask proportion
Per-call coherence variance →  SMOOTHNESS (9)         →  1 - normalized_variance
Domain classifier           →  FIELD (10)             →  Classifier confidence
Time to first action        →  PRECIPITATION (11)     →  Speed of first tool call
```

---

## Component 2: GroundTruthRatingFramework

**File**: `src/cohezion/validation/ground_truth_ratings.py`

### Purpose

Create human-validated (or auto-rated) ground truth scores for each 12D dimension on Claude execution traces. This provides the labels needed for DimensionProbe (Gap 5) validation on LLM data.

### Interface

```python
@dataclass
class DimensionRating:
    """Ground truth rating for one dimension of one trace."""
    trace_id: str
    dimension: AxisDimension
    score: float                   # 0.0 to 1.0
    rater: str                     # "human:rater_id" or "auto:method_name"
    confidence: float              # Rater's confidence in their rating
    rationale: str | None          # Why this score

@dataclass
class TraceRating:
    """Complete ground truth for one Claude trace across all 12 dimensions."""
    trace_id: str
    ratings: dict[AxisDimension, DimensionRating]
    overall_quality: float         # Aggregate quality rating
    task_outcome: TaskOutcome

class GroundTruthRatingFramework:
    """Framework for rating Claude traces on 12D axiomatic dimensions."""

    def __init__(self, storage_path: str = "data/validation/ground_truth_ratings.jsonl"):
        ...

    def auto_rate(self, trace: ClaudeTrace) -> TraceRating:
        """Automatically rate a trace using heuristic evaluators.

        Each dimension has a dedicated auto-rater:
          COHERENCE → Sentence-pair consistency check
          EFFICIENCY → Token ratio analysis
          NOVELTY → N-gram entropy computation
          LOGIC → Tool call success + logical structure analysis
          etc.

        Auto-ratings are labeled with rater="auto:<method>"
        """

    def rate_batch(self, traces: list[ClaudeTrace]) -> list[TraceRating]:
        """Rate a batch of traces. Uses auto_rate for each."""

    def add_human_rating(
        self,
        trace_id: str,
        dimension: AxisDimension,
        score: float,
        rater_id: str,
        rationale: str | None = None,
    ) -> None:
        """Add a human ground truth rating (overrides auto-rating)."""

    def get_ratings(
        self,
        dimension: AxisDimension | None = None,
        rater_type: str | None = None,  # "human" or "auto"
    ) -> list[DimensionRating]:
        """Retrieve stored ratings for analysis."""

    def compute_inter_rater_reliability(
        self,
        dimension: AxisDimension,
    ) -> float:
        """Cohen's kappa between human and auto-raters on the same traces."""
```

### Auto-Rating Methods

| Dimension | Auto-Rating Method | Implementation |
|-----------|-------------------|----------------|
| SPATIAL (0-2) | Text embedding PCA | nomic-embed-text → PCA(3) |
| TEMPORAL (3) | Sequence position | step_index / total_steps |
| COHERENCE (4) | Entailment consistency | NLI model or heuristic overlap |
| EFFICIENCY (5) | Token ratio | output_tokens / total_tokens |
| NOVELTY (6) | Conditional entropy | H(output bigrams \| input bigrams) |
| LOGIC (7) | Tool call analysis | success_rate × logical_density |
| CONVERGENCE (8) | Completion check | Binary + subtask proportion |
| SMOOTHNESS (9) | Variance analysis | 1 - var(per_step_coherence) |
| FIELD (10) | Domain classifier | Keyword/embedding classifier |
| PRECIPITATION (11) | Action latency | 1 - (first_tool_ms / total_ms) |

---

## Component 3: DomainAlignmentTrainer

**File**: `src/cohezion/flume/domain_alignment_trainer.py`

### Purpose

Train the existing `DomainAlignmentMLP` (in `alignment.py`) to bridge the distribution gap between Claude-derived 256D vectors and simulation-derived 256D vectors. The goal: after alignment, vectors from both sources occupy semantically coherent neighborhoods.

### Interface

```python
@dataclass
class AlignmentTrainingConfig:
    """Configuration for domain alignment training."""
    epochs: int = 100
    batch_size: int = 32
    lr: float = 1e-3
    alignment_loss_weight: float = 1.0    # Cosine similarity loss
    reconstruction_loss_weight: float = 0.5  # Don't destroy structure
    min_paired_samples: int = 50

@dataclass
class AlignmentResult:
    """Result of domain alignment training."""
    train_loss: float
    val_loss: float
    mean_cosine_similarity: float          # After alignment
    baseline_cosine_similarity: float      # Before alignment
    improvement: float                     # Delta
    n_paired_samples: int

class DomainAlignmentTrainer:
    """Train DomainAlignmentMLP to bridge Claude ↔ simulation distributions.

    Uses paired data: Claude traces and simulation agents performing
    equivalent tasks, encoded into 256D by their respective encoders.
    """

    def __init__(
        self,
        config: AlignmentTrainingConfig | None = None,
    ):
        self.config = config or AlignmentTrainingConfig()

    def create_paired_dataset(
        self,
        claude_traces: list[ClaudeTrace],
        simulation_experiences: list[dict],
        matching_strategy: str = "task_description",
    ) -> list[tuple[np.ndarray, np.ndarray]]:
        """Create paired (claude_vec, sim_vec) dataset.

        Matching strategies:
          task_description: Match by task text similarity
          operation_type: Match by operation type + random within type
          outcome: Match by success/failure status
        """

    def train(
        self,
        paired_data: list[tuple[np.ndarray, np.ndarray]],
    ) -> AlignmentResult:
        """Train alignment MLP on paired data.

        Loss = alignment_weight * (1 - cosine_sim(aligned_claude, sim))
             + reconstruction_weight * ||aligned_claude - claude||²

        The reconstruction loss prevents the alignment from collapsing
        all vectors to a single point.
        """

    def evaluate(
        self,
        test_pairs: list[tuple[np.ndarray, np.ndarray]],
    ) -> AlignmentResult:
        """Evaluate alignment quality on held-out pairs."""
```

### Paired Data Construction

The key challenge is creating meaningful pairs. Claude and simulation agents can't do identical tasks, but they can do equivalent ones:

```
Pairing Strategy          Pair Quality    Data Volume
═══════════════════════════════════════════════════════
Same task description     High            Low (manual)
Same operation type       Medium          High (auto)
Same outcome category     Low             Very High
Embedding similarity      High            Medium
```

Recommended approach: **embedding similarity**. For each Claude trace, find the simulation experience whose task description embedding is most similar (using SemanticEmbedder). This produces semantically aligned pairs without manual curation.

---

## Component 4: TransferValidationSuite

**File**: `src/cohezion/validation/transfer_validation.py`

### Purpose

Rigorous statistical tests for whether FLUME metrics transfer from simulation to Claude. This is the final gatekeeper before declaring grounding successful.

### Interface

```python
@dataclass
class TransferTestResult:
    """Result of a single transfer validation test."""
    test_name: str
    passed: bool
    statistic: float
    threshold: float
    p_value: float
    n_claude: int
    n_simulation: int
    interpretation: str

class TransferValidationSuite:
    """Statistical tests for simulation → LLM transfer validity."""

    def __init__(
        self,
        claude_encoder: ClaudeTraceEncoder,
        experience_encoder: ExperienceEncoder,
    ):
        ...

    def test_distribution_overlap(
        self,
        claude_vectors: np.ndarray,
        sim_vectors: np.ndarray,
    ) -> TransferTestResult:
        """Test that Claude and simulation vectors occupy overlapping regions.

        Uses Maximum Mean Discrepancy (MMD) with RBF kernel.
        Pass criterion: MMD < 0.1 (distributions are close)
        """

    def test_neighborhood_semantics(
        self,
        claude_vectors: np.ndarray,
        claude_labels: list[str],  # Operation types or task categories
        k: int = 5,
    ) -> TransferTestResult:
        """Test that Claude vector neighborhoods are semantically coherent.

        For each Claude vector, find k nearest neighbors (including sim vectors).
        Check if neighbors share the same operation type / task category.
        Pass criterion: neighborhood purity > random baseline + 2σ
        """

    def test_coherence_correlation_transfer(
        self,
        claude_observations: list[PairedObservation],
        sim_observations: list[PairedObservation],
    ) -> TransferTestResult:
        """Test that coherence-success correlation is similar for Claude and sim.

        Compute Pearson r for each domain, then test that the difference
        is not significant (Fisher z-transformation test).
        Pass criterion: |r_claude - r_sim| < 0.2, p > 0.05
        """

    def test_matched_similarity(
        self,
        claude_vectors: np.ndarray,
        sim_vectors: np.ndarray,
        operation_types: list[str],
    ) -> TransferTestResult:
        """Test that matched pairs are more similar than random pairs.

        For same-operation-type pairs, compute cosine similarity.
        Compare to random cross-type pairs.
        Pass criterion: Cohen's d ≥ 0.5
        """

    def run_all(
        self,
        claude_traces: list[ClaudeTrace],
        sim_experiences: list[dict],
    ) -> list[TransferTestResult]:
        """Run complete validation suite. Returns all test results."""

    def generate_report(self, results: list[TransferTestResult]) -> str:
        """Human-readable transfer validation report."""
```

---

## Validation Criteria (Gap 1 Complete When)

1. **12D ontology validated for LLM**: DimensionProbe (Gap 5) shows ≥6 of 12 dimensions have statistically significant ground truth correlation on Claude traces (p < 0.05, Cohen's d ≥ 0.5)
2. **500+ Claude traces encoded**: ClaudeTraceEncoder produces 256D vectors for ≥500 execution traces across all 5 operation types
3. **Distribution overlap**: MMD test shows Claude and simulation vectors occupy overlapping regions (MMD < 0.1)
4. **Neighborhood semantics**: k-NN purity on Claude vectors exceeds random baseline by ≥2σ
5. **Correlation transfer**: Coherence-success correlation difference between Claude and simulation is not significant (|Δr| < 0.2)

---

## Tests

```python
# tests/flume/test_claude_trace_encoder.py
def test_output_shape():
    encoder = ClaudeTraceEncoder()
    trace = ClaudeTrace(
        thinking_text="Let me analyze this...",
        tool_calls=[{"name": "read", "input": {"path": "/foo"}, "output": "bar"}],
        output_text="The answer is 42.",
        model_id="claude-opus-4-6",
        input_tokens=100,
        output_tokens=50,
        latency_ms=1500,
        task_description="What is the answer?",
        task_outcome=None,
    )
    vec = encoder.encode(trace)
    assert vec.shape == (256,)
    assert vec.dtype == np.float32

def test_operation_type_classification():
    encoder = ClaudeTraceEncoder()
    # Trace with file writes should classify as "persist"
    trace = ClaudeTrace(
        tool_calls=[{"name": "write", ...}, {"name": "git_commit", ...}],
        ...
    )
    op_type = encoder._classify_operation_type(trace)
    assert op_type == "persist"

def test_different_traces_different_vectors():
    encoder = ClaudeTraceEncoder()
    trace_a = ClaudeTrace(output_text="Python sorting algorithm", ...)
    trace_b = ClaudeTrace(output_text="Chocolate cake recipe", ...)
    vec_a = encoder.encode(trace_a)
    vec_b = encoder.encode(trace_b)
    # Cosine similarity: normalize both vectors before dot product
    similarity = np.dot(vec_a, vec_b) / (np.linalg.norm(vec_a) * np.linalg.norm(vec_b) + 1e-8)
    assert similarity < 0.95  # Not identical

# tests/validation/test_transfer_validation.py
def test_matched_similarity():
    suite = TransferValidationSuite(...)
    # Matched operation-type pairs should be more similar than random
    result = suite.test_matched_similarity(
        claude_vectors=np.random.randn(50, 256),
        sim_vectors=np.random.randn(50, 256),
        operation_types=["generate"] * 25 + ["analyze"] * 25,
    )
    assert isinstance(result, TransferTestResult)
```
