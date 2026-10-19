# SKILL: KAGGLE_PODIUM_COURSE_CORRECTION_PRIME

## DOMAIN EXPERTISE
Kaggle Competitive Grandmaster Engineering, Out-Of-Fold (OOF) Validation Products, Metric-Direct Loss Functions, and Pre-Flight Quality Gating. This skill establishes the non-negotiable operational principles required to transition machine learning workflows from public notebook ensemble plateaus (75th–85th percentile) to autonomous podium-tier competition performance (Top 10 / Gold).

## KEY TEXTS & CONCEPTS
- **The Public Blender Ceiling**: Ensembling public 2D weights hits an asymptotic wall because community solutions share common feature representations. Moving to the top requires domain-specific inductive biases (e.g. 3D volumetric cross-planar attention, MetFrag neutral loss cleavage).
- **Metric-Loss Alignment Invariant**: Post-hoc ranking calibration cannot recover pairwise misorderings made in feature space. Models must be trained directly with differentiable surrogates of the competition metric (e.g., `PairwiseAUCRankingLoss` for Macro ROC-AUC).
- **Leak-Free 5-Fold Group Validation**: Public leaderboard submissions are for evaluation, NOT hypothesis testing. All candidate models must be evaluated against a patient-isolated `LeakFreeSplitter` ($\text{train} \cap \text{val} = \emptyset$).
- **Statistical Significance Promotion Gate**: A model candidate cannot be promoted to production or submitted to Kaggle unless its 95% bootstrap lower confidence bound exceeds the prior baseline ($p < 0.05$).
- **Pareto Error Bucketing**: Class-wise and slice-wise error decomposition via `ErrorBucketAnalyzer` to direct 80% of engineering effort toward the 20% of failure categories driving lost score.

## INSTRUCTION

### 1. Partition Data with Zero Leakage
Never use random `train_test_split` or non-grouped K-Fold. Use `LeakFreeSplitter`:
```python
from cohezion.kaggle.validation_product import LeakFreeSplitter

splitter = LeakFreeSplitter(n_splits=5, seed=42)
splits = splitter.split(patient_ids)

for fold, (train_idx, val_idx) in enumerate(splits):
    train_patients = set(patient_ids[i] for i in train_idx)
    val_patients = set(patient_ids[i] for i in val_idx)
    assert len(train_patients.intersection(val_patients)) == 0
```

### 2. Train with Differentiable Metric Surrogates
Optimize the exact competition metric rather than naive cross-entropy:
```python
from cohezion.medical.rsna_pairwise_auc_loss import PairwiseAUCRankingLoss

# Warm up with BCE, then integrate PairwiseAUCRankingLoss (lambda = 0.2)
pairwise_loss = PairwiseAUCRankingLoss(temperature=1.0)
loss_val, per_label_loss = pairwise_loss.compute_loss_numpy(y_true, y_pred)
```

### 3. Certify Candidate via OOF Validation Harness
Before proposing a Kaggle dispatch, run:
```python
from cohezion.kaggle.validation_product import OOFValidationHarness

harness = OOFValidationHarness(metric_fn=macro_auc, metric_name="macro_auc")
result = harness.evaluate_oof(
    y_true=y_true,
    y_pred=candidate_oof,
    splits=splits,
    groups=patient_ids,
    baseline_pred=baseline_oof,
    n_bootstraps=1000,
)

if result.recommendation != "DEPLOY_RECOMMENDED":
    raise ValueError(f"Candidate rejected by OOF Validation Gate: {result.recommendation}")
```

### 4. Isolate Priority Error Buckets
Use `ErrorBucketAnalyzer` to discover the top failure modes:
```python
from cohezion.kaggle.error_bucket_analyzer import ErrorBucketAnalyzer

analyzer = ErrorBucketAnalyzer(class_names=labels, competition_name="rsna_knee")
report = analyzer.analyze_rsna_knee_errors(y_true, candidate_oof)
print("Top priority failure modes:", report.top_priority_buckets)
```

## VERSION
v0.1

## SEE ALSO
- `src/cohezion/skills/KAGGLE_GRANDMASTER_ASCENT_PRIME.md`
- `src/cohezion/skills/KAGGLE_ADVERSARIAL_VALIDATION_PRIME.md`
- `src/cohezion/skills/AUTOHARNESS_ZERO_LATENCY_INVARIANT_COMPILER_PRIME.md`
