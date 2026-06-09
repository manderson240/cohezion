"""Tests for cohezion.inference.router_client (Phase 0a gate + Phase 1 R1 fix).

Test matrix:
  1. Leaf-module isolation: importing router_client does NOT pull in any
     cohezion.inference.*, cohezion.swarm.*, or cohezion.compound.* modules.
  2. Response parsing: mock httpx returns OpenAI-shaped completion; verify
     RouterResult fields.
  3. N3 compliance: ctx_size is clamped to ≤16384 regardless of input.
  4. load() POST shape: posts to /api/v1/load with save_options=True and
     correct llamacpp_backend for each backend value.
  5. Label: client.label == "router:<model_id>".
  6. R1 — Ollama options not silently dropped: from_ollama_options() maps
     num_predict/temperature/num_ctx/stop and records unknown keys in
     _dropped_ollama_opts.
  7. Empty completion surfaced as error (not silently swallowed).
  8. base_url normalization: trailing /api/v1 suffix is stripped.
  9. Backend "npu" omits llamacpp_backend from load payload.
 10. FLM-recipe models omit llamacpp_backend regardless of backend value.
 11. R1 wiring fix: stop sequences are sent as "stop" in chat payload.
 12. R1 wiring fix: dropped_options appear in RouterResult.dropped_options.
"""

from __future__ import annotations

import ast
import pathlib
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.inference.router_client import (
    LemonadeRouterClient,
    RouterResult,
    _MAX_CTX_SIZE,
    build_router_cpu_client,
    build_router_igpu_client,
    build_router_npu_client,
)


# ---------------------------------------------------------------------------
# 1. Leaf-module isolation (import cycle guard)
# ---------------------------------------------------------------------------


def test_leaf_module_no_cohezion_imports() -> None:
    """router_client.py must not contain any ``import cohezion.*`` statements.

    The leaf constraint (R4) means the FILE ITSELF has no cohezion imports —
    it does NOT mean that importing it at runtime avoids loading the package
    __init__.py (Python always loads the parent package's __init__ when you
    import any submodule; that behaviour cannot be avoided without namespace
    packages).

    We use AST inspection rather than a runtime sys.modules check because:
    1. AST checks are deterministic and independent of package __init__ side effects.
    2. A future refactor that adds ``from cohezion.inference.x import Y`` to this
       file would be caught immediately, before any circular import manifests at runtime.
    3. This is the authoritative "no cohezion import in source" check that the plan
       refers to as the R4 cycle-safety constraint.
    """
    src_path = pathlib.Path(__file__).parent.parent.parent.parent / "src" / "cohezion" / "inference" / "router_client.py"
    assert src_path.exists(), f"router_client.py not found at {src_path}"

    tree = ast.parse(src_path.read_text())
    cohezion_imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.startswith("cohezion"):
                cohezion_imports.append(f"from {node.module} import ...")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.startswith("cohezion"):
                    cohezion_imports.append(f"import {alias.name}")

    assert cohezion_imports == [], (
        f"router_client.py contains cohezion imports: {cohezion_imports}\n"
        "Violates LEAF constraint (R4) — swarm/providers will import FROM this file, "
        "any cohezion import here creates a cycle."
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _mock_openai_response(content: str) -> MagicMock:
    """Build a minimal mock httpx Response that looks like an OAI completion."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(
        return_value={
            "choices": [{"message": {"content": content}}]
        }
    )
    return resp


def _mock_load_response() -> MagicMock:
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value={"status": "ok"})
    return resp


# ---------------------------------------------------------------------------
# 2. Response parsing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_returns_router_result() -> None:
    client = LemonadeRouterClient(model_id="Gemma-4-E4B-it-GGUF")

    with patch("httpx.AsyncClient") as mock_cls:
        mock_acm = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_acm)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_acm.post = AsyncMock(return_value=_mock_openai_response("hello world"))

        result = await client.run("Say hello")

    assert isinstance(result, RouterResult)
    assert result.text == "hello world"
    assert result.error is None
    assert result.label == "router:Gemma-4-E4B-it-GGUF"
    assert result.latency_ms >= 0.0


@pytest.mark.asyncio
async def test_run_posts_openai_shape() -> None:
    """Verify the JSON payload sent to the router uses OpenAI messages format."""
    client = LemonadeRouterClient(
        model_id="Gemma-4-31B-it-GGUF",
        max_tokens=128,
        temperature=0.5,
    )
    captured_payload: dict[str, Any] = {}

    async def fake_post(url: str, **kwargs: Any) -> MagicMock:
        captured_payload.update(kwargs.get("json", {}))
        return _mock_openai_response("ok")

    with patch("httpx.AsyncClient") as mock_cls:
        mock_acm = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_acm)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_acm.post = fake_post

        await client.run("test prompt")

    assert "messages" in captured_payload, "Payload must use 'messages' key (OpenAI shape)"
    assert isinstance(captured_payload["messages"], list)
    assert captured_payload["messages"][-1]["content"] == "test prompt"
    assert captured_payload["messages"][-1]["role"] == "user"
    assert captured_payload["max_tokens"] == 128
    assert captured_payload["temperature"] == 0.5
    assert "prompt" not in captured_payload, "Must not use flat Ollama 'prompt' key"


# ---------------------------------------------------------------------------
# 3. N3 compliance — ctx_size clamped
# ---------------------------------------------------------------------------


def test_ctx_size_clamped_to_max() -> None:
    """ctx_size must never exceed 16384 (N3 OOM guard)."""
    client = LemonadeRouterClient(model_id="Gemma-4-31B-it-GGUF", ctx_size=999_999)
    assert client.ctx_size == _MAX_CTX_SIZE


def test_ctx_size_clamped_to_min() -> None:
    """ctx_size must be at least 1 (zero would mean unbounded)."""
    client = LemonadeRouterClient(model_id="Gemma-4-31B-it-GGUF", ctx_size=0)
    assert client.ctx_size == 1


def test_ctx_size_valid_value_preserved() -> None:
    client = LemonadeRouterClient(model_id="Gemma-4-31B-it-GGUF", ctx_size=4096)
    assert client.ctx_size == 4096


# ---------------------------------------------------------------------------
# 4. load() POST shape
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_posts_to_correct_url_with_save_options() -> None:
    client = LemonadeRouterClient(
        "http://localhost:13305",
        model_id="Gemma-4-31B-it-GGUF",
        backend="cpu",
        ctx_size=8192,
    )
    captured: dict[str, Any] = {}
    captured_url: list[str] = []

    async def fake_post(url: str, **kwargs: Any) -> MagicMock:
        captured_url.append(url)
        captured.update(kwargs.get("json", {}))
        return _mock_load_response()

    with patch("httpx.AsyncClient") as mock_cls:
        mock_acm = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_acm)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_acm.post = fake_post

        await client.load(save_options=True)

    assert captured_url[0] == "http://localhost:13305/api/v1/load"
    assert captured["model_name"] == "Gemma-4-31B-it-GGUF"
    assert captured["save_options"] is True
    assert captured["ctx_size"] == 8192
    assert captured["llamacpp_backend"] == "cpu"


@pytest.mark.asyncio
async def test_load_idempotent() -> None:
    """Second call to load() must be a no-op (already loaded guard)."""
    client = LemonadeRouterClient(model_id="Gemma-4-31B-it-GGUF", backend="cpu")
    call_count = 0

    async def fake_post(url: str, **kwargs: Any) -> MagicMock:
        nonlocal call_count
        call_count += 1
        return _mock_load_response()

    with patch("httpx.AsyncClient") as mock_cls:
        mock_acm = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_acm)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_acm.post = fake_post

        await client.load()
        await client.load()  # second call must not reach httpx

    assert call_count == 1, "load() must only POST once (idempotent)"


# ---------------------------------------------------------------------------
# 5. Label
# ---------------------------------------------------------------------------


def test_label_format() -> None:
    client = LemonadeRouterClient(model_id="llama3.2-1b-FLM")
    assert client.label == "router:llama3.2-1b-FLM"


# ---------------------------------------------------------------------------
# 6. R1 — Ollama options not silently dropped
# ---------------------------------------------------------------------------


def test_from_ollama_options_maps_num_predict() -> None:
    client = LemonadeRouterClient.from_ollama_options(
        model_id="Gemma-4-E4B-it-GGUF",
        options={"num_predict": 200, "temperature": 0.8},
    )
    assert client.max_tokens == 200
    assert client.temperature == 0.8


def test_from_ollama_options_maps_num_ctx_with_n3_clamp() -> None:
    client = LemonadeRouterClient.from_ollama_options(
        model_id="Gemma-4-31B-it-GGUF",
        options={"num_ctx": 999_999},
    )
    assert client.ctx_size == _MAX_CTX_SIZE


def test_from_ollama_options_records_dropped_options() -> None:
    """Unknown Ollama options must appear in _dropped_ollama_opts — not silently lost."""
    client = LemonadeRouterClient.from_ollama_options(
        model_id="Gemma-4-E4B-it-GGUF",
        options={
            "num_predict": 256,
            "temperature": 0.5,
            "top_k": 40,       # no OpenAI equivalent
            "top_p": 0.9,      # not forwarded by canonical client
            "repeat_penalty": 1.1,  # no OpenAI equivalent
        },
    )
    dropped = client._dropped_ollama_opts
    assert "top_k" in dropped, "top_k must be recorded as dropped"
    assert "top_p" in dropped, "top_p must be recorded as dropped"
    assert "repeat_penalty" in dropped, "repeat_penalty must be recorded as dropped"
    # Known fields must NOT appear in dropped
    assert "num_predict" not in dropped
    assert "temperature" not in dropped


def test_from_ollama_options_stop_sequences_preserved() -> None:
    client = LemonadeRouterClient.from_ollama_options(
        model_id="Gemma-4-E4B-it-GGUF",
        options={"stop": ["<|end|>", "User:"]},
    )
    assert client._stop_sequences == ["<|end|>", "User:"]


def test_from_ollama_options_empty_options() -> None:
    """Constructing from empty options dict must not raise."""
    client = LemonadeRouterClient.from_ollama_options(
        model_id="Gemma-4-E4B-it-GGUF",
        options={},
    )
    assert client.max_tokens == 512   # default
    assert client._dropped_ollama_opts == {}


# ---------------------------------------------------------------------------
# 7. Empty completion surfaced as error (R1)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_completion_sets_error() -> None:
    """An empty response body must set error, not silently return empty text."""
    client = LemonadeRouterClient(model_id="Gemma-4-E4B-it-GGUF")

    with patch("httpx.AsyncClient") as mock_cls:
        mock_acm = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_acm)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_acm.post = AsyncMock(return_value=_mock_openai_response(""))

        result = await client.run("Generate something")

    assert result.text == ""
    assert result.error is not None
    assert "empty" in result.error.lower()


@pytest.mark.asyncio
async def test_http_error_propagated_as_error_field() -> None:
    """HTTP errors must set error field, not raise to caller."""
    client = LemonadeRouterClient(model_id="Gemma-4-E4B-it-GGUF")

    with patch("httpx.AsyncClient") as mock_cls:
        mock_acm = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_acm)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_acm.post = AsyncMock(side_effect=Exception("connection refused"))

        result = await client.run("test")

    assert result.error is not None
    assert "connection refused" in result.error


# ---------------------------------------------------------------------------
# 8. base_url normalization
# ---------------------------------------------------------------------------


def test_base_url_strips_api_v1_suffix() -> None:
    """Callers passing base_url with /api/v1 should get the same client as without."""
    c1 = LemonadeRouterClient("http://localhost:13305", model_id="m")
    c2 = LemonadeRouterClient("http://localhost:13305/api/v1", model_id="m")
    assert c1._chat_url == c2._chat_url
    assert c1._load_url == c2._load_url


def test_base_url_strips_trailing_slash() -> None:
    c = LemonadeRouterClient("http://localhost:13305/", model_id="m")
    assert not c._chat_url.startswith("http://localhost:13305//")


# ---------------------------------------------------------------------------
# 9. Backend "npu" omits llamacpp_backend from load payload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_npu_backend_omits_llamacpp_backend_in_load() -> None:
    client = LemonadeRouterClient(
        model_id="Gemma-4-E2B-it-GGUF",
        backend="npu",
    )
    captured: dict[str, Any] = {}

    async def fake_post(url: str, **kwargs: Any) -> MagicMock:
        captured.update(kwargs.get("json", {}))
        return _mock_load_response()

    with patch("httpx.AsyncClient") as mock_cls:
        mock_acm = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_acm)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_acm.post = fake_post

        await client.load()

    assert "llamacpp_backend" not in captured, (
        "NPU backend must omit llamacpp_backend key — FLM recipe handles selection"
    )


@pytest.mark.asyncio
async def test_auto_backend_omits_llamacpp_backend_in_load() -> None:
    client = LemonadeRouterClient(model_id="Gemma-4-31B-it-GGUF", backend="auto")
    captured: dict[str, Any] = {}

    async def fake_post(url: str, **kwargs: Any) -> MagicMock:
        captured.update(kwargs.get("json", {}))
        return _mock_load_response()

    with patch("httpx.AsyncClient") as mock_cls:
        mock_acm = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_acm)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_acm.post = fake_post

        await client.load()

    assert "llamacpp_backend" not in captured


# ---------------------------------------------------------------------------
# 10. FLM-recipe models omit llamacpp_backend even when backend="cpu"
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_flm_model_omits_llamacpp_backend_regardless_of_backend_param() -> None:
    """FLM models use their own recipe; llamacpp_backend must be omitted."""
    client = LemonadeRouterClient(
        model_id="llama3.2-1b-FLM",
        backend="cpu",  # would normally set llamacpp_backend=cpu, but FLM overrides
    )
    captured: dict[str, Any] = {}

    async def fake_post(url: str, **kwargs: Any) -> MagicMock:
        captured.update(kwargs.get("json", {}))
        return _mock_load_response()

    with patch("httpx.AsyncClient") as mock_cls:
        mock_acm = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_acm)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_acm.post = fake_post

        await client.load()

    assert "llamacpp_backend" not in captured, (
        "FLM-recipe models must never include llamacpp_backend in load payload"
    )


# ---------------------------------------------------------------------------
# Builder helpers
# ---------------------------------------------------------------------------


def test_build_router_cpu_client() -> None:
    c = build_router_cpu_client()
    assert c.backend == "cpu"
    assert c.model_id == "Gemma-4-31B-it-GGUF"
    assert c.ctx_size <= _MAX_CTX_SIZE


def test_build_router_igpu_client() -> None:
    c = build_router_igpu_client()
    assert c.backend == "vulkan"
    assert c.model_id == "Gemma-4-E4B-it-GGUF"


def test_build_router_npu_client() -> None:
    c = build_router_npu_client()
    assert c.backend == "npu"
    assert c.model_id == "llama3.2-1b-FLM"
    assert c.max_tokens == 256


# ---------------------------------------------------------------------------
# /no_think injection for qualifying models
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_think_injected_for_qualifying_models() -> None:
    """Qwen3 models must receive /no_think system message."""
    client = LemonadeRouterClient(model_id="Qwen3-0.6B-GGUF")
    captured_messages: list[dict[str, str]] = []

    async def fake_post(url: str, **kwargs: Any) -> MagicMock:
        captured_messages.extend(kwargs.get("json", {}).get("messages", []))
        return _mock_openai_response("response")

    with patch("httpx.AsyncClient") as mock_cls:
        mock_acm = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_acm)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_acm.post = fake_post

        await client.run("hello")

    assert captured_messages[0] == {"role": "system", "content": "/no_think"}


# ---------------------------------------------------------------------------
# 11. R1 wiring fix: stop sequences sent in chat payload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stop_sequences_forwarded_to_chat_payload() -> None:
    """R1 fix: _stop_sequences set by from_ollama_options must appear as 'stop' in chat payload."""
    client = LemonadeRouterClient.from_ollama_options(
        model_id="Gemma-4-E4B-it-GGUF",
        options={"stop": ["<|end|>", "User:"]},
    )
    captured_payload: dict[str, Any] = {}

    async def fake_post(url: str, **kwargs: Any) -> MagicMock:
        captured_payload.update(kwargs.get("json", {}))
        return _mock_openai_response("ok")

    with patch("httpx.AsyncClient") as mock_cls:
        mock_acm = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_acm)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_acm.post = fake_post

        await client.run("test")

    assert "stop" in captured_payload, (
        "R1 fix: stop sequences must be forwarded in chat payload, not just stored"
    )
    assert captured_payload["stop"] == ["<|end|>", "User:"]


@pytest.mark.asyncio
async def test_no_stop_field_when_no_stop_sequences() -> None:
    """When no stop sequences are set, 'stop' key must not appear in payload."""
    client = LemonadeRouterClient(model_id="Gemma-4-E4B-it-GGUF")
    captured_payload: dict[str, Any] = {}

    async def fake_post(url: str, **kwargs: Any) -> MagicMock:
        captured_payload.update(kwargs.get("json", {}))
        return _mock_openai_response("ok")

    with patch("httpx.AsyncClient") as mock_cls:
        mock_acm = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_acm)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_acm.post = fake_post

        await client.run("test")

    assert "stop" not in captured_payload, (
        "No stop key should appear when _stop_sequences is None"
    )


# ---------------------------------------------------------------------------
# 12. R1 wiring fix: dropped_options in RouterResult
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dropped_options_appear_in_router_result() -> None:
    """R1 fix: dropped Ollama options must appear in RouterResult.dropped_options."""
    client = LemonadeRouterClient.from_ollama_options(
        model_id="Gemma-4-E4B-it-GGUF",
        options={
            "num_predict": 256,
            "top_k": 40,
            "top_p": 0.9,
        },
    )

    with patch("httpx.AsyncClient") as mock_cls:
        mock_acm = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_acm)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_acm.post = AsyncMock(return_value=_mock_openai_response("hello"))

        result = await client.run("test")

    assert "top_k" in result.dropped_options, (
        "R1 fix: top_k must appear in RouterResult.dropped_options"
    )
    assert "top_p" in result.dropped_options, (
        "R1 fix: top_p must appear in RouterResult.dropped_options"
    )
    assert result.dropped_options["top_k"] == 40
    assert result.dropped_options["top_p"] == 0.9


@pytest.mark.asyncio
async def test_dropped_options_empty_for_plain_client() -> None:
    """A client not constructed via from_ollama_options must have empty dropped_options."""
    client = LemonadeRouterClient(model_id="Gemma-4-E4B-it-GGUF")

    with patch("httpx.AsyncClient") as mock_cls:
        mock_acm = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_acm)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_acm.post = AsyncMock(return_value=_mock_openai_response("hi"))

        result = await client.run("test")

    assert result.dropped_options == {}
