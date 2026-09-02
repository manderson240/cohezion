"""ModelScoutLane — Lane 1.

Scans for new models that could improve the local silicon neural net.
Sources:
  1. HuggingFace daily papers feed (JSON; requires HF_TOKEN) → each
     paper's LINKED MODELS via ``/api/models?filter=arxiv:<id>``
  2. arXiv abstracts (helper only — not yet a candidate source)
  3. Lemonade /v1/models on port 13305 (live catalog diff — not yet wired)

For each candidate, parse the model card. Drop `card_missing`
candidates. Drop candidates whose CapabilityProfile doesn't beat any
existing default registry entry for at least one task — the lane is
about IMPROVING the local silicon, not just discovering models.

Then the HARDWARE-FIT gate (skill: local-model-hardware-fit-triage,
Gate 1): price weights + KV cache with ``hf-mem`` (HTTP range reads of
the safetensors/GGUF headers — nothing is downloaded) and drop any
candidate that does not fit ``available RAM − N3 floor``. A candidate
the lane cannot price is dropped too: the 2026-08-31 freeze was an
UNPRICED load, so "unknown" must not read as "fits".

The lane does NOT call extend_claude_aligned; it reads HTTP directly
so the cloud-escalation budget is preserved for the synthesis lane
which actually needs it.
"""

from __future__ import annotations

import logging
import os
import re
import time
from typing import Any

import httpx

from cohezion.researcher.daily_researcher import DryRunReport, _BaseLane
from cohezion.researcher.hf_mem_fit import (
    FIT_MAX_MODEL_LEN,
    FitEstimator,
    default_fit_budget_bytes,
    hf_mem_estimate,
)


# ``cohezion.inference.*`` is imported lazily inside the methods that need it:
# DailyResearcher() is constructed by many callers purely for ``.fleet_lock``,
# and importing any inference submodule executes the whole inference package.


logger = logging.getLogger(__name__)


# ── HTTP fetcher helpers (httpx, async) ──────────────────────────────────────


_HF_BASE = "https://huggingface.co"
_ARXIV_BASE = "https://arxiv.org"
_LEMONADE_BASE = "http://127.0.0.1:13305"


def _hf_headers() -> dict[str, str]:
    """Bearer header when a Hub token is present (the daily feed 401s without one)."""
    token = os.environ.get("HF_TOKEN") or os.environ.get("HF_API_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}


async def _fetch_hf_daily_papers(client: httpx.AsyncClient) -> tuple[list[str], str]:
    """Fetch the HuggingFace daily papers feed.

    Returns ``(arxiv_ids, status_note)``. The feed is JSON —
    ``[{"paper": {"id": "<arxiv_id>", ...}, ...}, ...]`` — and requires
    a Hub token (HTTP 401 otherwise). Failures are returned in the note,
    never raised: the lane is best-effort and the cron must not fail
    because of a flaky upstream, but the reason must not be swallowed.
    """
    try:
        r = await client.get(f"{_HF_BASE}/api/daily-papers", headers=_hf_headers(), timeout=10.0)
    except httpx.HTTPError as e:  # TimeoutException is an HTTPError subclass
        return [], f"hf_daily_papers fetch failed: {e}"
    if r.status_code != 200:
        hint = " (set HF_TOKEN; the feed requires auth)" if r.status_code == 401 else ""
        return [], f"hf_daily_papers HTTP {r.status_code}{hint}"
    try:
        entries = r.json()
    except ValueError:
        return [], "hf_daily_papers: non-JSON body"
    ids: list[str] = []
    for entry in entries if isinstance(entries, list) else []:
        paper = entry.get("paper", {}) if isinstance(entry, dict) else {}
        arxiv_id = paper.get("id") if isinstance(paper, dict) else None
        if isinstance(arxiv_id, str) and arxiv_id:
            ids.append(arxiv_id)
    return ids, f"hf_daily_papers={len(ids)}"


async def _fetch_models_for_paper(
    client: httpx.AsyncClient, arxiv_id: str
) -> tuple[list[str], str | None]:
    """Models whose card links this paper (``/api/models?filter=arxiv:<id>``).

    Returns ``(model_ids, error_note)`` — a failed fetch must reach the
    report, or "endpoint down all day" reads as "no new models today".
    """
    try:
        r = await client.get(
            f"{_HF_BASE}/api/models",
            params={"filter": f"arxiv:{arxiv_id}", "limit": 20},
            headers=_hf_headers(),
            timeout=10.0,
        )
        r.raise_for_status()
        return [m["id"] for m in r.json() if isinstance(m, dict) and m.get("id")], None
    except (httpx.HTTPError, ValueError) as e:
        logger.warning("HF linked-models for %s failed: %s", arxiv_id, e)
        return [], f"linked_models_fetch_failed: {arxiv_id}: {e}"


async def _fetch_arxiv_abstract(client: httpx.AsyncClient, arxiv_id: str) -> str:
    """Fetch a single arXiv abstract."""
    try:
        r = await client.get(f"{_ARXIV_BASE}/abs/{arxiv_id}", timeout=10.0)
        r.raise_for_status()
        return r.text
    except httpx.HTTPError as e:
        logger.warning("arXiv %s fetch failed: %s", arxiv_id, e)
        return ""


async def _fetch_hf_model_card(client: httpx.AsyncClient, model_id: str) -> str:
    """Fetch a HuggingFace model card README."""
    try:
        r = await client.get(
            f"{_HF_BASE}/{model_id}/raw/main/README.md", headers=_hf_headers(), timeout=10.0
        )
        r.raise_for_status()
        return r.text
    except httpx.HTTPError as e:
        logger.debug("HF card %s fetch failed: %s", model_id, e)
        return ""


# ── Hardware-fit gate: pricing lives in ``cohezion.researcher.hf_mem_fit`` ──

# Fan-out bounds: run() executes under DailyResearcher's shared fleet lock, whose other
# acquirers wait at most 300 s — an uncapped scout with 60 s hf-mem calls would starve them.
_MAX_CANDIDATES_PER_RUN = 25
_RUN_DEADLINE_S = 240.0


# ── The lane ────────────────────────────────────────────────────────────────


class ModelScoutLane(_BaseLane):
    """Lane 1: card-first model scout with an hf-mem hardware-fit gate."""

    lane_name = "model_scout"

    def __init__(
        self,
        researcher: Any,
        *,
        fit_estimator: FitEstimator | None = None,
        budget_bytes: int | None = None,
        max_candidates: int = _MAX_CANDIDATES_PER_RUN,
        deadline_s: float = _RUN_DEADLINE_S,
    ) -> None:
        super().__init__(researcher)
        self._fit_estimator: FitEstimator = fit_estimator or hf_mem_estimate
        self._budget_bytes = budget_bytes  # None → measured live at run()
        self._max_candidates = max_candidates
        self._deadline_s = deadline_s

    async def run(self, dry_run: bool) -> DryRunReport:
        report = DryRunReport(lane=self.lane_name, dry_run=dry_run)
        if dry_run:
            report.notes.append(
                "dry-run: no model loads attempted; would scan HF daily papers → "
                "linked models, drop card_missing / no_improvement, then hf-mem fit-gate"
            )
            return report

        budget = (
            self._budget_bytes if self._budget_bytes is not None else default_fit_budget_bytes()
        )
        report.notes.append(f"fit_budget_gb={budget / 2**30:.1f}")
        seen: set[str] = set()
        started = time.monotonic()
        async with httpx.AsyncClient() as client:
            arxiv_ids, feed_note = await _fetch_hf_daily_papers(client)
            report.notes.append(feed_note)
            for arxiv_id in arxiv_ids:
                model_ids, fetch_note = await _fetch_models_for_paper(client, arxiv_id)
                if fetch_note:
                    report.notes.append(fetch_note)
                for model_id in model_ids:
                    if model_id in seen:
                        continue
                    if self._out_of_budget(len(seen), started, report):
                        break
                    seen.add(model_id)
                    await self._consider(client, model_id, budget, report)
                else:
                    continue
                break

        unknown = sum(n.startswith("dropped fit_unknown:") for n in report.notes)
        if seen and unknown == len(seen):
            # Every candidate failed the SAME gate: hf-mem shape drift or uvx missing,
            # not a quiet day. Without this the two are indistinguishable.
            report.notes.append(f"all_candidates_dropped_fit_unknown: {unknown} (hf-mem broken?)")
        report.notes.append(f"candidates kept: {len(report.candidates)}")
        return report

    def _out_of_budget(self, considered: int, started: float, report: DryRunReport) -> bool:
        elapsed = time.monotonic() - started
        if considered < self._max_candidates and elapsed <= self._deadline_s:
            return False
        report.notes.append(
            f"stopped: fan-out bound reached after {considered} candidates "
            f"(max {self._max_candidates}, {elapsed:.0f}s of {self._deadline_s:.0f}s)"
        )
        return True

    async def _consider(
        self, client: httpx.AsyncClient, model_id: str, budget: int, report: DryRunReport
    ) -> None:
        """Cheap gates first (card, improvement), the subprocess fit gate last."""
        from cohezion.inference.capability_profile import CardParseError, CardParser

        card_md = await _fetch_hf_model_card(client, model_id)
        if not card_md:
            report.notes.append(f"dropped card_missing: {model_id}")
            return
        try:
            profile = CardParser.parse_huggingface(card_md, model_id=model_id)
        except CardParseError as e:
            report.notes.append(f"dropped card_unparseable: {model_id}: {e}")
            return
        if not self._beats_any_default(profile):
            report.notes.append(
                f"dropped no_improvement: {model_id} (no task beats the default registry)"
            )
            return
        est = await self._fit_estimator(model_id)
        if est is None:
            report.notes.append(f"dropped fit_unknown: {model_id} (no hf-mem estimate)")
            return
        need_gb = est.total_bytes / 2**30
        priced = est.filename or "safetensors"
        if est.total_bytes > budget:
            report.notes.append(
                f"dropped fit_exceeds_budget: {model_id} needs {need_gb:.1f}GB "
                f"({priced}: weights+kv@{FIT_MAX_MODEL_LEN}) > budget {budget / 2**30:.1f}GB"
            )
            return
        report.notes.append(
            f"fit_ok: {model_id} {need_gb:.1f}GB ({priced}) <= {budget / 2**30:.1f}GB"
        )
        report.candidates.append(model_id)

    def _beats_any_default(self, profile) -> bool:
        """True if the card claims a strength no default profile already covers.

        Card strengths are free-text bullets ("code completion for python");
        default strengths are snake_case capabilities ("code_completion"). A
        bullet is COVERED when some default capability's tokens all appear in
        it; a card beats the defaults only if at least one bullet is not
        covered. (Raw set difference never matched across the two vocabularies,
        and the parser fixes optimal_ctx=32768 while defaults start at 8192, so
        the previous ctx branch passed every card — both gates were dead.)
        """
        from cohezion.inference.default_profiles import DEFAULT_PROFILES

        known = {frozenset(s.split("_")) for d in DEFAULT_PROFILES.values() for s in d.strengths}
        for bullet in profile.strengths:
            tokens = set(re.findall(r"[a-z0-9]+", bullet.lower()))
            if not any(cap <= tokens for cap in known):
                return True
        return False
