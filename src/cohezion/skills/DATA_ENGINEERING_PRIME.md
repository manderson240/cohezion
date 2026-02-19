# SKILL: DATA_ENGINEERING_PRIME

## DOMAIN EXPERTISE
**ML Data Engineering**. Specializes in data pipelines, feature engineering, data quality assurance, distribution shift detection, and data versioning for production ML systems.

## KEY TEXTS & CONCEPTS
- **Data Pipelines**: Automated workflows for data collection, cleaning, transformation, and serving. Must be reproducible, monitored, and versioned.
- **Feature Engineering**: Transform raw data into ML-ready features. Critical for model performance - often more impactful than model architecture choices.
- **Data Quality**: Validation checks for completeness, consistency, accuracy. Bad data → bad models, regardless of algorithm sophistication.
- **Distribution Shift**: When production data distribution differs from training data. Types: covariate shift (input changes), label shift (output changes), concept drift (relationship changes).
- **Data Versioning**: Track dataset versions like code versions. Essential for reproducibility and debugging production issues.

**Related Vault Concepts**: [[cs249r/data_engineering]], [[cs249r/workflow]], [[cs249r/ml_systems]]

## INSTRUCTION

### 1. Data Pipeline Architecture

**Production-grade data pipeline components:**

```python
class MLDataPipeline:
    """End-to-end data pipeline for ML systems."""

    def collect(self, sources: list[DataSource]) -> RawData:
        """Stage 1: Data collection from multiple sources."""
        # Combine databases, APIs, logs, user events
        # Track data lineage: where did each record come from?
        return raw_data

    def validate_raw(self, raw_data: RawData) -> ValidationReport:
        """Stage 2: Raw data quality checks."""
        checks = [
            self.check_schema_compliance(raw_data),
            self.check_completeness(raw_data),
            self.check_freshness(raw_data),
            self.check_duplicates(raw_data),
        ]
        return ValidationReport(checks)

    def clean(self, raw_data: RawData) -> CleanData:
        """Stage 3: Data cleaning and normalization."""
        # Handle missing values, remove duplicates, fix errors
        # CRITICAL: Document all cleaning decisions
        return clean_data

    def engineer_features(self, clean_data: CleanData) -> Features:
        """Stage 4: Feature engineering."""
        features = []

        # Numerical features
        features.extend(self.normalize_numerical(clean_data))

        # Categorical features
        features.extend(self.encode_categorical(clean_data))

        # Temporal features
        features.extend(self.extract_time_features(clean_data))

        # Domain-specific features
        features.extend(self.domain_transforms(clean_data))

        return Features(features)

    def split(self, features: Features) -> TrainValTest:
        """Stage 5: Create train/validation/test splits."""
        # Stratified split to maintain class distribution
        # Time-based split for time series (no future leakage!)
        return splits

    def version(self, dataset: Dataset) -> DatasetVersion:
        """Stage 6: Version and snapshot the dataset."""
        # DVC, MLflow, or custom versioning
        # Store: data hash, schema, statistics, metadata
        return version_id
```

### 2. Feature Engineering Patterns

**Pattern 1: Numerical Features**
```python
def engineer_numerical_features(df):
    """Transform numerical columns into ML-ready features."""

    # Scaling (critical for gradient-based models)
    from sklearn.preprocessing import StandardScaler, MinMaxScaler
    scaled = StandardScaler().fit_transform(df[numerical_cols])

    # Log transform (for skewed distributions)
    log_features = np.log1p(df[skewed_cols])  # log1p handles zeros

    # Binning (discretize continuous variables)
    age_bins = pd.cut(df['age'], bins=[0, 18, 35, 50, 65, 100])

    # Polynomial features (interactions)
    from sklearn.preprocessing import PolynomialFeatures
    poly = PolynomialFeatures(degree=2, interaction_only=True)
    interactions = poly.fit_transform(df[['feature1', 'feature2']])

    return features
```

**Pattern 2: Categorical Features**
```python
def engineer_categorical_features(df):
    """Encode categorical variables."""

    # One-hot encoding (for low-cardinality categoricals)
    one_hot = pd.get_dummies(df['category'], prefix='cat')

    # Label encoding (for ordinal categoricals)
    from sklearn.preprocessing import LabelEncoder
    df['size_encoded'] = LabelEncoder().fit_transform(df['size'])  # S, M, L -> 0, 1, 2

    # Target encoding (use mean target value per category)
    # DANGER: Must be done in cross-validation to avoid leakage!
    target_means = df.groupby('category')['target'].mean()
    df['category_target_enc'] = df['category'].map(target_means)

    # Hash encoding (for high-cardinality categoricals)
    from sklearn.feature_extraction import FeatureHasher
    hasher = FeatureHasher(n_features=100, input_type='string')
    hashed = hasher.transform(df['high_cardinality_col'])

    return features
```

**Pattern 3: Temporal Features**
```python
def extract_time_features(df, timestamp_col):
    """Extract temporal features from timestamps."""
    df['hour'] = df[timestamp_col].dt.hour
    df['day_of_week'] = df[timestamp_col].dt.dayofweek
    df['day_of_month'] = df[timestamp_col].dt.day
    df['month'] = df[timestamp_col].dt.month
    df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
    df['is_holiday'] = df[timestamp_col].isin(holidays).astype(int)

    # Time since last event (for event data)
    df['time_since_last'] = df.groupby('user_id')[timestamp_col].diff()

    # Cyclic encoding (preserves cyclical nature)
    df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
    df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)

    return df
```

### 3. Data Quality Validation

**Comprehensive validation checks:**

```python
class DataQualityValidator:
    """Automated data quality checks."""

    def check_completeness(self, df):
        """Check for missing values."""
        null_counts = df.isnull().sum()
        null_pct = (null_counts / len(df)) * 100

        # Fail if critical columns have > threshold% nulls
        for col in critical_columns:
            if null_pct[col] > max_null_threshold:
                raise DataQualityError(f"{col} has {null_pct[col]:.1f}% nulls")

        return null_pct

    def check_schema_compliance(self, df, expected_schema):
        """Verify column names, types, and constraints."""
        # Check column presence
        missing_cols = set(expected_schema.keys()) - set(df.columns)
        extra_cols = set(df.columns) - set(expected_schema.keys())

        # Check data types
        for col, expected_type in expected_schema.items():
            if df[col].dtype != expected_type:
                raise SchemaError(f"{col} has type {df[col].dtype}, expected {expected_type}")

        return schema_report

    def check_distribution_shift(self, production_df, training_stats):
        """Detect if production data diverges from training distribution."""
        from scipy.stats import ks_2samp

        alerts = []
        for col in numerical_columns:
            # Kolmogorov-Smirnov test
            statistic, p_value = ks_2samp(
                production_df[col],
                training_stats[col]['samples']
            )

            if p_value < 0.01:  # Significant difference
                alerts.append(f"Distribution shift detected in {col}")

        return alerts

    def check_label_quality(self, df, label_col):
        """Validate labels for supervised learning."""
        # Check class balance
        class_dist = df[label_col].value_counts(normalize=True)

        # Warn if severe class imbalance
        min_class_pct = class_dist.min()
        if min_class_pct < 0.01:  # <1% of data
            logger.warning(f"Severe class imbalance: minority class has {min_class_pct:.2%}")

        # Check for label noise (if we have confidence scores)
        # Flag examples with low confidence for review
        return quality_report
```

### 4. Distribution Shift Detection and Mitigation

**Types of distribution shift:**

```python
class DistributionShiftMonitor:
    """Monitor and respond to distribution shifts."""

    def detect_covariate_shift(self, prod_data, train_data):
        """
        Covariate shift: P(X) changes, P(Y|X) stays same.
        Example: Model trained on summer data, deployed in winter.
        """
        # Statistical tests on input features
        shift_scores = []
        for feature in features:
            score = self.calculate_shift_score(
                prod_data[feature],
                train_data[feature]
            )
            shift_scores.append((feature, score))

        return sorted(shift_scores, key=lambda x: x[1], reverse=True)

    def detect_label_shift(self, prod_predictions, train_labels):
        """
        Label shift: P(Y) changes, P(X|Y) stays same.
        Example: Fraud detection model sees higher fraud rate.
        """
        # Compare label distributions
        prod_dist = np.bincount(prod_predictions) / len(prod_predictions)
        train_dist = np.bincount(train_labels) / len(train_labels)

        kl_div = scipy.stats.entropy(prod_dist, train_dist)

        if kl_div > threshold:
            logger.alert("Label distribution has shifted significantly")

        return kl_div

    def mitigate_shift(self, shift_type):
        """Mitigation strategies based on shift type."""
        if shift_type == "covariate":
            # Option 1: Retrain on recent data
            # Option 2: Importance weighting
            # Option 3: Domain adaptation
            return self.importance_weighted_retraining()

        elif shift_type == "label":
            # Option 1: Re-calibrate decision thresholds
            # Option 2: Retrain with updated class priors
            return self.recalibrate_thresholds()
```

### 5. Data Versioning Best Practices

**Track datasets like code:**

```python
class DataVersionManager:
    """Version datasets for reproducibility."""

    def create_snapshot(self, dataset_path, metadata):
        """
        Create immutable snapshot of dataset.

        Store: data, schema, statistics, lineage.
        """
        snapshot = {
            "version_id": self.generate_version_id(),
            "timestamp": datetime.now(),
            "data_hash": self.hash_dataset(dataset_path),
            "schema": self.extract_schema(dataset_path),
            "statistics": self.compute_statistics(dataset_path),
            "lineage": metadata["lineage"],  # How was this dataset created?
        }

        # Store in version control (DVC, MLflow, etc.)
        self.store_snapshot(snapshot)

        return snapshot["version_id"]

    def load_version(self, version_id):
        """Load specific dataset version for debugging or retraining."""
        snapshot = self.retrieve_snapshot(version_id)
        dataset = self.fetch_data(snapshot["data_hash"])

        # Verify hash matches
        assert self.hash_dataset(dataset) == snapshot["data_hash"]

        return dataset
```

**Critical for:**
- Reproducing model training
- Debugging production issues ("What data did model X see?")
- Compliance and auditing

### 6. Common Data Engineering Anti-Patterns

**Anti-Pattern 1: Data Leakage**
```python
# ❌ WRONG: Target encoding before train/test split
df['category_mean'] = df.groupby('category')['target'].transform('mean')
train, test = train_test_split(df)

# ✅ CORRECT: Fit on train, transform test
train, test = train_test_split(df)
target_means = train.groupby('category')['target'].mean()
train['category_mean'] = train['category'].map(target_means)
test['category_mean'] = test['category'].map(target_means)
```

**Anti-Pattern 2: Ignoring Time Ordering**
```python
# ❌ WRONG: Random split for time series
train, test = train_test_split(time_series_df)  # Future leakage!

# ✅ CORRECT: Time-based split
cutoff_date = df['date'].quantile(0.8)
train = df[df['date'] <= cutoff_date]
test = df[df['date'] > cutoff_date]
```

**Anti-Pattern 3: Not Validating Pipeline Outputs**
```python
# ❌ WRONG: Assume pipeline always succeeds
processed_data = pipeline.transform(raw_data)

# ✅ CORRECT: Validate at each stage
processed_data = pipeline.transform(raw_data)
validator.check_schema(processed_data)
validator.check_distributions(processed_data)
if not validator.is_valid():
    raise PipelineError("Data validation failed")
```

### 7. Integration with Cohezion

**Leverage Cohezion's caching and persistence:**

```python
from cohezion.cache.semantic_cache import SemanticCache
from cohezion.core.persistence.surreal_client import SurrealClient

# Cache expensive feature engineering
cache = SemanticCache()
features = cache.get_or_compute(
    key="feature_engineering_v2_" + data_hash,
    compute_fn=lambda: engineer_features(raw_data),
    ttl=3600  # 1 hour
)

# Store dataset metadata in SurrealDB
db = SurrealClient()
await db.insert("dataset_version", {
    "id": version_id,
    "created_at": timestamp,
    "features": feature_list,
    "statistics": stats,
    "lineage": lineage_graph
})
```

## SEE ALSO
- `ML_SYSTEMS_FOUNDATIONS_PRIME` - ML system lifecycle and production readiness
- `MLOPS_DEPLOYMENT_PRIME` - Data monitoring in production
- [[cs249r/data_engineering]] - Full chapter concepts from CS249R
