# AI Mathematical Olympiad - Progress Prize 3: Rules

> **Source**: https://www.kaggle.com/competitions/ai-mathematical-olympiad-progress-prize-3/rules  
> **Status**: Accepted by manderson240

---

## Back Links

← [Back to Competition Index](../README.md) | [Overview](./OVERVIEW.md) | [Data](./DATA.md)

---

## Competition Rules Summary

### 1. Eligibility
- Open to individuals and teams
- Must comply with Kaggle's general competition rules
- Rules acceptance required before participation

### 2. Submission Requirements

**Format**: Code competition (inference server)

**Technical Specs:**
- Maximum runtime: **9 hours per submission**
- Language: **Python only**
- Framework: Must use provided `kaggle_evaluation` infrastructure
- Output: Integer answers only

**Code Requirements:**
- Must implement inference server inheriting from `kaggle_evaluation.core.templates.InferenceServer`
- Must provide `predict(data_batch, transforms)` method
- Must return Polars DataFrame with `id` and `answer` columns

### 3. Evaluation

**Scoring:**
- +1 point for each correct answer
- No partial credit
- Wrong answers score 0
- Maximum score based on number of test problems (~50)

**Test Sets:**
- **Public**: 3 problems for development (in `test.csv`)
- **Private**: Hidden test set used for final scoring
- Private set is randomly shuffled for each submission

**Final Ranking:**
- Based on private test set performance
- Tiebreaker: Earlier submission time wins
- Top submissions undergo manual review

### 4. Daily Submission Limits

Standard Kaggle competition limits apply:
- Limited submissions per day (typically 2-5)
- Check competition page for current limits

### 5. Prohibited Actions

**Not Allowed:**
- Manual labeling of test data
- Using external datasets beyond reference problems
- Multiple accounts to circumvent submission limits
- Sharing private test set information
- Code that attempts to access the test set outside the inference server

### 6. Prize Eligibility

**Progress Prize Requirements:**
- Must achieve breakthrough performance
- Solution must be reproducible
- Code will be reviewed
- May require technical documentation

### 7. Code Competition Specific Rules

**Inference Server:**
- Must run within Kaggle's compute environment
- No internet access during inference
- All models must be loaded within the 9-hour window
- Predictions must be generated programmatically

**Timeouts:**
- **Total**: 9 hours for entire test set
- **Per-problem**: Implicit (total / number of problems)
- **Setup**: Included in 9-hour limit

### 8. Manual Review Process

Top submissions will be:
1. Verified for rule compliance
2. Reviewed for valid methodology
3. Checked for data leakage or cheating
4. May require code explanation

### 9. Rules Acceptance

- Acceptance required before first submission
- One-time acceptance per competition
- **Status**: ✅ Accepted by `manderson240`

---

## Competition Timeline Rules

| Phase | Rule |
|-------|------|
| **Before Deadline** | Unlimited submissions (within daily limits) |
| **After Deadline** | No new submissions accepted |
| **Final Rerun** | All submissions re-run on private test set |
| **Winner Announcement** | After manual review completion |

---

## Technical Constraints

### Compute Resources
- **CPU**: Available throughout
- **GPU**: Optional (specify in kernel-metadata.json)
- **RAM**: Limited by Kaggle environment
- **Disk**: ~20GB available

### Network
- **Training**: Internet allowed for model download
- **Inference**: No internet access
- **Models**: Must be cached or pre-downloaded

### Dependencies
Standard Kaggle environment packages available:
- PyTorch, TensorFlow
- Transformers, Accelerate
- NumPy, Pandas, Polars
- Standard library

---

## Fair Play Guidelines

1. **Original Work**: Solutions must be your own
2. **Reference Usage**: Reference problems are for training only
3. **Teamwork**: Allowed, must be declared
4. **External Help**: Discussion allowed, code sharing prohibited

---

## Violation Consequences

| Violation | Consequence |
|-----------|-------------|
| Minor infraction | Warning |
| Major infraction | Disqualification |
| Cheating | Ban from future competitions |

---

## External Links

- [Full Rules on Kaggle](https://www.kaggle.com/competitions/ai-mathematical-olympiad-progress-prize-3/rules)
- [Kaggle Competition Rules](https://www.kaggle.com/competitions-rules)
- [Competition Overview](./OVERVIEW.md)
- [Data Documentation](./DATA.md)

---

← [Back to Competition Index](../README.md)
