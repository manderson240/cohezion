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
# Fixture generation = a structured task → the FAST iGPU model DIRECTLY, not the escalating triune
# cascade (which reaches the slow CPU 31B that empties/times out on structured prompts). Verified
# 2026-06-29: Gemma-4-E4B generated 3 fixtures in seconds; the 31B cascade timed out at 180s.
_FAST_CHAT_URL = "http://localhost:13305/api/v1/chat/completions"
_FAST_GEN_MODEL = "Gemma-4-E4B-it-GGUF"
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

    def bootstrap_fixtures(self, skill_name: str, prime_excerpt: str, chat_fn=None, n: int = 3) -> int:
        """Generate (local-first, $0) + persist behavioral golden fixtures so the M1 regression gate
        has cases to run for `skill_name`. Defaults to the fast iGPU model when chat_fn is None.
        Returns the count written (0 on any failure)."""
        chat_fn = chat_fn or _fast_local_chat
        written = 0
        for fx in generate_fixture_candidates(skill_name, prime_excerpt, chat_fn, n):
            if self._write_fixture(skill_name, fx):
                written += 1
        if written:
            logger.info("bootstrapped %d golden fixtures for %s", written, skill_name)
        return written

    def _write_fixture(self, skill_name: str, fx: dict) -> bool:
        import json

        import httpx

        try:
            # json.dumps escapes quotes/backslashes → injection-safe literals; _safe_ident guards skill_name.
            q = (
                f"CREATE golden_fixture SET skill_name='{_safe_ident(skill_name)}', "
                f"input={json.dumps(fx['input'])}, expected_output={json.dumps(fx['expected_output'])}, "
                f"validator_type={json.dumps(fx.get('validator_type', 'contains'))}, "
                f"critical={str(bool(fx.get('critical'))).lower()};"
            )
            r = httpx.post(_SURREAL_URL, content=q, headers=_SURREAL_HEADERS, auth=("root", "root"), timeout=5.0)
            r.raise_for_status()
            return True
        except Exception as exc:
            logger.debug("fixture write failed for %s: %s", skill_name, exc)
            return False

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


# ── golden-fixture bootstrap (local-first agentic data creation, Autodata #38) ─────────────────

def generate_fixture_candidates(
    skill_name: str, prime_excerpt: str, chat_fn, n: int = 3, retries: int = 3
) -> list[dict]:
    """Generate behavioral golden fixtures for a skill via LOCAL inference (chat_fn = GAIA SDK / the
    triune, $0). Converts local compute into eval data so the M1 regression gate has cases to run.
    A few-shot anchor + retry handle the local model's intermittent empty-on-structured-prompt
    calibration (harness N5/L369). Returns [{input, expected_output, validator_type, critical}];
    [] when every retry fails (fail-safe)."""
    import json
    import re

    prompt = (
        f"You are writing regression test cases for an AI skill named '{skill_name}'.\n"
        f"Skill documentation:\n{(prime_excerpt or '')[:1500]}\n\n"
        f"Produce exactly {n} behavioral test cases as a JSON array. Each object has keys "
        '"input" (a realistic concrete user request to this skill), "expected_output" (a SHORT '
        "lowercase keyword or phrase of AT MOST 3 words that the correct answer MUST contain), and "
        '"critical" (true if core to the skill).\n'
        "Example: "
        '[{"input": "summarize this in one word: cats are nice", "expected_output": "cat", '
        '"critical": true}]\n'
        "Return ONLY the JSON array."
    )
    for _ in range(max(1, retries)):
        try:
            raw = chat_fn(prompt)
        except Exception:
            continue
        # Robust extraction: the fast iGPU model often wraps the array in a ```json … ``` fence
        # (and is a thinking model — content arrives AFTER reasoning_content, see _fast_local_chat).
        # Strip the fence first, then grab the first top-level array.
        fenced = re.search(r"```(?:json)?\s*(.*?)```", raw or "", re.DOTALL)
        candidate = fenced.group(1) if fenced else (raw or "")
        m = re.search(r"\[.*\]", candidate, re.DOTALL)
        if not m:
            continue  # empty/unparseable (calibration) → retry
        try:
            arr = json.loads(m.group(0))
        except Exception:
            continue
        out = []
        for item in arr if isinstance(arr, list) else []:
            if isinstance(item, dict) and item.get("input") and item.get("expected_output"):
                out.append(
                    {
                        "input": str(item["input"]),
                        "expected_output": str(item["expected_output"]),
                        "validator_type": "contains",
                        "critical": bool(item.get("critical", False)),
                    }
                )
        if out:
            return out
    return []


def _fast_local_chat(prompt: str) -> str:
    """Default generation chat — the FAST iGPU model directly (NOT the escalating cascade). $0.

    Gemma-4-E4B is a THINKING model: it streams a `reasoning_content` phase first, then the final
    `content`. On abstract skill descriptions the reasoning phase is long, so a low max_tokens budget
    is exhausted mid-reasoning and `content` comes back EMPTY (harness N5: "the constraint is token
    budget, not model type"). max_tokens=2048 lets the reasoning finish and the JSON array land.
    """
    import httpx

    try:
        r = httpx.post(
            _FAST_CHAT_URL,
            json={
                "model": _FAST_GEN_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2048,
                "temperature": 0.4,
            },
            timeout=180,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"].get("content") or ""
    except Exception:
        return ""


# ── pure math (no deps) ───────────────────────────────────────────────────────

def _centroid(vecs: list[list[float]]) -> list[float]:
    n, dim = len(vecs), len(vecs[0])
    return [sum(v[i] for v in vecs) / n for i in range(dim)]


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    mag = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(x * x for x in b))
    return dot / mag if mag else 0.0
