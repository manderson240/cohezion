"""Tests for CompoundExecutor and CompoundConfig."""

from __future__ import annotations

import pytest

from cohezion.compound.config import CompoundConfig
from cohezion.compound.executor import (
    CompoundExecutionResult,
    CompoundExecutor,
    get_executor,
    reset_executor,
)


class TestCompoundConfig:
    """Tests for CompoundConfig Pydantic model."""

    def test_defaults(self) -> None:
        cfg = CompoundConfig()
        assert cfg.default_model == "phi3:mini"
        assert cfg.code_model == "qwen3-coder:30b"
        assert cfg.ollama_host == "http://localhost:11434"
        assert cfg.cache_max_size == 512

    def test_model_for_operation_generate(self) -> None:
        cfg = CompoundConfig()
        assert cfg.model_for_operation("generate") == "qwen3-coder:30b"

    def test_model_for_operation_analyze(self) -> None:
        cfg = CompoundConfig()
        assert cfg.model_for_operation("analyze") == "phi3:mini"

    def test_model_for_operation_search(self) -> None:
        cfg = CompoundConfig()
        assert cfg.model_for_operation("search") == "phi3:mini"

    def test_model_for_operation_transform_is_none(self) -> None:
        cfg = CompoundConfig()
        assert cfg.model_for_operation("transform") is None

    def test_model_for_operation_persist_is_none(self) -> None:
        cfg = CompoundConfig()
        assert cfg.model_for_operation("persist") is None

    def test_model_for_unknown_operation_uses_default(self) -> None:
        cfg = CompoundConfig()
        assert cfg.model_for_operation("unknown") == "phi3:mini"

    def test_custom_operation_map(self) -> None:
        cfg = CompoundConfig(operation_model_map={"generate": "llama3:8b", "analyze": "llama3:8b"})
        assert cfg.model_for_operation("generate") == "llama3:8b"


class _MockTokenClient:
    """Mock token client for testing."""

    def __init__(self, response: str = "mock output") -> None:
        self._response = response
        self.calls: list[dict] = []

    async def generate(self, prompt: str, **kwargs) -> str:
        self.calls.append({"prompt": prompt, **kwargs})
        return self._response

    def get_metrics(self) -> dict:
        return {
            "cache_hits": 0,
            "cache_misses": len(self.calls),
            "cache_hit_rate": 0.0,
            "tokens_saved": 0,
            "total_calls": len(self.calls),
            "model_usage": {},
        }


class TestCompoundExecutor:
    """Tests for CompoundExecutor with mocked Ollama."""

    @pytest.mark.asyncio
    async def test_execute_skill_basic(self) -> None:
        """Execute a known PRIME skill with mock token client."""
        mock = _MockTokenClient("Generated code output")
        executor = CompoundExecutor(token_client=mock)

        result = await executor.execute_skill(
            "COMPOUND_ENGINEERING_PRIME",
            "test input",
        )

        assert isinstance(result, CompoundExecutionResult)
        assert result.skill_name == "COMPOUND_ENGINEERING_PRIME"
        assert result.total_duration_ms > 0

    @pytest.mark.asyncio
    async def test_execute_skill_not_found(self) -> None:
        """Unknown skill raises KeyError."""
        mock = _MockTokenClient()
        executor = CompoundExecutor(token_client=mock)

        with pytest.raises(KeyError, match="Skill not found"):
            await executor.execute_skill("NONEXISTENT_SKILL", "test")

    @pytest.mark.asyncio
    async def test_execute_skill_with_model_override(self) -> None:
        """Model override is passed through to token_client."""
        mock = _MockTokenClient("overridden output")
        executor = CompoundExecutor(token_client=mock)

        result = await executor.execute_skill(
            "COMPOUND_ENGINEERING_PRIME",
            "test input",
            model="llama3:8b",
        )

        assert result.skill_name == "COMPOUND_ENGINEERING_PRIME"
        # Verify model was passed to generate calls
        for call in mock.calls:
            assert call.get("model") == "llama3:8b"

    @pytest.mark.asyncio
    async def test_execute_skill_tracks_model_usage(self) -> None:
        """Model usage dict is populated correctly."""
        mock = _MockTokenClient("output")
        executor = CompoundExecutor(token_client=mock)

        result = await executor.execute_skill(
            "COMPOUND_ENGINEERING_PRIME",
            "test input",
        )

        # Should have model entries for generate/analyze steps
        assert isinstance(result.model_usage, dict)

    @pytest.mark.asyncio
    async def test_execute_skill_no_instructions(self) -> None:
        """Skill with no instructions produces empty steps."""
        mock = _MockTokenClient()
        executor = CompoundExecutor(token_client=mock)

        # Find a skill with no instructions
        from cohezion.core.template_engine import TemplateEngine

        engine = TemplateEngine()
        specs = engine.parse_all()
        no_instr = [s for s in specs if not s.instructions]

        if not no_instr:
            pytest.skip("No skills without instructions found")

        result = await executor.execute_skill(no_instr[0].name, "test")
        assert result.steps == []
        assert result.total_tokens == 0


class TestCompoundExecutorSingleton:
    """Tests for get_executor/reset_executor."""

    def test_singleton_returns_same_instance(self) -> None:
        reset_executor()
        ex1 = get_executor()
        ex2 = get_executor()
        assert ex1 is ex2
        reset_executor()

    def test_reset_clears_singleton(self) -> None:
        reset_executor()
        ex1 = get_executor()
        reset_executor()
        ex2 = get_executor()
        assert ex1 is not ex2
        reset_executor()

    def test_get_executor_with_config(self) -> None:
        reset_executor()
        cfg = CompoundConfig(default_model="test:model")
        ex = get_executor(config=cfg)
        assert ex.config.default_model == "test:model"
        reset_executor()


class TestCompoundExecutionResult:
    """Tests for the result dataclass."""

    def test_defaults(self) -> None:
        r = CompoundExecutionResult(skill_name="test")
        assert r.skill_name == "test"
        assert r.final_output == ""
        assert r.steps == []
        assert r.total_tokens == 0
        assert r.total_duration_ms == 0.0
        assert r.model_usage == {}
