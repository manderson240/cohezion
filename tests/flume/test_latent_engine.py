"""Tests for the LatentEngine — COCONUT, CoE, SoftCoT, Recurrent Depth.

All tests use mocked httpx calls — no live models required.
"""

from __future__ import annotations

import math
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from cohezion.flume.latent_engine import (
    CoconutResult,
    LatentEngine,
    LatentReasoningResult,
    LatentState,
    RecurrentDepthResult,
    _logprob_to_dense,
    _text_to_latent_state,
    coconut_reason,
    coe_self_eval,
    recurrent_depth,
    soft_cot_prefix,
)
from cohezion.inference.distributed_swarm import _complexity_heuristic


def _make(text: str, step: int = 0) -> LatentState:
    """Test helper: create a latent state from text."""
    return _text_to_latent_state(text, step=step)


# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------


class TestLatentState:
    def test_cosine_identical(self):
        s = _text_to_latent_state("hello world", step=0)
        assert s.cosine_similarity(s) == pytest.approx(1.0, abs=1e-5)

    def test_cosine_different(self):
        a = _text_to_latent_state("cats eat fish", step=0)
        b = _text_to_latent_state("quantum entanglement mystery", step=0)
        sim = a.cosine_similarity(b)
        assert 0.0 <= sim < 1.0

    def test_zero_vec_returns_zero(self):
        a = LatentState(dense_vec=np.zeros(256, dtype=np.float32), text="a")
        b = _text_to_latent_state("anything", step=0)
        assert a.cosine_similarity(b) == 0.0


class TestLogprobToDense:
    def test_returns_correct_shape(self):
        top_k = [("hello", -0.5), ("world", -1.2), ("foo", -2.0)]
        vec = _logprob_to_dense(top_k, dim=256)
        assert vec.shape == (256,)

    def test_empty_returns_zeros(self):
        vec = _logprob_to_dense([], dim=256)
        assert np.all(vec == 0.0)

    def test_normalised(self):
        top_k = [("a", -0.1), ("b", -0.2), ("c", -0.3)]
        vec = _logprob_to_dense(top_k, dim=64)
        assert abs(vec.sum() - 1.0) < 1e-5


# ---------------------------------------------------------------------------
# CoE self-evaluation tests
# ---------------------------------------------------------------------------


class TestCoeSelfEval:
    def _make_converging(self, n: int = 4) -> list[LatentState]:
        """Smoothly converging states: each step moves slightly toward a fixed point."""
        target = np.random.rand(256).astype(np.float32)
        target /= np.linalg.norm(target)
        states = []
        for i in range(n):
            alpha = 0.3 * math.exp(-i * 0.5)  # exponentially decreasing perturbation
            vec = target + alpha * np.random.rand(256).astype(np.float32)
            vec /= np.linalg.norm(vec)
            states.append(LatentState(dense_vec=vec, text=f"step {i}"))
        return states

    def _make_drifting(self, n: int = 4) -> list[LatentState]:
        """Wildly drifting states (random each step)."""
        states = []
        for i in range(n):
            vec = np.random.rand(256).astype(np.float32)
            vec /= np.linalg.norm(vec)
            states.append(LatentState(dense_vec=vec, text=f"step {i}"))
        return states

    def test_too_few_states(self):
        result = coe_self_eval([_text_to_latent_state("x")])
        assert result["confidence"] == 0.5
        assert "Too few" in result["trajectory_summary"]

    def test_converging_high_confidence(self):
        states = self._make_converging()
        result = coe_self_eval(states, drift_threshold=0.15)
        assert result["confidence"] > 0.5

    def test_drifting_flags_drift_events(self):
        states = self._make_drifting(n=5)
        result = coe_self_eval(states, drift_threshold=0.05)
        assert result["drift_events"] >= 1

    def test_single_abrupt_jump(self):
        """One abrupt shift between identical sequences should be flagged."""
        converging = self._make_converging(3)
        wildly_diff = _make("totally unrelated concept", step=3)
        # Insert a big jump at position 2
        converging.append(wildly_diff)
        result = coe_self_eval(converging, drift_threshold=0.1)
        # max_drift should be high
        assert result["max_drift"] > 0.05


# ---------------------------------------------------------------------------
# Complexity heuristic tests
# ---------------------------------------------------------------------------


class TestComplexityHeuristic:
    def test_simple_returns_low(self):
        score = _complexity_heuristic("Hello!")
        assert score < 0.3

    def test_reasoning_keyword_raises_score(self):
        score = _complexity_heuristic("Please prove that the square root of 2 is irrational.")
        assert score >= 0.3

    def test_long_technical_prompt_high(self):
        long_prompt = (
            "Design and implement a distributed consensus algorithm using RAFT, "
            "then analyze its complexity and compare it with Paxos. "
            "Provide step by step reasoning and prove termination. "
            "Why does it work under Byzantine failures? Evaluate tradeoffs." * 2
        )
        score = _complexity_heuristic(long_prompt)
        assert score >= 0.5

    def test_code_block_raises_score(self):
        code_prompt = "```python\ndef foo(): pass\n```\nExplain this."
        no_code = "Explain foo."
        assert _complexity_heuristic(code_prompt) > _complexity_heuristic(no_code)


# ---------------------------------------------------------------------------
# SoftCoT prefix tests (mocked HTTP)
# ---------------------------------------------------------------------------


class TestSoftCotPrefix:
    @pytest.mark.asyncio
    async def test_returns_prefix_on_success(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value={"response": "Key idea: proof by contradiction."})

        with patch("cohezion.flume.latent_engine.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_client_cls.return_value = mock_client

            prefix = await soft_cot_prefix("Prove √2 is irrational", small_model="qwen3:1.7b")

        assert "SoftCoT" in prefix
        assert "contradiction" in prefix

    @pytest.mark.asyncio
    async def test_empty_on_failure(self):
        with patch(
            "cohezion.flume.latent_engine.httpx.AsyncClient",
            side_effect=Exception("connection refused"),
        ):
            prefix = await soft_cot_prefix("Some task", small_model="qwen3:1.7b")

        assert prefix == ""


# ---------------------------------------------------------------------------
# COCONUT reasoning tests (mocked HTTP)
# ---------------------------------------------------------------------------


class TestCoconutReason:
    @pytest.mark.asyncio
    async def test_returns_coconut_result(self):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(
            return_value={
                "response": "The answer involves inductive reasoning applied to natural numbers."
            }
        )

        with patch("cohezion.flume.latent_engine.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = mock_client

            result = await coconut_reason(
                "What is induction?", model="phi4-mini", max_rounds=2, bfs_width=1
            )

        assert isinstance(result, CoconutResult)
        assert result.final_answer != ""
        assert result.bfs_explored >= 1
        assert result.latency_ms > 0

    @pytest.mark.asyncio
    async def test_all_branches_fail_returns_empty(self):
        with patch(
            "cohezion.flume.latent_engine.httpx.AsyncClient",
            side_effect=Exception("down"),
        ):
            result = await coconut_reason("Test", model="phi4-mini", max_rounds=1, bfs_width=1)

        # Should not raise; final_answer may be empty
        assert isinstance(result, CoconutResult)
        assert True  # graceful fallback


# ---------------------------------------------------------------------------
# RecurrentDepth tests (mocked HTTP)
# ---------------------------------------------------------------------------


class TestRecurrentDepth:
    @pytest.mark.asyncio
    async def test_returns_result(self):
        responses = [
            "Initial answer.",
            "Improved answer with more detail.",
            "Final refined answer.",
        ]
        call_count = 0

        def make_response():
            nonlocal call_count
            text = responses[min(call_count, len(responses) - 1)]
            call_count += 1
            mock = MagicMock()
            mock.raise_for_status = MagicMock()
            mock.json = MagicMock(return_value={"response": text})
            return mock

        with patch("cohezion.flume.latent_engine.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(side_effect=lambda *a, **kw: make_response())
            mock_cls.return_value = mock_client

            result = await recurrent_depth("Explain recursion", model="phi4-mini", max_depth=3)

        assert isinstance(result, RecurrentDepthResult)
        assert result.depth_reached >= 1
        assert result.final_answer != ""


# ---------------------------------------------------------------------------
# LatentEngine integration tests
# ---------------------------------------------------------------------------


class TestLatentEngine:
    @pytest.mark.asyncio
    async def test_reason_returns_result(self):
        engine = LatentEngine(small_model="qwen3:1.7b", medium_model="phi4-mini")

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(
            return_value={
                "response": "Entropy measures disorder in a system according to thermodynamics."
            }
        )

        with patch("cohezion.flume.latent_engine.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = mock_client

            result = await engine.reason(
                "What is entropy?",
                use_soft_cot=True,
                use_coconut=True,
                use_recurrent=False,
                max_tokens=128,
            )

        assert isinstance(result, LatentReasoningResult)
        assert result.final_answer != ""
        assert 0.0 <= result.confidence <= 1.0
        assert result.coe_assessment is not None

    @pytest.mark.asyncio
    async def test_reason_no_coconut_fallback(self):
        """With use_coconut=False, falls back to direct inference."""
        engine = LatentEngine()

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json = MagicMock(return_value={"response": "Direct answer."})

        with patch("cohezion.flume.latent_engine.httpx.AsyncClient") as mock_cls:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_resp)
            mock_cls.return_value = mock_client

            result = await engine.reason("Hello?", use_soft_cot=False, use_coconut=False)

        assert result.coconut_bfs_explored == 0
        assert result.final_answer == "Direct answer."
