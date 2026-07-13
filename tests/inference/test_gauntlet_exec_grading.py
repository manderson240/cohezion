"""Discriminating tests for the execution-graded gauntlet upgrade (2026-07-13).

Each test fails a plausible WRONG implementation:
  T1 — reasoning model (content="", answer in reasoning_content) is now scored fairly (old: 0).
  T2 — keyword-matching but BROKEN code now fails (old keyword grader: 1.0). T1+T2 prove the
       grader measures behavior, not surface form.
  T3 — endpoint is /api/v1/chat/completions (old: /api/v1/chat → 404 → all-zeros).
  T4 — infinite-loop code fails within timeout, never hangs the gauntlet.
  T5 — inline <think>…</think> is stripped; code after it is extracted.
  T6 — existing keyword-graded tasks are byte-identical (no regression).
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from cohezion.inference.gauntlet import (
    BenchTask,
    _call_model,
    _extract_python,
    _run_python_test,
    _score_result,
)


CORRECT_FIB = (
    "def fib(n):\n"
    "    a, b, r = 0, 1, []\n"
    "    for _ in range(n):\n"
    "        r.append(a); a, b = b, a + b\n"
    "    return r\n"
)
FIB_TEST = "assert fib(7) == [0, 1, 1, 2, 3, 5, 8]\nassert fib(0) == []\nassert fib(1) == [0]"


def _mock_httpx(content: str = "", reasoning_content: str = "", capture: dict | None = None):
    """Return a patched httpx.AsyncClient whose POST yields the given message fields."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(
        return_value={
            "choices": [{"message": {"content": content, "reasoning_content": reasoning_content}}],
            "usage": {"completion_tokens": 42},
        }
    )

    async def _post(url, json=None):
        if capture is not None:
            capture["url"] = url
        return resp

    client = MagicMock()
    client.__aenter__ = AsyncMock(return_value=MagicMock(post=_post))
    client.__aexit__ = AsyncMock(return_value=False)
    return client


# ── T1: reasoning-model fairness ──────────────────────────────────────────────
def test_t1_reasoning_content_fallback_is_graded_fairly():
    """content='' but correct code in reasoning_content → exec quality 1.0 (old harness: 0.0)."""
    reasoning = f"Here's my plan...\n```python\n{CORRECT_FIB}```\nDone."
    with patch("httpx.AsyncClient", return_value=_mock_httpx(content="", reasoning_content=reasoning)):
        ttft, tps, text = asyncio.run(_call_model("m", "prompt", 3072, 300.0))
    assert CORRECT_FIB.split("\n")[0] in text, "reasoning_content must be used when content empty"
    task = BenchTask("code_fibonacci", "code", "p", ["def"], grader="python_exec", test_code=FIB_TEST)
    exec_pass = _run_python_test(text, task.test_code)
    res = _score_result(task, ttft, tps, text, exec_pass=exec_pass)
    assert res.quality_ratio == 1.0


# ── T2: keyword-liar mirror ───────────────────────────────────────────────────
def test_t2_keyword_matching_but_broken_code_fails_exec():
    """Text with 'def','fibonacci','return' but a SyntaxError scores 0 under exec (old keyword: 1.0)."""
    broken = "```python\ndef fibonacci(n) return n\n```"  # missing colon → SyntaxError
    task = BenchTask(
        "code_fibonacci", "code", "p", ["def", "fibonacci", "return"],
        grader="python_exec", test_code=FIB_TEST,
    )
    # Old keyword grader WOULD have scored this 1.0 (all 3 keywords present):
    kw_task = BenchTask("x", "code", "p", ["def", "fibonacci", "return"])  # grader defaults keyword
    assert _score_result(kw_task, 0.0, 10.0, broken).quality_ratio == 1.0  # the lie
    # Exec grader sees the truth:
    exec_pass = _run_python_test(broken, task.test_code)
    assert _score_result(task, 0.0, 10.0, broken, exec_pass=exec_pass).quality_ratio == 0.0


# ── T3: endpoint ──────────────────────────────────────────────────────────────
def test_t3_posts_to_chat_completions_endpoint():
    cap: dict = {}
    with patch("httpx.AsyncClient", return_value=_mock_httpx(content="ok", capture=cap)):
        asyncio.run(_call_model("m", "p", 10))
    assert cap["url"].endswith("/api/v1/chat/completions"), cap["url"]


# ── T4: timeout safety ────────────────────────────────────────────────────────
def test_t4_infinite_loop_fails_within_timeout():
    import time as _t

    t0 = _t.monotonic()
    ok = _run_python_test("while True:\n    pass\n", "assert True", timeout=3.0)
    assert ok is False
    assert _t.monotonic() - t0 < 8.0, "must return near the timeout, not hang"


# ── T5: think-strip + extraction ──────────────────────────────────────────────
def test_t5_think_block_stripped_and_code_extracted():
    text = f"<think>let me reason a lot</think>\n```python\n{CORRECT_FIB}```"
    with patch("httpx.AsyncClient", return_value=_mock_httpx(content=text)):
        _, _, out = asyncio.run(_call_model("m", "p", 3072))
    assert "<think>" not in out
    assert _run_python_test(out, FIB_TEST) is True


# ── T6: keyword regression (no behavior change for existing tasks) ────────────
def test_t6_keyword_tasks_byte_identical():
    task = BenchTask("math_proof", "code", "p", ["assume", "rational", "contradiction"])
    text = "Assume sqrt(2) is rational; by contradiction it is irrational."
    res = _score_result(task, 0.1, 50.0, text)
    assert res.keyword_hits == 3 and res.keyword_total == 3 and res.quality_ratio == 1.0


# ── correctness anchors for the exec grader itself ────────────────────────────
def test_correct_fib_passes_exec():
    assert _run_python_test(f"```python\n{CORRECT_FIB}```", FIB_TEST) is True


def test_extract_python_last_block():
    assert _extract_python("```python\nx=1\n```\ntext\n```python\ny=2\n```").strip() == "y=2"
