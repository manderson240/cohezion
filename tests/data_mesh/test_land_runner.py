"""V-model tests for land_runner — structural + discriminating, ZERO live inference.

The discriminating standard (verification-depth.md): each test neutralises one mechanism
and asserts the verdict flips. A runner that IGNORED gates or review (ready always True)
would fail T3/T4 — so these prove the results are CONSUMED, not merely computed.
"""

from __future__ import annotations

import inspect

from cohezion.data_mesh.land_runner import LandVerdict, run_land_review


def _PASS_GATES(repo):
    return {"ok": True, "failures": []}


def _FAIL_GATES(repo):
    return {"ok": False, "failures": ["ruff format: 1 file would be reformatted"]}


def _PASS_REVIEW(repo, br):
    return {"ok": True, "findings": [], "consensus": "local-clear"}


def _BLOCK_REVIEW(repo, br):
    return {"ok": False, "findings": ["CRITICAL | injection"], "consensus": "cloud-confirmed"}


def _SEMVER(repo, br):
    return "minor"


class TestStructural:
    def test_run_land_review_injectable_fns(self):
        params = inspect.signature(run_land_review).parameters
        assert {"gate_fn", "review_fn", "semver_fn"} <= set(params)

    def test_verdict_has_ready_title_body(self):
        v = LandVerdict(branch="feat/x", gates_ok=True, review_ok=True, semver="minor")
        assert isinstance(v.ready, bool) and callable(v.body) and isinstance(v.title, str)


class TestDiscriminating:
    def test_all_pass_is_ready_with_semver(self):
        v = run_land_review(
            "/repo", "feat/x", gate_fn=_PASS_GATES, review_fn=_PASS_REVIEW, semver_fn=_SEMVER
        )
        assert v.ready is True
        assert "READY" in v.title and "feat/x" in v.title and "minor" in v.title

    def test_gate_failure_blocks_even_if_review_passes(self):
        # Neutralise gates → verdict MUST be BLOCKED. A runner ignoring gates would return ready=True.
        v = run_land_review(
            "/repo", "feat/x", gate_fn=_FAIL_GATES, review_fn=_PASS_REVIEW, semver_fn=_SEMVER
        )
        assert v.ready is False
        assert "BLOCKED" in v.title
        assert any("ruff format" in f for f in v.detail["gates"]["failures"])

    def test_review_block_blocks_even_if_gates_pass(self):
        # Neutralise review → verdict MUST be BLOCKED. Proves the review result is consumed.
        v = run_land_review(
            "/repo", "feat/x", gate_fn=_PASS_GATES, review_fn=_BLOCK_REVIEW, semver_fn=_SEMVER
        )
        assert v.ready is False
        assert "BLOCKED" in v.title

    def test_body_surfaces_gate_failures_and_verdict(self):
        v = run_land_review(
            "/repo", "feat/x", gate_fn=_FAIL_GATES, review_fn=_PASS_REVIEW, semver_fn=_SEMVER
        )
        body = v.body()
        assert "BLOCKED" in body and "ruff format" in body and "do not land" in body.lower()

    def test_semver_default_when_fn_returns_empty(self):
        v = run_land_review(
            "/repo",
            "feat/x",
            gate_fn=_PASS_GATES,
            review_fn=_PASS_REVIEW,
            semver_fn=lambda r, b: "",
        )
        assert v.semver == "patch"  # safe default, never blank
