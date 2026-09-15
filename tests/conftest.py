"""Shared test fixtures for the Cohezion test suite."""

from __future__ import annotations

import asyncio
import contextlib
import os
import shutil
import subprocess
import sys
import time
import uuid
from collections.abc import Generator
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


# Hypothesis CI profile (loaded via HYPOTHESIS_PROFILE=ci in CI workflows):
# derandomize=True makes CI failures reproducible; deadline=None avoids flaky
# timing on shared runners; max_examples=200 balances bug-finding vs CI time.
# Local runs use the default profile (randomized, 100 examples) for power.
try:
    from hypothesis import HealthCheck, settings

    settings.register_profile(
        "ci",
        max_examples=200,
        derandomize=True,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow],
    )
except ImportError:
    pass  # hypothesis is a dev extra; property tests skip if absent


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


@pytest.fixture(scope="session", autouse=True)
def _isolate_cohezion_state(tmp_path_factory) -> Generator[Path, None, None]:
    """Keep SkillHealthTracker out of the user's real ~/.cohezion state root.

    Anchoring SkillHealthTracker's default to ~/.cohezion (2026-08-27) fixed a
    cwd-dependence bug and introduced a blast-radius one: the suite began
    writing records named "test" and "FULL_CYCLE_TEST" into the developer's
    shared state directory, where that pollution had previously been contained
    in a repo-local data/ file. 27 such records were found there.

    SCOPE, deliberately narrow and stated so nobody over-trusts it: this covers
    SkillHealthTracker ONLY. Eight other ~/.cohezion paths are module-level or
    ClassVar constants built from ``Path.home()`` AT IMPORT -- dev_loop,
    actioner/engine, cockpit/daemon_state, compound_health_oracle, skill_refiner
    (x2) and compound_feeder -- so they ignore this variable and still resolve to
    the real home. That is the same frozen-$HOME shape this branch fixed for
    skill-health, unfixed elsewhere; closing it wants one shared state_root()
    helper resolved per access, which is a larger change than this branch.

    Autouse and session-scoped so it applies without every test opting in --
    an override nothing consumes is not a fix.
    """
    state_dir = tmp_path_factory.mktemp("cohezion_state")
    previous = os.environ.get("COHEZION_STATE_DIR")
    os.environ["COHEZION_STATE_DIR"] = str(state_dir)
    try:
        yield state_dir
    finally:
        if previous is None:
            os.environ.pop("COHEZION_STATE_DIR", None)
        else:
            os.environ["COHEZION_STATE_DIR"] = previous


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

    def _run(cmd):
        return subprocess.run(
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

    # Reset the MyceliumRegistry singleton (shared writer/reader registry).
    try:
        from cohezion.learning.mycelium_registry import MyceliumRegistry

        MyceliumRegistry.reset_instance()
    except (ImportError, AttributeError):
        pass

    # Reset the precipitation bus singleton.
    try:
        from cohezion.precipitation.bus import set_bus

        set_bus(None)
    except ImportError:
        pass

    # Reset DynamicConcurrencyGate module-level singleton (Wave 3G).
    try:
        import cohezion.swarm.dynamic_concurrency_gate as _dcg_module

        _dcg_module._gate_instance = None
    except (ImportError, AttributeError):
        pass

    # Reset FLUME VAE singleton to prevent state pollution across tests
    api_module: ModuleType | None = None
    with contextlib.suppress(Exception):
        import cohezion.api as api_module
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

    # Reset the MyceliumRegistry singleton after test (shared writer/reader registry).
    try:
        from cohezion.learning.mycelium_registry import MyceliumRegistry

        MyceliumRegistry.reset_instance()
    except (ImportError, AttributeError):
        pass

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


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    """Quarantine logging hook for flaky and rerun test executions.

    Google-inspired flaky test quarantine protocol:
    Monitors test execution outcomes for reruns or quarantined tests.
    When an intermittent failure or rerun occurs, structured telemetry is appended
    to reports/quarantine.jsonl to maintain pipeline health while tracking flakiness.
    """
    rerun_count = getattr(report, "rerun", 0)
    is_rerun = report.outcome == "rerun" or rerun_count > 0
    if is_rerun and report.when == "call":
        with contextlib.suppress(Exception):
            import json

            reports_dir = Path("reports")
            reports_dir.mkdir(parents=True, exist_ok=True)
            quarantine_file = reports_dir / "quarantine.jsonl"
            entry = {
                "timestamp": time.time(),
                "nodeid": report.nodeid,
                "outcome": report.outcome,
                "rerun_attempt": rerun_count,
                "duration_s": round(report.duration, 4),
                "when": report.when,
                "error": str(report.longrepr) if report.failed else None,
            }
            with open(quarantine_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")


class MockInferenceGateway:
    """Hermetic mock inference gateway for Lemonade, FastFlowLM, and Ollama."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.default_response: str = "Mocked LLM generation"
        self.canned_responses: dict[str, str] = {}
        self.latency_s: float = 0.0
        self.error: Exception | None = None

    def set_response_for_model(self, model: str, response: str) -> None:
        """Set custom canned completion for a given model identifier."""
        self.canned_responses[model] = response

    def set_error(self, exc: Exception | None) -> None:
        """Inject an error to simulate gateway or rate-limiting failures."""
        self.error = exc

    def set_latency(self, seconds: float) -> None:
        """Simulate inference network/processing latency."""
        self.latency_s = seconds

    async def complete(
        self,
        prompt: str,
        model: str = "deepseek-r1-0528-8b-FLM",
        temperature: float = 0.0,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Execute hermetic completion without making external calls."""
        self.calls.append(
            {
                "prompt": prompt,
                "model": model,
                "temperature": temperature,
                "kwargs": kwargs,
                "timestamp": time.time(),
            }
        )
        if self.latency_s > 0:
            await asyncio.sleep(self.latency_s)
        if self.error is not None:
            raise self.error
        content = self.canned_responses.get(model, self.default_response)
        prompt_tokens = max(1, len(prompt.split()))
        completion_tokens = max(1, len(content.split()))
        return {
            "content": content,
            "model": model,
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }


@pytest.fixture
def mock_inference_gateway() -> MockInferenceGateway:
    """Provide a hermetic mock inference gateway for LLM agent testing."""
    return MockInferenceGateway()


@pytest_asyncio.fixture
async def async_event_bus():
    """Provide an isolated, in-memory EventBus for agentic workflows with auto-drain on exit."""
    from cohezion.core.event_bus import EventBus

    bus = EventBus(max_queue_size=1000)
    await bus.start()
    try:
        yield bus
    finally:
        await bus.stop(drain_timeout=0.5)


class AgentTurnHarness:
    """Harness for testing individual agent turns with hermetic isolation, timeouts, and assertion helpers."""

    def __init__(self, bus: Any = None, timeout_s: float = 5.0) -> None:
        self.bus = bus
        self.timeout_s = timeout_s
        self.state_history: list[str] = ["INITIALIZED"]

    def record_state(self, state: str) -> None:
        """Record an agent state transition."""
        self.state_history.append(state)

    @contextlib.asynccontextmanager
    async def run_turn(self, name: str = "agent_turn"):
        """Execute an agent turn within a protected timeout boundary and record lifecycle events."""
        self.record_state("RUNNING")
        if self.bus is not None:
            from cohezion.core.event_bus import Event

            await self.bus.publish(Event.agent_start(agent_name=name, model="test-harness"))

        start_time = time.time()
        try:
            async with asyncio.timeout(self.timeout_s):
                yield self
            duration_ms = (time.time() - start_time) * 1000.0
            self.record_state("COMPLETED")
            if self.bus is not None:
                from cohezion.core.event_bus import Event

                await self.bus.publish(
                    Event.agent_complete(agent_name=name, result="SUCCESS", duration_ms=duration_ms)
                )
        except Exception as exc:
            duration_ms = (time.time() - start_time) * 1000.0
            self.record_state("FAILED")
            if self.bus is not None:
                from cohezion.core.event_bus import Event

                await self.bus.publish(
                    Event.agent_complete(
                        agent_name=name,
                        result=f"ERROR: {exc}",
                        duration_ms=duration_ms,
                    )
                )
            raise


@pytest.fixture
def agent_turn_harness() -> AgentTurnHarness:
    """Provide an AgentTurnHarness for testing agent steps with strict timeout guards."""
    return AgentTurnHarness(timeout_s=5.0)
