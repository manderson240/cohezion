"""Adversarial stress tests for SurrealTraceAugmentor GAIA→httpx fallback chain and edge cases.

Dimensions covered:
  1. GAIA returns empty string (calibration) → httpx fallback fires
  2. GAIA raises exception → httpx succeeds
  3. Both GAIA and httpx fail → returns "" without raising
  4. _SKIP_SKILL_NAMES filter at batch scale (15 real + 5 skip = 15 calls)
  5. improved_score edge values (0.0, 1.0, 1.5) pass through verbatim
  6. Very long trace input truncated to 1500 chars before inference
  7. Unicode in trace content (emoji + CJK) passes without UnicodeError
  8. SQL injection in skill_name is escaped, not raw-injected
  9. augment_batch(limit=0) returns [] without calling Lemonade
  10. skill_filter appears as AND clause in the fetch SQL
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cohezion.skillopt.trace_augmentor import SurrealTraceAugmentor


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_trace(
    skill_name: str = "IDEATOR_PRIME",
    input_text: str = "think of something",
    output_text: str = "bad output",
    score: float = 0.1,
    trace_id: str = "execution_trace:t1",
) -> dict:
    return {
        "id": trace_id,
        "skill_name": skill_name,
        "input": input_text,
        "output": output_text,
        "score": score,
        "status": "failure",
    }


def _lemonade_resp(text: str = "improved via httpx") -> MagicMock:
    """Mock shaped like a Lemonade /v1/chat/completions response."""
    m = MagicMock()
    m.raise_for_status.return_value = None
    m.json.return_value = {"choices": [{"message": {"content": text}}]}
    return m


def _surreal_ok(rows: list | None = None) -> MagicMock:
    """Mock shaped like a SurrealDB response."""
    m = MagicMock()
    m.json.return_value = [{"result": rows or [], "status": "OK"}]
    return m


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def augmentor() -> SurrealTraceAugmentor:
    """Augmentor with httpx.Client mocked at construction; _http replaced post-init."""
    with patch("cohezion.skillopt.trace_augmentor.httpx.Client") as mock_client:
        mock_client.return_value.post.return_value.json.return_value = [
            {"result": [], "status": "OK"}
        ]
        aug = SurrealTraceAugmentor()
    # Replace _http with a fresh MagicMock so test call counts start at 0
    aug._http = MagicMock()
    aug._http.post.return_value = _surreal_ok()
    # Disable GAIA by default; individual tests enable it as needed
    aug._gaia_client = None
    return aug


# ---------------------------------------------------------------------------
# 1. GAIA returns empty string → httpx fallback must fire
# ---------------------------------------------------------------------------


class TestGaiaEmptyStringFallthrough:
    """DISCRIMINATING: empty content from GAIA must NOT cause _reflect_and_improve to return ''.

    A naïve implementation might treat empty text as the final result and skip httpx.
    The correct implementation logs calibration and falls through to the httpx block.
    """

    def test_gaia_empty_falls_through_to_httpx(self, augmentor: SurrealTraceAugmentor) -> None:
        """GAIA returns {content: ''} → httpx fallback is called and returns improved text.

        Architecture invariant: httpx fallback MUST call :13305 (OmniRouter), never a
        per-tier port (:13306/:13307/:13309).  All inference routes through the single router.
        """
        gaia_mock = MagicMock()
        gaia_mock.chat_completions.return_value = {"choices": [{"message": {"content": ""}}]}
        augmentor._gaia_client = gaia_mock

        # httpx fallback returns non-empty
        augmentor._http.post.return_value = _lemonade_resp("improved via httpx fallback")

        result = augmentor._reflect_and_improve(_make_trace())

        assert result == "improved via httpx fallback", (
            f"GAIA empty-string calibration must fall through to httpx; got: {result!r}"
        )
        gaia_mock.chat_completions.assert_called_once()
        augmentor._http.post.assert_called()
        # Verify the httpx fallback targeted the OmniRouter on :13305 (not a tier port)
        call_url = augmentor._http.post.call_args.args[0]
        assert "13305" in call_url, (
            f"httpx fallback must use the Lemonade OmniRouter on :13305; got URL: {call_url!r}"
        )

    def test_gaia_whitespace_only_also_falls_through(
        self, augmentor: SurrealTraceAugmentor
    ) -> None:
        """GAIA returns whitespace-only content → same fallthrough behaviour (strip() → empty)."""
        gaia_mock = MagicMock()
        gaia_mock.chat_completions.return_value = {
            "choices": [{"message": {"content": "   \n\t  "}}]
        }
        augmentor._gaia_client = gaia_mock

        augmentor._http.post.return_value = _lemonade_resp("httpx saved it")

        result = augmentor._reflect_and_improve(_make_trace())

        assert result == "httpx saved it", (
            "Whitespace-only GAIA response must fall through to httpx"
        )
        call_url = augmentor._http.post.call_args.args[0]
        assert "13305" in call_url, (
            f"httpx fallback must target :13305 OmniRouter; got: {call_url!r}"
        )


# ---------------------------------------------------------------------------
# 2. GAIA raises exception → httpx succeeds
# ---------------------------------------------------------------------------


class TestGaiaExceptionFallthrough:
    """GAIA raises any exception → httpx path is tried and its result is returned."""

    def test_connection_error_falls_through(self, augmentor: SurrealTraceAugmentor) -> None:
        gaia_mock = MagicMock()
        gaia_mock.chat_completions.side_effect = ConnectionError("GAIA endpoint down")
        augmentor._gaia_client = gaia_mock

        augmentor._http.post.return_value = _lemonade_resp("httpx rescue")

        result = augmentor._reflect_and_improve(_make_trace())

        assert result == "httpx rescue", (
            "ConnectionError from GAIA must not propagate; httpx must return its result"
        )
        augmentor._http.post.assert_called()
        call_url = augmentor._http.post.call_args.args[0]
        assert "13305" in call_url, f"httpx fallback must use :13305 OmniRouter; got: {call_url!r}"

    def test_runtime_error_falls_through(self, augmentor: SurrealTraceAugmentor) -> None:
        gaia_mock = MagicMock()
        gaia_mock.chat_completions.side_effect = RuntimeError("unexpected GAIA error")
        augmentor._gaia_client = gaia_mock

        augmentor._http.post.return_value = _lemonade_resp("runtime fallback")

        result = augmentor._reflect_and_improve(_make_trace())
        assert result == "runtime fallback"


# ---------------------------------------------------------------------------
# 3. Both GAIA and httpx fail → returns "" without raising
# ---------------------------------------------------------------------------


class TestBothFail:
    """When every inference path is down, _reflect_and_improve must return '' not raise."""

    def test_both_fail_returns_empty_string(self, augmentor: SurrealTraceAugmentor) -> None:
        gaia_mock = MagicMock()
        gaia_mock.chat_completions.side_effect = RuntimeError("GAIA dead")
        augmentor._gaia_client = gaia_mock

        augmentor._http.post.side_effect = OSError("Lemonade unreachable")

        result = augmentor._reflect_and_improve(_make_trace())

        assert result == "", "Both failure → must return '' not raise"

    def test_both_fail_gaia_disabled_httpx_fails(self, augmentor: SurrealTraceAugmentor) -> None:
        """GAIA absent (None) and httpx raises → empty string."""
        augmentor._gaia_client = None
        augmentor._http.post.side_effect = ConnectionRefusedError("Lemonade down")

        result = augmentor._reflect_and_improve(_make_trace())
        assert result == ""


# ---------------------------------------------------------------------------
# 4. _SKIP_SKILL_NAMES at batch scale (15 real + 5 skip)
# ---------------------------------------------------------------------------


class TestSkipFilterAtBatchScale:
    """_reflect_and_improve called exactly N times for N non-skip traces."""

    def test_15_real_5_skip_calls_reflect_exactly_15_times(
        self, augmentor: SurrealTraceAugmentor
    ) -> None:
        """DISCRIMINATING: if the filter is broken, reflect is called 20 times not 15."""
        real_names = [
            "IDEATOR_PRIME",
            "PLANNER_PRIME",
            "EXECUTOR_PRIME",
            "CRITIC_PRIME",
            "SYNTHESIZER_PRIME",
            "DEBUGGER_PRIME",
            "REFACTOR_PRIME",
            "TESTER_PRIME",
            "REVIEWER_PRIME",
            "ARCHITECT_PRIME",
            "DOCUMENTER_PRIME",
            "OPTIMIZER_PRIME",
            "VALIDATOR_PRIME",
            "COORDINATOR_PRIME",
            "ANALYZER_PRIME",
        ]
        # Pick exactly 5 names from the known skip set
        skip_names = ["TEST", "test", "skill", "generator", "unknown"]

        rows = [
            _make_trace(skill_name=n, trace_id=f"execution_trace:real{i}")
            for i, n in enumerate(real_names)
        ] + [
            _make_trace(skill_name=n, trace_id=f"execution_trace:skip{i}")
            for i, n in enumerate(skip_names)
        ]

        # Inject at the HTTP layer so the real _fetch_low_quality_traces filter runs
        fetch_done = {"v": False}

        def dispatch(url, content=None, **kwargs):
            if not fetch_done["v"] and content and "WHERE score" in content:
                fetch_done["v"] = True
                return _surreal_ok(rows)
            # Store calls
            return _surreal_ok([{"id": "execution_trace:new1"}])

        augmentor._http.post.side_effect = dispatch

        reflect_calls: list[str] = []

        def counting_reflect(trace: dict) -> str:
            reflect_calls.append(trace.get("skill_name", ""))
            return "improved output"

        with patch.object(augmentor, "_reflect_and_improve", side_effect=counting_reflect):
            augmentor.augment_batch(max_score=0.9, limit=20)

        assert len(reflect_calls) == 15, (
            f"Expected _reflect_and_improve called 15 times (5 skip filtered out), "
            f"got {len(reflect_calls)}. Called for: {reflect_calls}"
        )
        for skip in skip_names:
            assert skip not in reflect_calls, (
                f"Trace with skip skill '{skip}' was not filtered before _reflect_and_improve"
            )


# ---------------------------------------------------------------------------
# 5. improved_score edge values (0.0, 1.0, 1.5) stored verbatim
# ---------------------------------------------------------------------------


class TestImprovedScoreEdgeValues:
    """DISCRIMINATING: score must appear in SQL verbatim; clamping to [0,1] would fail 1.5."""

    @pytest.mark.parametrize(
        "score, expected_fragment",
        [
            (0.0, "score = 0.0"),
            (1.0, "score = 1.0"),
            (1.5, "score = 1.5"),
        ],
    )
    def test_score_in_sql(
        self,
        augmentor: SurrealTraceAugmentor,
        score: float,
        expected_fragment: str,
    ) -> None:
        stored_sqls: list[str] = []

        def capture(url, content=None, **kwargs):
            if content and "CREATE execution_trace" in content:
                stored_sqls.append(content)
            return _surreal_ok([{"id": "execution_trace:new1"}])

        augmentor._http.post.side_effect = capture

        original = {"id": "t:1", "skill_name": "IDEATOR_PRIME", "input": "x", "output": "y"}
        augmentor._store_augmented_trace(original, "improved", improved_score=score)

        assert stored_sqls, "No CREATE execution_trace SQL was sent"
        sql = stored_sqls[0]
        assert expected_fragment in sql, (
            f"Expected '{expected_fragment}' in stored SQL for improved_score={score}; got: {sql!r}"
        )


# ---------------------------------------------------------------------------
# 6. Very long input (6000 chars) truncated to 1500 before inference
# ---------------------------------------------------------------------------


class TestLongInputTruncation:
    """Ensures the :1500 slice in _reflect_and_improve is actually applied."""

    def test_long_input_truncated_in_httpx_prompt(self, augmentor: SurrealTraceAugmentor) -> None:
        """DISCRIMINATING: A prompt built from 6000 'a' chars must not contain 1501+ consecutive a's."""
        long_input = "a" * 6000
        trace = _make_trace(input_text=long_input)

        captured_prompts: list[str] = []
        captured_urls: list[str] = []

        def capture_httpx(url, json=None, **kwargs):
            captured_urls.append(url)
            if json and "messages" in json:
                captured_prompts.append(json["messages"][0]["content"])
            return _lemonade_resp("ok")

        augmentor._http.post.side_effect = capture_httpx
        augmentor._reflect_and_improve(trace)

        assert captured_prompts, "httpx was not called"
        prompt = captured_prompts[0]
        # The full 6000-char block must NOT appear — only the 1500-char truncated version
        assert "a" * 1501 not in prompt, (
            "Input was not truncated: found 1501+ consecutive 'a' chars in the prompt"
        )
        assert "a" * 1500 in prompt, (
            "Expected the 1500-char truncated input in the prompt, but it was missing"
        )
        # Architecture invariant: httpx fallback must always use :13305 OmniRouter
        assert all("13305" in u for u in captured_urls), (
            f"httpx fallback used a non-:13305 URL: {captured_urls}"
        )

    def test_long_input_truncated_in_gaia_prompt(self, augmentor: SurrealTraceAugmentor) -> None:
        """GAIA path also receives truncated input (1500 chars max)."""
        long_input = "b" * 6000
        trace = _make_trace(input_text=long_input)

        gaia_mock = MagicMock()
        gaia_mock.chat_completions.return_value = {
            "choices": [{"message": {"content": "improved via gaia"}}]
        }
        augmentor._gaia_client = gaia_mock

        augmentor._reflect_and_improve(trace)

        gaia_mock.chat_completions.assert_called_once()
        call_kwargs = gaia_mock.chat_completions.call_args.kwargs
        messages = call_kwargs["messages"]
        prompt = messages[0]["content"]

        assert "b" * 1501 not in prompt, (
            "GAIA also received 1501+ consecutive 'b' chars — truncation not applied"
        )
        assert "b" * 1500 in prompt, "1500-char truncated input not found in GAIA prompt"


# ---------------------------------------------------------------------------
# 7. Unicode in trace content
# ---------------------------------------------------------------------------


class TestUnicodeHandling:
    """Unicode (emoji + CJK) must not cause UnicodeError anywhere in the pipeline."""

    def test_unicode_in_input_output(self, augmentor: SurrealTraceAugmentor) -> None:
        trace = _make_trace(
            input_text="émoji: 🤖 and Chinese: 你好",
            output_text="café résumé 日本語",
        )
        augmentor._http.post.return_value = _lemonade_resp("unicode response: 你好 🤖")

        result = augmentor._reflect_and_improve(trace)
        assert result == "unicode response: 你好 🤖"

    def test_unicode_in_store(self, augmentor: SurrealTraceAugmentor) -> None:
        """Unicode in input/output passes through _store_augmented_trace without error."""
        original = {
            "id": "t:1",
            "skill_name": "IDEATOR_PRIME",
            "input": "题目: 分析数据 🔍",
            "output": "结果: 你好 café",
        }
        stored_sqls: list[str] = []

        def capture(url, content=None, **kwargs):
            if content and "CREATE execution_trace" in content:
                stored_sqls.append(content)
            return _surreal_ok([{"id": "execution_trace:new1"}])

        augmentor._http.post.side_effect = capture
        # Must not raise
        augmentor._store_augmented_trace(original, "改进后的输出 🤖", 0.8)

        assert stored_sqls, "Store call was not made"


# ---------------------------------------------------------------------------
# 8. SQL injection in skill_name is escaped
# ---------------------------------------------------------------------------


class TestSQLInjection:
    """DISCRIMINATING: _store_augmented_trace must escape quotes in skill_name."""

    def test_double_quote_injection_escaped(self, augmentor: SurrealTraceAugmentor) -> None:
        """skill_name containing '" must be escaped so SurrealDB sees \\\" not a raw terminator.

        _escape() turns " → \\". In the SQL bytes sent to SurrealDB:
          CORRECT (with escape):   skill_name = "PRIME\\"; DROP TABLE...;"
            \\"; is SurrealDB's escape-quote-inside-string → the " is part of the value.
          INCORRECT (no escape): skill_name = "PRIME"; DROP TABLE execution_trace;
            The unescaped " terminates the string early → injection executes.

        The discriminating Python check: 'PRIME";' (no backslash between PRIME and ")
        is absent when _escape() runs; 'PRIME\\";' (backslash before ") is present.
        """
        malicious_skill = 'PRIME"; DROP TABLE execution_trace; --'
        original = {
            "id": "t:1",
            "skill_name": malicious_skill,
            "input": "x",
            "output": "y",
        }

        stored_sqls: list[str] = []

        def capture(url, content=None, **kwargs):
            if content and "CREATE execution_trace" in content:
                stored_sqls.append(content)
            return _surreal_ok([{"id": "execution_trace:new1"}])

        augmentor._http.post.side_effect = capture
        augmentor._store_augmented_trace(original, "improved", 0.8)

        assert stored_sqls, "No CREATE SQL captured"
        sql = stored_sqls[0]

        # DISCRIMINATING: if _escape() is NOT called, 'PRIME";' appears (raw " after PRIME).
        # If _escape() IS called, there's a backslash between PRIME and ", so 'PRIME";' is absent.
        assert 'PRIME";' not in sql, (
            "Unescaped injection: '\"' immediately follows PRIME with no escape backslash — "
            "_escape() was not applied to skill_name"
        )
        # The correctly escaped form 'PRIME\\";' (backslash + quote + semicolon) must be present
        assert 'PRIME\\";' in sql, (
            "Expected backslash-escaped quote 'PRIME\\\";' in SQL — _escape() may not be applied"
        )

    def test_newline_injection_escaped(self, augmentor: SurrealTraceAugmentor) -> None:
        """Newlines in skill_name must be escaped to \\n in the SQL."""
        newline_skill = "SKILL\nINJECTED_LINE"
        original = {"id": "t:2", "skill_name": newline_skill, "input": "x", "output": "y"}

        stored_sqls: list[str] = []

        def capture(url, content=None, **kwargs):
            if content and "CREATE execution_trace" in content:
                stored_sqls.append(content)
            return _surreal_ok([{"id": "execution_trace:new1"}])

        augmentor._http.post.side_effect = capture
        augmentor._store_augmented_trace(original, "improved", 0.8)

        assert stored_sqls
        sql = stored_sqls[0]
        assert "\n" not in sql or "\\n" in sql, (
            "Raw newline found in stored SQL — _escape() must convert \\n"
        )


# ---------------------------------------------------------------------------
# 9. augment_batch(limit=0) returns [] without calling Lemonade
# ---------------------------------------------------------------------------


class TestBatchLimitZero:
    """limit=0 must return [] and must NOT invoke _reflect_and_improve."""

    def test_limit_zero_returns_empty_without_calling_reflect(
        self, augmentor: SurrealTraceAugmentor
    ) -> None:
        """DISCRIMINATING: a broken impl might ignore limit=0 and call reflect anyway."""
        # SurrealDB returns empty rows for LIMIT 0
        augmentor._http.post.return_value = _surreal_ok([])

        with patch.object(augmentor, "_reflect_and_improve") as mock_reflect:
            result = augmentor.augment_batch(max_score=0.5, limit=0)

        assert result == [], "limit=0 must return empty list"
        mock_reflect.assert_not_called()


# ---------------------------------------------------------------------------
# 10. skill_filter included in fetch SQL as AND clause
# ---------------------------------------------------------------------------


class TestSkillFilterSQL:
    """skill_filter must narrow the SurrealDB query with an AND skill_name clause."""

    def test_skill_filter_included_in_fetch_sql(self, augmentor: SurrealTraceAugmentor) -> None:
        """DISCRIMINATING: if filter is ignored, the SQL won't contain the AND clause."""
        captured_sqls: list[str] = []

        def capture(url, content=None, **kwargs):
            if content and "WHERE score" in content:
                captured_sqls.append(content)
            return _surreal_ok([])

        augmentor._http.post.side_effect = capture

        augmentor.augment_batch(max_score=0.5, limit=10, skill_filter="IDEATOR_PRIME")

        assert captured_sqls, "No SELECT SQL captured"
        sql = captured_sqls[0]
        assert 'AND skill_name = "IDEATOR_PRIME"' in sql, (
            f"skill_filter='IDEATOR_PRIME' not present in fetch SQL; got: {sql!r}"
        )

    def test_no_skill_filter_omits_skill_clause(self, augmentor: SurrealTraceAugmentor) -> None:
        """When skill_filter is None, the SQL must NOT contain an extra AND skill_name clause."""
        captured_sqls: list[str] = []

        def capture(url, content=None, **kwargs):
            if content and "WHERE score" in content:
                captured_sqls.append(content)
            return _surreal_ok([])

        augmentor._http.post.side_effect = capture

        augmentor.augment_batch(max_score=0.5, limit=10, skill_filter=None)

        assert captured_sqls
        sql = captured_sqls[0]
        assert "AND skill_name" not in sql, (
            "SQL unexpectedly contains AND skill_name when skill_filter=None"
        )
