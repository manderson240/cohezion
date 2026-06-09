"""Unit tests for compound.local_inference and compound.telegram_notify."""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

from cohezion.compound.local_inference import (
    _estimate_tokens,
    _is_cloud_model,
    get_recommended_concurrency,
    get_session_token_record,
    lemonade_available,
    make_local_execute_fn,
)
from cohezion.compound.telegram_notify import notify, notify_task_complete


# ---------------------------------------------------------------------------
# lemonade_available
# ---------------------------------------------------------------------------


class TestLemonadeAvailable:
    def test_returns_false_when_server_unreachable(self):
        with patch("cohezion.compound.local_inference.httpx") as mock_httpx:
            mock_httpx.get.side_effect = Exception("connection refused")
            assert lemonade_available() is False

    def test_returns_true_when_server_responds_200(self):
        with patch("cohezion.compound.local_inference.httpx") as mock_httpx:
            mock_httpx.get.return_value = MagicMock(status_code=200)
            assert lemonade_available() is True

    def test_returns_false_on_non_200_status(self):
        with patch("cohezion.compound.local_inference.httpx") as mock_httpx:
            mock_httpx.get.return_value = MagicMock(status_code=503)
            assert lemonade_available() is False

    def test_uses_npu_port_by_default(self):
        with patch("cohezion.compound.local_inference.httpx") as mock_httpx:
            mock_httpx.get.return_value = MagicMock(status_code=200)
            lemonade_available()
            called_url = mock_httpx.get.call_args[0][0]
            assert "13306" in called_url


# ---------------------------------------------------------------------------
# make_local_execute_fn
# ---------------------------------------------------------------------------


class TestMakeLocalExecuteFn:
    def test_returns_callable(self):
        fn = make_local_execute_fn("test task")
        assert callable(fn)

    def test_execute_fn_returns_tuple(self):
        mock_result = MagicMock()
        mock_result.text = "hello from NPU"
        mock_result.final_model = "llama3.2-1b-FLM"
        mock_result.primary_model = "llama3.2-1b-FLM"
        mock_result.latency_ms = 42.0
        mock_result.escalation_count = 0
        mock_result.cost_usd = 0.0

        with patch("cohezion.compound.local_inference._get_orchestrator") as mock_get:
            mock_orch = MagicMock()
            mock_orch.run = AsyncMock(return_value=mock_result)
            mock_get.return_value = mock_orch

            fn = make_local_execute_fn("classify this")
            output, metrics = fn("guidance text")

        assert isinstance(output, str)
        assert isinstance(metrics, dict)
        assert output == "hello from NPU"
        assert metrics["local_silicon"] is True
        assert metrics["model"] == "llama3.2-1b-FLM"

    def test_execute_fn_returns_empty_on_error(self):
        with patch("cohezion.compound.local_inference._get_orchestrator") as mock_get:
            mock_orch = MagicMock()
            mock_orch.run = AsyncMock(side_effect=RuntimeError("timeout"))
            mock_get.return_value = mock_orch

            fn = make_local_execute_fn()
            output, metrics = fn("guidance")

        assert output == ""
        assert "error" in metrics
        assert metrics["local_silicon"] is True

    def test_task_description_appended_to_prompt(self):
        captured_prompts: list[str] = []

        mock_result = MagicMock()
        mock_result.text = "ok"
        mock_result.final_model = "llama3.2-1b-FLM"
        mock_result.primary_model = "llama3.2-1b-FLM"
        mock_result.latency_ms = 10.0
        mock_result.escalation_count = 0
        mock_result.cost_usd = 0.0

        async def capture_run(prompt):
            captured_prompts.append(prompt)
            return mock_result

        with patch("cohezion.compound.local_inference._get_orchestrator") as mock_get:
            mock_orch = MagicMock()
            mock_orch.run = capture_run
            mock_get.return_value = mock_orch

            fn = make_local_execute_fn("my task description")
            fn("some guidance")

        assert "my task description" in captured_prompts[0]
        assert "some guidance" in captured_prompts[0]


# ---------------------------------------------------------------------------
# CompoundExecutor inference_provider integration
# ---------------------------------------------------------------------------


class TestCompoundExecutorInferenceProvider:
    def test_inference_provider_in_init_signature(self):
        from cohezion.compound.executor import CompoundExecutor

        sig = inspect.signature(CompoundExecutor.__init__)
        assert "inference_provider" in sig.parameters

    def test_execute_task_execute_fn_defaults_to_none(self):
        from cohezion.compound.executor import CompoundExecutor

        sig = inspect.signature(CompoundExecutor.execute_task)
        param = sig.parameters["execute_fn"]
        assert param.default is None


# ---------------------------------------------------------------------------
# telegram_notify
# ---------------------------------------------------------------------------


class TestTelegramNotify:
    def test_noop_without_env_vars(self, monkeypatch):
        monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
        monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
        notify("test")  # must not raise

    def test_sends_when_credentials_set(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "fake-token")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "12345")
        with patch("cohezion.compound.telegram_notify.httpx") as mock_httpx:
            mock_httpx.post.return_value = MagicMock()
            notify("hello Cohezion bot")
            assert mock_httpx.post.called
            call_json = mock_httpx.post.call_args[1]["json"]
            assert call_json["text"] == "hello Cohezion bot"

    def test_noop_on_network_error(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "99")
        with patch("cohezion.compound.telegram_notify.httpx") as mock_httpx:
            mock_httpx.post.side_effect = Exception("network error")
            notify("test")  # must not raise

    def test_notify_task_complete_sends_model_info(self, monkeypatch):
        monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "tok")
        monkeypatch.setenv("TELEGRAM_CHAT_ID", "99")
        with patch("cohezion.compound.telegram_notify.httpx") as mock_httpx:
            mock_httpx.post.return_value = MagicMock()
            notify_task_complete("classify sentiment", "llama3.2-1b-FLM", 42.0)
            body = mock_httpx.post.call_args[1]["json"]["text"]
            assert "llama3.2-1b-FLM" in body


# ---------------------------------------------------------------------------
# TokenUsageRecord wiring
# ---------------------------------------------------------------------------


class TestTokenUsageWiring:
    def test_estimate_tokens_proportional(self):
        assert _estimate_tokens("x" * 400) == 100
        assert _estimate_tokens("x" * 40) == 10
        assert _estimate_tokens("") == 1  # minimum 1

    def test_estimate_tokens_short_string(self):
        assert _estimate_tokens("hi") == 1  # < 4 chars → min 1

    def test_is_cloud_model_claude(self):
        assert _is_cloud_model("claude-sonnet-4-6")
        assert _is_cloud_model("claude-haiku-4-5")
        assert _is_cloud_model("claude-opus-4-8")
        assert _is_cloud_model("claude-fable-5")

    def test_is_cloud_model_gemini(self):
        assert _is_cloud_model("gemini-2.5-flash")
        assert _is_cloud_model("gemini-2.0-flash-lite")

    def test_is_cloud_model_local(self):
        assert not _is_cloud_model("llama3.2-1b-FLM")
        assert not _is_cloud_model("gemma-4-e4b-FLM")
        assert not _is_cloud_model("qwen3.5-4b-FLM")
        assert not _is_cloud_model("")

    def test_session_token_record_singleton(self):
        r1 = get_session_token_record()
        r2 = get_session_token_record()
        assert r1 is r2

    def test_session_token_record_is_token_usage_record(self):
        from cohezion.inference.token_budget import TokenUsageRecord

        r = get_session_token_record()
        assert isinstance(r, TokenUsageRecord)

    def test_execute_fn_metrics_include_token_fields(self):
        mock_result = MagicMock()
        mock_result.text = "short answer"
        mock_result.final_model = "llama3.2-1b-FLM"
        mock_result.primary_model = "llama3.2-1b-FLM"
        mock_result.latency_ms = 24.0
        mock_result.escalation_count = 0
        mock_result.cost_usd = 0.0

        with patch("cohezion.compound.local_inference._get_orchestrator") as mock_orch:
            mock_orch.return_value.run = AsyncMock(return_value=mock_result)
            fn = make_local_execute_fn("test task")
            _, metrics = fn("some guidance")

        assert "tokens_input" in metrics
        assert "tokens_output" in metrics
        assert "session_local_tokens" in metrics
        assert "session_cloud_cost_usd" in metrics
        assert "session_cloud_savings_usd" in metrics
        assert metrics["local_silicon"] is True
        assert metrics["tokens_input"] > 0
        assert metrics["tokens_output"] > 0

    def test_execute_fn_cloud_model_sets_local_silicon_false(self):
        mock_result = MagicMock()
        mock_result.text = "cloud response"
        mock_result.final_model = "claude-haiku-4-5"
        mock_result.primary_model = "claude-haiku-4-5"
        mock_result.latency_ms = 500.0
        mock_result.escalation_count = 3
        mock_result.cost_usd = 0.001

        with patch("cohezion.compound.local_inference._get_orchestrator") as mock_orch:
            mock_orch.return_value.run = AsyncMock(return_value=mock_result)
            fn = make_local_execute_fn()
            _, metrics = fn("complex question")

        assert metrics["local_silicon"] is False

    def test_execute_fn_accumulates_session_local_tokens(self):
        r = get_session_token_record()
        before = r.local_tokens

        mock_result = MagicMock()
        mock_result.text = "x" * 80  # ~20 output tokens
        mock_result.final_model = "llama3.2-1b-FLM"
        mock_result.primary_model = "llama3.2-1b-FLM"
        mock_result.latency_ms = 25.0
        mock_result.escalation_count = 0
        mock_result.cost_usd = 0.0

        with patch("cohezion.compound.local_inference._get_orchestrator") as mock_orch:
            mock_orch.return_value.run = AsyncMock(return_value=mock_result)
            fn = make_local_execute_fn("task")
            _, metrics = fn("guidance text here")

        assert r.local_tokens > before
        assert metrics["session_local_tokens"] == r.local_tokens


# NOTE: the durable usage-sink wiring moved OUT of make_local_execute_fn into
# TieredOrchestrator.run (the universal chokepoint that also covers run_batch). Its
# discriminating tests now live in tests/inference/test_orchestrator_usage_logging.py.
# The wrapper retains only the in-memory TokenUsageRecord update (TestTokenUsageWiring).


# ---------------------------------------------------------------------------
# get_recommended_concurrency (exp_NNNN1: adaptive batch sizing)
# ---------------------------------------------------------------------------


class TestGetRecommendedConcurrency:
    def test_returns_int(self):
        with patch("cohezion.compound.local_inference.httpx") as mock_httpx:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"data": [{"id": "m1"}, {"id": "m2"}]}
            mock_httpx.get.return_value = mock_resp
            result = get_recommended_concurrency()
        assert isinstance(result, int)

    def test_light_load_1_model_returns_5(self):
        with patch("cohezion.compound.local_inference.httpx") as mock_httpx:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"data": [{"id": "m1"}]}
            mock_httpx.get.return_value = mock_resp
            result = get_recommended_concurrency()
        assert result == 5

    def test_medium_load_5_models_returns_3(self):
        with patch("cohezion.compound.local_inference.httpx") as mock_httpx:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"data": [{"id": f"m{i}"} for i in range(5)]}
            mock_httpx.get.return_value = mock_resp
            result = get_recommended_concurrency()
        assert result == 3

    def test_heavy_load_13_models_returns_1(self):
        with patch("cohezion.compound.local_inference.httpx") as mock_httpx:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"data": [{"id": f"m{i}"} for i in range(13)]}
            mock_httpx.get.return_value = mock_resp
            result = get_recommended_concurrency()
        assert result == 1

    def test_connection_error_returns_safe_default(self):
        with patch("cohezion.compound.local_inference.httpx") as mock_httpx:
            mock_httpx.get.side_effect = Exception("connection refused")
            result = get_recommended_concurrency()
        assert result == 3  # safe default
