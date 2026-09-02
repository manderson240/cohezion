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

import asyncio
import contextlib
import json
import logging
import os
import re
import shutil
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

import httpx

from cohezion.researcher.daily_researcher import DryRunReport, _BaseLane


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


# ── Hardware-fit gate (hf-mem) ──────────────────────────────────────────────

# The working quant the gate prices for GGUF repos (fit-triage: "Q4 max params ≈ RAM × 2").
# Token-bounded so "IQ4_K_M" and "Q4_K_M_XL" (different quants) do not match.
_PREFERRED_QUANT_RE = re.compile(r"(?<![a-z0-9])q4_k_m(?![a-z0-9_])", re.IGNORECASE)
# Context the KV cache is priced at — the ctx cap the :13305 router serves models with.
_FIT_MAX_MODEL_LEN = 16384
_HF_MEM_TIMEOUT_S = 60.0
# Pinned: an unpinned `uvx hf-mem` whose JSON shape drifts would turn every candidate into
# fit_unknown — a silent zero. Bump deliberately, re-running the live smoke in the tests' docstring.
_HF_MEM_SPEC = "hf-mem==0.5.5"
# Fan-out bounds: run() executes under DailyResearcher's shared fleet lock, whose other
# acquirers wait at most 300 s — an uncapped scout with 60 s hf-mem calls would starve them.
_MAX_CANDIDATES_PER_RUN = 25
_RUN_DEADLINE_S = 240.0


def _size(value: Any) -> int | None:
    """A positive byte count, or None for anything else (null, bool, str, ≤0)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        return None
    return int(value)


@dataclass(frozen=True)
class FitEstimate:
    """Bytes a candidate needs to serve: weights + KV cache at ``_FIT_MAX_MODEL_LEN``."""

    model_id: str
    filename: str  # the GGUF file priced; "" for safetensors repos
    weights_bytes: int
    kv_bytes: int

    @property
    def total_bytes(self) -> int:
        return self.weights_bytes + self.kv_bytes


FitEstimator = Callable[[str], Awaitable["FitEstimate | None"]]


def _parse_hf_mem_output(payload: dict[str, Any]) -> FitEstimate | None:
    """Parse ``hf-mem --json-output`` (``--experimental`` form).

    Safetensors repos give scalar ``memory``/``kv_cache``; GGUF repos give
    per-file dicts (``total_memory`` null). For GGUF the gate prices the
    working quant (``Q4_K_M``), falling back to the smallest file.
    """
    model_id = str(payload.get("model_id", ""))
    memory = payload.get("memory")
    kv = payload.get("kv_cache")
    scalar = _size(memory)
    if scalar is not None:
        return FitEstimate(model_id, "", scalar, _size(kv) or 0)
    if isinstance(memory, dict):
        kv_map = kv if isinstance(kv, dict) else {}
        sized = {f: s for f, v in memory.items() if (s := _size(v)) is not None}
        if not sized:
            return None
        preferred = [f for f in sized if _PREFERRED_QUANT_RE.search(f)]
        fname = preferred[0] if preferred else min(sized, key=lambda f: sized[f])
        return FitEstimate(model_id, fname, sized[fname], _size(kv_map.get(fname)) or 0)
    return None


async def hf_mem_estimate(
    model_id: str, *, max_model_len: int = _FIT_MAX_MODEL_LEN
) -> FitEstimate | None:
    """Default estimator: ``uvx hf-mem`` (Hub HTTP range reads; no download, no load).

    Returns None when hf-mem is unavailable, times out, fails, or emits no
    JSON — the caller treats None as "cannot price", which is a DROP.
    """
    uvx = shutil.which("uvx")
    if uvx is None:
        logger.warning("hf-mem unavailable: uvx not on PATH")
        return None
    argv = [
        uvx,
        "--from",
        _HF_MEM_SPEC,
        "hf-mem",
        "--model-id",
        model_id,
        "--experimental",
        "--max-model-len",
        str(max_model_len),
        "--json-output",
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *argv, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
    except OSError as e:
        logger.warning("hf-mem spawn failed for %s: %s", model_id, e)
        return None
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=_HF_MEM_TIMEOUT_S)
    except TimeoutError:
        with contextlib.suppress(ProcessLookupError):  # may have exited between checks
            proc.kill()
            await proc.wait()  # reap — a killed-but-unwaited child is a zombie
        logger.warning("hf-mem timed out (%.0fs) for %s", _HF_MEM_TIMEOUT_S, model_id)
        return None
    if proc.returncode != 0:
        logger.warning(
            "hf-mem rc=%s for %s: %s",
            proc.returncode,
            model_id,
            err.decode(errors="replace")[-300:],
        )
        return None
    for line in reversed(out.decode(errors="replace").splitlines()):
        line = line.strip()
        if line.startswith("{"):
            try:
                return _parse_hf_mem_output(json.loads(line))
            except (TypeError, ValueError):  # ValueError covers JSONDecodeError
                logger.warning("hf-mem emitted an unparseable payload for %s", model_id)
                return None
    return None


def default_fit_budget_bytes() -> int:
    """Fit-triage Gate 1: ``available RAM − N3 floor`` (the 16 GB line between working and frozen)."""
    import psutil

    from cohezion.core.resource_management.session_monitor import N3_FLOOR_GB

    return max(0, int(psutil.virtual_memory().available - N3_FLOOR_GB * 2**30))


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
                f"({priced}: weights+kv@{_FIT_MAX_MODEL_LEN}) > budget {budget / 2**30:.1f}GB"
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
