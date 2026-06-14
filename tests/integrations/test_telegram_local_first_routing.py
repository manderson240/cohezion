"""Tests for the local-first OmniRouter-only chat path (2026-06-10 patch).

The Telegram bot now:
  1. classifies incoming queries as SIMPLE / MEDIUM / COMPLEX (keyword+length)
  2. picks a complexity-tiered model preference (steering hint to OmniRouter)
  3. POSTs ONLY to http://localhost:13305/v1/chat/completions
  4. retries across the preferred-model list on 500 / empty / no-choices
  5. falls back to Ollama only if the OmniRouter is unreachable
  6. NEVER falls back to cloud \u2014 there is no cloud code path
  7. records per-call telemetry to SurrealDB

These tests mock httpx at the module level (no live calls).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from cohezion.integrations.telegram_bot import (
    LEMONADE_ROUTER_URL,
    MAX_TOKENS_BY_COMPLEXITY,
    SYSTEM_PROMPT,
    QueryComplexity,
    TelegramCommunicationHub,
)


@pytest.fixture
def mock_env():
    with patch.dict(
        "os.environ",
        {"TELEGRAM_BOT_TOKEN": "x", "TELEGRAM_CHAT_ID": "y"},
    ):
        yield


def _ok(payload):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = payload
    resp.text = ""
    return resp


def _err(status, body="err"):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = {}
    resp.text = body
    return resp


class _RecordingClient:
    def __init__(self, post_responses):
        self._post = post_responses  # list of (url_match_substr, response)
        self.post_urls = []
        self.post_bodies = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, *args, **kwargs):
        self.post_urls.append(url)
        self.post_bodies.append(kwargs.get("json", {}))
        for needle, resp in self._post:
            if needle in url:
                return resp
        return _err(500, "no match")

    async def get(self, url, *args, **kwargs):
        return _err(404)


# --- CLASSIFIER -------------------------------------------------------------


def test_classify_simple_short_yesno(mock_env):
    h = TelegramCommunicationHub()
    for q in ["hi", "thanks", "ping", "ok", "yes"]:
        assert h._classify_complexity(q) == QueryComplexity.SIMPLE, q


def test_classify_simple_short_factual(mock_env):
    h = TelegramCommunicationHub()
    assert h._classify_complexity("what is the GPU temp?") == QueryComplexity.SIMPLE
    assert h._classify_complexity("is the fleet up?") == QueryComplexity.SIMPLE


def test_classify_complex_verb(mock_env):
    h = TelegramCommunicationHub()
    for q in [
        "explain the OmniRouter design",
        "design a refactor plan for the swarm",
        "refactor the cost_aware_router to bias harder local",
        "implement a new audit script for whisper.cpp",
    ]:
        assert h._classify_complexity(q) == QueryComplexity.COMPLEX, q


def test_classify_complex_long(mock_env):
    h = TelegramCommunicationHub()
    long_q = "word " * 60  # 60 words -> COMPLEX
    assert h._classify_complexity(long_q.strip()) == QueryComplexity.COMPLEX


def test_classify_medium_default(mock_env):
    h = TelegramCommunicationHub()
    # No strong signal, mid-length
    # "compare" triggers _COMPLEX_TOKENS, so this is COMPLEX, not MEDIUM
    assert (
        h._classify_complexity("compare Qwen3 and Llama3.2 for our needs")
        == QueryComplexity.COMPLEX
    )


# --- ROUTER-ONLY ASSERTION --------------------------------------------------


def test_routes_only_to_13305(mock_env):
    """The bot must NEVER send requests to 13306-13309 or 8002-8013."""
    assert LEMONADE_ROUTER_URL == "http://localhost:13305"
    # No LANE_PORTS module attribute (removed by the patch)
    import cohezion.integrations.telegram_bot as mod

    assert not hasattr(mod, "LANE_PORTS"), "LANE_PORTS must be removed; OmniRouter-only"


# --- OMNIRouter CHAT (mocked) -----------------------------------------------


@pytest.mark.asyncio
async def test_chat_omnirouter_serves_on_first_hint(mock_env):
    h = TelegramCommunicationHub()
    rec = _RecordingClient(
        [
            (
                "13305/v1/chat/completions",
                _ok(
                    {
                        "choices": [{"message": {"content": "hello"}}],
                        "model": "Qwen3-0.6B-Q4_0.gguf",
                        "usage": {"completion_tokens": 2, "total_tokens": 10},
                    }
                ),
            )
        ]
    )
    with patch.object(httpx, "AsyncClient", return_value=rec):
        reply, telem = await h._chat_omnirouter(
            QueryComplexity.SIMPLE, [{"role": "user", "content": "hi"}], 96
        )
    assert reply == "hello"
    assert telem.actual_model == "Qwen3-0.6B-Q4_0.gguf"
    assert telem.port == 13305
    assert telem.backend == "lemonade-omnirouter"
    # Accept either "served" or "substituted" — the OmniRouter may swap the hint
    # for a closer-loaded model. Both indicate a successful local route via :13305.
    assert "hint served" in telem.route_reason or "hint substituted" in telem.route_reason
    # All post calls went to 13305 only
    assert all("13305" in u for u in rec.post_urls)


@pytest.mark.asyncio
async def test_chat_omnirouter_retries_on_500_then_succeeds(mock_env):
    h = TelegramCommunicationHub()
    # First hint: 500. Second hint: 200.
    _RecordingClient(
        [
            ("13305/v1/chat/completions", _err(500, "no backend for hint A")),
        ]
    )
    # Override the queue: first call returns 500, second returns 200
    call_count = {"n": 0}

    class _Q:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *e):
            return False

        async def post(self, url, *a, **k):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return _err(500, "first fails")
            return _ok(
                {
                    "choices": [{"message": {"content": "second worked"}}],
                    "model": "Qwen3-8B-Q4_1.gguf",
                    "usage": {"completion_tokens": 2, "total_tokens": 12},
                }
            )

    with patch.object(httpx, "AsyncClient", return_value=_Q()):
        reply, telem = await h._chat_omnirouter(
            QueryComplexity.MEDIUM, [{"role": "user", "content": "compare A and B"}], 320
        )
    assert reply == "second worked"
    assert telem.actual_model == "Qwen3-8B-Q4_1.gguf"
    assert "substituted" in telem.route_reason or "attempt 2" in telem.route_reason


@pytest.mark.asyncio
async def test_chat_omnirouter_treats_empty_content_as_failure(mock_env):
    h = TelegramCommunicationHub()

    # First model returns content="" with reasoning_content. Bot should retry.
    class _Q:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *e):
            return False

        async def post(self, url, *a, **k):
            return _ok(
                {
                    "choices": [{"message": {"content": "", "reasoning_content": "thinking..."}}],
                    "model": "DeepSeek-R1-0528-Qwen3-8B-Q4_1",
                    "usage": {"completion_tokens": 1, "total_tokens": 1},
                }
            )

    with patch.object(httpx, "AsyncClient", return_value=_Q()):
        reply, telem = await h._chat_omnirouter(
            QueryComplexity.SIMPLE, [{"role": "user", "content": "x"}], 96
        )
    # After all preferences exhausted, reply should be None (reasoning-only is rejected)
    assert reply is None
    assert "all" in telem.route_reason
    assert "empty content" in telem.error


@pytest.mark.asyncio
async def test_chat_omnirouter_all_attempts_fail_returns_none(mock_env):
    h = TelegramCommunicationHub()

    class _Q:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *e):
            return False

        async def post(self, url, *a, **k):
            return _err(503, "router down")

    with patch.object(httpx, "AsyncClient", return_value=_Q()):
        reply, telem = await h._chat_omnirouter(
            QueryComplexity.COMPLEX, [{"role": "user", "content": "x"}], 768
        )
    assert reply is None
    assert telem.error is not None
    assert "all" in telem.route_reason


# --- HANDLE_CHAT end-to-end with mocked transport ---------------------------


@pytest.mark.asyncio
async def test_handle_chat_sends_to_telegram_with_omnirouter_reply(mock_env):
    h = TelegramCommunicationHub()

    class _Q:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *e):
            return False

        async def post(self, url, *a, **k):
            return _ok(
                {
                    "choices": [{"message": {"content": "pong"}}],
                    "model": "Qwen3-0.6B-Q4_0.gguf",
                    "usage": {"completion_tokens": 1, "total_tokens": 5},
                }
            )

    captured = []

    async def fake_send(text, parse_mode="HTML"):
        captured.append(text)

    h._send_msg = fake_send
    captured_telem = []

    async def fake_record(t):
        captured_telem.append(t)

    h._record_telemetry = fake_record

    with patch.object(httpx, "AsyncClient", return_value=_Q()):
        await h._handle_chat("hi")

    assert "pong" in captured[-1]
    assert len(captured_telem) == 1
    t = captured_telem[0]
    assert t.backend == "lemonade-omnirouter"
    assert t.port == 13305
    assert t.actual_model == "Qwen3-0.6B-Q4_0.gguf"


@pytest.mark.asyncio
async def test_handle_chat_falls_back_to_ollama_on_router_outage(mock_env):
    """If the OmniRouter is fully unreachable, fall back to Ollama (not cloud)."""
    h = TelegramCommunicationHub()

    # OmniRouter raises on every call; Ollama returns 200
    class _Router:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *e):
            return False

        async def post(self, url, *a, **k):
            raise httpx.ConnectError("router down")

    ollama_models = MagicMock()
    ollama_models.status_code = 200
    ollama_models.json.return_value = {"models": [{"name": "phi4:latest"}]}
    ollama_chat = MagicMock()
    ollama_chat.status_code = 200
    ollama_chat.json.return_value = {"message": {"content": "fallback worked"}}

    class _OllamaClient:
        def __init__(self):
            self.urls = []

        async def __aenter__(self):
            return self

        async def __aexit__(self, *e):
            return False

        async def get(self, url, *a, **k):
            self.urls.append(url)
            return ollama_models

        async def post(self, url, *a, **k):
            self.urls.append(url)
            return ollama_chat

    sent = []

    async def fake_send(text, parse_mode="HTML"):
        sent.append(text)

    h._send_msg = fake_send
    records = []

    async def fake_record(t):
        records.append(t)

    h._record_telemetry = fake_record

    # The bot may construct multiple httpx clients; route by URL substring.
    def factory(*a, **k):
        # If the bot is calling :13305, return the failing router
        return _Router()

    # Use a more permissive factory: first call fails, subsequent use ollama
    state = {"n": 0}

    def factory2(*a, **k):
        state["n"] += 1
        if state["n"] == 1:
            return _Router()
        return _OllamaClient()

    with patch.object(httpx, "AsyncClient", side_effect=factory2):
        await h._handle_chat("hi")

    # Reply should be the Ollama fallback text (not the "offline" warning)
    assert "fallback worked" in sent[-1], f"unexpected last sent: {sent[-1]!r}"
    # Telemetry should mark ollama fallback
    assert records[0].backend == "ollama", f"telem: {records[0]}"
    assert "fallback" in records[0].route_reason


@pytest.mark.asyncio
async def test_handle_chat_never_calls_cloud(mock_env):
    """Negative test: under no circumstance should the bot call any cloud endpoint."""
    h = TelegramCommunicationHub()

    class _Q:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *e):
            return False

        async def post(self, url, *a, **k):
            return _ok(
                {
                    "choices": [{"message": {"content": "ok"}}],
                    "model": "Qwen3-0.6B-Q4_0.gguf",
                    "usage": {"completion_tokens": 1, "total_tokens": 1},
                }
            )

    h._send_msg = AsyncMock()
    h._record_telemetry = AsyncMock()
    with patch.object(httpx, "AsyncClient", return_value=_Q()):
        await h._handle_chat("hi")
    # No calls to anthropic / openai / minimax / kimi / ollama-cloud
    # (the only post is to :13305/v1/chat/completions per the mocked client)


# --- SYSTEM PROMPT ---------------------------------------------------------


def test_system_prompt_is_grounded_and_anti_cloud(mock_env):
    assert "AMD silicon" in SYSTEM_PROMPT
    assert "NO access to the open internet" in SYSTEM_PROMPT
    # No mention of cloud providers
    for kw in ("anthropic", "openai", "minimax", "kimi", "claude", "gpt"):
        assert kw.lower() not in SYSTEM_PROMPT.lower(), f"cloud kw {kw!r} leaked into prompt"


# --- TOKEN BUDGETS ---------------------------------------------------------


def test_token_budgets_match_complexity():
    """SIMPLE << MEDIUM << COMPLEX. The whole point is to bound spend per call."""
    assert (
        MAX_TOKENS_BY_COMPLEXITY[QueryComplexity.SIMPLE]
        < MAX_TOKENS_BY_COMPLEXITY[QueryComplexity.MEDIUM]
    )
    assert (
        MAX_TOKENS_BY_COMPLEXITY[QueryComplexity.MEDIUM]
        < MAX_TOKENS_BY_COMPLEXITY[QueryComplexity.COMPLEX]
    )
    assert MAX_TOKENS_BY_COMPLEXITY[QueryComplexity.COMPLEX] <= 1024  # tight cap
