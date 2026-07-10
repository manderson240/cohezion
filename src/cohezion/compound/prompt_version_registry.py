"""Golden-fixture drift gate for SkillRefiner promotions.

Wraps the three SurrealDB tables defined for V-model verification:
  - golden_fixture  — reference (input, expected_output, embedding_768d) per skill
  - prompt_version  — version history of skill prompt content
  - fixture_run     — log of each gate evaluation

check_drift() is fail-open: any error (DB unavailable, Lemonade down, no
fixtures registered) returns True so SkillRefiner continues normally.
"""

from __future__ import annotations

import json
import logging
import math
import re
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
    """M5 + review#4: SLUGIFY skill_name for safe SurrealQL interpolation — non-identifier chars
    ([^A-Za-z0-9_./-]) → '_'. Injection-safe (no quote/semicolon/space survives, so a single-quoted
    literal can't be broken out of) AND total: skills whose name has spaces get a STABLE slug instead
    of raising ValueError — which silently left those skills un-gated and un-bootstrapped. The same
    slug is produced at write and read, so a skill maps consistently. Empty/None → 'unknown'."""
    import re

    slug = re.sub(r"[^A-Za-z0-9_./-]+", "_", (name or "").strip()) or "unknown"
    if slug != name:
        # review#2: distinct names can collide onto one slug (e.g. "my skill" & "my_skill") →
        # shared golden_fixture rows → gate cross-contamination. Make it visible, at least.
        logger.warning("skill_name slugified for SurrealQL: %r -> %r (collision risk)", name, slug)
    return slug


def _surreal_rows(data) -> list:
    """Extract result rows from a SurrealDB /sql response, treating SQL errors (HTTP 200 +
    status='ERR', e.g. a missing table) as NO ROWS — not data. SurrealDB returns the error as a
    STRING 'result'; the old code iterated that string as fixtures, which inverted regression_check's
    fail-policy and FROZE the self-improvement loop on a fresh deploy (review #2)."""
    if not data:
        return []
    row = data[0]
    if not isinstance(row, dict) or row.get("status") == "ERR":
        return []
    result = row.get("result", [])
    return result if isinstance(result, list) else []


# ── safe SurrealQL builder — STRUCTURAL kill of the injection class ─────────────────────────────
# No writer hand-builds an interpolated SurrealQL f-string. Every VALUE goes through _surql_lit
# (json.dumps escapes BOTH quotes AND backslashes → an inert string literal that cannot be broken
# out of — this is what closed the journey_tracker trailing-backslash hole); every FIELD NAME is
# validated as a bare identifier (the one spot json.dumps can't cover); time::now() is the ONLY raw
# expression, reachable solely via the _RawSurql sentinel. Writers pass a dict to _surql_set, so a
# raw f-string literally cannot be constructed. The future BMAD qa_gate writers reuse this.

_IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class _RawSurql:
    """A pre-validated raw SurrealQL expression (e.g. ``time::now()``). The ONLY way to place a
    non-literal into a builder clause — must be a developer-controlled constant, never user input."""

    __slots__ = ("expr",)

    def __init__(self, expr: str) -> None:
        self.expr = expr


_NOW = _RawSurql("time::now()")


def _surql_lit(value: Any) -> str:
    """Render a Python value as an INERT SurrealQL literal. json.dumps emits its own double-quotes
    and escapes quotes+backslashes, so no value can break out of its string literal. ``_RawSurql`` is
    the sole expression escape hatch (constants like ``time::now()``)."""
    if isinstance(value, _RawSurql):
        return value.expr
    return json.dumps(value)


def _surql_set(fields: dict[str, Any]) -> str:
    """Build a SAFE ``k1=v1, k2=v2`` SurrealQL clause (a SET body or a WHERE equality) from a dict.
    Every VALUE passes through ``_surql_lit`` (inert); every FIELD NAME is validated as a bare
    identifier. Writers MUST go through this — they cannot pass a raw interpolated f-string, so the
    injection class is eliminated by construction."""
    parts = []
    for name, value in fields.items():
        if not _IDENT_RE.match(name):
            raise ValueError(f"unsafe SurrealQL field name: {name!r}")
        parts.append(f"{name}={_surql_lit(value)}")
    return ", ".join(parts)


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
                    skill_name,
                    dist,
                    DRIFT_THRESHOLD,
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
            logger.warning(
                "RegressionGate BLOCK: eval failed with fixtures present (%s): %s", skill_name, exc
            )
            return False  # fail-CLOSED: fixtures exist, can't verify → don't promote
        self._log_run(skill_name, drift=-1.0, passed=passed)
        return passed

    # ── internal helpers ──────────────────────────────────────────────────────

    def _load_behavioral_fixtures(self, skill_name: str) -> list[dict[str, Any]]:
        import httpx

        q = (
            "SELECT input, expected_output, validator_type, critical FROM golden_fixture WHERE "
            + _surql_set({"skill_name": _safe_ident(skill_name)})
            + ";"
        )
        r = httpx.post(
            _SURREAL_URL, content=q, headers=_SURREAL_HEADERS, auth=("root", "root"), timeout=5.0
        )
        r.raise_for_status()
        return _surreal_rows(r.json())

    def bootstrap_fixtures(
        self, skill_name: str, prime_excerpt: str, chat_fn=None, n: int = 3, ground_fn=None
    ) -> int:
        """Generate (local-first, $0) + persist behavioral golden fixtures so the M1 regression gate
        has cases to run for `skill_name`. Defaults to the fast iGPU model when chat_fn is None.

        ground_fn (H1 real fix): when provided, each candidate keyword is GROUNDED against the CURRENT
        skill's actual output (`ground_fn(input)`) — a keyword the current skill genuinely produces is
        VERIFIED behaviour (not an LLM guess), so the fixture is marked `critical=True` and CAN hard-
        block a regression. A keyword the current skill does NOT produce is dropped (un-grounded false
        criterion). Without ground_fn, fixtures stay `critical=False` (observe-only) as before.
        Returns the count written (0 on any failure)."""
        chat_fn = chat_fn or _fast_local_chat
        written = 0
        for fx in generate_fixture_candidates(skill_name, prime_excerpt, chat_fn, n):
            if ground_fn is not None:
                fx = _ground_fixture(fx, ground_fn)
                if fx is None:
                    continue  # un-grounded keyword (current skill doesn't produce it) → drop
            if self._write_fixture(skill_name, fx):
                written += 1
        if written:
            logger.info("bootstrapped %d golden fixtures for %s", written, skill_name)
        return written

    def _write_fixture(self, skill_name: str, fx: dict) -> bool:
        import httpx

        try:
            # _surql_set renders every value via json.dumps (inert) — injection-safe by construction.
            q = (
                "CREATE golden_fixture SET "
                + _surql_set(
                    {
                        "skill_name": _safe_ident(skill_name),
                        "input": fx["input"],
                        "expected_output": fx["expected_output"],
                        "validator_type": fx.get("validator_type", "contains"),
                        "critical": bool(fx.get("critical")),
                    }
                )
                + ";"
            )
            r = httpx.post(
                _SURREAL_URL,
                content=q,
                headers=_SURREAL_HEADERS,
                auth=("root", "root"),
                timeout=5.0,
            )
            r.raise_for_status()
            return True
        except Exception as exc:
            logger.debug("fixture write failed for %s: %s", skill_name, exc)
            return False

    def _load_fixtures(self, skill_name: str) -> list[dict[str, Any]]:
        import httpx

        q = (
            "SELECT embedding_768d FROM golden_fixture WHERE "
            + _surql_set({"skill_name": _safe_ident(skill_name)})
            + ";"
        )
        r = httpx.post(
            _SURREAL_URL, content=q, headers=_SURREAL_HEADERS, auth=("root", "root"), timeout=5.0
        )
        r.raise_for_status()
        return _surreal_rows(r.json())

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
                "CREATE fixture_run SET "
                + _surql_set(
                    {
                        "skill_name": _safe_ident(skill_name),
                        "drift_score": round(drift, 4),
                        "passed": bool(passed),
                        "created_at": _NOW,
                    }
                )
                + ";"
            )
            httpx.post(
                _SURREAL_URL,
                content=q,
                headers=_SURREAL_HEADERS,
                auth=("root", "root"),
                timeout=3.0,
            )
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
    A SINGLE per-fixture execution error fails OPEN (skip it), but if WELL-FORMED fixtures exist and
    NONE could be evaluated (e.g. inference down), fail CLOSED — the candidate is unverified and must
    not auto-promote (bughunt #8: matches regression_check's M1 contract; the old code swallowed all
    per-fixture errors and returned True → promotion allowed). Pure: run_fn(candidate, input)->str."""
    well_formed = evaluated = 0
    critical_unevaluable = False
    for f in fixtures:
        inp, exp = f.get("input"), f.get("expected_output")
        if not inp or exp is None:
            continue  # malformed fixture — not a real test case
        well_formed += 1
        try:
            out = run_fn(candidate, inp)
        except Exception:
            if f.get("critical", True):
                critical_unevaluable = True  # a CRITICAL case couldn't be verified (review #1)
            continue  # per-fixture error — fail open only for NON-critical
        evaluated += 1
        if not _validate(out, exp, f.get("validator_type") or "contains") and f.get(
            "critical", True
        ):
            logger.info(
                "RegressionGate BLOCK: critical fixture regressed (input=%r)", str(inp)[:50]
            )
            return False
    # fail-CLOSED if a CRITICAL fixture couldn't be evaluated (not just the all-or-nothing case),
    # or if well-formed fixtures exist but NONE evaluated — the candidate is unverified.
    if critical_unevaluable or (well_formed and evaluated == 0):
        logger.warning("RegressionGate BLOCK: critical/all fixtures unevaluable — fail-closed")
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
                expected = str(item["expected_output"])
                # WIRING H1 anti-poisoning: reject DEGENERATE expected_output. A 1-char or
                # whitespace-only keyword `_validate(..., "contains")`-matches almost any output,
                # so it would silently NEVER block — a poisoned fixture that auto-promotes anything.
                # Require >=3 non-space chars of real signal.
                if len(expected.replace(" ", "")) < 3:
                    continue
                # DEFAULT critical=False: an auto-generated (hallucinated-criterion-risk) fixture
                # must NOT be able to HARD-block a promotion. Only a human / later promotion step
                # may mark a fixture critical=True. evaluate_regression only blocks on critical
                # fixtures, so an unsupervised bootstrap is observe-and-log, never a hard gate.
                out.append(
                    {
                        "input": str(item["input"]),
                        "expected_output": expected,
                        "validator_type": "contains",
                        "critical": False,
                    }
                )
        if out:
            return out
    return []


def _ground_fixture(fx: dict, ground_fn) -> dict | None:
    """H1 real fix — confirm a candidate keyword against the CURRENT skill's actual output, resolving
    the poisoning↔dormancy contradiction. Returns the fixture marked ``critical=True`` when the current
    skill's output CONTAINS the keyword (grounded = verified current behaviour → safe to HARD-block on a
    regression); returns ``None`` to DROP it when the keyword is not produced (an un-grounded LLM guess
    that would be a false criterion). Fail-safe: any ``ground_fn`` error → ``None`` (never write an
    untrustworthy fixture). Uses the same ``_validate`` the gate uses, so grounding and gating agree."""
    try:
        current_out = ground_fn(fx["input"])
    except Exception:
        return None
    if _validate(current_out, fx["expected_output"], fx.get("validator_type", "contains")):
        return {**fx, "critical": True}
    return None


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
