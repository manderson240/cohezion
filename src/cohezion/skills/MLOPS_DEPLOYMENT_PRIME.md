# SKILL: MLOPS_DEPLOYMENT_PRIME

## DOMAIN EXPERTISE
**MLOps and Production ML Deployment**. Specializes in model serving, A/B testing, monitoring for drift, CI/CD for ML, on-device learning, privacy-preserving inference, and operational best practices for production ML systems.

## KEY TEXTS & CONCEPTS
- **Model Serving**: Deploying trained models to handle inference requests. Patterns: online (real-time), batch (scheduled), streaming (event-driven). Infrastructure: REST APIs, gRPC, model servers (TF Serving, Triton).
- **A/B Testing for ML**: Compare model versions in production with statistical rigor. Shadow mode (log predictions without serving), canary deployment (gradual rollout), multi-armed bandits (adaptive allocation).
- **Drift Monitoring**: Detect when production data or model behavior changes. Types: data drift (input distribution), concept drift (relationship changes), prediction drift (output distribution).
- **On-Device Learning**: Training or fine-tuning models directly on edge devices. Techniques: federated learning, transfer learning on-device, personalization. Constraints: limited memory, no GPU, privacy requirements.
- **CI/CD for ML**: Continuous integration and deployment adapted for ML. Includes: data validation, model training, model evaluation, model registry, automated deployment with rollback.

**Related Vault Concepts**: [[cs249r/ops]], [[cs249r/ondevice_learning]], [[cs249r/privacy_security]]

## INSTRUCTION

### 1. Deployment Pattern Selection

**Choose based on latency, throughput, and freshness requirements:**

```
Inference Requirement?
├─ Real-time (< 100ms)
│   ├─ High throughput → Model server (Triton, TF Serving) with batching
│   ├─ Low throughput → REST API with single model instance
│   └─ Ultra-low latency → Edge deployment or in-process inference
│
├─ Batch (minutes to hours OK)
│   ├─ Scheduled → Cron job with batch prediction pipeline
│   ├─ On-demand → Serverless (Cloud Functions/Lambda)
│   └─ Large scale → Spark/distributed batch processing
│
└─ Streaming (event-driven)
    ├─ Message queue → Model behind Kafka/Pub-Sub consumer
    └─ Real-time features → Feature store + online inference
```

### 2. Model Serving Architecture

**Production serving patterns:**

```python
class ModelServer:
    """Production model serving with versioning and fallback."""

    def __init__(self):
        self.models = {}         # version -> model
        self.active_version = None
        self.fallback_version = None

    def load_model(self, version, model_path):
        """Load model version with validation."""
        model = load_and_validate(model_path)
        # Validate: correct input/output shapes, reasonable predictions
        self.models[version] = model

    def predict(self, input_data):
        """Serve prediction with fallback."""
        try:
            model = self.models[self.active_version]
            prediction = model.predict(input_data)

            # Validate prediction (sanity checks)
            if not self.is_valid_prediction(prediction):
                raise PredictionError("Invalid prediction output")

            return prediction

        except Exception as e:
            logger.error(f"Primary model failed: {e}")
            # Fallback to previous version
            if self.fallback_version:
                return self.models[self.fallback_version].predict(input_data)
            raise

    def is_valid_prediction(self, prediction):
        """Sanity check predictions before serving."""
        # Check for NaN, extreme values, wrong shape
        if np.isnan(prediction).any():
            return False
        if prediction.max() > self.max_expected:
            return False
        return True
```

**Request batching for throughput:**
```python
class BatchPredictor:
    """Accumulate requests and predict in batches for GPU efficiency."""

    def __init__(self, model, max_batch_size=32, max_wait_ms=10):
        self.model = model
        self.max_batch_size = max_batch_size
        self.max_wait_ms = max_wait_ms
        self.queue = []

    async def predict(self, input_data):
        """Queue request and wait for batch prediction."""
        future = asyncio.Future()
        self.queue.append((input_data, future))

        if len(self.queue) >= self.max_batch_size:
            await self._process_batch()

        return await future

    async def _process_batch(self):
        """Process accumulated requests as a single batch."""
        batch = self.queue[:self.max_batch_size]
        self.queue = self.queue[self.max_batch_size:]

        inputs = np.stack([item[0] for item in batch])
        predictions = self.model.predict(inputs)

        for (_, future), pred in zip(batch, predictions):
            future.set_result(pred)
```

### 3. A/B Testing and Canary Deployment

**Statistically rigorous model comparison:**

```python
class ABTestManager:
    """Manage A/B tests between model versions."""

    def __init__(self, control_model, treatment_model, traffic_split=0.1):
        self.control = control_model
        self.treatment = treatment_model
        self.traffic_split = traffic_split  # 10% to treatment
        self.metrics = {"control": [], "treatment": []}

    def route_request(self, request):
        """Route to control or treatment based on traffic split."""
        import hashlib
        # Deterministic routing based on request ID (reproducible)
        hash_val = int(hashlib.md5(request.id.encode()).hexdigest(), 16)
        if (hash_val % 100) < (self.traffic_split * 100):
            return self.treatment.predict(request), "treatment"
        return self.control.predict(request), "control"

    def evaluate(self):
        """Statistical test for significant difference."""
        from scipy.stats import mannwhitneyu

        stat, p_value = mannwhitneyu(
            self.metrics["control"],
            self.metrics["treatment"],
            alternative="two-sided"
        )

        return {
            "p_value": p_value,
            "significant": p_value < 0.05,
            "control_mean": np.mean(self.metrics["control"]),
            "treatment_mean": np.mean(self.metrics["treatment"]),
            "recommendation": "deploy" if p_value < 0.05 and
                np.mean(self.metrics["treatment"]) > np.mean(self.metrics["control"])
                else "keep_control"
        }
```

**Canary deployment schedule:**
```
Day 1: 1% traffic → monitor for errors, latency regression
Day 2: 5% traffic → compare accuracy metrics
Day 3: 25% traffic → statistical significance check
Day 4: 50% traffic → final validation
Day 5: 100% traffic → full rollout (keep rollback ready)
```

### 4. Drift Monitoring

**Comprehensive monitoring system:**

```python
class DriftMonitor:
    """Monitor production model for drift and degradation."""

    def __init__(self, reference_stats):
        self.reference = reference_stats

    def check_data_drift(self, production_batch):
        """Detect if input distribution has shifted."""
        from scipy.stats import ks_2samp

        alerts = []
        for feature in self.reference.features:
            stat, p_val = ks_2samp(
                production_batch[feature],
                self.reference.distributions[feature]
            )
            if p_val < 0.01:
                alerts.append({
                    "feature": feature,
                    "type": "data_drift",
                    "severity": "high" if p_val < 0.001 else "medium",
                    "p_value": p_val
                })
        return alerts

    def check_prediction_drift(self, recent_predictions):
        """Detect if model output distribution has changed."""
        # Population Stability Index (PSI)
        expected = self.reference.prediction_distribution
        actual = np.histogram(recent_predictions, bins=self.reference.bins)[0]
        actual = actual / actual.sum()

        psi = np.sum((actual - expected) * np.log(actual / expected + 1e-10))

        if psi > 0.25:
            return {"type": "prediction_drift", "severity": "critical", "psi": psi}
        elif psi > 0.10:
            return {"type": "prediction_drift", "severity": "warning", "psi": psi}
        return None

    def check_performance_decay(self, labeled_sample):
        """Check if accuracy has degraded (requires ground truth labels)."""
        current_accuracy = self.evaluate(labeled_sample)
        baseline_accuracy = self.reference.accuracy

        if current_accuracy < baseline_accuracy * 0.95:  # >5% drop
            return {
                "type": "performance_decay",
                "severity": "critical",
                "current": current_accuracy,
                "baseline": baseline_accuracy
            }
        return None
```

**Monitoring frequency:**

| Check | Frequency | Action on Alert |
|-------|-----------|-----------------|
| Error rate, latency | Real-time | Page on-call if >2x baseline |
| Input distribution | Hourly | Investigate; may need retraining |
| Prediction distribution | Daily | Compare with A/B baseline |
| Model performance | Weekly | Schedule retraining if declining |
| Full drift analysis | Monthly | Comprehensive model review |

### 5. CI/CD for ML

**ML pipeline stages:**

```
Data Validation
  → Training
    → Model Evaluation
      → Model Registry
        → Staging Deployment
          → Production Deployment

# Each stage has gates:
# Data: schema checks, distribution checks, freshness
# Training: convergence, no NaN losses, reasonable metrics
# Evaluation: beats baseline, no fairness regressions
# Registry: model card, lineage, artifact hash
# Staging: integration tests, load tests
# Production: canary deployment, rollback plan
```

**Automated retraining trigger:**
```python
def should_retrain(drift_alerts, performance_metrics, model_age_days):
    """Decide if model needs retraining."""
    if any(a["severity"] == "critical" for a in drift_alerts):
        return True, "Critical drift detected"
    if performance_metrics.accuracy < performance_metrics.baseline * 0.95:
        return True, "Performance below threshold"
    if model_age_days > 30:
        return True, "Scheduled retraining (>30 days)"
    return False, None
```

### 6. On-Device Learning

**Federated learning pattern:**
```python
class FederatedLearningServer:
    """Coordinate training across edge devices without sharing raw data."""

    def __init__(self, global_model):
        self.global_model = global_model

    def federated_round(self, participating_devices):
        """One round of federated averaging."""
        # 1. Send global model to selected devices
        local_updates = []
        for device in participating_devices:
            # Device trains locally on its private data
            update = device.train_local(self.global_model, epochs=5)
            local_updates.append(update)

        # 2. Aggregate updates (FedAvg)
        # Weight by number of samples per device
        total_samples = sum(u.num_samples for u in local_updates)
        new_weights = {}
        for key in self.global_model.weights:
            new_weights[key] = sum(
                u.weights[key] * (u.num_samples / total_samples)
                for u in local_updates
            )

        # 3. Update global model
        self.global_model.set_weights(new_weights)

        # Privacy preserved: raw data never leaves devices
```

**On-device constraints:**
- Memory: typically < 4GB RAM available
- Compute: no GPU, limited CPU
- Power: battery-powered devices
- Network: intermittent connectivity

### 7. Integration with Cohezion

**Leverage Cohezion's existing infrastructure:**

```python
from cohezion.cache.semantic_cache import SemanticCache
from cohezion.compound.journey_tracker import JourneyTracker

# Cache inference results for repeated queries
cache = SemanticCache()
cached_result = cache.get(query_embedding)
if cached_result:
    return cached_result  # 95%+ hit rate reduces compute

# Track model serving in 12D universe
tracker = JourneyTracker()
tracker.record_transition(
    before_state={"model_version": "v2.1", "latency_p99": 45},
    action="serve_prediction",
    after_state={"predictions_served": count + 1},
    coherence_after=0.91
)
```

### 8. Common Anti-Patterns

**Anti-Pattern 1: No rollback plan**
- Always keep the previous model version loaded and ready
- Test rollback procedure before deployment

**Anti-Pattern 2: Monitoring only errors**
- Error rate catches crashes, but not silent degradation
- Must monitor drift, prediction distribution, and performance

**Anti-Pattern 3: Manual deployment**
- Use CI/CD pipelines for reproducible, auditable deployments
- Manual steps = human error + no audit trail

**Anti-Pattern 4: Ignoring data quality in production**
- Production data is messier than training data
- Validate inputs before prediction (schema, ranges, nulls)

## SEE ALSO
- `ML_SYSTEMS_FOUNDATIONS_PRIME` - ML system lifecycle and production readiness
- `DATA_ENGINEERING_PRIME` - Data pipelines and quality monitoring
- `EFFICIENT_AI_PRIME` - Model compression for edge deployment
- `EDGE_INTELLIGENCE_PRIME` - Federated learning and distributed inference
- [[cs249r/ops]] - Full chapter on MLOps practices
