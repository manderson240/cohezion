# Experience-Guided Skill Selection

## Overview

Experience-Guided Skill Selection is an intelligent system that learns from vault execution history to automatically select the best-performing skills for new tasks. It eliminates the need for manual skill selection by analyzing past executions and recommending skills that have performed well on similar tasks.

## Architecture

```
New Task
    ↓
SkillSelector queries vault for similar past executions
    ↓
Extracts performance metrics (coherence, efficiency, success rate)
    ↓
Ranks candidate skills using composite scoring
    ↓
Returns top-K ranked skills
    ↓
Executor selects and runs best skill
    ↓
Logs execution results back to vault
    ↓
Future tasks benefit from this learning
```

## How It Works

### 1. Skill Performance Metrics

Skills are evaluated on three key dimensions:

| Metric | Definition | Weight | Interpretation |
|--------|-----------|--------|-----------------|
| **Coherence** | Quality/correctness of output | 50% | How good is the result? |
| **Token Efficiency** | Tokens used relative to quality | 30% | How cost-effective? |
| **Success Rate** | Historical success percentage | 20% | How often does it work? |

### 2. Composite Score Calculation

The composite score combines all metrics using configurable weights:

```
composite_score = (coherence × 0.5) + (efficiency × 0.3) + (success_rate × 0.2)
```

Example:
- Skill A: coherence=0.92, efficiency=0.85, success=0.95
- Score = (0.92 × 0.5) + (0.85 × 0.3) + (0.95 × 0.2) = **0.894**

### 3. Learning Cycle

1. **New Task Arrives** - Executor receives a task description and operation type
2. **Vault Query** - SkillSelector queries vault for similar past executions
3. **Metric Extraction** - Parses patterns to extract skill performance data
4. **Skill Ranking** - Computes composite scores and sorts candidates
5. **Skill Selection** - Returns top-K skills with highest scores
6. **Execution** - Executor runs selected skill
7. **Logging** - Results saved to vault as new patterns
8. **Feedback Loop** - Future tasks benefit from accumulated knowledge

## API Usage

### Using CompoundExecutor's `suggest_skills()`

```python
from cohezion.compound import CompoundExecutor
from cohezion.core.mcp_client import MCPClient, MCPConfig

# Initialize
config = MCPConfig(server_url="http://localhost:8360/mcp")
mcp_client = MCPClient(config)
executor = CompoundExecutor(mcp_client=mcp_client)

# Get skill suggestions
suggestions = executor.suggest_skills(
    task_description="Analyze customer feedback",
    operation_type="analyze",
    project="cohezion",
    top_k=3,  # Return top 3 skills
)

# suggestions is a list of (skill_name, score) tuples
for skill_name, score in suggestions:
    print(f"  {skill_name}: score={score:.3f}")
```

### Using SkillSelector Directly

```python
from cohezion.compound import SkillSelector

selector = SkillSelector(
    mcp_client=mcp_client,
    coherence_weight=0.5,
    efficiency_weight=0.3,
    success_weight=0.2,
)

# Get detailed scores with metrics
scores = selector.select_skills(
    task_description="Generate creative content",
    operation_type="generate",
    project="cohezion",
    top_k=5,
)

for score in scores:
    print(f"Skill: {score.skill_name}")
    print(f"  Composite: {score.composite_score:.3f}")
    print(f"  Coherence: {score.coherence_score:.2f}")
    print(f"  Efficiency: {score.token_efficiency:.2f}")
    print(f"  Success Rate: {score.success_rate:.2f}")
    print(f"  Times Used: {score.times_used}")
```

## Team Execution Integration

The TeamExecutor automatically uses experience-guided skill selection when executing team tasks:

```python
from cohezion.compound import TeamExecutor, AgentTask

# Create executor with skill selection enabled
executor = TeamExecutor(mcp_client, project="cohezion")

# Create a team task
task = AgentTask(
    task_id="task_1",
    description="Analyze quarterly results",
    operation_type="analyze",
    available_skills=["analyze_reports", "summarize", "extract_insights"],
)

# TeamExecutor automatically:
# 1. Queries vault for skill performance
# 2. Selects best skill from available_skills
# 3. Executes the task
# 4. Logs results to vault
result = await executor.execute_team([task])
```

## Vault Patterns Structure

Skills' historical performance is stored in vault patterns with the following structure:

```markdown
# Pattern: skill_name_operation_type_success

## Source
- Execution from CompoundExecutor
- Date: 2026-02-08

## Performance Metrics
- Coherence: 0.92 (quality of output)
- Token Efficiency: 0.85 (tokens used relative to quality)
- Success: 1.0 (execution succeeded)

## Task Context
- Task Type: analyze
- Domain: customer feedback analysis
- Tokens Used: 250
- Duration: 2.3 seconds

## Results Summary
Successfully extracted key themes with high coherence...
```

The SkillSelector parses these patterns to extract:
- Skill name (from title or content)
- Operation type (from context)
- Performance metrics (coherence, efficiency, success)
- Number of uses (pattern count)

## Scoring Algorithm Details

### Metric Extraction

The system extracts metrics from vault patterns using regex patterns:

```python
# Looks for patterns like:
# - "coherence: 0.85" or "coherence=0.85"
# - "efficiency: 0.75" or "efficiency=0.75"
# - "success_rate: 0.9" or "success=0.9"
# - "75% success" or "0.75 success"
```

### Skill Name Extraction

Skill names are extracted using multiple strategies:

1. **Pattern Matching**: `skill_operation_type_success` format
2. **Prefix Detection**: "Skill: name" or "Skill Name:"
3. **First Token**: First word-like token (if not a common article)

### Aggregation

For multiple pattern records of the same skill:

```python
# Average all metrics across patterns
coherence_avg = mean(all_coherence_scores)
efficiency_avg = mean(all_efficiency_scores)
success_avg = mean(all_success_rates)

# Compute composite with normalized weights
composite = (
    weights_coherence * coherence_avg
    + weights_efficiency * efficiency_avg
    + weights_success * success_avg
)
```

## Configuration

### Weight Adjustment

Customize the scoring weights based on your priorities:

```python
selector = SkillSelector(
    mcp_client=mcp_client,
    coherence_weight=0.7,  # Prioritize quality (70%)
    efficiency_weight=0.2,  # Less focus on cost (20%)
    success_weight=0.1,  # Minimal success rate weight (10%)
)
```

Common configurations:

| Profile | Coherence | Efficiency | Success | Use Case |
|---------|-----------|-----------|---------|----------|
| Quality-First | 0.7 | 0.2 | 0.1 | High-stakes analysis |
| Balanced | 0.5 | 0.3 | 0.2 | General purpose |
| Cost-Optimized | 0.4 | 0.5 | 0.1 | Token-constrained |
| Reliability-First | 0.3 | 0.2 | 0.5 | Critical systems |

## Examples

### Example 1: Basic Skill Suggestion

```python
# Get top skill for a task
suggestions = executor.suggest_skills(
    task_description="Generate product descriptions", operation_type="generate", top_k=1
)

if suggestions:
    best_skill, best_score = suggestions[0]
    print(f"Recommended: {best_skill} (score: {best_score:.3f})")
```

### Example 2: Multi-Candidate Ranking

```python
# Get ranked list for manual review
suggestions = executor.suggest_skills(
    task_description="Summarize legal documents", operation_type="analyze", top_k=5
)

print("Skill Recommendations (ranked):")
for i, (skill_name, score) in enumerate(suggestions, 1):
    print(f"{i}. {skill_name}: {score:.3f}")
```

### Example 3: Custom Weight Profile

```python
# Create quality-focused selector
selector = SkillSelector(
    mcp_client=mcp_client,
    coherence_weight=0.7,
    efficiency_weight=0.2,
    success_weight=0.1,
)

# Get suggestions with quality prioritized
scores = selector.select_skills(
    task_description="Generate medical reports", operation_type="generate", top_k=3
)

for score in scores:
    print(f"{score.skill_name}: coherence={score.coherence_score:.2f}")
```

## Performance Characteristics

| Operation | Time | Notes |
|-----------|------|-------|
| Vault Query | 50-200ms | Depends on vault size |
| Pattern Parsing | 10-50ms | Per 100 patterns |
| Skill Ranking | <1ms | Composite score calculation |
| Total Suggestion Time | 100-300ms | End-to-end |

## Benefits

1. **Automatic Optimization** - System learns and improves over time
2. **Reduced Manual Work** - No need to manually choose skills
3. **Better Resource Usage** - Selects most efficient skills
4. **Higher Success Rate** - Picks proven performers
5. **Institutional Knowledge** - Vault captures and shares learnings

## Limitations and Future Enhancements

### Current Limitations

- Requires execution history in vault to be effective
- Pattern parsing may miss metrics in non-standard formats
- Limited context understanding (simple keyword matching)

### Future Enhancements

1. **Semantic Context** - Use embeddings for better pattern matching
2. **Multi-Task Learning** - Cross-domain skill transfer
3. **Real-Time Adaptation** - Adjust weights based on results
4. **Skill Clustering** - Group similar skills and learn relationships
5. **Offline Learning** - Pre-train selector on historical data

## Testing

### Unit Tests

```bash
uv run pytest tests/compound/test_skill_selector.py -v
```

Test coverage includes:
- Skill name extraction (various formats)
- Metric extraction (patterns and values)
- Pattern parsing (dict and string)
- Composite score calculation
- Skill ranking and sorting

### Integration Tests

```bash
uv run pytest tests/compound/test_executor_skill_selection.py -v
```

Tests cover:
- CompoundExecutor.suggest_skills() integration
- Vault query and pattern extraction
- Error handling and graceful fallbacks

## Troubleshooting

### No Suggestions Returned

1. Check vault is running: `http://localhost:8360/mcp`
2. Verify vault has execution patterns logged
3. Check MCP client connection: `MCPClient(config).health_check()`

### Low Scores

1. Few execution records in vault (scores default to 0.5)
2. Skills have poor historical performance
3. Operation type mismatch between task and patterns

### Skill Not Selected

1. Skill not in `available_skills` list (TeamExecutor check)
2. No pattern match for the skill in vault
3. Multiple skills with same score (ties broken by first match)

## See Also

- [CompoundExecutor Documentation](compound_executor.md)
- [Vault Integration](vault_integration.md)
- [TeamExecutor Guide](team_executor.md)
- [PRIME Skills](prime_skills.md)
