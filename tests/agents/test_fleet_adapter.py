"""Tests for cohezion.agents.fleet_adapter.

All live I/O is mocked. We verify task classification, local-only routing,
escalation, and the synchronous CompoundExecutor helper.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from cohezion.agents.fleet_adapter import (
    _classify_task,
    call_local_first,
    get_default_execute_fn,
    run_task_sync,
)
from cohezion.inference import RouteResult
from cohezion.inference.registry import Task


@pytest.mark.asyncio
async def test_call_local_first_returns_local_when_quality_ok():
    local_result = RouteResult(
        text="This is a long enough local answer for the prompt.",
        model="gemma-4-e2b-it-gguf",
        lane="npu",
        latency_ms=12.0,
        error=None,
    )

    with patch("cohezion.agents.fleet_adapter.route", AsyncMock(return_value=local_result)):
        result = await call_local_first("What is Cohezion?")

    assert result["text"] == local_result.text
    assert result["model"] == "gemma-4-e2b-it-gguf"
    assert result["lane"] == "npu"
    assert result["error"] is None
    assert result["escalated_to_cloud"] is False


@pytest.mark.asyncio
async def test_call_local_first_escalates_when_local_short():
    local_result = RouteResult(
        text="short",
        model="gemma-4-e2b-it-gguf",
        lane="npu",
        latency_ms=12.0,
        error=None,
    )
    cloud_result = RouteResult(
        text="A detailed cloud answer that is long enough.",
        model="claude-sonnet-4-6",
        lane="cloud_claude",
        latency_ms=120.0,
        error=None,
    )

    route_mock = AsyncMock(side_effect=[local_result, cloud_result])
    with patch("cohezion.agents.fleet_adapter.route", route_mock):
        result = await call_local_first("Explain quantum computing.")

    assert result["text"] == cloud_result.text
    assert result["model"] == "claude-sonnet-4-6"
    assert result["escalated_to_cloud"] is True


@pytest.mark.asyncio
async def test_call_local_first_no_cloud_fallback():
    local_result = RouteResult(
        text="short",
        model="gemma-4-e2b-it-gguf",
        lane="npu",
        latency_ms=12.0,
        error=None,
    )

    with patch("cohezion.agents.fleet_adapter.route", AsyncMock(return_value=local_result)):
        result = await call_local_first("Explain quantum computing.", allow_cloud_fallback=False)

    assert result["error"] == "local quality gate failed"
    assert result["escalated_to_cloud"] is False


def test_classify_task_heuristics():
    assert _classify_task("def foo(): pass") == Task.CODE_GEN
    assert _classify_task("Why is the sky blue?") == Task.REASONING
    assert _classify_task("Summarize this document") == Task.SUMMARIZATION
    assert _classify_task("Return a JSON schema") == Task.STRUCTURED
    assert _classify_task("Hello") == Task.GENERAL
    assert _classify_task("Write a python function") == Task.GENERAL


def test_run_task_sync_uses_httpx_client():
    response_json = {
        "choices": [{"message": {"content": "sync answer"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 2},
    }
    with patch("httpx.Client") as client_cls:
        client = client_cls.return_value.__enter__.return_value
        client.post.return_value.raise_for_status.return_value = None
        client.post.return_value.json.return_value = response_json

        output, metrics = run_task_sync({"relevant_context": {"task_description": "hi"}})

    assert output == "sync answer"
    assert metrics["model"] == "gemma-4-e2b-it-gguf"
    assert metrics["error"] is None
    assert metrics["tokens_used"] > 0


def test_run_task_sync_handles_timeout():
    with patch("httpx.Client") as client_cls:
        client = client_cls.return_value.__enter__.return_value
        client.post.side_effect = Exception("connection refused")

        output, metrics = run_task_sync({"relevant_context": {"task_description": "hi"}})

    assert output == ""
    assert metrics["error"] is not None


def test_get_default_execute_fn_signature():
    fn = get_default_execute_fn(model="gemma-4-e2b-it-gguf", timeout=10.0, max_tokens=128)
    assert callable(fn)
    with patch(
        "cohezion.agents.fleet_adapter.run_task_sync", return_value=("out", {"m": 1})
    ) as mock:
        out, met = fn({"relevant_context": {"task_description": "hi"}})
    assert out == "out"
    assert met == {"m": 1}
    assert mock.called
