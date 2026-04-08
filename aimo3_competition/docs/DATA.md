# AI Mathematical Olympiad - Progress Prize 3: Data Documentation

> **Source**: https://www.kaggle.com/competitions/ai-mathematical-olympiad-progress-prize-3/data  
> **Location**: [../data/](../data/)

---

## Back Links

← [Back to Competition Index](../README.md) | [Overview](./OVERVIEW.md) | [Rules](./RULES.md)

---

## Files Description

### 1. test.csv
**Public test set** - 3 problems for development

| Column | Type | Description |
|--------|------|-------------|
| `id` | string | Unique problem identifier (e.g., "000aaa") |
| `problem` | string | Mathematical problem in LaTeX format |

**Example entries:**
```csv
id,problem
000aaa,"What is $1-1$?"
111bbb,"What is $0\times10$?"
222ccc,"Solve $4+x=4$ for $x$."
```

**Location**: [../data/test.csv](../data/test.csv)

---

### 2. reference.csv
**Training set** - 10 solved problems with answers

| Column | Type | Description |
|--------|------|-------------|
| `id` | string | Unique problem identifier |
| `problem` | string | Mathematical problem in LaTeX format |
| `answer` | integer | Correct integer answer |

**Problem Categories in Reference:**

| ID | Category | Difficulty | Answer |
|----|----------|------------|--------|
| 0e644e | Geometry (Triangle) | IMO-level | 336 |
| 26de63 | Number Theory | Advanced | 32951 |
| 424e18 | Combinatorics (Tournament) | IMO-level | 21818 |
| 42d360 | Number Theory (Base representation) | Advanced | 32193 |
| 641659 | Geometry (Triangle + Fibonacci) | IMO-level | 57447 |
| 86e8e5 | Number Theory (Divisors) | Advanced | 8687 |
| 92ba6a | Algebra (Word problem) | AIME-level | 50 |
| 9c1c5f | Functional Equations | Olympiad | 580 |
| a295e9 | Combinatorics (Rectangles) | Olympiad | 520 |
| dd7f5e | Abstract Algebra | Advanced | 160 |

**Location**: [../data/reference.csv](../data/reference.csv)

---

### 3. sample_submission.csv
**Submission format template**

```csv
id,answer
000aaa,0
111bbb,0
222ccc,0
```

**Location**: [../data/sample_submission.csv](../data/sample_submission.csv)

---

### 4. AIMO3_Reference_Problems.pdf
**Detailed solutions manual** (676KB)

Contains:
- Full problem statements
- Step-by-step solutions
- Mathematical reasoning explanations
- Hints and approaches

**Location**: [../data/AIMO3_Reference_Problems.pdf](../data/AIMO3_Reference_Problems.pdf)

---

## Evaluation Infrastructure

### kaggle_evaluation/ Directory
Code required for inference server implementation:

| File | Purpose |
|------|---------|
| `aimo_3_gateway.py` | Competition gateway implementation |
| `aimo_3_inference_server.py` | Base inference server class |
| `core/base_gateway.py` | Gateway base functionality |
| `core/relay.py` | gRPC communication layer |
| `core/templates.py` | Server templates |

### Key Technical Details

**Inference Server Requirements:**
- Must implement `predict(data_batch, transforms)` method
- Receives problems via gRPC from gateway
- Returns DataFrame with `id` and `answer` columns
- 9-hour total timeout across all problems

**Response Format:**
```python
import polars as pl

# Return format for predict()
return pl.DataFrame({
    'id': ['000aaa', '111bbb'],
    'answer': [42, 0]
})
```

---

## Problem Difficulty Distribution

Based on reference problems:

| Difficulty Level | Count | Examples |
|-----------------|-------|----------|
| **AIME-level** | 1 | Word problems, simple algebra |
| **National Olympiad** | 2 | Combinatorics, functional equations |
| **IMO-level** | 7 | Complex geometry, advanced number theory |

---

## Data Statistics

### Reference Set
- **Total problems**: 10
- **Average answer size**: ~12,000 (range: 50 - 57,447)
- **Answer format**: All positive integers
- **Problem length**: 50-500 characters (LaTeX)

### Answer Distribution
```
Min: 50
Max: 57,447
Mean: ~11,500
Median: ~1,600
```

---

## Usage Guidelines

### For Training
1. Use `reference.csv` to train/validate your models
2. Study `AIMO3_Reference_Problems.pdf` for solution strategies
3. Test on `test.csv` to verify inference pipeline

### For Submission
1. Build inference server following `aimo_3_inference_server.py` template
2. Submit to Kaggle for evaluation on private test set
3. Results appear on leaderboard within minutes

---

## External Resources

- [Kaggle Data Page](https://www.kaggle.com/competitions/ai-mathematical-olympiad-progress-prize-3/data)
- [Competition Overview](./OVERVIEW.md)
- [Evaluation Rules](./RULES.md)

---

← [Back to Competition Index](../README.md)
