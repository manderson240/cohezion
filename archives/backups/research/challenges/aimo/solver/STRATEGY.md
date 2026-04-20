# AIMO3 Score Improvement Strategy

Current status: 0/50  
Goal: 44-46/50 (top tier)  
Gap: Need ~90% accuracy

---

## Phase 1: Get Off Zero (0 → 10+)

### Why 0 points?
1. ❌ Inference server format wrong
2. ❌ Runtime crash/timeout
3. ❌ All answers incorrect

### Solution
✅ **Simple working baseline** (simple_solver.py)
- HTTP requests directly to Ollama
- Clean answer extraction with regex
- Test locally first

### Quick Win
Run on reference problems:
```bash
cd aimo3_solver
python3 simple_solver.py
```

Expected: 2-5/10 correct with basic prompting (20-50%)

---

## Phase 2: Baseline Working (10 → 25)

### Model Selection
| Model | Speed | Math Quality | Score Potential |
|-------|-------|--------------|-----------------|
| qwen2-math:1.5b | ⚡ Fast | ⭐⭐ | 10-15% |
| deepseek-r1:7b | 🐢 Medium | ⭐⭐⭐⭐ | 30-40% |
| qwen3-coder:30b | 🐢 Slow | ⭐⭐⭐⭐⭐ | 40-50% |
| holo3-35b | 🐢 Slow | ⭐⭐⭐⭐⭐ | 40-50% |

### Prompt Engineering

**Current (Basic):**
```
Solve this problem...
FINAL ANSWER: <integer>
```

**Improved (Chain of Thought):**
```
You are an expert mathematician solving an IMO-level problem.

Problem: {problem}

Step 1: Identify the key mathematical concepts.
Step 2: Break down the problem into smaller parts.
Step 3: Solve each part systematically.
Step 4: Verify your answer.

Provide your complete reasoning, then give the final answer.

FINAL ANSWER: <integer>
```

**Advanced (Self-Consistency):**
- Generate N answers
- Vote on final answer
- Use confidence scoring

### Answer Extraction
Current: Simple regex  
Improved:
- Multiple patterns
- Validate integers
- Handle edge cases

---

## Phase 3: Competitive Scoring (25 → 40)

### Key Techniques (From Leaderboard Analysis)

#### 1. Self-Consistency / Majority Voting
```python
answers = []
for _ in range(N):
    ans = solve_with_temperature(problem, temp=0.7)
    answers.append(ans)

final_answer = mode(answers)  # Most common
```

#### 2. Tool-Integrated Reasoning (TIR)
Use Python to verify calculations:
```python
# After LLM reasoning
if "need calculation":
    code = generate_python_code(problem)
    result = execute_safely(code)
    answer = extract_from_result(result)
```

#### 3. Model Ensemble
```python
models = ['qwen3-coder:30b', 'deepseek-r1:7b', 'gemma4:31b']
answers = [m.solve(problem) for m in models]
final = vote_or_median(answers)
```

#### 4. Problem-Specific Strategies

**Problem Type Detection:**
- Geometry → Use coordinate/vector methods
- Number Theory → Modulo analysis
- Combinatorics → Recursive formulas
- Algebra → Symbolic manipulation

**Example (Geometry):**
```
If problem contains "triangle", "circle", "angle":
    Prompt += "Consider using coordinate geometry or trigonometry."
```

---

## Phase 4: Top Tier (40 → 46+)

### Techniques from Top Teams

#### 1. Batched Generation (ippeiogawa #1)
- Generate 4+ answers in parallel per problem
- High-confidence consensus voting
- Early stopping on agreement

#### 2. Context Truncation
- Limit tokens to 4096
- Focus on solution, not fluff
- Reduce VRAM usage

#### 3. Verification Loop
```
Solve → Verify → If uncertain, re-solve → Final answer
```

#### 4. Reference Problem Learning
- Fine-tune on patterns from reference
- Embed problem embeddings
- Similarity search for hints

---

## Implementation Plan

### Week 1 (Now - Apr 11)
- [ ] Get baseline working (2-5/10 on reference)
- [ ] Submit working solution (score > 0)

### Week 2 (Apr 11-13)
- [ ] Implement self-consistency (N=3)
- [ ] Add tool use for calculations
- [ ] Target: 20-30/50

### Week 3 (Apr 13-15)
- [ ] Ensemble of 2 models
- [ ] Problem-type specific prompting
- [ ] Target: 40-44/50

### Final Days (Apr 15)
- [ ] Final tweaks
- [ ] Submit best configuration
- [ ] Target: 44-46/50

---

## Quick Reference: Problem Breakdown

### Reference Problems by Difficulty

**Easy (AIME-level):**
- 92ba6a: Word problem → 50
- Target: Should get these right

**Medium (National Olympiad):**
- 9c1c5f: Functional equations → 580
- dd7f5e: Abstract algebra → 160
- Target: 50% accuracy

**Hard (IMO-level):**
- 641659: Complex geometry → 57447
- 26de63: Number theory → 32951
- 424e18: Combinatorics → 21818
- Target: Even top teams miss some

---

## Testing Commands

```bash
# Test on reference (fast model)
python3 simple_solver.py --test-public

# Test on full reference (best model)
python3 simple_solver.py

# Verify output format
python3 -c "import polars as pl; df = pl.read_csv('submission.csv'); print(df.head())"

# Submit to Kaggle (when ready)
kaggle competitions submit \
  -c ai-mathematical-olympiad-progress-prize-3 \
  -f submission.csv \
  -m "Baseline solver v1"
```

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Model timeout | Set max tokens, use faster models for test |
| Wrong format | Validate before submission |
| Ollama unavailable | Fallback answers, error handling |
| Low accuracy | Ensemble, self-consistency |

---

## Success Metrics

| Milestone | Score | Status |
|-----------|-------|--------|
| Working submission | > 0 | ⏳ Pending |
| Reference baseline | 20%+ | ⏳ Pending |
| Competitive | 30+ | ⏳ Pending |
| Top tier | 40+ | ⏳ Pending |
| Winner | 44+ | ⏳ Pending |

---

Next step: **Test simple_solver.py on reference problems**

---

← [Back to Competition](../aimo3_competition/)
