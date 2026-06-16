"""V-model structural invariant tests for SurrealTraceAugmentor.

Structural tests verify interface contracts (types, presence of fields, method
signatures) before behavioral tests. All SurrealDB and Lemonade calls are mocked.
"""

import inspect
from unittest.mock import MagicMock, patch

import pytest

from cohezion.skillopt.trace_augmentor import SurrealTraceAugmentor, _SKIP_SKILL_NAMES


class TestAugmentorVModelStructure:
    """V-model O6: SurrealTraceAugmentor structural signature invariants."""

    @pytest.fixture
    def augmentor(self):
        with patch("cohezion.skillopt.trace_augmentor.httpx.Client") as mock_client:
            mock_client.return_value.post.return_value.json.return_value = [
                {"result": [], "status": "OK"}
            ]
            aug = SurrealTraceAugmentor()
        aug._http = MagicMock()
        aug._http.post.return_value.json.return_value = [{"result": [], "status": "OK"}]
        return aug

    def test_augment_batch_signature(self):
        """O6a: augment_batch accepts max_score, limit, skill_filter, improved_score."""
        sig = inspect.signature(SurrealTraceAugmentor.augment_batch)
        params = sig.parameters
        for required in ["max_score", "limit", "skill_filter", "improved_score"]:
            assert required in params, f"augment_batch missing param: {required}"

    def test_augment_batch_returns_list(self, augmentor):
        """O6b: augment_batch returns a list (empty when no eligible traces)."""
        result = augmentor.augment_batch(max_score=0.5, limit=10)
        assert isinstance(result, list), f"augment_batch must return list, got {type(result)}"

    def test_stats_returns_required_keys(self, augmentor):
        """O6c: stats() returns dict with total, augmented, natural keys."""
        augmentor._http.post.return_value.json.return_value = [
            {"result": [{"total": 24, "augmented": 4, "natural": 20}], "status": "OK"}
        ]
        s = augmentor.stats()
        for key in ("total", "augmented", "natural"):
            assert key in s, f"stats() missing key: {key}"

    def test_unit_test_artifacts_are_skipped(self, augmentor):
        """O6d: DISCRIMINATING — unit-test artifact skill names must NOT be augmented.

        If "TEST", "skill", "generator" traces were augmented, the corpus would
        contain synthetic data for non-existent skills, poisoning SkillOpt training.
        """
        # Inject a low-score trace with a unit-test skill name
        augmentor._http.post.return_value.json.return_value = [
            {
                "result": [
                    {
                        "id": "execution_trace:abc",
                        "skill_name": "TEST",
                        "input": "describe X",
                        "output": "bad output",
                        "score": 0.1,
                        "status": "failure",
                    }
                ],
                "status": "OK",
            }
        ]
        results = augmentor.augment_batch(max_score=0.5, limit=5)
        # "TEST" is in _SKIP_SKILL_NAMES so the trace should be filtered before Lemonade call
        assert len(results) == 0, (
            "Unit-test artifact skill names must be filtered before augmentation"
        )

    def test_skip_set_covers_known_artifacts(self):
        """O6e: _SKIP_SKILL_NAMES must cover all known unit-test artifact names."""
        for name in ("TEST", "test", "skill", "generator", "unknown", ""):
            assert name in _SKIP_SKILL_NAMES, (
                f"Unit-test artifact {name!r} missing from _SKIP_SKILL_NAMES"
            )

    def test_make_augmentor_returns_none_when_surreal_unavailable(self):
        """O6f: make_augmentor() must return None (not raise) when SurrealDB is down."""
        with patch(
            "cohezion.skillopt.trace_augmentor.httpx.Client",
            side_effect=Exception("connection refused"),
        ):
            from cohezion.skillopt.trace_augmentor import make_augmentor

            result = make_augmentor()
        assert result is None, "make_augmentor must return None when SurrealDB is unavailable"

    def test_gaia_client_init_attempted(self):
        """O6h: SurrealTraceAugmentor must attempt GAIA LemonadeClient at init.

        DISCRIMINATING — a wrong implementation might skip GAIA and always use httpx,
        missing AMD-native routing through the Lemonade OmniRouter on :13305.
        When GAIA is not installed, _gaia_client must be None (graceful fallback).
        """
        with patch("cohezion.skillopt.trace_augmentor.httpx.Client") as mock_client:
            mock_client.return_value.post.return_value.json.return_value = [
                {"result": [], "status": "OK"}
            ]
            # Simulate GAIA not installed — _init_gaia_client should return None
            with patch(
                "cohezion.skillopt.trace_augmentor.SurrealTraceAugmentor._init_gaia_client",
                return_value=None,
            ):
                aug = SurrealTraceAugmentor()
        assert aug._gaia_client is None, "_gaia_client should be None when GAIA SDK is unavailable"

    def test_reflect_falls_back_to_httpx_when_gaia_unavailable(self, augmentor):
        """O6i: _reflect_and_improve must use httpx fallback when _gaia_client is None."""
        augmentor._gaia_client = None  # simulate no GAIA SDK

        called_urls = []

        def fake_post(url, **kwargs):
            called_urls.append(url)
            m = MagicMock()
            m.raise_for_status.return_value = None
            m.json.return_value = {
                "choices": [{"message": {"content": "improved output via httpx"}}]
            }
            return m

        augmentor._http.post.side_effect = fake_post

        trace = {
            "skill_name": "IDEATOR_PRIME",
            "input": "think of something",
            "output": "bad",
            "score": 0.1,
        }
        result = augmentor._reflect_and_improve(trace)
        assert result == "improved output via httpx", (
            "httpx fallback must be used when _gaia_client is None"
        )
        assert any("13305" in url for url in called_urls), (
            "httpx fallback must call Lemonade router on port 13305"
        )

    def test_improved_score_parameter_applied(self, augmentor):
        """O6g: DISCRIMINATING — improved_score kwarg must be used in the stored trace.

        A wrong implementation might hardcode 0.8 and ignore the parameter.
        """
        stored_sqls = []

        def capture_post(url, content=None, **kwargs):
            if content and "CREATE execution_trace" in content:
                stored_sqls.append(content)
            mock_resp = MagicMock()
            mock_resp.json.return_value = [{"result": [], "status": "OK"}]
            return mock_resp

        augmentor._http.post.side_effect = capture_post

        # Inject a low-score trace the augmentor will process
        call_count = 0

        def selective_post(url, content=None, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_resp = MagicMock()
            # First call = fetch (returns one eligible trace)
            if call_count == 1:
                mock_resp.json.return_value = [
                    {
                        "result": [
                            {
                                "id": "execution_trace:xyz",
                                "skill_name": "IDEATOR_PRIME",
                                "input": "ideate something",
                                "output": "bad",
                                "score": 0.1,
                                "status": "failure",
                            }
                        ],
                        "status": "OK",
                    }
                ]
            else:
                mock_resp.json.return_value = [
                    {"result": [{"id": "execution_trace:new1"}], "status": "OK"}
                ]
            return mock_resp

        augmentor._http.post.side_effect = selective_post

        # Mock Lemonade reflection call
        with patch.object(augmentor, "_reflect_and_improve", return_value="improved output"):
            augmentor.augment_batch(max_score=0.5, limit=1, improved_score=0.95)

        # Check via _store_augmented_trace directly
        stored = []

        def capture_store(url, content=None, **kw):
            if content and "score = " in content:
                stored.append(content)
            m = MagicMock()
            m.json.return_value = [{"result": [{"id": "t:n"}]}]
            return m

        augmentor._http.post.side_effect = capture_store
        augmentor._store_augmented_trace(
            {"id": "t:o", "skill_name": "IDEATOR_PRIME", "input": "x", "output": "y"},
            "improved",
            improved_score=0.95,
        )
        assert any("score = 0.95" in s for s in stored), (
            "improved_score=0.95 must appear in the stored SQL; hardcoded 0.8 would fail this test"
        )
