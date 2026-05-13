"""Shared test fixtures for the Cohezion test suite."""

from __future__ import annotations

import asyncio
import shutil
import subprocess
import sys
import uuid
from collections.abc import Generator
from pathlib import Path
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# Block heavy ML libraries from loading their C extensions into this process at
# import time.  sklearn (via transformers) and torch use different BLAS allocators;
# loading them in the wrong order causes a SIGSEGV.  The segfault was traced to
# tests/test_aimo_predict_tdd.py importing submission_transformers which does
# `from transformers import ...` at module level — this loads sklearn C exts AFTER
# torch._C is already loaded → BLAS conflict.  See L290 (Session 94).
#
# Mocking transformers here is safe because:
#  - No pytest test file directly imports transformers
#  - tests/test_aimo_predict_tdd.py overrides _model/_tokenizer with MagicMock anyway
#  - The mock satisfies `from transformers import X` by returning MagicMock instances
if "sentence_transformers" not in sys.modules:
    _mock_st = MagicMock()
    _mock_st.SentenceTransformer = MagicMock
    sys.modules["sentence_transformers"] = _mock_st

if "transformers" not in sys.modules:
    _mock_tr = MagicMock()
    _mock_tr.AutoModelForCausalLM = MagicMock
    _mock_tr.AutoTokenizer = MagicMock
    # Import and expose PretrainedConfig/PreTrainedModel/PreTrainedTokenizer as real classes
    # so that FlumeEncoder, FlumeTokenizer, etc. can inherit from them correctly.
    try:
        import transformers as _real_tr

        _mock_tr.PretrainedConfig = _real_tr.PretrainedConfig
        _mock_tr.PreTrainedModel = _real_tr.PreTrainedModel
        _mock_tr.PreTrainedTokenizer = _real_tr.PreTrainedTokenizer
    except Exception:
        # If transformers isn't installed, use MagicMock as fallback
        _mock_tr.PretrainedConfig = MagicMock
        _mock_tr.PreTrainedModel = MagicMock
        _mock_tr.PreTrainedTokenizer = MagicMock
    sys.modules["transformers"] = _mock_tr


@pytest.fixture
def mock_ollama():
    """Patch httpx calls to Ollama, returning a canned JSON response."""
    canned = {"response": "mocked-ollama-response", "done": True}
    mock_response = MagicMock(
        status_code=200,
        json=MagicMock(return_value=canned),
        raise_for_status=MagicMock(),
    )
    with patch(
        "httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response
    ) as mock_post:
        yield mock_post


@pytest.fixture
def mock_surreal():
    """Patch SurrealDB client methods to return empty results without a live connection."""
    with patch("cohezion.core.persistence.surreal_client.SurrealClient") as mock_cls:
        instance = mock_cls.return_value
        instance.connect = AsyncMock()
        instance.close = AsyncMock()
        instance.query = AsyncMock(return_value=[])
        instance.store_node = AsyncMock()
        instance.get_node = AsyncMock(return_value=None)
        yield instance


@pytest.fixture
def tmp_workdir(tmp_path: Path):
    """Provide a temporary working directory that auto-cleans after the test."""
    workdir = tmp_path / "workdir"
    workdir.mkdir()
    return workdir


@pytest.fixture
def git_repo(tmp_path: Path) -> Path:
    """Create an initialized git repo with safe defaults for testing.

    Prevents GPG signing failures, sets dummy user info, and creates
    an initial commit so that git operations (diff, log, etc.) work.

    Returns the repo root path.
    """
    _run = lambda cmd: subprocess.run(
        cmd,
        cwd=tmp_path,
        capture_output=True,
        check=True,
    )
    _run(["git", "init"])
    _run(["git", "config", "user.email", "test@cohezion.dev"])
    _run(["git", "config", "user.name", "Test User"])
    _run(["git", "config", "commit.gpgsign", "false"])
    # Create initial commit so HEAD exists
    (tmp_path / ".gitkeep").write_text("")
    _run(["git", "add", ".gitkeep"])
    _run(["git", "commit", "-m", "initial"])
    return tmp_path


@pytest.fixture
def data_temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory under data/ for security compliance.

    ResearchConfig requires paths within data/ directory (Issue #12).
    This fixture creates a unique temp directory under data/test_runs/
    and cleans it up after the test.

    Yields:
        Path to the temporary directory
    """
    test_dir = Path("data") / "test_runs" / uuid.uuid4().hex[:8]
    test_dir.mkdir(parents=True, exist_ok=True)
    yield test_dir
    # Cleanup
    shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture(autouse=True)
def event_loop_fixture():
    """Ensure a fresh event loop is available for each test."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        # No running loop, create a new one
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        yield
        loop.close()
    else:
        # Already have a running loop (pytest-asyncio)
        yield


@pytest.fixture(autouse=True)
def reset_singletons():
    """Auto-reset critical singletons before each test to prevent state pollution.

    Singletons covered (file path -> module-level state reset):
      - cohezion.concurrency.ollama_gate                  (reset_gate())
      - cohezion.swarm.model_pool_manager                 (reset_pool_manager())
      - cohezion.compound.executor.ExecutorFactory        (reset_singleton())
      - cohezion.compound.batch_executor.BatchableExecutor (reset_singleton())
      - cohezion.swarm.cost_aware_router.CostAwareRouter  (reset_singleton())
      - cohezion.cost_optimization.cost_tracker.SessionCostTracker (reset_instance())
      - cohezion.cost_optimization.budget_enforcer.BudgetEnforcer  (reset_instance())
      - cohezion.swarm.dynamic_concurrency_gate._gate_instance     (Wave 3G)
      - cohezion.api._vae_trainer (FLUME VAE)
      - cohezion.api._rl_policy   (RL policy)
      - All loggers' handlers + filters (RedactionFilter contamination guard)

    Note: cohezion.platform.resource_manager has NO module-level singleton —
    state is held in per-instance ResourceClient/ResourceDaemon objects.
    """
    import logging

    from cohezion.compound.batch_executor import BatchableExecutor
    from cohezion.compound.executor_factory import ExecutorFactory
    from cohezion.concurrency.ollama_gate import reset_gate
    from cohezion.cost_optimization.budget_enforcer import BudgetEnforcer
    from cohezion.cost_optimization.cost_tracker import SessionCostTracker
    from cohezion.security.rate_limiter import reset_rate_limiter
    from cohezion.swarm.cost_aware_router import CostAwareRouter
    from cohezion.swarm.model_pool_manager import reset_pool_manager

    # Reset before test
    reset_gate()  # Reset OllamaGate singleton
    reset_pool_manager()  # Reset ModelPoolManager singleton
    reset_rate_limiter()  # Reset RateLimiter token buckets (isolation)
    ExecutorFactory.reset_singleton()
    if hasattr(BatchableExecutor, "reset_singleton"):
        BatchableExecutor.reset_singleton()
    if hasattr(CostAwareRouter, "reset_singleton"):
        CostAwareRouter.reset_singleton()
    if hasattr(SessionCostTracker, "reset_instance"):
        SessionCostTracker.reset_instance()
    if hasattr(BudgetEnforcer, "reset_instance"):
        BudgetEnforcer.reset_instance()

    # Reset the precipitation bus singleton.
    try:
        from cohezion.precipitation.bus import set_bus

        set_bus(None)
    except ImportError:
        pass

    # Reset DynamicConcurrencyGate module-level singleton (Wave 3G).
    # Reset DynamicConcurrencyGate module-level singleton (Wave 3G).
    # Test pollution surfaced via audit: _gate_instance retained metrics across tests.
    try:
        import cohezion.swarm.dynamic_concurrency_gate as _dcg_module

        _dcg_module._gate_instance = None
    except (ImportError, AttributeError):
        pass

    # Reset FLUME VAE singleton to prevent state pollution across tests
    api_module: ModuleType | None = None
    try:
        import cohezion.api as api_module
    except Exception:  # noqa: S110 — intentional: optional API module may not be present
        pass
    if api_module is not None and hasattr(api_module, "_vae_trainer"):
        api_module._vae_trainer = None

    # Reset RL policy singleton as well
    if api_module is not None and hasattr(api_module, "_rl_policy"):
        api_module._rl_policy = None

    # Clear ALL logger handlers and filters to prevent test pollution.
    # Root cause: RedactionFilter (or any filter) can modify LogRecord.args,
    # corrupting types (%d expects int, but filter may convert to str).
    # Clearing filters on every logger before each test prevents this.
    root = logging.getLogger()
    root.handlers.clear()
    root.filters.clear()
    for name in list(logging.Logger.manager.loggerDict.keys()):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.filters.clear()
        logger.propagate = True

    yield

    # Reset after test
    reset_gate()  # Reset OllamaGate singleton
    reset_pool_manager()  # Reset ModelPoolManager singleton
    reset_rate_limiter()  # Reset RateLimiter token buckets (isolation)
    ExecutorFactory.reset_singleton()
    if hasattr(BatchableExecutor, "reset_singleton"):
        BatchableExecutor.reset_singleton()
    if hasattr(CostAwareRouter, "reset_singleton"):
        CostAwareRouter.reset_singleton()
    if hasattr(SessionCostTracker, "reset_instance"):
        SessionCostTracker.reset_instance()
    if hasattr(BudgetEnforcer, "reset_instance"):
        BudgetEnforcer.reset_instance()

    # Reset DynamicConcurrencyGate module-level singleton (Wave 3G)
    try:
        import cohezion.swarm.dynamic_concurrency_gate as _dcg_module

        _dcg_module._gate_instance = None
    except (ImportError, AttributeError):
        pass

    # Reset FLUME VAE singleton after test
    if hasattr(api_module, "_vae_trainer"):
        api_module._vae_trainer = None

    # Reset RL policy singleton after test
    if hasattr(api_module, "_rl_policy"):
        api_module._rl_policy = None

    # Clear ALL logger handlers and filters after test too
    root = logging.getLogger()
    root.handlers.clear()
    root.filters.clear()
    for name in list(logging.Logger.manager.loggerDict.keys()):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.filters.clear()
        logger.propagate = True