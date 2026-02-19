# SKILL: RESPONSIBLE_AI_PRIME

## DOMAIN EXPERTISE
**Responsible and Trustworthy AI Systems**. Specializes in fairness metrics, bias detection and mitigation, explainability (SHAP, LIME), environmental impact assessment, carbon-aware scheduling, robustness testing, and safety alignment for production ML systems.

## KEY TEXTS & CONCEPTS
- **Algorithmic Fairness**: Ensuring ML systems don't discriminate against protected groups. Key metrics: demographic parity, equalized odds, equal opportunity, calibration. Trade-offs exist between different fairness definitions — they cannot all be satisfied simultaneously (impossibility theorem).
- **Explainability (XAI)**: Making model decisions interpretable to humans. Model-agnostic methods: SHAP (game theory-based attribution), LIME (local linear approximation). Model-specific: Grad-CAM (CNN attention maps), attention weights (transformers).
- **Sustainable AI / Green AI**: Measuring and reducing the environmental impact of ML training and inference. Metrics: carbon footprint (CO2e), energy consumption (kWh), compute efficiency (accuracy per FLOP). Carbon-aware scheduling shifts workloads to low-carbon periods.
- **Robustness**: Model reliability under adversarial inputs, distribution shift, and noisy data. Adversarial examples expose vulnerabilities. Certification methods provide formal guarantees.
- **AI Safety Alignment**: Ensuring AI systems act in accordance with human values and intentions. Connects to Cohezion's CONSTITUTION.md principles: honesty, safety, helpfulness.

**Related Vault Concepts**: [[cs249r/responsible_ai]], [[cs249r/sustainable_ai]], [[cs249r/robust_ai]], [[cs249r/ai_for_good]], [[cs249r/privacy_security]]

## INSTRUCTION

### 1. Fairness Assessment Framework

**Step-by-step fairness evaluation:**

```python
class FairnessAuditor:
    """Audit ML model for fairness across protected attributes."""

    def __init__(self, protected_attributes):
        self.protected_attrs = protected_attributes

    def demographic_parity(self, predictions, groups):
        """
        Equal positive prediction rates across groups.
        P(Y_hat=1 | A=a) = P(Y_hat=1 | A=b) for all groups a, b.
        """
        rates = {}
        for group in set(groups):
            mask = groups == group
            rates[group] = predictions[mask].mean()

        max_diff = max(rates.values()) - min(rates.values())
        return {
            "metric": "demographic_parity",
            "rates": rates,
            "max_disparity": max_diff,
            "passes": max_diff < 0.1  # 10% threshold (common standard)
        }

    def equalized_odds(self, predictions, labels, groups):
        """
        Equal TPR and FPR across groups.
        More stringent than demographic parity.
        """
        results = {}
        for group in set(groups):
            mask = groups == group
            tp = ((predictions[mask] == 1) & (labels[mask] == 1)).sum()
            fp = ((predictions[mask] == 1) & (labels[mask] == 0)).sum()
            fn = ((predictions[mask] == 0) & (labels[mask] == 1)).sum()
            tn = ((predictions[mask] == 0) & (labels[mask] == 0)).sum()

            results[group] = {
                "tpr": tp / (tp + fn) if (tp + fn) > 0 else 0,
                "fpr": fp / (fp + tn) if (fp + tn) > 0 else 0,
            }
        return results

    def calibration(self, predictions, probabilities, labels, groups):
        """
        When model says 80% confident, is it right 80% of the time?
        Check calibration per group.
        """
        # Bin predictions by confidence
        bins = np.linspace(0, 1, 11)
        calibration_per_group = {}

        for group in set(groups):
            mask = groups == group
            group_probs = probabilities[mask]
            group_labels = labels[mask]

            bin_accs = []
            for i in range(len(bins) - 1):
                bin_mask = (group_probs >= bins[i]) & (group_probs < bins[i + 1])
                if bin_mask.sum() > 0:
                    bin_accs.append(group_labels[bin_mask].mean())

            calibration_per_group[group] = bin_accs

        return calibration_per_group
```

**Fairness metric selection guide:**

| Metric | Use When | Trade-off |
|--------|----------|-----------|
| Demographic Parity | Equal outcomes desired (hiring) | May sacrifice accuracy |
| Equalized Odds | Equal accuracy across groups | Harder to achieve |
| Equal Opportunity | Focus on positive class (loans) | Allows FPR differences |
| Calibration | Probabilistic predictions matter | Doesn't guarantee equal rates |

### 2. Bias Detection and Mitigation

**Three intervention points:**

```python
# 1. PRE-PROCESSING: Fix data before training
def reweight_training_data(data, labels, groups):
    """Assign weights to equalize representation."""
    weights = np.ones(len(data))
    for group in set(groups):
        mask = groups == group
        for label in set(labels):
            label_mask = labels == label
            group_label_mask = mask & label_mask
            # Weight inversely proportional to group-label frequency
            expected = len(data) / (len(set(groups)) * len(set(labels)))
            actual = group_label_mask.sum()
            if actual > 0:
                weights[group_label_mask] = expected / actual
    return weights

# 2. IN-PROCESSING: Constrain model during training
def fairness_regularized_loss(predictions, labels, groups, lambda_fair=0.1):
    """Add fairness penalty to training loss."""
    task_loss = cross_entropy(predictions, labels)
    fairness_penalty = demographic_parity_difference(predictions, groups)
    return task_loss + lambda_fair * fairness_penalty

# 3. POST-PROCESSING: Adjust predictions after training
def equalize_odds_postprocess(predictions, groups, thresholds):
    """Apply group-specific thresholds to equalize TPR/FPR."""
    adjusted = predictions.copy()
    for group in set(groups):
        mask = groups == group
        adjusted[mask] = (predictions[mask] > thresholds[group]).astype(int)
    return adjusted
```

### 3. Explainability Methods

**SHAP (SHapley Additive exPlanations):**
```python
def explain_prediction_shap(model, instance, background_data):
    """
    Attribute prediction to each feature using Shapley values.

    Shapley value = average marginal contribution of feature
    across all possible feature coalitions.
    """
    # For each feature:
    #   For each subset of other features:
    #     Measure change in prediction when this feature is added
    #   Average across all subsets (weighted by coalition size)

    # Practical: Use sampling-based approximation (exact is O(2^n))
    n_features = instance.shape[0]
    shap_values = np.zeros(n_features)

    for _ in range(n_samples):
        # Random permutation of features
        perm = np.random.permutation(n_features)
        # Add features one at a time, measure marginal contribution
        for i, feature_idx in enumerate(perm):
            x_with = background_sample.copy()
            x_with[perm[:i + 1]] = instance[perm[:i + 1]]
            x_without = background_sample.copy()
            x_without[perm[:i]] = instance[perm[:i]]

            shap_values[feature_idx] += model(x_with) - model(x_without)

    return shap_values / n_samples
```

**LIME (Local Interpretable Model-agnostic Explanations):**
```python
def explain_prediction_lime(model, instance, n_samples=1000):
    """
    Fit a local linear model around the prediction point.

    1. Perturb the instance randomly
    2. Get model predictions for perturbations
    3. Weight by proximity to original instance
    4. Fit weighted linear model → coefficients = feature importance
    """
    perturbations = generate_perturbations(instance, n_samples)
    predictions = model.predict(perturbations)
    weights = proximity_weights(instance, perturbations)

    # Weighted linear regression
    linear_model = LinearRegression()
    linear_model.fit(perturbations, predictions, sample_weight=weights)

    return {
        "feature_importance": linear_model.coef_,
        "local_accuracy": linear_model.score(perturbations, predictions, sample_weight=weights)
    }
```

### 4. Environmental Impact Assessment

**Carbon footprint estimation:**
```python
class CarbonTracker:
    """Track carbon emissions from ML training and inference."""

    # Average carbon intensity by region (gCO2/kWh)
    CARBON_INTENSITY = {
        "us_west": 190,      # California (mix of solar/wind/gas)
        "us_east": 380,      # Virginia (more fossil fuels)
        "europe_north": 30,  # Norway/Sweden (hydroelectric)
        "europe_west": 250,  # Germany/France (nuclear + renewables)
        "asia_east": 550,    # China (coal-heavy)
    }

    def estimate_training_carbon(self, gpu_hours, gpu_type, region):
        """
        Estimate CO2 emissions from training.

        CO2 = Energy × Carbon Intensity
        Energy = GPU Power × Hours × PUE
        """
        gpu_power_watts = {"A100": 400, "V100": 300, "T4": 70, "CPU": 150}
        pue = 1.1  # Typical datacenter Power Usage Effectiveness

        energy_kwh = (gpu_power_watts[gpu_type] * gpu_hours * pue) / 1000
        carbon_g = energy_kwh * self.CARBON_INTENSITY[region]

        return {
            "energy_kwh": energy_kwh,
            "carbon_g_co2": carbon_g,
            "equivalent_km_driven": carbon_g / 120,  # Average car: 120g/km
        }

    def carbon_aware_schedule(self, job, available_regions):
        """Schedule training job in lowest-carbon region."""
        costs = []
        for region in available_regions:
            carbon = self.estimate_training_carbon(
                job.estimated_gpu_hours,
                job.gpu_type,
                region
            )
            costs.append((region, carbon["carbon_g_co2"]))

        return min(costs, key=lambda x: x[1])  # Lowest carbon region
```

**Green AI practices:**
- Report accuracy **per FLOP** (not just accuracy)
- Use smaller models first; scale up only if needed
- Transfer learning and fine-tuning over training from scratch
- Early stopping to avoid wasted compute
- Prefer efficient architectures (MobileNet over ResNet for equivalent tasks)

### 5. Robustness Testing

**Adversarial robustness evaluation:**
```python
def fgsm_attack(model, input_data, label, epsilon=0.01):
    """
    Fast Gradient Sign Method: minimal perturbation to flip prediction.

    Perturbation = epsilon * sign(gradient of loss w.r.t. input)
    """
    input_data.requires_grad = True
    loss = cross_entropy(model(input_data), label)
    loss.backward()

    # Perturb in direction that increases loss
    perturbation = epsilon * np.sign(input_data.grad)
    adversarial = input_data + perturbation

    # Clip to valid range
    adversarial = np.clip(adversarial, 0, 1)

    return adversarial

def robustness_report(model, test_data, test_labels, epsilons=[0.01, 0.05, 0.1]):
    """Generate robustness report across perturbation strengths."""
    results = {"clean_accuracy": accuracy(model, test_data, test_labels)}

    for eps in epsilons:
        adversarial_data = [fgsm_attack(model, x, y, eps) for x, y in zip(test_data, test_labels)]
        results[f"accuracy_eps_{eps}"] = accuracy(model, adversarial_data, test_labels)

    return results
```

### 6. Safety Alignment Principles

**Connection to Cohezion's CONSTITUTION.md:**

```python
# Cohezion's Constitution mandates:
# 1. Honesty - Report true capabilities and limitations
# 2. Safety - Never generate harmful outputs
# 3. Helpfulness - Maximize user value within constraints

class SafetyGuard:
    """Pre-deployment safety checks aligned with CONSTITUTION.md."""

    def check_output_safety(self, model_output):
        """Verify model output meets safety constraints."""
        checks = [
            self.no_harmful_content(model_output),
            self.no_private_data_leakage(model_output),
            self.confidence_calibrated(model_output),
            self.uncertainty_communicated(model_output),
        ]
        return all(checks)

    def confidence_calibrated(self, output):
        """Honesty principle: model confidence matches actual accuracy."""
        # Overconfident models violate honesty
        # Underconfident models reduce helpfulness
        return abs(output.confidence - output.empirical_accuracy) < 0.1

    def uncertainty_communicated(self, output):
        """Honesty principle: communicate when model is uncertain."""
        if output.confidence < 0.7:
            return hasattr(output, 'uncertainty_message')
        return True
```

### 7. Responsible AI Checklist

**Before deploying ANY model, verify:**

- [ ] **Fairness**: Tested on all protected groups with documented metrics
- [ ] **Explainability**: Key predictions can be explained to stakeholders
- [ ] **Robustness**: Tested against adversarial inputs at relevant epsilon levels
- [ ] **Privacy**: No personal data leakage, differential privacy if needed
- [ ] **Sustainability**: Carbon footprint estimated and minimized where possible
- [ ] **Safety**: Output safety checks pass, harmful outputs impossible
- [ ] **Documentation**: Model card with intended use, limitations, and failure modes
- [ ] **Monitoring**: Fairness metrics tracked in production, not just at launch

## SEE ALSO
- `ML_SYSTEMS_FOUNDATIONS_PRIME` - ML system lifecycle and production readiness
- `MLOPS_DEPLOYMENT_PRIME` - Production monitoring and drift detection
- `EDGE_INTELLIGENCE_PRIME` - Privacy-preserving on-device learning
- `.agent/CONSTITUTION.md` - Cohezion's core safety and honesty principles
- [[cs249r/responsible_ai]] - Full chapter on responsible AI practices
- [[cs249r/sustainable_ai]] - Environmental impact of AI systems
