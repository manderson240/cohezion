---
project_name: aimo-progress-prize-3
author: Mike-anderson
date: 2026-03-24
version: 1.0
status: draft
workflow_type: architecture
components:
  - Doer (Perception & Execution)
  - Thinker (Reasoning & Interpolation)
  - Knower (Validation & Stability)
patterns:
  - Triune Manifold
  - 12D State Vector
  - Dual-Run Verification
  - Adversarial Review
---

# Architecture - AIMO Mathematical Reasoning Swarm

## Overview

This document defines the technical architecture for the AIMO Mathematical Reasoning Swarm (MRS), a sovereign AI system that treats mathematical proofs as stable trajectories in a 12-dimensional latent manifold.

**Key Innovation:** Triune Manifold architecture segregating responsibilities into:
- **Doer** (12D perception + symbolic execution)
- **Thinker** (512D reasoning + specialist routing)
- **Knower** (2048D validation + stability scoring)

---

## Architectural Pillars

### 1. The Doer (Perception & Execution)

**Responsibility:** Parse LaTeX problems, execute symbolic code, extract answers.

**Components:**
- `MathParser`: LaTeX → 12D state vector
- `SymbolicExecutor`: Sandboxed Python execution (SymPy/NumPy)
- `MockAIMOApi`: Competition API integration

**Input:** LaTeX problem string
**Output:** 12D state vector + integer answer (0-99,999)

**Data Flow:**
```
LaTeX String → MathParser → 12D Vector → SymbolicExecutor → Answer
```

**Key Methods:**
```python
class MathParser:
    def parse(latex_string: str) -> MathProblemState
    def extract_equations(text: str) -> list[str]
    def extract_variables(text: str) -> set[str]
    def get_max_nesting(text: str) -> int

class SymbolicExecutor:
    def execute(code: str, timeout: int = 30) -> ExecutionResult
```

---

### 2. The Thinker (Reasoning & Interpolation)

**Responsibility:** Route problems, generate reasoning chains, encode proof steps.

**Components:**
- `SwarmCoordinator`: Domain routing + journey planning
- `BaseSpecialist`: 4 domain specialists (Algebraist, Geometer, NumberTheorist, Combinatorist)
- `AdversaryAgent`: Adversarial review loop

**Input:** 12D state vector
**Output:** Reasoning chain + Python code block

**Data Flow:**
```
12D Vector → SwarmCoordinator → Specialist Selection → LLM Reasoning → Code Block
```

**Specialist Routing:**
```python
def plan_journey(problem_id: str, problem_text: str) -> JourneyTask:
    state = MathParser().parse(problem_text)
    
    # Domain detection via keyword matching
    if state.algebra > threshold:
        domain = "Algebraist"
    elif state.number_theory > threshold:
        domain = "NumberTheorist"
    elif state.geometry > threshold:
        domain = "Geometer"
    elif state.combinatorics > threshold:
        domain = "Combinatorist"
    
    return JourneyTask(
        assigned_specialists=[domain, get_secondary_specialist(domain)],
        reasoning_complexity=state.reasoning_complexity
    )
```

**Adversarial Review Loop:**
```python
for attempt in range(2):  # Max 2 refinement cycles
    review_result = adversary.review(problem_text, reasoning_chain, code_block)
    if review_result["verified"]:
        break
    else:
        reasoning_chain = refine(reasoning_chain, review_result["critique"])
```

---

### 3. The Knower (Validation & Stability)

**Responsibility:** Verify dual-run consistency, audit reasoning, resolve ties.

**Components:**
- `KnowerAuditor`: Dual-run comparison + stability scoring
- `TieBreaker`: Majority voting for divergent answers

**Input:** Two reasoning chains + answers
**Output:** Final answer + stability score

**Data Flow:**
```
[Run1, Run2] → KnowerAuditor → Consistency Check → Final Answer
                    ↓
              Divergent? → TieBreaker → Majority Vote
```

**Audit Protocol:**
```python
def audit_runs(run_results: list[int], reasoning_chains: list[str]) -> AuditResult:
    ans1, ans2 = run_results
    
    if ans1 == ans2:
        stability_score = 1.0
        action = "CONSISTENT"
        final_answer = ans1
    else:
        stability_score = 0.0
        action = "TIE_BREAKER"
        final_answer = None  # Trigger tie-breaker
    
    return AuditResult(
        stability_score=stability_score,
        action=action,
        final_answer=final_answer
    )
```

**Tie-Breaker:**
```python
if audit["action"] == "TIE_BREAKER":
    res3 = tie_specialist.solve(problem_text)  # Run 3 with Phi-4
    final_answer = resolve_tie(ans1, ans2, res3)  # Majority voting
```

---

## 12D State Vector Specification

### Mathematical Definition

The 12D state vector encodes problem characteristics across 3 spatial, 1 temporal, and 8 brane dimensions:

```python
@dataclass
class MathProblemState:
    # 3 Spatial: Problem 'Geometry' (Structural complexity)
    structural_depth: float      # Max nesting of LaTeX braces { }
    token_density: float         # Ratio of math tokens to text
    constraint_density: float    # Constraints per variable
    
    # 1 Time: Temporal 'Flow' (Expected reasoning steps)
    reasoning_complexity: float  # Estimated CoT length
    
    # 8 Brane: Domain and Character
    algebra: float               # Algebra keyword probability
    number_theory: float         # Number theory keyword probability
    geometry: float              # Geometry keyword probability
    combinatorics: float         # Combinatorics keyword probability
    calculus: float              # Calculus keyword probability
    logic_type: float            # 0: Calculation, 1: Optimization, 2: Proof
    abstraction_level: float     # Abstract structures (groups, rings)
    stability_heuristic: float   # Expected cross-run consistency
```

### Computation Details

**structural_depth:**
```python
def get_max_nesting(text: str) -> int:
    max_depth = 0
    current_depth = 0
    for char in text:
        if char == '{':
            current_depth += 1
            max_depth = max(max_depth, current_depth)
        elif char == '}':
            current_depth -= 1
    return max_depth
```

**token_density:**
```python
def compute_token_density(text: str) -> float:
    math_tokens = len(re.findall(r'\$[^$]+\$|\\[a-z]+', text))
    total_tokens = len(text.split())
    return math_tokens / max(total_tokens, 1)
```

**domain_scores:**
```python
def compute_domain_score(text: str, domain: str) -> float:
    patterns = self.domains[domain]  # Regex patterns from config
    matches = sum(len(re.findall(p, text)) for p in patterns)
    return min(matches / 10.0, 1.0)  # Normalize to [0, 1]
```

### Vector to Numpy Array

```python
def to_vector(self) -> np.ndarray:
    return np.array([
        self.structural_depth,
        self.token_density,
        self.constraint_density,
        self.reasoning_complexity,
        self.algebra,
        self.number_theory,
        self.geometry,
        self.combinatorics,
        self.calculus,
        self.logic_type,
        self.abstraction_level,
        self.stability_heuristic,
    ])
```

---

## Component Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    AIMO Competition API                      │
│              (kaggle_evaluation.aimo_3_inference_server)     │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ iter_test() → problem_text
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                      SwarmDriver                             │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              SwarmCoordinator                         │  │
│  │  • plan_journey() → JourneyTask                       │  │
│  │  • assigned_specialists = [primary, secondary]        │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                │
│              ┌─────────────┴─────────────┐                 │
│              ↓                           ↓                 │
│  ┌──────────────────────┐   ┌──────────────────────┐      │
│  │   Run 1: Primary     │   │   Run 2: Secondary   │      │
│  │   BaseSpecialist     │   │   BaseSpecialist     │      │
│  │   • solve()          │   │   • solve()          │      │
│  │   • extract_answer() │   │   • extract_answer() │      │
│  └──────────────────────┘   └──────────────────────┘      │
│              │                           │                 │
│              └─────────────┬─────────────┘                 │
│                            ↓                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              KnowerAuditor                            │  │
│  │  • audit_runs() → stability_score                    │  │
│  │  • action: CONSISTENT | TIE_BREAKER                  │  │
│  │  • final_answer: int | None                          │  │
│  └──────────────────────────────────────────────────────┘  │
│                            │                                │
│              ┌─────────────┴─────────────┐                 │
│              ↓                           ↓                 │
│     [CONSISTENT]                  [TIE_BREAKER]            │
│         │                               │                  │
│         │                               ↓                  │
│         │                    ┌──────────────────────┐     │
│         │                    │   TieBreaker         │     │
│         │                    │   • Run 3 (Phi-4)    │     │
│         │                    │   • Majority Vote    │     │
│         │                    └──────────────────────┘     │
│         │                               │                  │
│         └───────────────┬───────────────┘                  │
│                         ↓                                  │
│              final_answer → env.predict()                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Internal Components                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │  MathParser  │  │  Adversary   │  │  Symbolic    │     │
│  │  • 12D State │  │  Agent       │  │  Executor    │     │
│  │  • Equations │  │  • Review    │  │  • SymPy     │     │
│  │  • Variables │  │  • Critique  │  │  • NumPy     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### End-to-End Problem Processing

```
1. AIMO API yields problem_text (single row)
   ↓
2. MathParser.parse(problem_text)
   → MathProblemState (12D vector)
   ↓
3. SwarmCoordinator.plan_journey(problem_id, problem_text)
   → JourneyTask(assigned_specialists=[...])
   ↓
4. Run 1: BaseSpecialist(primary).solve(problem_text)
   → reasoning_chain_1 + answer_1
   ↓
5. Run 2: BaseSpecialist(secondary).solve(problem_text)
   → reasoning_chain_2 + answer_2
   ↓
6. KnowerAuditor.audit_runs([answer_1, answer_2], [chain_1, chain_2])
   → AuditResult(stability_score, action, final_answer)
   ↓
7. If TIE_BREAKER:
   Run 3: BaseSpecialist(tie_breaker).solve(problem_text)
   → answer_3
   final_answer = resolve_tie(answer_1, answer_2, answer_3)
   ↓
8. env.predict(submission_df)  # Called exactly once
   ↓
9. Next problem (repeat steps 1-8)
```

---

## Specialist Routing Logic

### Domain Detection Keywords

| Domain | Keywords |
|--------|----------|
| **Algebraist** | `solve`, `equation`, `function`, `polynomial`, `root`, `coefficient`, `quadratic`, `cubic`, `inequality` |
| **NumberTheorist** | `integer`, `divisor`, `prime`, `modular`, `congruent`, `gcd`, `lcm`, `divides`, `mod`, `remainder`, `coprime` |
| **Geometer** | `triangle`, `circle`, `area`, `angle`, `perpendicular`, `parallel`, `radius`, `tangent`, `chord`, `vertex`, `polygon` |
| **Combinatorist** | `number of ways`, `how many`, `permutation`, `combination`, `probability`, `subset`, `distinct`, `arrangement`, `die`, `dice`, `coin` |

### Routing Algorithm

```python
def route_by_domain(problem_text: str) -> str:
    domain_scores = {
        "Algebraist": compute_domain_score(problem_text, "algebra"),
        "NumberTheorist": compute_domain_score(problem_text, "number_theory"),
        "Geometer": compute_domain_score(problem_text, "geometry"),
        "Combinatorist": compute_domain_score(problem_text, "combinatorics"),
    }
    
    # Select primary specialist (highest score)
    primary = max(domain_scores, key=domain_scores.get)
    
    # Select secondary specialist (second highest or same if tie)
    sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
    secondary = sorted_domains[1][0] if len(sorted_domains) > 1 else primary
    
    return [primary, secondary]
```

---

## Resource Management

### Memory Safety (12GB VRAM)

**Constraint:** Only one large model (≥30B) loaded at a time.

**Strategy:**
```python
# Sequential model loading
for problem in problems:
    # Load primary model
    load_model("DeepSeek-R1-32B")
    run1_result = specialist1.solve(problem_text)
    unload_model("DeepSeek-R1-32B")  # Free VRAM
    
    # Load secondary model
    load_model("DeepSeek-R1-32B")
    run2_result = specialist2.solve(problem_text)
    unload_model("DeepSeek-R1-32B")  # Free VRAM
    
    # Keep_alive: 0 ensures model unloads after request
    keep_alive="0"
```

**Memory Budget:**
| Model | Quantization | VRAM | Strategy |
|-------|--------------|------|----------|
| DeepSeek-R1-32B | Q5_K_M | ~18GB | CPU offload (main RAM) |
| Phi-4-7B | Q6_K | ~6GB | GPU only |
| Qwen2.5-Coder-14B | Q5_K_M | ~9GB | GPU only |
| qwen2-math:1.5B | N/A | ~2GB | GPU only |

---

### Time Budgeting

**Per-Problem Allocation:**
```python
TARGET_TIME = 150       # seconds (compute)
SAFETY_MARGIN = 15      # seconds (overhead)
TOTAL_TIME = 165        # seconds per problem

# Timeout configuration
timeout = 300           # 5 minutes (covers CPU fallback)
num_thread = 16         # Maximize CPU utilization
```

**Budget Breakdown:**
| Phase | Time | Component |
|-------|------|-----------|
| Parsing | ~1s | MathParser |
| Run 1 | ~75s | Primary LLM + Adversarial review |
| Run 2 | ~75s | Secondary LLM + Adversarial review |
| Audit | ~5s | KnowerAuditor |
| Tie-Breaker | ~75s | If triggered (Run 3) |
| Overhead | ~15s | I/O, logging, process mgmt |

---

## Error Handling Architecture

### Timeout Configuration

**MANDATORY:** All API calls must have explicit timeouts.

```python
payload = {
    "model": self.model_name,
    "messages": messages,
    "stream": False,
    "keep_alive": "1m",
    "options": {
        "temperature": 0.2,
        "num_ctx": 8192,
        "num_thread": 16
    },
}

try:
    response = requests.post(
        self.ollama_url,
        json=payload,
        timeout=self.timeout  # 300 seconds
    )
    response.raise_for_status()
    result = response.json()
except requests.exceptions.Timeout as e:
    return f"Error calling Ollama: Read timed out. (read timeout={self.timeout})"
except requests.exceptions.RequestException as e:
    return f"Error calling Ollama: {str(e)}"
```

---

### Fail-Safe Patterns

**CRITICAL:** Fallback logic must never mask `NameError` or `ImportError`.

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

---

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
    
    # Fallback: last number in response
    numbers = re.findall(r"\d+", response_text)
    return int(numbers[-1]) if numbers else 0
```

---

## Security Architecture

### Sandboxed Execution

**Constraint:** No file I/O, no network access in code execution.

```python
class SymbolicExecutor:
    def execute(self, code: str, timeout: int = 30) -> ExecutionResult:
        # Restricted globals
        safe_globals = {
            "sympy": sympy,
            "numpy": np,
            "__builtins__": {"int": int, "float": float, "str": str, "len": len},
        }
        
        # Restricted locals
        safe_locals = {}
        
        try:
            exec(code, safe_globals, safe_locals)
            return safe_locals.get("ans", 0)
        except Exception as e:
            return f"Execution error: {str(e)}"
        finally:
            # Cleanup
            safe_globals.clear()
            safe_locals.clear()
```

---

### Input Validation

**LaTeX parsing with regex sanitization:**

```python
def clean_latex(text: str) -> str:
    # Remove potentially dangerous LaTeX commands
    text = text.replace(r"\\", " ")
    text = re.sub(r"\\(text|textbf|textit)\{([^}]*)\}", r"\2", text)
    text = re.sub(r"\\[a-z]+\{[^}]*\}", "", text)  # Remove unknown commands
    return text
```

---

### Output Validation

**Integer range check (0-99,999):**

```python
def validate_answer(answer: int) -> bool:
    return 0 <= answer <= 99999
```

---

## Testing Architecture

### Mock Environment

**Pattern:**
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

accuracy = env.competition.get_score()
```

**Test Requirements:**
- 10 reference problems
- 100% accuracy target
- ≥0.90 stability target

---

### Integration Test Requirements

**Must Test:**
1. Single-row API iteration
2. Exactly one `env.predict()` call per row
3. Dual-run execution for all problems
4. Tie-breaker trigger when answers diverge
5. Adversarial review loop (max 2 cycles)
6. Answer extraction with error handling

---

## Deployment Architecture

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
- Log progress: `sprint_monitor.log`

**After Sprint:**
- Clean processes
- Save metrics: `research_results.tsv`
- Archive logs

---

### Logging & Telemetry

**Progress Tracking:**
```python
def log_progress(problem_num: int, total: int, elapsed: float, latency: float):
    log(f"Problem {problem_num}/{total} | "
        f"Elapsed: {elapsed:.1f}s | "
        f"Latency: {latency:.1f}s | "
        f"Avg: {avg_latency:.1f}s")
```

**Metrics Logged:**
- Problem X/110
- Time elapsed
- Average latency
- Stability score
- Final accuracy

---

## Appendix

### A. Related Documents

- `spec.md`: Full specification with architectural pillars
- `prd.md`: Product requirements
- `project-context.md`: AI agent implementation rules
- `TROUBLESHOOTING_RETRO.md`: Issue post-mortems

### B. File Manifest

| File | Lines | Purpose |
|------|-------|---------|
| `base_specialist.py` | 151 | Specialist swarm agent base class |
| `math_parser.py` | 163 | LaTeX → 12D state vector |
| `swarm_coordinator.py` | 48 | Domain routing + journey planning |
| `knower_auditor.py` | 65 | Dual-run verification |
| `symbolic_executor.py` | 164 | Sandboxed code execution |
| `adversary_agent.py` | 61 | Adversarial review loop |
| `mock_aimo_api.py` | 50 | Competition API mock |
| `swarm_driver.py` | 92 | End-to-end orchestration |

---

**Document Status:** Draft (pending PRD approval + epics)
**Next:** Create Epics & Stories → Sprint Planning
