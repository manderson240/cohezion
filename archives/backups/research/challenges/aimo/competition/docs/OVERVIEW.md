# AI Mathematical Olympiad - Progress Prize 3: Overview

> **Source**: https://www.kaggle.com/competitions/ai-mathematical-olympiad-progress-prize-3/overview  
> **Competition**: AI Mathematical Olympiad - Progress Prize 3  
> **Type**: Featured Code Competition

---

## Back Links

← [Back to Competition Index](../README.md) | [Data](./DATA.md) | [Rules](./RULES.md) | [Leaderboard](../leaderboard/README.md)

---

## Competition Summary

**Goal**: Solve international-level math challenges using artificial intelligence models

The AI Mathematical Olympiad (AIMO) Progress Prize 3 is a code competition where participants build AI systems capable of solving problems at the level of the International Mathematical Olympiad (IMO). 

### What Makes This Competition Unique

- **Integer Answers Only**: Problems have deterministic integer solutions
- **Code Competition**: Your inference code runs on Kaggle's infrastructure
- **9-Hour Timeout**: Each submission has 9 hours to solve all test problems
- **Private Re-run**: Final evaluation uses a private test set to prevent overfitting
- **Manual Review**: Top submissions are manually reviewed for validity

---

## Competition Timeline

| Phase | Date | Description |
|-------|------|-------------|
| **Start** | November 20, 2025 | Competition launched |
| **End** | April 15, 2026 | Submission deadline (8 days remaining) |
| **Evaluation** | Post-deadline | Private re-run on hidden test set |

---

## Prize Structure

| Place | Prize |
|-------|-------|
| **1st** | Progress Prize (amount TBD) |
| **Total Pool** | $2,207,152 USD |

The competition is part of the AI Mathematical Olympiad series, with progress prizes awarded for breakthrough achievements.

---

## Problem Format

### Input
Mathematical problems written in LaTeX format. Example:
```
Let $ABC$ be an acute-angled triangle with integer side lengths...
```

### Output
A single integer answer. Examples from reference data:
- Simple: "What is $1-1$?" → `0`
- Complex: Geometry proof → `57447`

### Difficulty Levels
Problems range from:
- **AMC/AIME level** (American competitions)
- **National Olympiad level** (country-specific)
- **IMO level** (International Mathematical Olympiad - hardest)

---

## Participation Stats

| Metric | Value |
|--------|-------|
| **Total Participants** | 3,921 |
| **Competition Type** | Featured |
| **Active Now** | Yes |

---

## Evaluation Methodology

### Public Test Set
- 3 problems visible during development
- Used for debugging and validation

### Private Test Set
- Hidden until final re-run
- Contains problems of similar difficulty
- Shuffled differently for each submission

### Scoring
- **Correct answers**: +1 point per problem
- **Maximum score**: 50 (or more in private set)
- **Tiebreaker**: Submission time (earlier is better)

---

## Key Challenges

1. **Mathematical Reasoning**: Requires multi-step logical deduction
2. **Precision**: Must output exact integer, no approximations
3. **Time Constraints**: 9 hours total for all problems
4. **Generalization**: Must work on unseen problem types

---

## Reference Materials

- [Reference Problems](../data/AIMO3_Reference_Problems.pdf) - 10 solved examples with detailed solutions
- [Test Data](../data/test.csv) - Public test set
- [Sample Submission](../data/sample_submission.csv) - Output format template

---

## External Links

- [Competition Homepage](https://www.kaggle.com/competitions/ai-mathematical-olympiad-progress-prize-3)
- [Full Rules](https://www.kaggle.com/competitions/ai-mathematical-olympiad-progress-prize-3/rules)
- [Data Page](https://www.kaggle.com/competitions/ai-mathematical-olympiad-progress-prize-3/data)
- [Leaderboard](https://www.kaggle.com/competitions/ai-mathematical-olympiad-progress-prize-3/leaderboard)

---

← [Back to Competition Index](../README.md)
