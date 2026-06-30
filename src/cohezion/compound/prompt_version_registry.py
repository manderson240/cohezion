"""Golden-fixture drift gate for SkillRefiner promotions.

Wraps the three SurrealDB tables defined for V-model verification:
  - golden_fixture  — reference (input, expected_output, embedding_768d) per skill
  - prompt_version  — version history of skill prompt content
  - fixture_run     — log of each gate evaluation

check_drift() is fail-open: any error (DB unavailable, Lemonade down, no
fixtures registered) returns True so SkillRefiner continues normally.
"""

from __future__ import annotations

import logging
import math
from typing import Any

logger = logging.getLogger(__name__)

_SURREAL_URL = "http://localhost:8001/sql"
_SURREAL_HEADERS = {
    "surreal-ns": "cohezion",
    "surreal-db": "main",
    "Content-Type": "text/plain",
}
_EMBED_URL = "http://localhost:13305/v1/embeddings"
_EMBED_MODEL = "nomic-embed-text-v2-moe-GGUF"
DRIFT_THRESHOLD = 0.35  # cosine distance; block if drift >= this


def _safe_ident(name: str) -> str:
    """M5: guard against SurrealQL injection — skill_name flows from the registry/loop into
    interpolated queries. Allow only identifier-safe chars; reject quote/semicolon/space breakouts.
    Raises ValueError on a bad name (callers fail-open via their try/except)."""
    import re

    if not re.fullmatch(r"[A-Za-z0-9_./-]+", name or ""):
        raise ValueError(f"unsafe skill_name for query: {name!r}")
    return name


class PromptVersionRegistry:
    """Gate: block SkillRefiner from promoting a change that drifts ≥0.35 from golden fixtures."""

    def check_drift(self, skill_name: str, new_content: str) -> bool:
        """Return True (allow) or False (block — drift too high vs golden fixtures).

        Fail-open on any error so the compound loop never stalls.
        """
        try:
            fixtures = self._load_fixtures(skill_name)
            if not fixtures:
                return True

            stored_embeddings = [f["embedding_768d"] for f in fixtures if f.get("embedding_768d")]
            if not stored_embeddings:
                return True

            new_emb = self._embed(new_content)
            if new_emb is None:
                return True

            centroid = _centroid(stored_embeddings)
            dist = 1.0 - _cosine(new_emb, centroid)

            if dist >= DRIFT_THRESHOLD:
                logger.info(
                    "GoldenFixtureGate BLOCK: skill=%s drift=%.3f >= %.3f",
                    skill_name, dist, DRIFT_THRESHOLD,
                )
                self._log_run(skill_name, dist, passed=False)
                return False

            logger.debug("GoldenFixtureGate ALLOW: skill=%s drift=%.3f", skill_name, dist)
            self._log_run(skill_name, dist, passed=True)
            return True

        except Exception as exc:
            logger.debug("GoldenFixtureGate error (fail-open): %s", exc)
            return True

    def regression_check(self, skill_name: str, candidate: str, run_fn) -> bool:
        """FAPO R3 behavioral regression gate: run the CANDIDATE skill against the skill's golden
        fixtures and BLOCK promotion (return False) if any CRITICAL case regresses. Complements
        check_drift (which only compares EDIT-TEXT embeddings) by checking actual BEHAVIOR — the
        quiet-failure mode prompt edits cause. Fail-open: no run_fn / no fixtures / errors → True."""
        # Fail-policy (M1, AUTO-promotion): no run_fn / infra load error → fail-OPEN (don't halt the
        # loop); no fixtures → skip-but-log; fixtures EXIST but eval can't complete → fail-CLOSED.
        if run_fn is None:
            return True
        try:
            fixtures = self._load_behavioral_fixtures(skill_name)
        except Exception as exc:
            logger.warning("RegressionGate: fixture load failed — fail-open (infra): %s", exc)
            return True
        if not fixtures:
            logger.debug("RegressionGate: no golden fixtures for %s — skip", skill_name)
            return True
        try:
            passed = evaluate_regression(fixtures, candidate, run_fn)
        except Exception as exc:
            logger.warning("RegressionGate BLOCK: eval failed with fixtures present (%s): %s", skill_name, exc)
            return False  # fail-CLOSED: fixtures exist, can't verify → don't promote
        self._log_run(skill_name, drift=-1.0, passed=passed)
        return passed

    # ── internal helpers ──────────────────────────────────────────────────────

    def _load_behavioral_fixtures(self, skill_name: str) -> list[dict[str, Any]]:
        import httpx

        q = (
            "SELECT input, expected_output, validator_type, critical FROM golden_fixture "
            f"WHERE skill_name = '{_safe_ident(skill_name)}';"
        )
        r = httpx.post(_SURREAL_URL, content=q, headers=_SURREAL_HEADERS, auth=("root", "root"), timeout=5.0)
        r.raise_for_status()
        data = r.json()
        return data[0].get("result", []) if data else []

    def _load_fixtures(self, skill_name: str) -> list[dict[str, Any]]:
        import httpx
        q = f"SELECT embedding_768d FROM golden_fixture WHERE skill_name = '{_safe_ident(skill_name)}';"
        r = httpx.post(_SURREAL_URL, content=q, headers=_SURREAL_HEADERS, auth=("root", "root"), timeout=5.0)
        r.raise_for_status()
        data = r.json()
        return data[0].get("result", []) if data else []

    def _embed(self, text: str) -> list[float] | None:
        try:
            import httpx
            r = httpx.post(_EMBED_URL, json={"model": _EMBED_MODEL, "input": text}, timeout=10.0)
            r.raise_for_status()
            return r.json()["data"][0]["embedding"]
        except Exception:
            return None

    def _log_run(self, skill_name: str, drift: float, *, passed: bool) -> None:
        try:
            import httpx
            q = (
                f"CREATE fixture_run SET skill_name='{_safe_ident(skill_name)}', "
                f"drift_score={drift:.4f}, passed={str(passed).lower()}, "
                f"created_at=time::now();"
            )
            httpx.post(_SURREAL_URL, content=q, headers=_SURREAL_HEADERS, auth=("root", "root"), timeout=3.0)
        except Exception:
            pass


# ── behavioral regression eval (FAPO R3 — defends against quiet prompt regression) ────────────

def _validate(output: str, expected: str, validator: str = "contains") -> bool:
    """DETERMINISTIC validator (no LLM-as-judge, per the prompt-regression discipline)."""
    o, e = (output or "").strip(), (expected or "").strip()
    if validator == "exact":
        return o == e
    if validator == "regex":
        import re

        try:
            return re.search(e, o) is not None
        except re.error:
            return True  # malformed pattern → don't block on it
    return e.lower() in o.lower()  # default "contains"


def evaluate_regression(fixtures: list[dict[str, Any]], candidate: str, run_fn) -> bool:
    """Run the CANDIDATE skill against each golden fixture; return False if any CRITICAL fixture
    REGRESSES (output fails its deterministic validator). Non-critical failures are allowed; this
    is the article's 'critical-category gate that blocks even when the aggregate improves'.
    Per-fixture execution errors fail OPEN (skip, don't block). Pure: run_fn(candidate, input)->str."""
    for f in fixtures:
        inp, exp = f.get("input"), f.get("expected_output")
        if not inp or exp is None:
            continue
        try:
            out = run_fn(candidate, inp)
        except Exception:
            continue  # execution error is not a regression signal
        if not _validate(out, exp, f.get("validator_type") or "contains") and f.get("critical", True):
            logger.info("RegressionGate BLOCK: critical fixture regressed (input=%r)", str(inp)[:50])
            return False
    return True


# ── pure math (no deps) ───────────────────────────────────────────────────────

def _centroid(vecs: list[list[float]]) -> list[float]:
    n, dim = len(vecs), len(vecs[0])
    return [sum(v[i] for v in vecs) / n for i in range(dim)]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(x * x for x in b))
    return dot / mag if mag else 0.0
