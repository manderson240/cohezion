# Security Patterns for Python ML Code

## Executive Summary

This document describes security patterns and anti-patterns specific to Python machine learning codebases, with a focus on Cohezion's use case as an AI training environment framework.

## ML-Specific Security Concerns

### 1. Model Serialization Vulnerabilities

**The Problem:**
ML models are often serialized using `pickle`, which can execute arbitrary code during deserialization.

**Vulnerable Pattern:**
```python
# BAD: Unpickling untrusted model
with open("model.pkl", "rb") as f:
    model = pickle.load(f)  # Can execute malicious code!
```

**Secure Pattern:**
```python
# GOOD: Use safe serialization formats
import joblib
from pathlib import Path

# Option 1: joblib (still uses pickle, but safer for trusted sources)
model = joblib.load("model.joblib")

# Option 2: ONNX (safer, but requires conversion)
import onnx

model = onnx.load("model.onnx")

# Option 3: JSON for simple models (scikit-learn)
from sklearn import json

model = json.loads(model_json)

# Option 4: Validate pickle source
allowed_path = Path("/safe/models")
model_path = allowed_path / Path(user_input).name
if not model_path.resolve().is_relative_to(allowed_path):
    raise ValueError("Invalid model path")
with open(model_path, "rb") as f:
    model = pickle.load(f)  # nosec: B301 - Path validated
```

**CodeQL Detection:**
- Rule: `py/unsafe-deserialization`
- CWE: CWE-502 (Deserialization of Untrusted Data)

### 2. Path Traversal in Data Loading

**The Problem:**
Loading datasets from user-provided paths can lead to reading sensitive files.

**Vulnerable Pattern:**
```python
# BAD: User-controlled path
df = pd.read_csv(user_input)
```

**Secure Pattern:**
```python
# GOOD: Path validation
from pathlib import Path
import pandas as pd

DATA_ROOT = Path("/app/data")


@validate_path
def load_dataset(filename: str) -> pd.DataFrame:
    """Load dataset with path validation."""
    safe_path = DATA_ROOT / Path(filename).name

    # Canonicalize and check
    try:
        canonical = safe_path.resolve()
        if not canonical.is_relative_to(DATA_ROOT.resolve()):
            raise ValueError("Path traversal detected")
    except (OSError, ValueError) as e:
        raise SecurityError(f"Invalid path: {e}")

    return pd.read_csv(canonical)


# Decorator implementation
from functools import wraps
from typing import Callable


def validate_path(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(filename: str, *args, **kwargs):
        # Additional validation
        if ".." in filename or filename.startswith("/"):
            raise SecurityError("Absolute or relative paths not allowed")
        return func(filename, *args, **kwargs)

    return wrapper
```

**CodeQL Detection:**
- Rule: `py/path-injection`
- CWE: CWE-22 (Path Traversal)

### 3. SQL Injection in Data Pipelines

**The Problem:**
Dynamic SQL queries with user input in ML data pipelines.

**Vulnerable Pattern:**
```python
# BAD: String formatting in SQL
query = f"SELECT * FROM training_data WHERE label = '{user_label}'"
df = pd.read_sql(query, conn)
```

**Secure Pattern:**
```python
# GOOD: Parameterized queries
from sqlalchemy import text

query = text("SELECT * FROM training_data WHERE label = :label")
df = pd.read_sql(query, conn, params={"label": user_label})

# Even better: ORM with validation
from pydantic import BaseModel, Field


class DataQuery(BaseModel):
    label: str = Field(min_length=1, max_length=50, pattern=r"^[a-zA-Z0-9_]+$")
    limit: int = Field(default=1000, le=10000)


def fetch_training_data(query: DataQuery):
    return (
        session.query(TrainingData)
        .filter(TrainingData.label == query.label)
        .limit(query.limit)
        .all()
    )
```

**CodeQL Detection:**
- Rule: `py/sql-injection`
- CWE: CWE-89 (SQL Injection)

### 4. Hardcoded Credentials in Configurations

**The Problem:**
ML pipelines often have configuration files with API keys for model registries, data sources, etc.

**Vulnerable Pattern:**
```python
# BAD: Hardcoded in config
# config.py
MLFLOW_TRACKING_URI = "https://mlflow.example.com"
MLFLOW_TRACKING_TOKEN = "ml-abc123xyz789"  # Hardcoded!
```

**Secure Pattern:**
```python
# GOOD: Environment-based configuration
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with secure defaults."""

    # Required settings
    mlflow_tracking_uri: str
    mlflow_tracking_token: str = Field(..., min_length=20)

    # Optional with defaults
    model_registry: str = "local"
    max_model_size_mb: int = 1000

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Usage
settings = get_settings()
client = MlflowClient(
    tracking_uri=settings.mlflow_tracking_uri, token=settings.mlflow_tracking_token
)
```

**CodeQL Detection:**
- Rule: `py/hardcoded-credentials`
- CWE: CWE-798 (Use of Hard-coded Credentials)

### 5. Command Injection in System Calls

**The Problem:**
ML training often requires system calls for GPU monitoring, distributed training, etc.

**Vulnerable Pattern:**
```python
# BAD: User input in shell command
import os

cmd = f"nvidia-smi --query-gpu=name --format=csv -i {gpu_id}"
os.system(cmd)  # Injection risk!
```

**Secure Pattern:**
```python
# GOOD: Whitelist validation and subprocess
import subprocess
from typing import Literal


def get_gpu_info(gpu_id: int) -> str:
    """Get GPU info with validation."""
    # Validate GPU ID
    if not isinstance(gpu_id, int) or gpu_id < 0 or gpu_id > 16:
        raise ValueError("Invalid GPU ID")

    # Use subprocess with list (safer than shell=True)
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=name", "--format=csv", "-i", str(gpu_id)],
        capture_output=True,
        text=True,
        check=True,
        timeout=30,  # Prevent hanging
    )

    return result.stdout


# For more complex commands, use shlex
import shlex


def run_training(script_path: str, args: list[str]) -> None:
    """Run training script with validation."""
    allowed_scripts = {"train.py", "evaluate.py", "export.py"}

    script_name = Path(script_path).name
    if script_name not in allowed_scripts:
        raise SecurityError(f"Script not allowed: {script_name}")

    # Validate all arguments are safe
    safe_args = []
    for arg in args:
        if not arg.isalnum() and not arg.replace("-", "").replace("_", "").isalnum():
            raise SecurityError(f"Unsafe argument: {arg}")
        safe_args.append(shlex.quote(arg))

    cmd = ["python", script_path] + safe_args
    subprocess.run(cmd, check=True)
```

**CodeQL Detection:**
- Rule: `py/command-line-injection`
- CWE: CWE-78 (OS Command Injection)

### 6. Insecure Temporary Files

**The Problem:**
ML training generates temporary files for checkpoints, logs, etc.

**Vulnerable Pattern:**
```python
# BAD: Predictable temp file
checkpoint_path = "/tmp/checkpoint_{epoch}.pt"
torch.save(model.state_dict(), checkpoint_path)
```

**Secure Pattern:**
```python
# GOOD: Secure temporary files
import tempfile
from pathlib import Path
import uuid


def save_checkpoint_secure(model: torch.nn.Module, epoch: int) -> Path:
    """Save checkpoint to secure temp location."""
    # Use secure temp directory
    with tempfile.TemporaryDirectory(prefix="cohezion_") as tmpdir:
        # Generate unique filename
        filename = f"checkpoint_{epoch}_{uuid.uuid4().hex[:8]}.pt"
        checkpoint_path = Path(tmpdir) / filename

        # Set secure permissions (owner only)
        torch.save(model.state_dict(), checkpoint_path)
        checkpoint_path.chmod(0o600)

        # Move to persistent location atomically
        persistent_path = CHECKPOINT_DIR / filename
        checkpoint_path.rename(persistent_path)

        return persistent_path


# Alternative: Use tempfile directly
with tempfile.NamedTemporaryFile(
    mode="w", suffix=".json", prefix="metrics_", delete=False, dir=SECURE_TEMP_DIR
) as f:
    json.dump(metrics, f)
    # File created with secure permissions
```

**CodeQL Detection:**
- Rule: `py/insecure-temporary-file`
- CWE: CWE-377 (Insecure Temporary File)

### 7. Information Disclosure in Error Messages

**The Problem:**
Verbose error messages can leak sensitive information about the system.

**Vulnerable Pattern:**
```python
# BAD: Detailed error messages
@app.exception_handler(Exception)
async def debug_exception_handler(request, exc):
    return JSONResponse(
        status_code=500, content={"detail": str(exc), "traceback": traceback.format_exc()}
    )
```

**Secure Pattern:**
```python
# GOOD: Sanitized error messages
import logging
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class MLAPIException(HTTPException):
    """Custom exception with safe error messages."""

    def __init__(self, detail: str, internal_error: str | None = None):
        self.internal_error = internal_error
        super().__init__(status_code=500, detail=detail)


@app.exception_handler(Exception)
async def secure_exception_handler(request, exc):
    """Handle exceptions without leaking internal details."""

    # Generate safe error ID
    error_id = uuid.uuid4().hex[:8]

    # Log full details internally
    logger.exception("Unhandled exception", extra={"error_id": error_id, "path": request.url.path})

    # Return safe message to user
    if isinstance(exc, MLAPIException):
        return JSONResponse(
            status_code=exc.status_code, content={"error": exc.detail, "error_id": error_id}
        )

    # Generic message for unexpected errors
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "error_id": error_id,
            "message": "An unexpected error occurred. Please try again later.",
        },
    )


# Usage in code
try:
    model = load_model(model_id)
except ModelNotFoundError as e:
    # Safe user-facing message
    raise MLAPIException(
        detail="Model not found",
        internal_error=str(e),  # Logged internally, not exposed
    )
```

**CodeQL Detection:**
- Rule: `py/stack-trace-exposure`
- CWE: CWE-209 (Generation of Error Message Containing Sensitive Information)

### 8. Resource Exhaustion (DoS)

**The Problem:**
ML training can be exploited to consume excessive resources.

**Vulnerable Pattern:**
```python
# BAD: Unbounded resource usage
@app.post("/train")
async def train(request: TrainingRequest):
    model = load_model(request.model_config)
    # Training runs until completion - no limits!
    model.fit(request.data, epochs=request.epochs)
    return {"status": "complete"}
```

**Secure Pattern:**
```python
# GOOD: Resource limits and timeouts
import asyncio
from pydantic import BaseModel, Field


class TrainingRequest(BaseModel):
    """Training request with resource limits."""

    epochs: int = Field(default=10, ge=1, le=1000)
    batch_size: int = Field(default=32, ge=1, le=1024)
    max_runtime_seconds: int = Field(default=3600, ge=60, le=86400)
    model_size_mb: int = Field(default=100, le=10000)

    @model_validator(mode="after")
    def validate_resources(self):
        total_iterations = self.epochs * (dataset_size / self.batch_size)
        if total_iterations > MAX_ITERATIONS:
            raise ValueError("Training would exceed iteration limit")
        return self


@app.post("/train")
async def train(request: TrainingRequest):
    """Train model with resource constraints."""

    # Timeout wrapper
    try:
        result = await asyncio.wait_for(
            run_training_with_limits(request), timeout=request.max_runtime_seconds
        )
    except asyncio.TimeoutError:
        logger.warning(f"Training timed out after {request.max_runtime_seconds}s")
        raise MLAPIException(detail="Training exceeded time limit", internal_error="timeout")

    return {"status": "complete", "result": result}


async def run_training_with_limits(request: TrainingRequest):
    """Run training with memory and CPU limits."""
    import resource

    # Set memory limit (if supported)
    try:
        resource.setrlimit(resource.RLIMIT_AS, (request.model_size_mb * 1024 * 1024, -1))
    except ValueError:
        pass  # May not be supported on all systems

    # Training logic here
    ...
```

**CodeQL Detection:**
- Rule: Custom - Resource exhaustion patterns
- CWE: CWE-770 (Allocation of Resources Without Limits or Throttling)

## ML Framework-Specific Patterns

### PyTorch Security

```python
# Secure model loading
def load_checkpoint_secure(path: str, map_location: str = "cpu"):
    """Load checkpoint with validation."""
    allowed_locations = ["cpu", "cuda", "cuda:0", "cuda:1"]
    if map_location not in allowed_locations:
        raise ValueError(f"Invalid map_location: {map_location}")

    # Only load from allowed directories
    checkpoint_path = Path(ALLOWED_CHECKPOINT_DIR) / Path(path).name
    if not checkpoint_path.is_relative_to(ALLOWED_CHECKPOINT_DIR):
        raise SecurityError("Invalid checkpoint path")

    # Load with weights_only=True (PyTorch 2.0+)
    checkpoint = torch.load(
        checkpoint_path,
        map_location=map_location,
        weights_only=True,  # Prevents arbitrary code execution
    )

    return checkpoint
```

### TensorFlow/Keras Security

```python
# Secure model loading
def load_keras_model_secure(path: str):
    """Load Keras model with validation."""
    # Keras models are HDF5 format - validate structure
    import h5py

    try:
        with h5py.File(path, "r") as f:
            # Validate it's a valid Keras model
            if "model_config" not in f.attrs:
                raise ValueError("Invalid Keras model format")

            # Additional validation...

        model = keras.models.load_model(path)
        return model
    except Exception as e:
        raise SecurityError(f"Failed to load model: {e}")
```

### Scikit-learn Security

```python
# Safe model persistence
import joblib
from sklearn.utils.validation import check_is_fitted


def save_model_secure(model, path: str):
    """Save scikit-learn model with metadata."""
    # Verify model is fitted
    check_is_fitted(model)

    # Add metadata
    metadata = {
        "sklearn_version": sklearn.__version__,
        "python_version": sys.version_info[:2],
        "model_type": type(model).__name__,
        "save_date": datetime.now().isoformat(),
    }

    joblib.dump({"model": model, "metadata": metadata}, path)


def load_model_secure(path: str, max_size_mb: int = 1000):
    """Load scikit-learn model with checks."""
    # Check file size
    size_mb = Path(path).stat().st_size / (1024 * 1024)
    if size_mb > max_size_mb:
        raise ValueError(f"Model file too large: {size_mb:.1f}MB > {max_size_mb}MB")

    data = joblib.load(path)

    # Validate metadata
    if "metadata" in data:
        metadata = data["metadata"]
        if metadata["sklearn_version"] != sklearn.__version__:
            logger.warning(f"Model saved with scikit-learn {metadata['sklearn_version']}")

    return data["model"]
```

## CodeQL Custom Queries

For ML-specific patterns, add custom CodeQL queries:

```ql
// ml-security-queries/pickles.ql
/**
 * @name Unsafe Pickle Usage in ML Code
 * @description Detects pickle.loads calls without proper validation
 * @kind path-problem
 * @problem.severity error
 * @security-severity 8.0
 * @precision high
 * @id py/ml-unsafe-pickle
 * @tags security
 *       ml
 *       external/cwe/cwe-502
 */

import python
import semmle.python.dataflow.new.DataFlow
import semmle.python.dataflow.new.TaintTracking

class UnsafePickleUsage extends TaintTracking::Configuration {
  UnsafePickleUsage() { this = "UnsafePickleUsage" }

  override predicate isSource(DataFlow::Node source) {
    // User input sources
    source.asExpr() instanceof CallExpr and
    source.asExpr().(CallExpr).getFunction().toString() = "input"
  }

  override predicate isSink(DataFlow::Node sink) {
    // pickle.load or pickle.loads
    exists(CallExpr call |
      call.getFunction().toString().matches("pickle.load%") and
      sink.asExpr() = call.getArg(0)
    )
  }
}

from UnsafePickleUsage config, DataFlow::PathNode source, DataFlow::PathNode sink
where config.hasFlowPath(source, sink)
select sink.getNode(), source, sink,
  "Unsafe pickle deserialization of user-controlled data"
```

## Testing Security Patterns

```python
# tests/test_security_patterns.py
import pytest
from unittest.mock import patch, MagicMock


def test_path_traversal_protection():
    """Test path validation blocks traversal attempts."""
    with pytest.raises(SecurityError):
        load_dataset("../../../etc/passwd")

    with pytest.raises(SecurityError):
        load_dataset("/absolute/path/to/file")


def test_sql_injection_protection():
    """Test SQL injection is blocked."""
    malicious_input = "'; DROP TABLE users; --"

    # Should not raise exception (parameterized query)
    result = fetch_training_data(DataQuery(label=malicious_input))
    assert result == []  # No matches, but no injection


def test_model_loading_security():
    """Test secure model loading."""
    # Attempt to load from outside allowed directory
    with pytest.raises(SecurityError):
        load_checkpoint_secure("/etc/passwd")

    # Attempt path traversal
    with pytest.raises(SecurityError):
        load_checkpoint_secure("../malicious.pkl")


@pytest.mark.parametrize(
    "bad_input",
    [
        "; rm -rf /",
        "$(whoami)",
        "`cat /etc/passwd`",
    ],
)
def test_command_injection_protection(bad_input):
    """Test command injection is blocked."""
    with pytest.raises((SecurityError, ValueError)):
        get_gpu_info(bad_input)
```

## References

1. [OWASP Machine Learning Security Top 10](https://owasp.org/www-project-machine-learning-security-top-10/)
2. [Microsoft AI Security](https://docs.microsoft.com/en-us/security/engineering/ai-security)
3. [PyTorch Security](https://pytorch.org/docs/stable/notes/security.html)
4. [TensorFlow Security](https://github.com/tensorflow/tensorflow/blob/master/SECURITY.md)
5. [Bandit ML Security Checks](https://bandit.readthedocs.io/en/latest/plugins/index.html)
6. [CWE Top 25](https://cwe.mitre.org/top25/)
