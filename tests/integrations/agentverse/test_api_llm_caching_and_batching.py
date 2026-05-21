"""Dogfood tests for prompt-caching and Message Batches in APILLMExecutor.

Covers:
  - Cache-aware cost calculation (read 0.10×, write 1.25×, normal 1.0×)
  - APIResult carries cache_read_tokens / cache_write_tokens from response usage
  - batch_submit builds correct JSONL payload with cache_control on system prompts
  - batch_poll parses JSONL result stream and applies per-result cache costs
  - batch_poll returns None when batch is still processing
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.integrations.agentverse.api_llm_executor import APILLMExecutor, APIResult


# ── helpers ────────────────────────────────────────────────────────────────


def _executor(model: str = "claude-sonnet-4-6") -> APILLMExecutor:
    e = APILLMExecutor(provider="anthropic", model=model)
    e.api_key = "sk-test-fake"
    return e


def _input_rate(model: str = "claude-sonnet-4-6") -> float:
    costs = APILLMExecutor.COSTS["anthropic"]
    return costs[model]["input"] / 1_000_000


def _output_rate(model: str = "claude-sonnet-4-6") -> float:
    costs = APILLMExecutor.COSTS["anthropic"]
    return costs[model]["output"] / 1_000_000


# ── cache cost math ─────────────────────────────────────────────────────────


class TestCacheAwareCost:
    def test_no_cache_matches_old_behaviour(self):
        e = _executor()
        expected = 1000 * _input_rate() + 500 * _output_rate()
        assert abs(e._calculate_cost_with_cache(1000, 500) - expected) < 1e-12

    def test_cache_reads_charged_at_10pct(self):
        e = _executor()
        r = _input_rate()
        cost = e._calculate_cost_with_cache(0, 0, cache_read_tokens=1_000_000)
        assert abs(cost - r * 0.10 * 1_000_000) < 1e-9

    def test_cache_writes_charged_at_125pct(self):
        e = _executor()
        r = _input_rate()
        cost = e._calculate_cost_with_cache(0, 0, cache_write_tokens=1_000_000)
        assert abs(cost - r * 1.25 * 1_000_000) < 1e-9

    def test_mixed_all_four_buckets(self):
        e = _executor()
        r = _input_rate()
        o = _output_rate()
        cost = e._calculate_cost_with_cache(
            input_tokens=500,
            output_tokens=200,
            cache_read_tokens=800,
            cache_write_tokens=300,
        )
        expected = 500 * r + 800 * r * 0.10 + 300 * r * 1.25 + 200 * o
        assert abs(cost - expected) < 1e-12

    def test_all_cache_reads_is_cheaper_than_all_normal_input(self):
        e = _executor()
        normal = e._calculate_cost_with_cache(1000, 0)
        cached_read = e._calculate_cost_with_cache(0, 0, cache_read_tokens=1000)
        assert cached_read < normal

    def test_legacy_calculate_cost_delegates(self):
        e = _executor()
        assert e._calculate_cost(100, 50) == e._calculate_cost_with_cache(100, 50)


# ── _execute_anthropic picks up cache fields ─────────────────────────────────


class TestExecuteAnthropicCacheStats:
    @pytest.mark.asyncio
    async def test_cache_tokens_propagate_to_result(self):
        e = _executor()

        mock_response_data = {
            "content": [{"text": "hello"}],
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "cache_read_input_tokens": 900,
                "cache_write_input_tokens": 200,
            },
        }

        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response_data
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await e._execute_anthropic("hi", "sys", 128, 0.5)

        assert isinstance(result, APIResult)
        assert result.success
        assert result.cache_read_tokens == 900
        assert result.cache_write_tokens == 200
        assert result.output == "hello"

    @pytest.mark.asyncio
    async def test_cost_reflects_cache_savings(self):
        e = _executor()

        mock_response_data = {
            "content": [{"text": "ok"}],
            "usage": {
                "input_tokens": 0,
                "output_tokens": 10,
                "cache_read_input_tokens": 2000,
                "cache_write_input_tokens": 0,
            },
        }

        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response_data
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await e._execute_anthropic("hi", None, 128, 0.5)

        # 2000 cache reads at 0.10× should be far cheaper than 2000 normal tokens
        full_price = e._calculate_cost_with_cache(2000, 10)
        assert result.cost_usd < full_price

    @pytest.mark.asyncio
    async def test_system_prompt_has_cache_control(self):
        e = _executor()

        mock_response_data = {
            "content": [{"text": "ok"}],
            "usage": {"input_tokens": 10, "output_tokens": 5},
        }

        mock_resp = MagicMock()
        mock_resp.json.return_value = mock_response_data
        mock_resp.raise_for_status = MagicMock()

        captured_payload: dict = {}

        async def capture_post(url, headers, json):
            captured_payload.update(json)
            return mock_resp

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=capture_post)

        with patch("httpx.AsyncClient", return_value=mock_client):
            await e._execute_anthropic("hi", "You are helpful.", 128, 0.5)

        system_block = captured_payload["system"][0]
        assert system_block["cache_control"] == {"type": "ephemeral"}
        assert system_block["text"] == "You are helpful."


# ── batch_submit ──────────────────────────────────────────────────────────────


class TestBatchSubmit:
    @pytest.mark.asyncio
    async def test_returns_batch_id(self):
        e = _executor()

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "batch_abc123"}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            batch_id = await e.batch_submit(
                [
                    {"custom_id": "r1", "prompt": "Say hello", "system": "Be brief."},
                ]
            )

        assert batch_id == "batch_abc123"

    @pytest.mark.asyncio
    async def test_system_gets_cache_control(self):
        e = _executor()

        captured: list[dict] = []

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"id": "batch_xyz"}
        mock_resp.raise_for_status = MagicMock()

        async def capture_post(url, headers, json):
            captured.append(json)
            return mock_resp

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(side_effect=capture_post)

        with patch("httpx.AsyncClient", return_value=mock_client):
            await e.batch_submit(
                [
                    {"custom_id": "r1", "prompt": "hello", "system": "You are helpful."},
                    {"custom_id": "r2", "prompt": "world"},  # no system
                ]
            )

        requests = captured[0]["requests"]
        r1 = next(r for r in requests if r["custom_id"] == "r1")
        r2 = next(r for r in requests if r["custom_id"] == "r2")

        assert r1["params"]["system"][0]["cache_control"] == {"type": "ephemeral"}
        assert "system" not in r2["params"]

    @pytest.mark.asyncio
    async def test_raises_for_non_anthropic_provider(self):
        e = APILLMExecutor(provider="openai")
        e.api_key = "sk-test"
        with pytest.raises(ValueError, match="batch_submit only supports"):
            await e.batch_submit([{"custom_id": "r1", "prompt": "hi"}])


# ── batch_poll ────────────────────────────────────────────────────────────────


class TestBatchPoll:
    def _jsonl(self, items: list[dict]) -> str:
        return "\n".join(json.dumps(i) for i in items)

    @pytest.mark.asyncio
    async def test_returns_none_while_processing(self):
        e = _executor()

        status_resp = MagicMock()
        status_resp.json.return_value = {"processing_status": "processing"}
        status_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(return_value=status_resp)

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await e.batch_poll("batch_xyz")

        assert result is None

    @pytest.mark.asyncio
    async def test_parses_succeeded_results_with_cache_tokens(self):
        e = _executor()

        jsonl_lines = self._jsonl(
            [
                {
                    "custom_id": "r1",
                    "result": {
                        "type": "succeeded",
                        "message": {
                            "content": [{"text": "answer one"}],
                            "usage": {
                                "input_tokens": 100,
                                "output_tokens": 40,
                                "cache_read_input_tokens": 500,
                                "cache_write_input_tokens": 100,
                            },
                        },
                    },
                },
                {
                    "custom_id": "r2",
                    "result": {
                        "type": "succeeded",
                        "message": {
                            "content": [{"text": "answer two"}],
                            "usage": {
                                "input_tokens": 80,
                                "output_tokens": 20,
                                "cache_read_input_tokens": 0,
                                "cache_write_input_tokens": 0,
                            },
                        },
                    },
                },
            ]
        )

        status_resp = MagicMock()
        status_resp.json.return_value = {"processing_status": "ended"}
        status_resp.raise_for_status = MagicMock()

        results_resp = MagicMock()
        results_resp.text = jsonl_lines
        results_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(side_effect=[status_resp, results_resp])

        with patch("httpx.AsyncClient", return_value=mock_client):
            results = await e.batch_poll("batch_xyz")

        assert results is not None
        assert len(results) == 2

        r1 = next(r for r in results if r["custom_id"] == "r1")
        assert r1["success"]
        assert r1["output"] == "answer one"
        assert r1["cache_read_tokens"] == 500
        assert r1["cache_write_tokens"] == 100

        # cache reads at 0.10× should lower the cost vs all-normal-input
        full_cost = e._calculate_cost_with_cache(100 + 500, 40)
        assert r1["cost_usd"] < full_cost

    @pytest.mark.asyncio
    async def test_handles_errored_result(self):
        e = _executor()

        jsonl_lines = self._jsonl(
            [
                {
                    "custom_id": "r1",
                    "result": {
                        "type": "errored",
                        "error": {"message": "overloaded"},
                    },
                },
            ]
        )

        status_resp = MagicMock()
        status_resp.json.return_value = {"processing_status": "ended"}
        status_resp.raise_for_status = MagicMock()

        results_resp = MagicMock()
        results_resp.text = jsonl_lines
        results_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get = AsyncMock(side_effect=[status_resp, results_resp])

        with patch("httpx.AsyncClient", return_value=mock_client):
            results = await e.batch_poll("batch_xyz")

        assert results is not None
        r1 = results[0]
        assert not r1["success"]
        assert "overloaded" in r1["error"]
        assert r1["cost_usd"] == 0.0
        assert r1["cache_read_tokens"] == 0

    @pytest.mark.asyncio
    async def test_raises_for_non_anthropic_provider(self):
        e = APILLMExecutor(provider="openai")
        e.api_key = "sk-test"
        with pytest.raises(ValueError, match="batch_poll only supports"):
            await e.batch_poll("batch_xyz")


# ── batch_execute (submit + poll loop) ─────────────────────────────────────


class TestBatchExecute:
    """APILLMExecutor.batch_execute: submit → poll loop → return APIResult list."""

    @pytest.mark.asyncio
    async def test_returns_on_first_completed_poll(self):
        e = _executor()

        submit_resp = MagicMock()
        submit_resp.json.return_value = {"id": "batch_loop1"}
        submit_resp.raise_for_status = MagicMock()

        # First poll: still processing. Second poll: ended.
        processing_resp = MagicMock()
        processing_resp.json.return_value = {"processing_status": "processing"}
        processing_resp.raise_for_status = MagicMock()

        ended_resp = MagicMock()
        ended_resp.json.return_value = {"processing_status": "ended"}
        ended_resp.raise_for_status = MagicMock()

        import json as _json

        results_line = _json.dumps(
            {
                "custom_id": "r1",
                "result": {
                    "type": "succeeded",
                    "message": {
                        "content": [{"text": "done"}],
                        "usage": {"input_tokens": 10, "output_tokens": 5},
                    },
                },
            }
        )
        results_resp = MagicMock()
        results_resp.text = results_line
        results_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=submit_resp)
        mock_client.get = AsyncMock(
            side_effect=[
                processing_resp,  # first batch_poll → None
                ended_resp,  # second batch_poll status
                results_resp,  # second batch_poll results
            ]
        )

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            results = await e.batch_execute(
                [{"custom_id": "r1", "prompt": "hello"}],
                poll_interval_s=0.01,
            )

        assert len(results) == 1
        assert results[0]["success"]
        assert results[0]["output"] == "done"

    @pytest.mark.asyncio
    async def test_raises_timeout_when_never_ends(self):
        e = _executor()

        submit_resp = MagicMock()
        submit_resp.json.return_value = {"id": "batch_timeout"}
        submit_resp.raise_for_status = MagicMock()

        processing_resp = MagicMock()
        processing_resp.json.return_value = {"processing_status": "processing"}
        processing_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=submit_resp)
        mock_client.get = AsyncMock(return_value=processing_resp)

        with (
            patch("httpx.AsyncClient", return_value=mock_client),
            patch("asyncio.sleep", new_callable=AsyncMock),
        ):
            with pytest.raises(TimeoutError):
                await e.batch_execute(
                    [{"custom_id": "r1", "prompt": "hello"}],
                    poll_interval_s=0.01,
                    max_wait_s=0.02,  # tiny window → guaranteed timeout
                )


# ── HybridExecutor.batch_execute ────────────────────────────────────────────


class TestHybridBatchExecute:
    @pytest.mark.asyncio
    async def test_anthropic_routes_to_api_batch_execute(self):
        from cohezion.integrations.agentverse.api_llm_executor import HybridExecutor

        api = _executor()
        hybrid = HybridExecutor(api_executor=api)
        assert hybrid.api.provider == "anthropic"

        expected = [
            {
                "custom_id": "r1",
                "success": True,
                "output": "hi",
                "tokens_used": 5,
                "cost_usd": 0.0,
                "cache_read_tokens": 0,
                "cache_write_tokens": 0,
                "error": None,
            }
        ]

        with patch.object(api, "batch_execute", new=AsyncMock(return_value=expected)):
            results = await hybrid.batch_execute([{"custom_id": "r1", "prompt": "hello"}])

        assert len(results) == 1
        # HybridExecutor wraps raw dicts into APIResult
        from cohezion.integrations.agentverse.api_llm_executor import APIResult

        assert isinstance(results[0], APIResult)
        assert results[0].output == "hi"

    @pytest.mark.asyncio
    async def test_non_anthropic_uses_gather(self):
        from cohezion.integrations.agentverse.api_llm_executor import HybridExecutor

        api = APILLMExecutor(provider="openai")
        api.api_key = "sk-test"
        hybrid = HybridExecutor(api_executor=api)

        call_count = 0

        async def fake_execute(prompt, system=None, max_tokens=1024, temperature=0.7):
            nonlocal call_count
            call_count += 1
            return APIResult(True, f"resp{call_count}", 10.0, 10, 0.0)

        with patch.object(hybrid, "execute", side_effect=fake_execute):
            results = await hybrid.batch_execute(
                [
                    {"custom_id": "a", "prompt": "q1"},
                    {"custom_id": "b", "prompt": "q2"},
                ]
            )

        assert call_count == 2
        assert len(results) == 2


# ── AutoHarnessSynthesizer parallel fast path ───────────────────────────────


class TestAutoHarnessParallelCandidates:
    """Verify the batch_execute fast path in AutoHarnessSynthesizer."""

    def _make_synth(self, batch_results, sequential_fallback="fallback"):
        """Build a synthesizer whose batch_execute returns batch_results."""
        from cohezion.compound.autoharness import AutoHarnessSynthesizer

        class FakeLLM:
            async def batch_execute(self, requests):
                return [
                    type("R", (), {"output": r, "cache_read_tokens": 0})() for r in batch_results
                ]

            async def execute_task(self, task, skill):
                return type("R", (), {"output": sequential_fallback})()

        return AutoHarnessSynthesizer(FakeLLM(), max_iterations=2, initial_candidates=3)

    @pytest.mark.asyncio
    async def test_returns_first_passing_candidate_without_sequential(self):
        from cohezion.compound.autoharness import AutoHarnessSynthesizer

        call_log = []

        class FakeLLM:
            async def batch_execute(self, requests):
                call_log.append("batch")
                # First candidate fails, second passes
                return [
                    type(
                        "R",
                        (),
                        {"output": "def verify_action(s,a): return False", "cache_read_tokens": 0},
                    )(),
                    type(
                        "R",
                        (),
                        {"output": "def verify_action(s,a): return True", "cache_read_tokens": 0},
                    )(),
                    type(
                        "R",
                        (),
                        {"output": "def verify_action(s,a): return False", "cache_read_tokens": 0},
                    )(),
                ]

            async def execute_task(self, task, skill):
                call_log.append("sequential")
                return type("R", (), {"output": "def verify_action(s,a): return False"})()

        synth = AutoHarnessSynthesizer(FakeLLM(), max_iterations=5, initial_candidates=3)

        def dummy_env(code):
            return "return True" in code, "expected True"

        result = await synth.synthesize_verifier("check something", dummy_env)

        assert "return True" in result
        assert "batch" in call_log
        assert "sequential" not in call_log, "sequential should not run when batch succeeds"

    @pytest.mark.asyncio
    async def test_falls_through_to_sequential_when_all_candidates_fail(self):
        from cohezion.compound.autoharness import AutoHarnessSynthesizer

        call_log = []

        class FakeLLM:
            async def batch_execute(self, requests):
                call_log.append("batch")
                return [
                    type(
                        "R",
                        (),
                        {"output": "def verify_action(s,a): return False", "cache_read_tokens": 0},
                    )()
                    for _ in requests
                ]

            async def execute_task(self, task, skill):
                call_log.append("sequential")
                return type("R", (), {"output": "def verify_action(s,a): return True"})()

        synth = AutoHarnessSynthesizer(FakeLLM(), max_iterations=1, initial_candidates=2)

        def dummy_env(code):
            return "return True" in code, "expected True"

        result = await synth.synthesize_verifier("check something", dummy_env)

        assert "batch" in call_log
        assert "sequential" in call_log, "sequential must run as fallback"
        assert "return True" in result

    @pytest.mark.asyncio
    async def test_no_batch_path_when_initial_candidates_equals_one(self):
        from cohezion.compound.autoharness import AutoHarnessSynthesizer

        call_log = []

        class FakeLLM:
            async def batch_execute(self, requests):
                call_log.append("batch")
                return []

            async def execute_task(self, task, skill):
                call_log.append("sequential")
                return type("R", (), {"output": "def verify_action(s,a): return True"})()

        # initial_candidates=1 → no batch even though executor supports it
        synth = AutoHarnessSynthesizer(FakeLLM(), max_iterations=1, initial_candidates=1)

        def dummy_env(code):
            return "return True" in code, ""

        await synth.synthesize_verifier("env", dummy_env)

        assert "batch" not in call_log
        assert "sequential" in call_log
