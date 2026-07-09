"""SiriuS-style execution trace augmentor for SkillOpt corpus quality.

Implements the Library Augmentation Procedure from SiriuS (arXiv:2502.04780):
  1. SELECT low-scoring execution traces from SurrealDB
  2. Reflect on each trace via local Lemonade model (free, AMD silicon)
  3. Store improved synthetic traces as high-quality SkillOpt training data

Inference path (preferred → fallback):
  GAIA SDK LemonadeClient → Lemonade OmniRouter :13305 → AMD iGPU
  Raw httpx → :13305/v1/chat/completions (if GAIA not installed)

The GAIA path is preferred because it reuses the already-running Lemonade fleet
(no second process, OOM-safe on unified memory) and benefits from GAIA's
AMD-native tier routing (XDNA2 NPU → RDNA 3.5 iGPU → CPU fallback).

The augmented traces have `is_augmented=true` and `parent_id` pointing back
to the original, so SkillOpt can distinguish natural from synthetic samples.

Usage:
    augmentor = SurrealTraceAugmentor()
    results = augmentor.augment_batch(max_score=0.5, limit=20)
    print(f"Augmented {len(results)} low-quality traces")
"""

from __future__ import annotations

import logging
from typing import Any

import httpx


logger = logging.getLogger(__name__)

_SURREAL_URL = "http://127.0.0.1:8001/sql"
_SURREAL_AUTH = ("root", "root")
_SURREAL_HEADERS = {
    "surreal-ns": "cohezion",
    "surreal-db": "main",
    "Content-Type": "text/plain",
    "Accept": "application/json",
}
# GAIA OmniRouter — primary inference path via LemonadeClient
_GAIA_ROUTER_URL = "http://localhost:13305/api/v1"
# Fallback raw HTTP path (httpx, no GAIA SDK dependency)
_LEMONADE_URL = "http://localhost:13305/v1/chat/completions"
# iGPU tier — fast enough for batch augmentation, quality sufficient for reflection
_AUGMENT_MODEL = "Gemma-4-E4B-it-GGUF"

# Unit-test artifact names that should not be augmented (no real task content)
_SKIP_SKILL_NAMES = frozenset({"TEST", "test", "skill", "generator", "unknown", ""})


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class SurrealTraceAugmentor:
    """Augments low-quality execution traces for SkillOpt corpus improvement.

    Each call to augment_batch() is idempotent: traces that have already been
    augmented (is_augmented=true) are excluded from future augmentation rounds.
    """

    def __init__(
        self,
        surreal_url: str = _SURREAL_URL,
        lemonade_url: str = _LEMONADE_URL,
        model: str = _AUGMENT_MODEL,
        timeout: float = 60.0,
        gaia_router_url: str = _GAIA_ROUTER_URL,
    ) -> None:
        self._surreal_url = surreal_url
        self._lemonade_url = lemonade_url
        self._gaia_router_url = gaia_router_url
        self._model = model
        self._http = httpx.Client(timeout=timeout)
        # Prefer GAIA SDK's LemonadeClient — zero extra process, AMD-native routing.
        # Falls back to raw httpx if amd-gaia is not installed.
        self._gaia_client: Any | None = self._init_gaia_client()
        self._ensure_augmentation_fields()

    def _init_gaia_client(self) -> Any | None:
        """Try to build a GAIA LemonadeClient; return None if not installed."""
        try:
            from gaia.llm.lemonade_client import LemonadeClient

            client = LemonadeClient(
                base_url=self._gaia_router_url,
                model=self._model,
                verbose=False,
            )
            logger.debug("SurrealTraceAugmentor: using GAIA LemonadeClient for inference")
            return client
        except Exception as exc:
            logger.debug(
                "SurrealTraceAugmentor: GAIA SDK unavailable (%s), falling back to httpx", exc
            )
            return None

    def _ensure_augmentation_fields(self) -> None:
        """Extend execution_trace schema with augmentation tracking fields."""
        ddl = """
        DEFINE FIELD IF NOT EXISTS is_augmented ON execution_trace TYPE bool;
        DEFINE FIELD IF NOT EXISTS parent_id    ON execution_trace TYPE option<string>;
        """
        try:
            self._http.post(
                self._surreal_url,
                content=ddl,
                headers=_SURREAL_HEADERS,
                auth=_SURREAL_AUTH,
                timeout=10.0,
            )
        except Exception as exc:
            logger.debug("SurrealTraceAugmentor schema extension failed (non-fatal): %s", exc)

    def _fetch_low_quality_traces(
        self, max_score: float, limit: int, skill_filter: str | None
    ) -> list[dict[str, Any]]:
        """Query execution_trace for unaugmented traces below the quality threshold."""
        skill_clause = ""
        if skill_filter:
            skill_clause = f'AND skill_name = "{_escape(skill_filter)}" '

        sql = (
            f"SELECT id, skill_name, input, output, score, status "
            f"FROM execution_trace "
            f"WHERE score < {max_score} "
            f"AND (is_augmented = false OR is_augmented = NONE) "
            f"AND output != '' "
            f"{skill_clause}"
            f"ORDER BY score ASC "
            f"LIMIT {limit};"
        )
        try:
            resp = self._http.post(
                self._surreal_url,
                content=sql,
                headers=_SURREAL_HEADERS,
                auth=_SURREAL_AUTH,
            )
            results = resp.json()
            if isinstance(results, list) and results:
                rows = results[0].get("result", [])
                # Filter out unit-test artifacts
                return [r for r in rows if r.get("skill_name", "") not in _SKIP_SKILL_NAMES]
        except Exception as exc:
            logger.debug("SurrealTraceAugmentor fetch failed: %s", exc)
        return []

    def _reflect_and_improve(self, trace: dict[str, Any]) -> str:
        """Call Lemonade to produce an improved output for a low-quality trace.

        Inference path priority:
          1. GAIA SDK LemonadeClient (AMD-native, zero extra process, router at :13305)
          2. Raw httpx POST to :13305/v1/chat/completions (fallback)
        """
        skill_name = trace.get("skill_name", "unknown")
        input_text = trace.get("input", "")[:1500]
        output_text = trace.get("output", "")[:2000]
        score = trace.get("score", 0.0)

        prompt = (
            f"You are improving a compound AI skill execution trace for SkillOpt training data.\n\n"
            f"Skill: {skill_name}\n"
            f"Task: {input_text}\n"
            f"Current output (quality score {score:.2f}/1.0):\n{output_text}\n\n"
            f"The current output is below quality threshold. Rewrite it as a high-quality, "
            f"complete, accurate response to the task. Focus on correctness and clarity. "
            f"Return only the improved output — no explanations, no preamble."
        )

        # --- GAIA path (preferred) ---
        if self._gaia_client is not None:
            try:
                result = self._gaia_client.chat_completions(
                    model=self._model,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=1024,
                    temperature=0.2,
                )
                text = result["choices"][0]["message"].get("content", "").strip()
                if text:
                    return text
                logger.debug(
                    "GAIA LemonadeClient returned empty for skill '%s' (calibration), "
                    "falling back to httpx",
                    skill_name,
                )
            except Exception as exc:
                logger.debug(
                    "GAIA reflection failed for skill '%s': %s — falling back to httpx",
                    skill_name,
                    exc,
                )

        # --- httpx fallback ---
        try:
            resp = self._http.post(
                self._lemonade_url,
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1024,
                    "temperature": 0.2,
                },
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logger.debug("Lemonade reflection call failed for skill '%s': %s", skill_name, exc)
            return ""

    def _store_augmented_trace(
        self, original: dict[str, Any], improved_output: str, improved_score: float = 0.8
    ) -> str | None:
        """Write the augmented trace to SurrealDB and return its record ID."""
        parent_id = str(original.get("id", ""))
        skill_name = _escape(original.get("skill_name", "unknown"))
        input_text = _escape(original.get("input", "")[:2000])
        output_text = _escape(improved_output[:4000])
        status = "success"

        sql = (
            f"CREATE execution_trace SET "
            f'skill_name = "{skill_name}", '
            f'input = "{input_text}", '
            f'output = "{output_text}", '
            f"score = {improved_score}, "
            f'status = "{status}", '
            f"tokens_used = 0, "
            f'model_tier = "igpu", '
            f"is_augmented = true, "
            f'parent_id = "{_escape(parent_id)}";'
        )
        try:
            resp = self._http.post(
                self._surreal_url,
                content=sql,
                headers=_SURREAL_HEADERS,
                auth=_SURREAL_AUTH,
            )
            results = resp.json()
            if isinstance(results, list) and results:
                rows = results[0].get("result", [])
                if rows:
                    return str(rows[0].get("id", ""))
        except Exception as exc:
            logger.debug("SurrealTraceAugmentor store failed: %s", exc)
        return None

    def augment_batch(
        self,
        max_score: float = 0.5,
        limit: int = 20,
        skill_filter: str | None = None,
        improved_score: float = 0.8,
    ) -> list[tuple[str, str]]:
        """Augment up to `limit` low-scoring traces, returning (original_id, augmented_id) pairs.

        Args:
            max_score: Only augment traces with score below this threshold.
            limit: Maximum number of traces to augment per call.
            skill_filter: Optional canonical skill name to target (e.g. "IDEATOR_PRIME").
            improved_score: Score assigned to augmented traces (default 0.8).

        Returns:
            List of (original_id, augmented_id) pairs for successfully augmented traces.
        """
        traces = self._fetch_low_quality_traces(max_score, limit, skill_filter)
        if not traces:
            logger.info(
                "SurrealTraceAugmentor: no eligible traces found (max_score=%.2f)", max_score
            )
            return []

        logger.info(
            "SurrealTraceAugmentor: augmenting %d traces (max_score=%.2f)", len(traces), max_score
        )
        results: list[tuple[str, str]] = []
        for trace in traces:
            improved = self._reflect_and_improve(trace)
            if not improved:
                continue
            augmented_id = self._store_augmented_trace(trace, improved, improved_score)
            if augmented_id:
                original_id = str(trace.get("id", ""))
                results.append((original_id, augmented_id))
                logger.debug(
                    "Augmented trace %s → %s for skill '%s'",
                    original_id,
                    augmented_id,
                    trace.get("skill_name", "?"),
                )

        logger.info("SurrealTraceAugmentor: produced %d augmented traces", len(results))
        return results

    def stats(self) -> dict[str, int]:
        """Return counts of natural vs augmented traces in the corpus."""
        sql = (
            "SELECT "
            "  count() AS total, "
            "  count(is_augmented = true) AS augmented, "
            "  count(is_augmented = false OR is_augmented = NONE) AS natural "
            "FROM execution_trace;"
        )
        try:
            resp = self._http.post(
                self._surreal_url,
                content=sql,
                headers=_SURREAL_HEADERS,
                auth=_SURREAL_AUTH,
            )
            results = resp.json()
            if isinstance(results, list) and results:
                rows = results[0].get("result", [])
                if rows:
                    return {
                        "total": rows[0].get("total", 0),
                        "augmented": rows[0].get("augmented", 0),
                        "natural": rows[0].get("natural", 0),
                    }
        except Exception as exc:
            logger.debug("SurrealTraceAugmentor.stats failed: %s", exc)
        return {"total": 0, "augmented": 0, "natural": 0}


def make_augmentor() -> SurrealTraceAugmentor | None:
    """Factory — returns None if SurrealDB is unreachable."""
    try:
        aug = SurrealTraceAugmentor()
        logger.info("SurrealTraceAugmentor ready")
        return aug
    except Exception as exc:
        logger.debug("SurrealTraceAugmentor unavailable: %s", exc)
        return None
