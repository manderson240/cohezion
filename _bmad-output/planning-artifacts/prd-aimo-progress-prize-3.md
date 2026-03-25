---
project_name: aimo-progress-prize-3
author: Mike-anderson
date: 2026-03-24
version: 1.0
status: draft
workflow_type: prd
classification:
  projectType: AI Competition / Mathematical Reasoning
  domain: Machine Learning / Formal Verification
  complexity: Very High
  projectContext: Brownfield (existing implementation, planning needed)
---

# Product Requirements Document - AIMO Progress Prize 3

## Executive Summary

The AIMO Mathematical Reasoning Swarm is an autonomous AI system designed to win the **AI Mathematical Olympiad Progress Prize 3** ($2,207,152 prize pool) by solving IMO-level LaTeX mathematics problems with high accuracy and stability.

**Key Innovation:** Triune Manifold architecture (Doer/Thinker/Knower) that treats mathematical proofs as stable trajectories in a 12-dimensional latent space, achieving ≥0.95 dual-run consistency through adversarial verification.

**Target:** ≥47/50 on competition leaderboard (94% accuracy) with ≥0.95 stability ratio.

---

## Competition Requirements

### Official Rules

**Competition:** AI Mathematical Olympiad - Progress Prize 3
**Platform:** Kaggle
**Prize Pool:** $2,207,152
**Timeline:** 5-hour compute window, 110 problems
**Format:** LaTeX text-only (no diagrams)
**Output:** Integer answers (0-99,999)

### Data Format

**Input:**
- `reference.csv`: 10 benchmark problems with ground truth
- `test.csv`: 50 public + 50 hidden problems
- `sample_submission.csv`: Template (`id`, `answer`)

**API Protocol:**
```python
from kaggle_evaluation.aimo_3_inference_server import AIMO3InferenceServer

def predict(problem_id: str, problem_text: str) -> int:
    # Must return integer 0-99999
    # Called exactly once per problem
    pass

server = AIMO3InferenceServer(predict)
```

### Constraints

**Runtime:**
- Total Time: 5 hours (18,000 seconds)
- Problems: 110
- Time per Problem: 150 seconds + 15s safety margin
- No internet access during runtime
- No human hand-labeling

**Compute:**
- Memory: 128GB RAM / 12GB VRAM
- GPU: H100 (5-hour limit)
- Models: Pre-March 15, 2026 cutoff only

---

## Success Metrics

### Primary Metrics

| Metric | Target | Threshold | Measurement |
|--------|--------|-----------|-------------|
| Leaderboard Accuracy | ≥47/50 | ≥40/50 | Private leaderboard |
| Dual-Run Stability | ≥0.95 | ≥0.90 | Ratio of consistent runs |
| Reference Problems | 100% (10/10) | ≥80% (8/10) | Internal benchmark |

### Secondary Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Time per Problem | ≤165s | Avg latency |
| Memory Usage | ≤12GB VRAM | Peak during execution |
| Model Throughput | 1 problem / 150s | Sustained rate |

### MVP Scope

**Phase 1 MVP:** 100% accuracy on 10 reference problems
**Phase 2 MVP:** ≥90% accuracy on 50 public problems
**Phase 3 Production:** ≥94% accuracy on full leaderboard

---

## Functional Requirements

### FR-1: Problem Perception (Doer)

**Description:** Parse LaTeX problem strings into structured 12D state vectors.

**Acceptance Criteria:**
- [ ] Extract all equations from LaTeX ($...$ delimiters)
- [ ] Identify variables (single letters in math mode)
- [ ] Compute structural depth (brace nesting)
- [ ] Calculate token density (math/text ratio)
- [ ] Detect domain keywords (algebra, geometry, number theory, combinatorics)
- [ ] Generate 12D numpy array for routing

**Tools:** MathParser, SymPy, NumPy

---

### FR-2: Specialist Routing (Thinker)

**Description:** Route problems to domain specialists based on 12D state vector.

**Acceptance Criteria:**
- [ ] Algebraist: Detect `solve`, `equation`, `polynomial`, `inequality`
- [ ] NumberTheorist: Detect `integer`, `prime`, `modular`, `gcd`, `divides`
- [ ] Geometer: Detect `triangle`, `circle`, `area`, `angle`, `radius`
- [ ] Combinatorist: Detect `how many`, `permutation`, `probability`, `subset`
- [ ] Assign primary + secondary specialist for dual-run

**Output:** `task.assigned_specialists = ["Algebraist", "NumberTheorist"]`

---

### FR-3: Reasoning Chain Generation (Thinker)

**Description:** Generate step-by-step mathematical proofs using LLMs.

**Acceptance Criteria:**
- [ ] Load specialist system prompt from JSON
- [ ] Include math knowledge vault (theorems, identities)
- [ ] Generate CoT reasoning with LaTeX formatting
- [ ] Extract Python code blocks for symbolic execution
- [ ] Run adversarial review (max 2 refinement cycles)
- [ ] Timeout: 300 seconds for reasoning models

**Models:** DeepSeek-R1-32B (primary), Phi-4-7B (verifier)

---

### FR-4: Symbolic Execution (Doer)

**Description:** Execute Python code for deterministic verification.

**Acceptance Criteria:**
- [ ] Sandboxed execution (no file I/O, no network)
- [ ] SymPy for symbolic manipulation
- [ ] NumPy for numerical validation
- [ ] Timeout: 30 seconds per execution
- [ ] Capture stdout/stderr for debugging
- [ ] Return execution result or error

---

### FR-5: Dual-Run Verification (Knower)

**Description:** Execute two independent reasoning chains and verify consistency.

**Acceptance Criteria:**
- [ ] Run 1: Primary specialist (e.g., Algebraist)
- [ ] Run 2: Secondary specialist (or same if only one)
- [ ] Compare answers: `ans1 == ans2`
- [ ] Compute stability score: 1.0 if match, 0.0 if divergent
- [ ] Trigger tie-breaker if answers diverge
- [ ] Majority voting for final answer

**Target:** ≥0.95 stability ratio across all problems

---

### FR-6: Adversarial Review (Knower)

**Description:** Review reasoning chains for logical flaws and hallucination patterns.

**Acceptance Criteria:**
- [ ] Detect sign errors, division by zero, invalid assumptions
- [ ] Validate Python code correctness
- [ ] Identify common hallucination patterns
- [ ] Provide critique for refinement
- [ ] Max 2 refinement cycles
- [ ] Verified → proceed to answer extraction

**Model:** Phi-4-7B or Mistral-7B-Instruct

---

### FR-7: Answer Extraction (Doer)

**Description:** Extract final integer answer from reasoning chain.

**Acceptance Criteria:**
- [ ] Check for error BEFORE regex extraction
- [ ] Extract `\boxed{answer}` pattern
- [ ] Fallback: last number in response
- [ ] Return 0 on error (prevent error-as-answer)
- [ ] Validate range: 0-99,999

**Anti-Pattern:** Never use greedy regex on error messages

---

### FR-8: API Integration (Doer)

**Description:** Integrate with official AIMO evaluation API.

**Acceptance Criteria:**
- [ ] Use `kaggle_evaluation.aimo_3_inference_server`
- [ ] Call `env.predict()` exactly once per row
- [ ] Handle single-row constraint (no batch processing)
- [ ] Maintain progress telemetry (Problem X/110)
- [ ] Mock environment for testing with reference problems

---

## Non-Functional Requirements

### NFR-1: Performance

- **Latency:** ≤165 seconds per problem (including safety margin)
- **Throughput:** 110 problems / 5 hours = 0.37 problems/second
- **Memory:** ≤12GB VRAM peak usage
- **CPU:** 16 threads for fallback inference

---

### NFR-2: Reliability

- **Stability:** ≥0.95 dual-run consistency
- **Error Handling:** All API calls with explicit timeout=300
- **Fail-Safe:** Check error before answer extraction
- **Process Management:** Clean zombie processes before sprint

---

### NFR-3: Scalability

- **Sequential Execution:** One model loaded at a time
- **Memory Flushing:** `keep_alive: 0` between problems
- **Quantization:** Q5_K_M or Q6_K for 30B+ models
- **Model Unloading:** Explicit unload after each problem

---

### NFR-4: Security

- **Sandboxed Execution:** No file I/O, no network in code execution
- **No Internet:** Runtime without external access
- **Input Validation:** LaTeX parsing with regex sanitization
- **Output Validation:** Integer range check (0-99,999)

---

### NFR-5: Maintainability

- **Type Hints:** Mandatory (mypy --strict)
- **Error Logging:** All exceptions logged with context
- **Progress Tracking:** Telemetry logged to `sprint_monitor.log`
- **Documentation:** Project context for AI agents

---

## Model Selection

### Primary Models (Pre-March 15, 2026 Cutoff)

| Role | Primary | Alternative | Quantization |
|------|---------|-------------|--------------|
| Lead Reasoner | DeepSeek-R1-Distill-Qwen-32B | Qwen2.5-Math-72B-Instruct | Q5_K_M |
| Logic Verifier | Phi-4-7B | Mistral-7B-Instruct-v0.3 | Q6_K |
| Code Executor | Qwen2.5-Coder-14B | DeepSeek-Coder-V2-Lite | Q5_K_M |
| Default Specialist | qwen2-math:1.5b | phi3:mini | N/A |

### Model Loading Strategy

**Sequential:**
1. Load Lead Reasoner → solve problem → unload
2. Load Logic Verifier → verify → unload
3. Load Code Executor → execute → unload

**Memory Budget:**
- 32B Q5_K_M: ~18GB VRAM (requires CPU offload)
- 7B Q6_K: ~6GB VRAM (fits in GPU)
- 1.5B: ~2GB VRAM (fits in GPU)

---

## MVP Scope

### MVP Definition

**Minimum Viable Product:** 100% accuracy on 10 reference problems with ≥0.90 stability.

**In Scope:**
- MathParser (12D state vector)
- 4 Specialists (Algebraist, Geometer, NumberTheorist, Combinatorist)
- Dual-run verification
- Adversarial review (1 cycle)
- Mock environment testing
- Stability fixes (4 critical bugs)

**Out of Scope (Post-MVP):**
- Model fine-tuning
- Cloud provider integration (Gemini, Claude)
- Advanced FLUME encoding
- Monte Carlo simulation

---

## User Stories

### US-1: As a competition participant, I want the swarm to solve reference problems accurately so that I can validate the implementation before submission.

**Acceptance Criteria:**
- 10/10 reference problems solved correctly
- ≥0.90 dual-run stability
- Progress logged to `sprint_monitor.log`

### US-2: As a developer, I want explicit timeout handling so that the swarm doesn't hang indefinitely.

**Acceptance Criteria:**
- All `requests.post()` calls have `timeout=300`
- Timeout exceptions logged and handled
- Fallback returns 0 (not error message)

### US-3: As a developer, I want error-as-answer prevention so that extracted answers are valid.

**Acceptance Criteria:**
- `extract_answer()` checks `response_text.startswith("Error")`
- Returns 0 on error (bypasses regex)
- No regex extraction on error tracebacks

### US-4: As a developer, I want process management so that zombie swarms don't cause OOM.

**Acceptance Criteria:**
- `ps aux | grep aimo | xargs kill -9` before sprint
- Monitor system load < 20
- Clean orphaned `uv run` and `python` processes

### US-5: As a developer, I want polars instead of pandas so that DataFrame operations are performant.

**Acceptance Criteria:**
- `import polars as pl` in all files
- No `import pandas as pd`
- DataFrame access logic fixed

---

## Technical Debt

### Known Issues (from Troubleshooting Retro)

1. **Infinite Hang:** Fixed with `timeout=300`
2. **Error-as-Answer:** Fixed with error check before regex
3. **Dependency Desync:** Fixed with polars migration
4. **Zombie Swarms:** Fixed with process cleanup

### Debt Priority

**P0 (Critical):** All 4 issues must be fixed before sprint
**P1 (High):** Adversarial review integration
**P2 (Medium):** FLUME proof navigator
**P3 (Low):** Monte Carlo simulation

---

## Risks & Mitigation

### Risk 1: Model Timeout on CPU

**Probability:** High
**Impact:** High (infinite hang)
**Mitigation:** `timeout=300`, `num_thread=16`

### Risk 2: Silent Extraction Failure

**Probability:** Medium
**Impact:** High (wrong answers)
**Mitigation:** Error check before regex, return 0 on error

### Risk 3: Memory OOM

**Probability:** Medium
**Impact:** High (crash)
**Mitigation:** Sequential model loading, `keep_alive: 0`

### Risk 4: Zombie Processes

**Probability:** Medium
**Impact:** High (system load 24+)
**Mitigation:** Process cleanup before sprint

---

## Compliance & Ethics

### Licensing

- **Code:** CC-BY 4.0
- **Datasets:** CC-BY 4.0
- **Models:** Pre-March 15, 2026 cutoff only

### Rule Adherence

- ✅ No internet access during runtime
- ✅ No human hand-labeling of test data
- ✅ Official AIMO API usage
- ✅ Integer answer format (0-99,999)

---

## Appendix

### A. Reference Problems

Location: `sandbox/aimo/reference_problems.json`
Format: `{id, problem, solution, answer}`
Count: 10 problems

### B. Competition Links

- **Kaggle:** https://www.kaggle.com/competitions/ai-mathematical-olympiad-progress-prize-3
- **Rules:** `conductor/tracks/aimo_progress_prize_3_20260319/RULES.md`
- **Data:** `conductor/tracks/aimo_progress_prize_3_20260319/DATA_OFFICIAL.md`

### C. Related Documents

- `spec.md`: Technical specification
- `plan.md`: Implementation plan
- `project-context.md`: AI agent rules
- `TROUBLESHOOTING_RETRO.md`: Issue post-mortems

---

**Document Status:** Draft (pending architecture + epics)
**Next:** Create Architecture document → Create Epics & Stories
