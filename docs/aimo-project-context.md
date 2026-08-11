---
project_name: 'aimo-progress-prize-3'
user_name: 'Mike-anderson'
date: '2026-03-24'
status: 'complete'
sections_completed:
  - technology_stack
  - architecture_patterns
  - swarm_agent_rules
  - math_processing_rules
  - api_integration_rules
  - stability_verification_rules
  - resource_management_rules
  - error_handling_rules
  - troubleshooting_patterns
existing_patterns_found: 15
optimized_for_llm: true
---

# AIMO Progress Prize 3 - Project Context for AI Agents

_This file contains critical rules and patterns for implementing the Mathematical Reasoning Swarm for the AI Mathematical Olympiad Progress Prize 3 ($2.2M prize). Focus on unobvious details that agents might otherwise miss._

---

## Technology Stack & Versions

**Core Technologies:**
- Python 3.13+
- Package Manager: `uv` (never use bare pip)
- Line Length: 100 characters
- Type Hints: Mandatory (mypy --strict compatible)

**AI/ML Dependencies:**
- Ollama >=0.5.0 (local model inference)
- Polars >=1.0.0 (DataFrame processing - NOT pandas)
- NumPy >=1.24.0 (12D state vectors)
- SymPy (symbolic mathematics)
- Requests >=2.31.0 (HTTP with explicit timeouts)

**Models (Pre-March 15, 2026 Cutoff):**
- Lead Reasoner: `DeepSeek-R1-Distill-Qwen-32B` or `qwen2-math:1.5b`
- Logic Verifier: `Phi-4-7B` or `phi3:mini`
- Code Executor: `Qwen2.5-Coder-14B`
- Default Specialist: `qwen2-math:1.5b`

**Competition Constraints:**
- Total Time: 5 hours (18,000 seconds)
- Target Problems: 110
- Time per Problem: 150 seconds + 15s safety margin
- Memory: 128GB RAM / 12GB VRAM
- Compute: 5-hour H100 limit

---

## Architecture Patterns

### Triune Manifold Architecture

**1. Doer (Perception & Execution)**
- Input: LaTeX problem string from AIMO API
- Output: 12D Problem State Vector + Symbolic Constraints
- Components: `MathParser`, `SymbolicExecutor`
- Tools: SymPy (symbolic), NumPy (numerical)

**2. Thinker (Reasoning & Interpolation)**
- Input: 12D State Vector
- Process:
  - Domain Routing: Assign to specialist (Algebra, Geometry, Number Theory, Combinatorics)
  - Long-Horizon Chain-of-Thought: DeepSeek-R1-32B for step-by-step proofs
  - FLUME Encoding: Map proof steps to latent vectors for "logical drift" detection

**3. Knower (Validation & Stability)**
- Input: Dual-run proof results
- Process:
  - Consistency Check: Compare Run 1 and Run 2
  - Adversarial Review: Secondary agent (Phi-4) reviews proof logic
  - Stability Score: Confidence metric for final integer answer

### 12D Mathematical State Vector

```python
@dataclass
class MathProblemState:
    # 3 Spatial: Problem 'Geometry' (Structural complexity)
    structural_depth: float  # Max nesting of LaTeX braces
    token_density: float  # Ratio of math tokens to text
    constraint_density: float  # Constraints per variable
    
    # 1 Time: Temporal 'Flow' (Expected reasoning steps)
    reasoning_complexity: float
    
    # 8 Brane: Domain and Character
    algebra: float
    number_theory: float
    geometry: float
    combinatorics: float
    calculus: float
    logic_type: float  # 0: Calculation, 1: Optimization, 2: Proof
    abstraction_level: float  # Presence of abstract structures
    stability_heuristic: float  # Expected consistency across runs
```

---

## Swarm Agent Rules

### Specialist Routing

**Domain Detection Keywords:**
- **Algebraist**: `solve`, `equation`, `function`, `polynomial`, `root`, `coefficient`, `quadratic`, `inequality`
- **NumberTheorist**: `integer`, `divisor`, `prime`, `modular`, `congruent`, `gcd`, `lcm`, `mod`, `coprime`
- **Geometer**: `triangle`, `circle`, `area`, `angle`, `perpendicular`, `parallel`, `radius`, `tangent`
- **Combinatorist**: `number of ways`, `how many`, `permutation`, `combination`, `probability`, `subset`, `arrangement`

**Model Assignment:**
```python
default_models = {
    "Algebraist": "qwen2-math:1.5b",
    "NumberTheorist": "qwen2-math:1.5b",
    "Geometer": "phi3:mini",
    "Combinatorist": "qwen2-math:1.5b",
    "Coordinator": "phi3:mini",
}
```

### Adversarial TDD Loop

**Maximum 2 refinement cycles:**
1. Specialist generates reasoning + Python code block
2. AdversaryAgent reviews logic for flaws
3. If verified: proceed to answer extraction
4. If flaws found: fix and regenerate (max 2 cycles)

---

## Math Processing Rules

### LaTeX Parsing

**Critical Patterns:**
- Clean LaTeX: Remove `\text{}`, `\textbf{}`, `\textit{}` but preserve math
- Extract equations: Content between `$...$` or `\begin{equation}...`
- Extract variables: Single letters in math mode (exclude `d`, `e`, `i`)
- Max nesting: Count `{}` brace depth for structural complexity

**Answer Extraction:**
```python
# CORRECT: Check for error before regex
if response_text.startswith("Error"):
    return 0  # Bypass regex on error tracebacks

# Extract boxed answer
boxed_match = re.search(r"\\boxed{([^}]+)}", response_text)
if boxed_match:
    return int(boxed_match.group(1))

# Fallback: Last number in response
numbers = re.findall(r"\d+", response_text)
return int(numbers[-1]) if numbers else 0
```

### Symbolic Execution

**Sandboxed Execution Rules:**
- All Python code from LLM must execute in restricted environment
- Use SymPy for symbolic manipulation
- Use NumPy for numerical validation
- Timeout: 30 seconds per execution
- No file I/O, no network access

---

## API Integration Rules

### AIMO API Protocol

**Official API Pattern:**
```python
from kaggle_evaluation.aimo_3_inference_server import AIMO3InferenceServer


def predict(problem_id: str, problem_text: str) -> int:
    # Must return integer 0-99999
    # Called exactly once per problem
    pass


server = AIMO3InferenceServer(predict)
```

**Mock Environment for Testing:**
```python
from mock_aimo_api import make_env

env = make_env("reference_problems.json")
iter_test = env.iter_test()

for test_df, sample_submission_df in iter_test:
    problem_id = test_df.iloc[0]["id"]
    problem_text = test_df.iloc[0]["problem"]
    
    # Process exactly once per row
    final_answer = swarm.predict(problem_id, problem_text)
    sample_submission_df.loc[0, "answer"] = final_answer
    env.predict(sample_submission_df)  # Call exactly once
```

**Critical Constraints:**
- Single-Row Constraint: API yields exactly one row per `iter_test()` iteration
- Stateful Validation: `env.predict()` must be called exactly once per row
- No batch processing possible
- Sequential execution mandatory

---

## Stability Verification Rules

### Dual-Run Protocol

**Execution Pattern:**
```python
# Run 1: Primary Specialist
specialist1 = BaseSpecialist(task.assigned_specialists[0])
response1 = specialist1.solve(problem_text, keep_alive="1m")
ans1 = specialist1.extract_answer(response1)

# Run 2: Secondary Specialist (or same if only one)
spec2_name = task.assigned_specialists[1] if len(task.assigned_specialists) > 1 else spec1_name
specialist2 = BaseSpecialist(spec2_name)
response2 = specialist2.solve(problem_text, keep_alive="1m")
ans2 = specialist2.extract_answer(response2)

# Knower Audit
audit = auditor.audit_runs([ans1, ans2], [response1, response2])
```

**Stability Scoring:**
- Consistent answers (ans1 == ans2): stability_score = 1.0
- Divergent answers: stability_score = 0.0, trigger tie-breaker
- Target: ≥0.95 stability ratio across all problems

### Tie-Breaker Protocol

**When ans1 != ans2:**
```python
if audit["action"] == "TIE_BREAKER":
    tie_specialist = BaseSpecialist(spec1_name, "phi4:latest")
    res3_text = tie_specialist.solve(problem_text, keep_alive="1m")
    res3 = tie_specialist.extract_answer(res3_text)
    final_answer = auditor.resolve_tie(ans1, ans2, res3)  # Majority voting
```

---

## Resource Management Rules

### Memory Safety (12GB VRAM)

**Critical Rules:**
- Sequential Execution: Only one large model (≥30B) loaded at a time
- Memory Flushing: Use Ollama's `keep_alive: 0` or explicit model unloading between problems
- Quantization: Primary models must be Q5_K_M or Q6_K to balance accuracy and memory
- Model Selection: Never load multiple 30B+ models simultaneously

### Time Budgeting

**Per-Problem Allocation:**
```python
TARGET_TIME_PER_PROBLEM = 150  # seconds
SAFETY_MARGIN = 15  # seconds
TOTAL_TIME_PER_PROBLEM = 165  # seconds

# Timeout configuration
timeout = 300  # 5 minutes for reasoning models (covers CPU fallback)
num_thread = 16  # Maximize CPU utilization if GPU busy
```

**Process Management:**
- Before starting sprint: `ps aux | grep aimo | xargs kill -9`
- Clean zombie processes: Ensure no orphaned `uv run` or `python` scripts
- Monitor system load: Alert if load > 20 (indicates zombie swarms)

---

## Error Handling Rules

### Timeout Configuration

**MANDATORY: All API calls must have explicit timeouts:**
```python
# CORRECT
payload = {
    "model": self.model_name,
    "messages": messages,
    "stream": False,
    "keep_alive": keep_alive,
    "options": {"temperature": 0.2, "num_ctx": 8192, "num_thread": 16},
}

try:
    response = requests.post(self.ollama_url, json=payload, timeout=self.timeout)  # 300s
    response.raise_for_status()
    result = response.json()
except requests.exceptions.Timeout:
    return f"Error calling Ollama: Read timed out. (read timeout={self.timeout})"
except requests.exceptions.RequestException as e:
    return f"Error calling Ollama: {str(e)}"
```

### Fail-Safe Patterns

**CRITICAL: Fallback logic must never mask NameError or ImportError:**
```python
# WRONG: Buries critical errors
try:
    result = complex_llm_logic()
except Exception as e:
    return "Fallback: Basic refinement."  # Masks NameError

# CORRECT: Specific exception handling
try:
    result = complex_llm_logic()
except (NameError, ImportError) as e:
    raise  # Re-raise critical errors
except Exception as e:
    return f"Fallback: Basic refinement. Error: {str(e)}"
```

### Error-as-Answer Prevention

**Answer extraction must check for errors FIRST:**
```python
def extract_answer(response_text: str) -> int:
    # Check for error BEFORE regex extraction
    if response_text.startswith("Error"):
        return 0  # Prevent regex from catching error numbers
    
    # Extract boxed answer
    boxed_match = re.search(r"\\boxed{([^}]+)}", response_text)
    if boxed_match:
        return int(boxed_match.group(1))
    
    # Fallback
    numbers = re.findall(r"\d+", response_text)
    return int(numbers[-1]) if numbers else 0
```

---

## Troubleshooting Patterns

### Known Issues & Fixes

**1. Infinite Hang (No Timeout)**
- **Symptom**: Script hangs indefinitely, system load skyrockets
- **Fix**: Add `timeout=300` to all `requests.post()` calls
- **Prevention**: Never make HTTP calls without explicit timeout

**2. Silent Extraction Failures**
- **Symptom**: Answer is unrelated number (e.g., 180 from error message)
- **Fix**: Check `response_text.startswith("Error")` before regex
- **Prevention**: Error-as-answer anti-pattern in extract_answer()

**3. Dependency Desync**
- **Symptom**: LLM logic silently fails, always returns fallback
- **Fix**: Migrate pandas → polars, add explicit `import polars as pl`
- **Prevention**: Never use blanket `except Exception` that masks NameError

**4. Zombie Swarms**
- **Symptom**: Multiple instances running, OOM or near-OOM (load 24+)
- **Fix**: `ps aux | grep aimo | xargs kill -9` before new sprint
- **Prevention**: Centralized process management, worktree isolation

### Worktree Isolation

**For concurrent high-intensity swarms:**
```bash
# Create isolated worktree
git worktree add ../aimo-worktree main

# Run sprint in isolated worktree
cd ../aimo-worktree
uv run python aimo_overnight.py

# Prevents file state corruption when multiple agents active
```

---

## Testing Rules

### Reference Problems Benchmark

**10 Official Reference Problems:**
- Location: `sandbox/aimo/reference_problems.json`
- Format: `{id, problem, solution, answer}`
- Success Metric: 100% accuracy on reference problems
- Stability Threshold: ≥90% dual-run consistency

### Mock Environment Testing

**Test Pattern:**
```python
from swarm_driver import run_simulation

accuracy, avg_stability = run_simulation()
print(f"Final Accuracy: {accuracy * 100:.2f}% | Avg Stability: {avg_stability:.3f}")

# Target: accuracy > 0.0, stability > 0.9
```

### Integration Test Requirements

**Must Test:**
- Single-row API iteration
- Exactly one `env.predict()` call per row
- Dual-run execution for all problems
- Tie-breaker trigger when answers diverge
- Adversarial review loop (max 2 cycles)
- Answer extraction with error handling

---

## Workflow Rules

### Sprint Execution Flow

**SwarmDriver Sequence:**
1. Initialize Mock Environment
2. Initialize Swarm Components (coordinator, auditor)
3. For each problem:
   - A. Plan Journey (assign specialists)
   - B. Dual-Run Execution (cross-specialist verification)
   - C. Knower Audit (stability scoring)
   - D. Tie-Breaker (if needed)
   - E. Predict and Update Environment
4. Report Final Accuracy + Avg Stability

### Process Lifecycle

**Before Sprint:**
```bash
# Clean state
ps aux | grep -i aimo | grep -v grep | awk '{print $2}' | xargs kill -9
ps aux | grep -i ollama | grep -v grep | awk '{print $2}' | xargs kill -9
```

**During Sprint:**
- Monitor system load: `top` or `htop`
- Alert if load > 20
- Log progress: Problem X/110, Time elapsed, Avg latency

**After Sprint:**
- Clean processes
- Save metrics to `research_results.tsv`
- Archive logs: `overnight_aimo.log`, `sprint_monitor.log`

---

## Implementation Guardrails

### DOs

✅ Always use explicit timeouts on API calls
✅ Check for errors before answer extraction
✅ Run dual-verification for stability scoring
✅ Use polars (not pandas) for DataFrame processing
✅ Clean processes before starting new sprint
✅ Log progress metrics during execution
✅ Use worktree isolation for concurrent development

### DON'Ts

❌ Never call env.predict() multiple times per row
❌ Never use blanket except Exception without re-raise
❌ Never load multiple 30B+ models simultaneously
❌ Never skip adversarial review for code blocks
❌ Never proceed without explicit user approval on changes
❌ Never commit without cleaning zombie processes
❌ Never use pandas in AIMO subsystem (use polars)

---

## See Also

- `MATH_REASONING_SWARM_PRIME` - Skill definition for swarm architecture
- `FLUME_ENCODING_PRIME` - Latent vector encoding for proof stability
- `HIHO_STABILITY_PRIME` - 0.5 coherence threshold for dual-run verification
- `spec.md` - Full specification with architectural pillars
- `plan.md` - 4-phase implementation plan
- `TROUBLESHOOTING_RETRO.md` - Detailed issue post-mortems
