---
title: "Phase 4B & 5 Detailed Design Specification"
date: 2026-02-16
status: approved
type: design-specification
phase: 4B-5
estimated_loc: 900
estimated_tests: 50
target_coverage: 85%
tags: [phase-4b, phase-5, api, dashboard, bayesian, ml, design-spec]
---

# Phase 4B & 5 Detailed Design Specification

## Overview

**Phases 4B & 5** deliver the REST API, interactive dashboard, and advanced statistical/ML scoring for Cohezion's decision intelligence platform.

- **Phase 4B** (Conditional, Week 3): Dashboard & REST API foundations
- **Phase 5** (Weeks 3-4): Bayesian scoring + ML confidence calibration
- **Combined Duration**: 2-3 weeks
- **Combined Deliverables**: 900+ LOC, 50+ tests, 85%+ coverage
- **Teams**: integration-engineer, data-graph-specialist, observability-specialist

---

## Architecture Overview

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                             │
├──────────────────────┬──────────────────────────────────────┤
│  React Dashboard     │  REST API Clients                    │
│  (Zustand state)     │  (Python SDK, TypeScript SDK)        │
└──────────────────────┼──────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────────────┐
│                   FastAPI SERVER                            │
├───────────────┬───────────────┬───────────────┬─────────────┤
│  Auth Layer   │  REST Routes  │  WebSocket    │  Middleware │
│  (JWT/API)    │  (20+ endpoints)│  (Real-time)│  (CORS/rate)│
└───────────────┼───────────────┼───────────────┴─────────────┘
                │
┌───────────────┴─────────────────────────────────────────────┐
│                   LOGIC LAYER                               │
├───────────────┬──────────────┬──────────────┬───────────────┤
│ Confidence    │ Bayesian     │ ML Scoring   │ Dashboard     │
│ Scoring       │ Inference    │ (XGBoost)    │ Queries       │
│ (Phase 4A)    │ (Phase 5)    │ (Phase 5)    │ (Phase 4B)    │
└───────────────┴──────────────┴──────────────┴───────────────┘
                │
┌───────────────┴─────────────────────────────────────────────┐
│                   DATA LAYER                                │
├───────────────┬──────────────┬──────────────┬───────────────┤
│ SurrealDB     │ Cache        │ Time-series  │ Feature       │
│ (decisions,   │ (Redis)      │ (TSDB)       │ Store         │
│ scoring)      │              │              │               │
└───────────────┴──────────────┴──────────────┴───────────────┘
```

### Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Frontend** | React 18 + TypeScript | Interactive UI |
| **State Mgmt** | Zustand | Client-side state |
| **API Server** | FastAPI 0.104+ | REST API endpoints |
| **Auth** | JWT + API Keys | Secure access |
| **WebSocket** | Starlette WS | Real-time updates |
| **DB** | SurrealDB | Primary data store |
| **Scoring** | PyMC 5.0+ | Bayesian inference |
| **ML** | XGBoost 2.0+ | Confidence calibration |
| **Cache** | Redis (optional) | Performance optimization |
| **Feature Store** | Feast (optional) | ML feature management |

---

## Phase 4B: REST API & Dashboard (CONDITIONAL)

### Trigger Condition
**Phase 4B executes ONLY if Phase 4A completes by 2026-02-25** (day 10 of 14 target)

### 4B.1: REST API Architecture

#### API Design Principles
- **RESTful**: Resource-oriented endpoints, standard HTTP methods
- **Stateless**: No server-side session state
- **Versioned**: `/api/v1/` prefix for backward compatibility
- **Paginated**: Large result sets use cursor pagination
- **Rate-limited**: 1000 req/min per API key (adjustable)
- **Documented**: Full OpenAPI 3.0 spec, Swagger UI

#### Authentication & Authorization

**JWT-based Authentication:**
```python
# POST /api/v1/auth/login
{
  "email": "user@example.com",
  "password": "secure_password"
}

Response:
{
  "access_token": "eyJhbGc...",
  "refresh_token": "eyJhbGc...",
  "expires_in": 3600,
  "token_type": "bearer"
}
```

**API Key Authentication (for SDK clients):**
```
Headers: Authorization: Bearer {api_key}
```

**Permissions Model:**
- `read:decisions` - Query decisions
- `write:decisions` - Create/update decisions
- `read:analytics` - View dashboards and reports
- `admin:system` - System configuration
- `write:scores` - Update confidence scores (admin only)

#### Core REST Endpoints (20+ total)

**Decision Management** (8 endpoints):
```
GET    /api/v1/decisions               # List all decisions (paginated)
POST   /api/v1/decisions               # Create decision
GET    /api/v1/decisions/{id}          # Get decision details
PUT    /api/v1/decisions/{id}          # Update decision
DELETE /api/v1/decisions/{id}          # Archive decision
GET    /api/v1/decisions/{id}/history  # Decision audit trail
GET    /api/v1/decisions/{id}/impact   # Cascade impact analysis
GET    /api/v1/decisions/{id}/score    # Current confidence score
```

**Scoring & Confidence** (5 endpoints):
```
GET    /api/v1/scores/{decision_id}    # Get current score
POST   /api/v1/scores/{decision_id}    # Recalculate score
GET    /api/v1/scores/batch            # Batch score lookup
GET    /api/v1/confidence/intervals     # Uncertainty quantification
GET    /api/v1/confidence/calibration   # Model calibration metrics
```

**Dashboard & Analytics** (5 endpoints):
```
GET    /api/v1/dashboard/summary       # KPI dashboard data
GET    /api/v1/dashboard/decisions     # Decision trend chart
GET    /api/v1/dashboard/scores        # Score distribution
GET    /api/v1/analytics/report        # Comprehensive report
POST   /api/v1/dashboard/presets       # Save dashboard view
```

**System & Health** (3 endpoints):
```
GET    /api/v1/health                  # Service health check
GET    /api/v1/metrics                 # Performance metrics
GET    /api/v1/system/status           # System status overview
```

#### Request/Response Models (Pydantic)

**Decision Model:**
```python
class DecisionBase(BaseModel):
    title: str
    description: str
    context: Optional[str] = None
    tags: List[str] = []
    priority: Literal["low", "medium", "high"] = "medium"

class DecisionCreate(DecisionBase):
    factor_weights: Dict[str, float]  # From Phase 4A scoring
    required_confidence: float = 0.75  # Minimum acceptable confidence

class Decision(DecisionBase):
    id: str
    created_at: datetime
    updated_at: datetime
    status: Literal["pending", "active", "resolved", "archived"]
    created_by: str
    current_confidence: float
    confidence_interval: Tuple[float, float]
    dependent_decisions: List[str]  # IDs of dependent decisions

class DecisionResponse(Decision):
    metadata: Dict[str, Any]
    recent_updates: List[Dict[str, Any]]
```

**Score Model:**
```python
class ConfidenceScore(BaseModel):
    decision_id: str
    base_confidence: float  # Phase 4A confidence
    bayesian_adjusted: float  # Phase 5 Bayesian adjustment
    ml_adjustment: float  # Phase 5 ML calibration
    final_confidence: float  # Weighted combination
    uncertainty: float  # Standard deviation
    lower_bound: float  # 95% CI lower
    upper_bound: float  # 95% CI upper
    factors: Dict[str, float]  # Component contributions
    calculated_at: datetime
    calculation_method: str  # "base" | "bayesian" | "ml"

class ScoreRecalculation(BaseModel):
    decision_id: str
    force_refresh: bool = False
    include_history: bool = False
    confidence_model: Literal["base", "bayesian", "ml"] = "ml"
```

**Dashboard Model:**
```python
class DashboardSummary(BaseModel):
    total_decisions: int
    active_decisions: int
    high_confidence_pct: float
    avg_confidence: float
    median_confidence: float
    decisions_with_updates_last_7d: int
    critical_decisions_at_risk: List[str]
    recommendation_acceptance_rate: float

class DashboardPreset(BaseModel):
    name: str
    description: Optional[str]
    filters: Dict[str, Any]
    metrics: List[str]
    layout: Dict[str, Any]
    created_at: datetime
    owner: str
    is_public: bool = False
```

#### Error Handling

**Standardized Error Response:**
```python
class ErrorResponse(BaseModel):
    status_code: int
    error_type: str  # "validation_error", "not_found", "unauthorized", etc.
    message: str
    details: Optional[Dict[str, Any]] = None
    request_id: str
    timestamp: datetime

# Example 400 Validation Error
{
  "status_code": 400,
  "error_type": "validation_error",
  "message": "Invalid confidence threshold",
  "details": {
    "field": "required_confidence",
    "value": 1.5,
    "constraint": "must be between 0.0 and 1.0"
  },
  "request_id": "req_abc123def456",
  "timestamp": "2026-02-16T10:30:00Z"
}
```

**HTTP Status Codes:**
- `200 OK` - Successful GET/PUT/DELETE
- `201 Created` - Successful POST
- `400 Bad Request` - Validation error
- `401 Unauthorized` - Missing/invalid token
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource doesn't exist
- `409 Conflict` - Resource state conflict
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

### 4B.2: FastAPI Implementation Structure

**File Structure:**
```
src/api/
├── __init__.py
├── main.py                 # FastAPI app initialization
├── config.py              # Configuration (env vars, settings)
├── dependencies.py        # Dependency injection (auth, db)
├── middleware.py          # CORS, rate limiting, logging
├── exceptions.py          # Custom exceptions
├── routers/
│   ├── __init__.py
│   ├── auth.py            # Authentication endpoints
│   ├── decisions.py       # Decision CRUD endpoints
│   ├── scoring.py         # Confidence scoring endpoints
│   ├── dashboard.py       # Dashboard data endpoints
│   └── health.py          # Health check endpoints
├── schemas/
│   ├── __init__.py
│   ├── decision.py        # Decision models
│   ├── score.py           # Score models
│   └── dashboard.py       # Dashboard models
├── services/
│   ├── __init__.py
│   ├── auth_service.py    # JWT/API key validation
│   ├── decision_service.py # Decision logic
│   ├── score_service.py   # Scoring service (calls Phase 4A)
│   └── dashboard_service.py # Dashboard data aggregation
└── utils/
    ├── __init__.py
    └── helpers.py         # Utility functions
```

**Core API Setup (main.py):**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi_limiter import FastAPILimiter
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await FastAPILimiter.init(redis_url="redis://localhost:6379")
    yield
    # Shutdown
    await FastAPILimiter.close()

app = FastAPI(
    title="Cohezion Decision Intelligence API",
    description="REST API for decision intelligence, scoring, and analytics",
    version="1.0.0",
    lifespan=lifespan
)

# Middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "example.com"])
app.add_middleware(CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://example.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Routes
from api.routers import auth, decisions, scoring, dashboard, health
app.include_router(auth.router, prefix="/api/v1", tags=["auth"])
app.include_router(decisions.router, prefix="/api/v1", tags=["decisions"])
app.include_router(scoring.router, prefix="/api/v1", tags=["scoring"])
app.include_router(dashboard.router, prefix="/api/v1", tags=["dashboard"])
app.include_router(health.router, prefix="/api/v1", tags=["health"])
```

### 4B.3: SurrealDB Schema Extensions

**New Tables for API/Dashboard:**

```sql
-- API Request Logging
DEFINE TABLE api_request_log SCHEMAFULL;
DEFINE FIELD timestamp ON api_request_log TYPE datetime DEFAULT fn::now();
DEFINE FIELD method ON api_request_log TYPE string;
DEFINE FIELD endpoint ON api_request_log TYPE string;
DEFINE FIELD status_code ON api_request_log TYPE number;
DEFINE FIELD user_id ON api_request_log TYPE string;
DEFINE FIELD response_time_ms ON api_request_log TYPE number;
DEFINE FIELD error_message ON api_request_log TYPE string;
DEFINE INDEX api_request_log_timestamp ON api_request_log (timestamp) DESC;
DEFINE INDEX api_request_log_user ON api_request_log (user_id);

-- Dashboard Presets (saved views)
DEFINE TABLE dashboard_preset SCHEMAFULL;
DEFINE FIELD name ON dashboard_preset TYPE string;
DEFINE FIELD owner ON dashboard_preset TYPE string;
DEFINE FIELD description ON dashboard_preset TYPE string;
DEFINE FIELD filters ON dashboard_preset TYPE object;
DEFINE FIELD metrics ON dashboard_preset TYPE array;
DEFINE FIELD layout ON dashboard_preset TYPE object;
DEFINE FIELD is_public ON dashboard_preset TYPE boolean DEFAULT false;
DEFINE FIELD created_at ON dashboard_preset TYPE datetime DEFAULT fn::now();
DEFINE FIELD updated_at ON dashboard_preset TYPE datetime DEFAULT fn::now();
DEFINE INDEX dashboard_preset_owner ON dashboard_preset (owner);

-- Decision Watchers (for notifications)
DEFINE TABLE decision_watch SCHEMAFULL;
DEFINE FIELD user_id ON decision_watch TYPE string;
DEFINE FIELD decision_id ON decision_watch TYPE record;
DEFINE FIELD watch_type ON decision_watch TYPE string; -- "score_change", "status_change", "all"
DEFINE FIELD threshold ON decision_watch TYPE number; -- For score_change alerts
DEFINE FIELD created_at ON decision_watch TYPE datetime DEFAULT fn::now();
DEFINE FIELD is_active ON decision_watch TYPE boolean DEFAULT true;
DEFINE INDEX decision_watch_user ON decision_watch (user_id);

-- Score History (for tracking confidence evolution)
DEFINE TABLE score_history SCHEMAFULL;
DEFINE FIELD decision_id ON score_history TYPE record;
DEFINE FIELD base_confidence ON score_history TYPE number;
DEFINE FIELD bayesian_adjusted ON score_history TYPE number;
DEFINE FIELD ml_adjusted ON score_history TYPE number;
DEFINE FIELD final_confidence ON score_history TYPE number;
DEFINE FIELD factors ON score_history TYPE object;
DEFINE FIELD recorded_at ON score_history TYPE datetime DEFAULT fn::now();
DEFINE FIELD calculation_method ON score_history TYPE string;
DEFINE INDEX score_history_decision ON score_history (decision_id);
DEFINE INDEX score_history_recorded ON score_history (recorded_at) DESC;

-- API Keys (for SDK clients)
DEFINE TABLE api_key SCHEMAFULL;
DEFINE FIELD user_id ON api_key TYPE string;
DEFINE FIELD key_hash ON api_key TYPE string;
DEFINE FIELD name ON api_key TYPE string;
DEFINE FIELD permissions ON api_key TYPE array;
DEFINE FIELD last_used ON api_key TYPE datetime;
DEFINE FIELD created_at ON api_key TYPE datetime DEFAULT fn::now();
DEFINE FIELD expires_at ON api_key TYPE datetime;
DEFINE FIELD is_active ON api_key TYPE boolean DEFAULT true;
DEFINE INDEX api_key_user ON api_key (user_id);
```

### 4B.4: React Dashboard Architecture

**Dashboard Components:**

```
Dashboard/
├── layouts/
│   ├── MainLayout.tsx      # Top-level layout with nav
│   └── DashboardLayout.tsx # Dashboard-specific layout
├── pages/
│   ├── DashboardPage.tsx   # Main dashboard view
│   ├── DecisionPage.tsx    # Single decision detail
│   ├── AnalyticsPage.tsx   # Analytics & reporting
│   └── SettingsPage.tsx    # User settings
├── components/
│   ├── cards/
│   │   ├── DecisionCard.tsx        # Decision summary card
│   │   ├── MetricCard.tsx          # KPI metric card
│   │   └── AlertCard.tsx           # Alert notification card
│   ├── charts/
│   │   ├── ScoreDistribution.tsx   # Histogram of scores
│   │   ├── ConfidenceTrend.tsx     # Line chart over time
│   │   ├── ImpactMatrix.tsx        # Decision dependency matrix
│   │   └── DecisionTimeline.tsx    # Chronological view
│   ├── tables/
│   │   ├── DecisionTable.tsx       # Sortable/filterable list
│   │   ├── ScoreHistory.tsx        # Historical score evolution
│   │   └── RecommendationTable.tsx # Action recommendations
│   └── controls/
│       ├── FilterPanel.tsx         # Filter controls
│       ├── DateRangePicker.tsx     # Date selection
│       └── PresetSelector.tsx      # Save/load dashboard presets
├── hooks/
│   ├── useDecisions.ts     # Decisions API hook
│   ├── useDashboard.ts     # Dashboard data hook
│   ├── useScores.ts        # Score calculation hook
│   └── useNotifications.ts # Real-time notifications
└── store/
    ├── dashboardStore.ts   # Zustand store for dashboard state
    ├── filterStore.ts      # Filter state
    └── presetStore.ts      # Dashboard preset state
```

**Zustand Store Example (dashboardStore.ts):**
```typescript
interface DashboardState {
  decisions: Decision[];
  selectedDecision: Decision | null;
  isLoading: boolean;
  error: string | null;
  filters: FilterOptions;
  setDecisions: (decisions: Decision[]) => void;
  selectDecision: (id: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  updateFilters: (filters: Partial<FilterOptions>) => void;
  fetchDecisions: () => Promise<void>;
  recalculateScore: (decisionId: string) => Promise<void>;
}

export const useDashboardStore = create<DashboardState>((set) => ({
  decisions: [],
  selectedDecision: null,
  isLoading: false,
  error: null,
  filters: defaultFilters,

  setDecisions: (decisions) => set({ decisions }),
  selectDecision: (id) => set(state => ({
    selectedDecision: state.decisions.find(d => d.id === id) || null
  })),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error }),

  updateFilters: (filters) => set(state => ({
    filters: { ...state.filters, ...filters }
  })),

  fetchDecisions: async () => {
    set({ isLoading: true });
    try {
      const response = await fetch('/api/v1/decisions');
      const data = await response.json();
      set({ decisions: data, isLoading: false });
    } catch (error) {
      set({ error: (error as Error).message, isLoading: false });
    }
  },

  recalculateScore: async (decisionId) => {
    try {
      await fetch(`/api/v1/scores/${decisionId}`, { method: 'POST' });
      // Refetch decisions to get updated scores
      const response = await fetch('/api/v1/decisions');
      const data = await response.json();
      set({ decisions: data });
    } catch (error) {
      set({ error: (error as Error).message });
    }
  }
}));
```

**Key Dashboard Features:**

1. **Real-time Score Updates**: WebSocket connection for live score changes
2. **Interactive Filters**: Status, confidence range, date range, tags
3. **Saved Presets**: Save/load custom dashboard configurations
4. **Alert Notifications**: Badge alerts for score changes >10%
5. **Export Capabilities**: Download data as CSV/JSON

---

## Phase 5: Bayesian Scoring & ML Confidence Calibration

### 5.1: Bayesian Confidence Model

**Objective**: Upgrade base confidence scores (Phase 4A) with Bayesian inference and uncertainty quantification.

**Bayesian Framework:**

The base confidence score $C_{base}$ (from Phase 4A) serves as a prior. We update it with historical evidence using Bayes' theorem:

$$P(\text{outcome=success} | \text{evidence}) = \frac{P(\text{evidence} | \text{outcome=success}) \cdot P(\text{outcome=success})}{P(\text{evidence})}$$

**Model Structure (PyMC):**

```python
import pymc as pm
import numpy as np

class BayesianConfidenceModel:
    def __init__(self, prior_alpha=10, prior_beta=10):
        """
        Beta-Binomial conjugate model for binary outcomes.

        Args:
            prior_alpha: Alpha parameter for Beta prior (success count)
            prior_beta: Beta parameter for Beta prior (failure count)
        """
        self.prior_alpha = prior_alpha
        self.prior_beta = prior_beta

    def fit(self, base_confidence: float,
            historical_outcomes: List[int],  # 1 for success, 0 for failure
            factor_importance: Dict[str, float]) -> Dict[str, Any]:
        """
        Fit Bayesian model with historical outcomes and factor importance.

        Args:
            base_confidence: Prior confidence from Phase 4A
            historical_outcomes: List of past decision outcomes
            factor_importance: Importance weights of decision factors

        Returns:
            Dictionary with posterior mean, credible interval, etc.
        """
        # Convert base_confidence to prior parameters using method of moments
        prior_alpha = self.prior_alpha * base_confidence
        prior_beta = self.prior_beta * (1 - base_confidence)

        with pm.Model() as model:
            # Prior: Beta distribution
            theta = pm.Beta('theta', alpha=prior_alpha, beta=prior_beta)

            # Likelihood: Binomial with historical outcomes
            outcomes = pm.Binomial('outcomes',
                                   n=len(historical_outcomes),
                                   p=theta,
                                   observed=sum(historical_outcomes))

            # MCMC sampling
            trace = pm.sample(2000, tune=1000, return_inferencedata=True,
                            progressbar=False)

        # Extract posterior statistics
        posterior_samples = trace.posterior['theta'].values.flatten()

        return {
            'posterior_mean': float(np.mean(posterior_samples)),
            'posterior_std': float(np.std(posterior_samples)),
            'hdi_lower': float(np.percentile(posterior_samples, 2.5)),
            'hdi_upper': float(np.percentile(posterior_samples, 97.5)),
            'posterior_samples': posterior_samples
        }

    def predict(self, base_confidence: float,
               historical_outcomes: List[int],
               factor_importance: Dict[str, float]) -> Dict[str, float]:
        """
        Generate Bayesian-adjusted confidence prediction.
        """
        posterior_stats = self.fit(base_confidence, historical_outcomes,
                                  factor_importance)

        # Weighted combination: prior (base confidence) and posterior mean
        adjustment_factor = len(historical_outcomes) / (len(historical_outcomes) + 5)
        bayesian_confidence = (
            (1 - adjustment_factor) * base_confidence +
            adjustment_factor * posterior_stats['posterior_mean']
        )

        return {
            'adjusted_confidence': bayesian_confidence,
            'uncertainty': posterior_stats['posterior_std'],
            'lower_bound': posterior_stats['hdi_lower'],
            'upper_bound': posterior_stats['hdi_upper'],
            'prior_mean': base_confidence,
            'posterior_mean': posterior_stats['posterior_mean']
        }
```

**Model Interpretation:**
- **Posterior Mean**: Updated confidence estimate (0.0-1.0)
- **Uncertainty (Std Dev)**: Degree of confidence in the estimate
- **Credible Interval (HDI)**: 95% range where true value likely lies
- **Adjustment Factor**: How much weight to give historical evidence

### 5.2: ML Confidence Calibration (XGBoost)

**Objective**: Learn systematic patterns in confidence prediction errors and correct them.

**Feature Engineering:**

```python
class MLConfidenceCalibrator:
    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.scaler = StandardScaler()
        self.feature_names = [
            'base_confidence', 'bayesian_confidence', 'factor_diversity',
            'dependency_count', 'historical_accuracy', 'factor_uncertainty',
            'time_since_decision', 'decision_complexity', 'update_frequency'
        ]
        if model_path:
            self.load(model_path)

    def engineer_features(self, decision_record: Dict[str, Any]) -> np.ndarray:
        """
        Extract 9 ML features from decision and scoring data.
        """
        features = np.array([
            decision_record['base_confidence'],
            decision_record['bayesian_confidence'],
            # Factor diversity: how spread out are factor weights?
            np.std(list(decision_record['factors'].values())),
            len(decision_record['dependent_decisions']),
            # Historical accuracy: success rate of similar decisions
            self._calculate_historical_accuracy(decision_record),
            # Factor uncertainty: inverse of factor agreement
            self._calculate_factor_uncertainty(decision_record),
            (time.time() - decision_record['created_at']) / 86400,  # days
            decision_record['complexity_score'],
            decision_record['update_count']
        ])
        return features.reshape(1, -1)

    def fit(self, training_data: List[Dict[str, Any]]):
        """
        Train XGBoost model on historical decision outcomes.

        Args:
            training_data: List of past decisions with known outcomes
        """
        X = np.array([self.engineer_features(d).flatten()
                     for d in training_data])
        y = np.array([d['outcome'] for d in training_data])  # 1 or 0

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Train XGBoost
        self.model = xgb.XGBClassifier(
            n_estimators=100,
            max_depth=6,
            learning_rate=0.1,
            subsample=0.8,
            colsample_bytree=0.8,
            random_state=42
        )
        self.model.fit(X_scaled, y)

    def predict_correction(self, bayesian_confidence: float,
                          decision_record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Predict ML-based correction to Bayesian confidence.
        """
        features = self.engineer_features(decision_record)
        X_scaled = self.scaler.transform(features)

        # Get prediction and SHAP explanation
        ml_probability = self.model.predict_proba(X_scaled)[0, 1]

        # SHAP for interpretability
        explainer = shap.TreeExplainer(self.model)
        shap_values = explainer.shap_values(X_scaled)

        # Correction factor (how much to adjust Bayesian score)
        correction_factor = ml_probability - bayesian_confidence

        return {
            'ml_probability': ml_probability,
            'correction_factor': correction_factor,
            'final_confidence': bayesian_confidence + correction_factor * 0.3,
            'feature_importance': dict(zip(self.feature_names,
                                          shap_values[0])),
            'model_confidence': float(self.model.predict_proba(X_scaled)[0].max())
        }

    def save(self, path: str):
        self.model.save_model(path)
        with open(f"{path}.scaler", 'wb') as f:
            pickle.dump(self.scaler, f)

    def load(self, path: str):
        self.model = xgb.XGBClassifier()
        self.model.load_model(path)
        with open(f"{path}.scaler", 'rb') as f:
            self.scaler = pickle.load(f)
```

### 5.3: Confidence Score Aggregation

**Complete Scoring Pipeline:**

```python
class ConfidenceScoringService:
    def __init__(self, phase_4a_scorer, bayesian_model, ml_calibrator):
        self.phase_4a = phase_4a_scorer  # From Phase 4A
        self.bayesian = bayesian_model
        self.ml = ml_calibrator

    def calculate_confidence(self, decision_id: str,
                           recalc_method: str = "ml") -> Dict[str, float]:
        """
        Complete confidence calculation pipeline.

        Methods:
        - "base": Phase 4A confidence only
        - "bayesian": Phase 4A + Bayesian adjustment
        - "ml": Phase 4A + Bayesian + ML calibration (best)
        """
        decision = self.db.get_decision(decision_id)

        # Step 1: Base confidence (Phase 4A)
        base = self.phase_4a.calculate_confidence(decision)

        if recalc_method == "base":
            return {
                'final_confidence': base['confidence'],
                'method': 'base',
                'components': {'base': base['confidence']}
            }

        # Step 2: Bayesian adjustment
        historical = self.db.get_historical_outcomes(decision_id)
        bayesian = self.bayesian.predict(
            base['confidence'],
            historical['outcomes'],
            decision['factor_weights']
        )

        if recalc_method == "bayesian":
            return {
                'final_confidence': bayesian['adjusted_confidence'],
                'method': 'bayesian',
                'components': {
                    'base': base['confidence'],
                    'bayesian': bayesian['adjusted_confidence']
                },
                'uncertainty': bayesian['uncertainty'],
                'bounds': (bayesian['lower_bound'], bayesian['upper_bound'])
            }

        # Step 3: ML calibration
        ml_result = self.ml.predict_correction(
            bayesian['adjusted_confidence'],
            decision
        )

        final_confidence = ml_result['final_confidence']

        # Store score in history
        self.db.insert_score_history({
            'decision_id': decision_id,
            'base_confidence': base['confidence'],
            'bayesian_adjusted': bayesian['adjusted_confidence'],
            'ml_adjusted': ml_result['ml_probability'],
            'final_confidence': final_confidence,
            'factors': decision['factor_weights'],
            'calculation_method': recalc_method
        })

        return {
            'final_confidence': final_confidence,
            'method': 'ml',
            'components': {
                'base': base['confidence'],
                'bayesian': bayesian['adjusted_confidence'],
                'ml': ml_result['ml_probability']
            },
            'uncertainty': bayesian['uncertainty'],
            'bounds': (bayesian['lower_bound'], bayesian['upper_bound']),
            'feature_importance': ml_result['feature_importance'],
            'correction_factor': ml_result['correction_factor']
        }
```

---

## Implementation Roadmap (5 Steps)

### Step 1: API Scaffolding & FastAPI Setup (2.5 days)
- [ ] Initialize FastAPI project
- [ ] Set up SurrealDB connections
- [ ] Implement authentication (JWT + API keys)
- [ ] Create Pydantic models for all endpoints
- [ ] Set up middleware (CORS, rate limiting, error handling)
- [ ] Create health check endpoint
- **Deliverable**: Runnable API server, OpenAPI docs

### Step 2: Decision & Scoring Endpoints (2 days)
- [ ] Implement decision CRUD endpoints
- [ ] Create score calculation endpoints
- [ ] Integrate Phase 4A confidence scorer
- [ ] Implement dashboard data aggregation
- [ ] Add pagination and filtering
- **Deliverable**: 12 decision/scoring endpoints working

### Step 3: Dashboard UI (React) (2.5 days)
- [ ] Create React project with TypeScript
- [ ] Set up Zustand store
- [ ] Build main dashboard page with KPI cards
- [ ] Implement decision list table with sorting/filtering
- [ ] Create decision detail view
- [ ] Add real-time score update hook
- **Deliverable**: Functional dashboard connected to API

### Step 4: Bayesian Scoring Model (2 days)
- [ ] Implement Beta-Binomial conjugate model
- [ ] Set up PyMC integration
- [ ] Create historical outcome tracking
- [ ] Add posterior inference and credible intervals
- [ ] Integrate with scoring service
- [ ] Store score history in SurrealDB
- **Deliverable**: Bayesian scoring working end-to-end

### Step 5: ML Calibration & Testing (2 days)
- [ ] Implement XGBoost calibrator
- [ ] Feature engineering pipeline
- [ ] SHAP explainability integration
- [ ] Complete test suite (unit, integration, e2e)
- [ ] Performance benchmarking
- [ ] Documentation & examples
- **Deliverable**: 50+ tests, 85%+ coverage, all features working

---

## Testing Strategy

### Unit Tests (25+ tests)

**Test Coverage by Component:**

```python
# tests/unit/test_api_models.py
def test_decision_model_validation():
    # Valid decision
    d = DecisionCreate(
        title="Test",
        description="Test decision",
        factor_weights={"factor1": 0.5}
    )
    assert d.title == "Test"

    # Invalid: factor weights must sum to 1.0
    with pytest.raises(ValidationError):
        DecisionCreate(factor_weights={"factor1": 1.5})

# tests/unit/test_bayesian_model.py
def test_bayesian_posterior_inference():
    model = BayesianConfidenceModel()
    result = model.fit(
        base_confidence=0.7,
        historical_outcomes=[1, 1, 0, 1, 1],  # 4/5 success rate
        factor_importance={"factor1": 0.5}
    )
    assert 0.7 <= result['posterior_mean'] <= 0.9
    assert result['hdi_lower'] < result['posterior_mean']
    assert result['posterior_mean'] < result['hdi_upper']

# tests/unit/test_ml_calibrator.py
def test_ml_feature_engineering():
    calibrator = MLConfidenceCalibrator()
    decision = {
        'base_confidence': 0.75,
        'bayesian_confidence': 0.78,
        'factors': {'f1': 0.5, 'f2': 0.5},
        'dependent_decisions': ['d1', 'd2'],
        'created_at': time.time(),
        'complexity_score': 3.5,
        'update_count': 5
    }
    features = calibrator.engineer_features(decision)
    assert features.shape == (1, 9)
    assert all(np.isfinite(features))
```

### Integration Tests (15+ tests)

```python
# tests/integration/test_api_endpoints.py
@pytest.mark.asyncio
async def test_create_and_score_decision():
    # Create decision via API
    decision_data = {
        "title": "API Test Decision",
        "description": "Testing full flow",
        "factor_weights": {"factor1": 1.0}
    }
    response = await client.post("/api/v1/decisions",
                                json=decision_data,
                                headers={"Authorization": "Bearer test_token"})
    assert response.status_code == 201
    decision_id = response.json()["id"]

    # Get decision
    response = await client.get(f"/api/v1/decisions/{decision_id}",
                               headers={"Authorization": "Bearer test_token"})
    assert response.status_code == 200

    # Recalculate score
    response = await client.post(f"/api/v1/scores/{decision_id}",
                                json={"force_refresh": True},
                                headers={"Authorization": "Bearer test_token"})
    assert response.status_code == 200
    assert "final_confidence" in response.json()

# tests/integration/test_confidence_pipeline.py
def test_full_confidence_calculation():
    service = ConfidenceScoringService(
        phase_4a_scorer,
        bayesian_model,
        ml_calibrator
    )

    # Create test decision
    decision_id = "test_decision_123"
    db.insert_decision({"id": decision_id, "factors": {...}})

    # Base confidence
    result_base = service.calculate_confidence(decision_id, "base")
    assert 0 <= result_base['final_confidence'] <= 1

    # Bayesian
    result_bayesian = service.calculate_confidence(decision_id, "bayesian")
    assert result_bayesian['method'] == 'bayesian'
    assert 'uncertainty' in result_bayesian

    # ML
    result_ml = service.calculate_confidence(decision_id, "ml")
    assert result_ml['method'] == 'ml'
    assert 'feature_importance' in result_ml
```

### E2E Tests (8+ tests)

```python
# tests/e2e/test_dashboard_flow.py
@pytest.mark.asyncio
async def test_dashboard_create_filter_export():
    # Login
    auth_response = await client.post("/api/v1/auth/login",
        json={"email": "test@example.com", "password": "password"})
    token = auth_response.json()["access_token"]

    # Create decisions
    for i in range(5):
        await client.post("/api/v1/decisions",
            json={"title": f"Decision {i}", "factor_weights": {...}},
            headers={"Authorization": f"Bearer {token}"})

    # Get dashboard summary
    response = await client.get("/api/v1/dashboard/summary",
        headers={"Authorization": f"Bearer {token}"})
    assert response.json()['total_decisions'] == 5

    # Filter decisions
    response = await client.get("/api/v1/decisions?status=active&min_confidence=0.7",
        headers={"Authorization": f"Bearer {token}"})
    assert len(response.json()) >= 0

    # Save preset
    preset = {"name": "High Confidence", "filters": {"min_confidence": 0.8}}
    await client.post("/api/v1/dashboard/presets",
        json=preset,
        headers={"Authorization": f"Bearer {token}"})
```

### Performance Benchmarks

**Targets:**
- API endpoints: <200ms p99 latency
- Bayesian inference: <1s per decision
- ML calibration: <500ms per decision
- Dashboard summary query: <500ms
- Real-time WebSocket updates: <100ms

**Benchmark Suite (src/benchmarks/benchmark_suite.py):**
```python
import timeit

def benchmark_confidence_calculation():
    service = ConfidenceScoringService(...)
    times = []
    for i in range(100):
        start = timeit.default_timer()
        service.calculate_confidence(f"decision_{i}", "ml")
        times.append(timeit.default_timer() - start)

    print(f"Mean: {np.mean(times)*1000:.2f}ms")
    print(f"p99: {np.percentile(times, 99)*1000:.2f}ms")
    assert np.percentile(times, 99) < 1.0  # 1 second
```

---

## Success Criteria & Metrics

### Phase 4B Success Criteria
- ✅ 20+ REST API endpoints fully functional
- ✅ React dashboard deployed and accessible
- ✅ JWT authentication working for all endpoints
- ✅ Dashboard CRUD operations complete
- ✅ Real-time score updates working
- ✅ 15+ tests passing, 85%+ coverage
- ✅ API documentation (OpenAPI) complete
- ✅ <200ms p99 API latency

### Phase 5 Success Criteria
- ✅ Bayesian model training and inference complete
- ✅ Credible intervals calculated for all decisions
- ✅ ML calibrator trained on historical data
- ✅ SHAP feature importance generated for explanations
- ✅ Score history tracked in SurrealDB
- ✅ 30+ tests passing, 85%+ coverage
- ✅ Confidence scores improved by 15%+ on validation set
- ✅ <1s end-to-end scoring latency

### Combined Metrics
- **Total LOC**: 900+ (500 API + 300 Dashboard + 100 ML/Bayesian)
- **Total Tests**: 50+ (25 unit + 15 integration + 8 e2e + 2 benchmarks)
- **Code Coverage**: 85%+
- **API Endpoints**: 20+
- **Dashboard Components**: 15+
- **ML Models**: 2 (Bayesian + XGBoost)

---

## Team Assignments & Timeline

| Phase | Team | Duration | Start | End |
|-------|------|----------|-------|-----|
| 4B | integration-engineer (API), observability-specialist (Dashboard) | 1 week | Mar 2 | Mar 8 |
| 5 | integration-engineer (Bayesian), data-graph-specialist (ML/Features) | 2 weeks | Mar 2 | Mar 15 |

**Parallel Execution**: Phase 4B and 5 run concurrently with different team members

---

## Dependencies & Risks

### External Dependencies
- Phase 4A must complete with stable confidence scoring interface
- SurrealDB cluster operational
- Redis (optional, for caching)

### Technical Risks
- Bayesian inference may be slow on large datasets → Implement caching
- XGBoost overfitting on historical data → Cross-validation + regularization
- API rate limits too restrictive → Monitor and adjust dynamically

### Mitigation Strategies
- Feature flag for Bayesian/ML calculations
- Fallback to Phase 4A scores if downstream models fail
- Comprehensive error handling and logging

---

## Deliverables Checklist

### Phase 4B Deliverables
- [ ] FastAPI application with 20+ endpoints
- [ ] Pydantic models and schemas
- [ ] SurrealDB migrations (api_request_log, dashboard_preset, decision_watch, api_key tables)
- [ ] React dashboard components
- [ ] Zustand state management
- [ ] Authentication system (JWT + API keys)
- [ ] OpenAPI documentation
- [ ] 15+ unit/integration tests
- [ ] User guide & API documentation

### Phase 5 Deliverables
- [ ] PyMC Bayesian inference model
- [ ] XGBoost ML calibrator
- [ ] Feature engineering pipeline
- [ ] SHAP explainability integration
- [ ] Score history tracking
- [ ] 30+ unit/integration tests
- [ ] Performance benchmarks
- [ ] Model comparison reports
- [ ] Examples and tutorials

---

**Status**: 🔵 SPECIFICATION COMPLETE - Ready for Implementation

**Next Steps**:
1. Phase 4A completion validation (by 2026-02-25)
2. Phase 4B trigger decision (if 4A early)
3. Phase 5 implementation begins (by 2026-03-02)
