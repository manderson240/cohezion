"""Tests for the ModelScoutLane (Lane 1) — the REAL lane in
``cohezion.researcher.lanes.model_scout``.

Contracts:
- ``DailyResearcher().model_scout`` IS the real lane (consumption, not the
  in-file stub that used to shadow it).
- The HF daily-papers feed is JSON (``[{"paper": {"id": <arxiv_id>, ...}}]``).
  Each paper is resolved to its linked models via
  ``GET /api/models?filter=arxiv:<id>``.
- For each linked model: fetch the card, parse it, drop ``card_missing`` /
  ``card_unparseable`` / ``no_improvement``.
- Hardware-fit gate (hf-mem): a candidate whose estimated weights + KV cache
  exceed the box budget is dropped (``fit_exceeds_budget``); an estimate the
  lane cannot obtain is ALSO dropped (``fit_unknown`` — conservative: the
  08-31 freeze came from an unpriced load).
- A 401 from the feed is reported in the notes, never silently swallowed.
- ``dry_run=True`` makes no network calls.
"""

from __future__ import annotations

import pytest


pytest.importorskip("respx")

import asyncio

import httpx
import respx

from cohezion.researcher.daily_researcher import DailyResearcher, DryRunReport
from cohezion.researcher.hf_mem_fit import FitEstimate, parse_hf_mem_output
from cohezion.researcher.lanes.model_scout import ModelScoutLane


_ARXIV_ID = "2609.00001"
_MODEL_ID = "acme/new-model-8b"

_FEED_JSON = [{"paper": {"id": _ARXIV_ID, "title": "A New Model"}, "title": "A New Model"}]
_LINKED_MODELS_JSON = [{"id": _MODEL_ID, "modelId": _MODEL_ID}]

# A card the CardParser accepts, carrying a strength no default profile has,
# so ``_beats_any_default`` is True.
_CARD_MD = """---
license: apache-2.0
---
# New Model 8B

## Intended Uses
- underwater basket weaving
- code completion

## Limitations
- long-horizon reasoning
"""

# Every strength here is COVERED by a default-profile capability token set
# ("code_completion", "general_chat") — the scout must not recommend it.
_KNOWN_CAPS_CARD_MD = """---
license: apache-2.0
---
# Same Old 8B

## Intended Uses
- fast code completion
- general chat and assistance

## Limitations
- long-horizon reasoning
"""

_GIB = 2**30


async def _small_fit(model_id: str) -> FitEstimate | None:
    return FitEstimate(
        model_id=model_id, filename="Q4_K_M", weights_bytes=5 * _GIB, kv_bytes=2 * _GIB
    )


async def _huge_fit(model_id: str) -> FitEstimate | None:
    return FitEstimate(
        model_id=model_id, filename="Q4_K_M", weights_bytes=90 * _GIB, kv_bytes=24 * _GIB
    )


async def _unknown_fit(model_id: str) -> FitEstimate | None:
    return None


def _mock_happy_path(
    mock_hf: respx.MockRouter, *, card_status: int = 200, card_md: str = _CARD_MD
) -> None:
    mock_hf.get("/api/daily-papers").mock(return_value=httpx.Response(200, json=_FEED_JSON))
    mock_hf.get("/api/models", params={"filter": f"arxiv:{_ARXIV_ID}"}).mock(
        return_value=httpx.Response(200, json=_LINKED_MODELS_JSON)
    )
    mock_hf.get(f"/{_MODEL_ID}/raw/main/README.md").mock(
        return_value=httpx.Response(card_status, text=card_md if card_status == 200 else "")
    )


# ── Consumption: DailyResearcher wires the REAL lane ────────────────────────


def test_daily_researcher_wires_real_model_scout_lane():
    """The orchestrator must run the real lane, not the in-file stub."""
    researcher = DailyResearcher()
    assert isinstance(researcher.model_scout, ModelScoutLane)
    assert researcher.model_scout in researcher._lanes


# ── Feed → paper → linked model → candidate ─────────────────────────────────


@pytest.mark.asyncio
async def test_run_resolves_daily_paper_to_linked_model_candidate():
    lane = ModelScoutLane(DailyResearcher(), fit_estimator=_small_fit, budget_bytes=40 * _GIB)
    with respx.mock(assert_all_called=True, base_url="https://huggingface.co") as mock_hf:
        _mock_happy_path(mock_hf)
        report = await lane.run(dry_run=False)
    assert isinstance(report, DryRunReport)
    assert report.candidates == [_MODEL_ID]
    assert any(f"fit_ok: {_MODEL_ID}" in n for n in report.notes)


@pytest.mark.asyncio
async def test_run_drops_candidate_exceeding_memory_budget():
    """Discriminating pair with the test above: identical fixtures, only the
    fit estimate differs. An implementation that ignores the gate keeps both."""
    lane = ModelScoutLane(DailyResearcher(), fit_estimator=_huge_fit, budget_bytes=40 * _GIB)
    with respx.mock(assert_all_called=False, base_url="https://huggingface.co") as mock_hf:
        _mock_happy_path(mock_hf)
        report = await lane.run(dry_run=False)
    assert report.candidates == []
    assert any(f"dropped fit_exceeds_budget: {_MODEL_ID}" in n for n in report.notes)


@pytest.mark.asyncio
async def test_run_drops_candidate_when_fit_unknown():
    """No estimate ≠ fits. The 08-31 freeze was an unpriced load."""
    lane = ModelScoutLane(DailyResearcher(), fit_estimator=_unknown_fit, budget_bytes=40 * _GIB)
    with respx.mock(assert_all_called=False, base_url="https://huggingface.co") as mock_hf:
        _mock_happy_path(mock_hf)
        report = await lane.run(dry_run=False)
    assert report.candidates == []
    assert any(f"dropped fit_unknown: {_MODEL_ID}" in n for n in report.notes)


@pytest.mark.asyncio
async def test_run_drops_candidate_with_only_known_capabilities():
    """Discriminating for the improvement gate: a card whose every strength
    maps onto an existing default capability is `no_improvement`. The old
    set-difference gate (and `return True`) keep it."""
    lane = ModelScoutLane(DailyResearcher(), fit_estimator=_small_fit, budget_bytes=40 * _GIB)
    with respx.mock(assert_all_called=False, base_url="https://huggingface.co") as mock_hf:
        _mock_happy_path(mock_hf, card_md=_KNOWN_CAPS_CARD_MD)
        report = await lane.run(dry_run=False)
    assert report.candidates == []
    assert any(f"dropped no_improvement: {_MODEL_ID}" in n for n in report.notes)


@pytest.mark.asyncio
async def test_run_caps_candidates_per_run():
    """Fan-out bound: with three linked models and max_candidates=1, exactly
    one is considered and the stop is recorded (the lane runs under the
    shared fleet lock; an uncapped scout starves the other acquirers)."""
    lane = ModelScoutLane(
        DailyResearcher(), fit_estimator=_small_fit, budget_bytes=40 * _GIB, max_candidates=1
    )
    linked = [{"id": f"acme/m{i}"} for i in range(3)]
    with respx.mock(assert_all_called=False, base_url="https://huggingface.co") as mock_hf:
        mock_hf.get("/api/daily-papers").mock(return_value=httpx.Response(200, json=_FEED_JSON))
        mock_hf.get("/api/models").mock(return_value=httpx.Response(200, json=linked))
        readme = mock_hf.get(url__regex=r".*/raw/main/README\.md$").mock(
            return_value=httpx.Response(200, text=_CARD_MD)
        )
        report = await lane.run(dry_run=False)
    assert readme.call_count == 1
    assert report.candidates == ["acme/m0"]
    assert any("stopped: fan-out bound reached after 1 candidates" in n for n in report.notes)


@pytest.mark.asyncio
async def test_run_drops_candidate_without_card():
    lane = ModelScoutLane(DailyResearcher(), fit_estimator=_small_fit, budget_bytes=40 * _GIB)
    with respx.mock(assert_all_called=False, base_url="https://huggingface.co") as mock_hf:
        _mock_happy_path(mock_hf, card_status=404)
        report = await lane.run(dry_run=False)
    assert report.candidates == []
    assert any(f"dropped card_missing: {_MODEL_ID}" in n for n in report.notes)


# ── Feed failures are reported, not swallowed ───────────────────────────────


@pytest.mark.asyncio
async def test_daily_papers_401_is_reported_in_notes():
    lane = ModelScoutLane(DailyResearcher(), fit_estimator=_small_fit, budget_bytes=40 * _GIB)
    with respx.mock(assert_all_called=False, base_url="https://huggingface.co") as mock_hf:
        mock_hf.get("/api/daily-papers").mock(
            return_value=httpx.Response(401, json={"error": "Invalid username or password."})
        )
        report = await lane.run(dry_run=False)
    assert report.candidates == []
    assert any("401" in n for n in report.notes)


@pytest.mark.asyncio
async def test_linked_models_fetch_failure_is_reported_in_notes():
    """A failing /api/models call must be visible in the report; otherwise
    'endpoint down all day' is indistinguishable from 'no new models'."""
    lane = ModelScoutLane(DailyResearcher(), fit_estimator=_small_fit, budget_bytes=40 * _GIB)
    with respx.mock(assert_all_called=False, base_url="https://huggingface.co") as mock_hf:
        mock_hf.get("/api/daily-papers").mock(return_value=httpx.Response(200, json=_FEED_JSON))
        mock_hf.get("/api/models").mock(return_value=httpx.Response(500))
        report = await lane.run(dry_run=False)
    assert report.candidates == []
    assert any(f"linked_models_fetch_failed: {_ARXIV_ID}" in n for n in report.notes)


@pytest.mark.asyncio
async def test_all_candidates_fit_unknown_is_flagged_as_estimator_failure():
    """100% fit_unknown is an instrument failure (hf-mem drift / uvx missing),
    not a quiet day — the lane must say so at lane level."""
    lane = ModelScoutLane(DailyResearcher(), fit_estimator=_unknown_fit, budget_bytes=40 * _GIB)
    with respx.mock(assert_all_called=False, base_url="https://huggingface.co") as mock_hf:
        _mock_happy_path(mock_hf)
        report = await lane.run(dry_run=False)
    assert any(n.startswith("all_candidates_dropped_fit_unknown: 1") for n in report.notes)


@pytest.mark.asyncio
async def test_dry_run_does_not_call_network():
    lane = ModelScoutLane(DailyResearcher(), fit_estimator=_small_fit, budget_bytes=40 * _GIB)
    with respx.mock(assert_all_called=False) as mock:
        mock.route(host="huggingface.co").mock(side_effect=AssertionError("called!"))
        report = await lane.run(dry_run=True)
    assert report.dry_run is True
    assert any("dry-run" in n.lower() for n in report.notes)


# ── hf-mem output parsing (pure) ────────────────────────────────────────────


def test_parse_hf_mem_scalar_shape():
    payload = {
        "model_id": "Qwen/Qwen3-0.6B",
        "memory": 1503264768,
        "kv_cache": 1879048192,
        "total_memory": 3382312960,
    }
    est = parse_hf_mem_output(payload)
    assert est is not None
    assert est.weights_bytes == 1503264768
    assert est.kv_bytes == 1879048192
    assert est.total_bytes == 3382312960


def test_parse_hf_mem_gguf_shape_prefers_q4_k_m():
    """GGUF repos report per-file dicts; the scout prices the working quant
    (Q4_K_M), not the smallest file — a wrong impl picking min() reports IQ1."""
    payload = {
        "model_id": "unsloth/Qwen3-8B-GGUF",
        "memory": {
            "Qwen3-8B-UD-IQ1_S.gguf": 2265769856,
            "Qwen3-8B-Q4_K_M.gguf": 5021827072,
            "Qwen3-8B-BF16.gguf": 16382087168,
        },
        "kv_cache": {
            "Qwen3-8B-UD-IQ1_S.gguf": 2415919104,
            "Qwen3-8B-Q4_K_M.gguf": 2415919104,
            "Qwen3-8B-BF16.gguf": 2415919104,
        },
        "total_memory": None,
    }
    est = parse_hf_mem_output(payload)
    assert est is not None
    assert est.filename == "Qwen3-8B-Q4_K_M.gguf"
    assert est.total_bytes == 5021827072 + 2415919104


def test_parse_hf_mem_gguf_shape_falls_back_to_smallest_when_no_q4():
    payload = {
        "model_id": "x/y-GGUF",
        "memory": {"y-Q8_0.gguf": 8_000, "y-Q6_K.gguf": 6_000},
        "kv_cache": {"y-Q8_0.gguf": 100, "y-Q6_K.gguf": 100},
        "total_memory": None,
    }
    est = parse_hf_mem_output(payload)
    assert est is not None and est.filename == "y-Q6_K.gguf" and est.total_bytes == 6_100


def test_parse_hf_mem_garbage_returns_none():
    assert parse_hf_mem_output({"error": "boom"}) is None
    assert parse_hf_mem_output({"model_id": "a/b", "memory": None}) is None


def test_parse_hf_mem_quant_match_is_token_bounded():
    """'IQ4_K_M' and 'Q4_K_M_XL' are different quants; a substring match
    picks whichever comes first. The real Q4_K_M must win regardless of order."""
    payload = {
        "model_id": "x/y-GGUF",
        "memory": {"y-IQ4_K_M.gguf": 3, "y-UD-Q4_K_M_XL.gguf": 6, "y-Q4_K_M.gguf": 5},
        "kv_cache": {},
    }
    est = parse_hf_mem_output(payload)
    assert est is not None and est.filename == "y-Q4_K_M.gguf" and est.total_bytes == 5
    # No true Q4_K_M → smallest file, and IQ4_K_M is NOT mistaken for it.
    est = parse_hf_mem_output({"model_id": "x", "memory": {"y-Q8_0.gguf": 8, "y-IQ4_K_M.gguf": 3}})
    assert est is not None and est.filename == "y-IQ4_K_M.gguf"


def test_parse_hf_mem_null_bool_and_string_sizes_do_not_crash():
    """hf-mem emits null for unknown entries; a wrong impl raises TypeError
    out of run() and aborts every lane queued behind the fleet lock."""
    payload = {
        "model_id": "x/y-GGUF",
        "memory": {"a.gguf": None, "b.gguf": "lots", "c.gguf": True, "d.gguf": 0, "e.gguf": 7},
        "kv_cache": {"e.gguf": None},
    }
    est = parse_hf_mem_output(payload)
    assert est is not None and est.filename == "e.gguf" and est.total_bytes == 7
    assert parse_hf_mem_output({"model_id": "x", "memory": {"a.gguf": None}}) is None
    assert parse_hf_mem_output({"model_id": "x", "memory": True}) is None


# ── default estimator: subprocess plumbing (mocked) ─────────────────────────


class _FakeProc:
    """Mimics asyncio's Process: returncode is None until the child exits."""

    def __init__(self, rc: int, out: bytes, err: bytes = b"", hang: bool = False) -> None:
        self._rc = rc
        self.returncode: int | None = None
        self._out, self._err = out, err
        self._hang = hang
        self.killed = False
        self.waited = False

    async def communicate(self) -> tuple[bytes, bytes]:
        if self._hang:
            await asyncio.sleep(3600)
        self.returncode = self._rc
        return self._out, self._err

    def kill(self) -> None:
        self.killed = True

    async def wait(self) -> int:
        self.waited = True
        self.returncode = -9
        return -9


# Two JSON lines: the FIRST is a decoy. hf-mem prints its result last (warnings and
# progress precede it), so a first-match parser would report the wrong size.
_HF_MEM_STDOUT = (
    b'{"model_id": "a/b", "memory": 999, "kv_cache": 999}\n'
    b"noise\n"
    b'{"model_id": "a/b", "memory": 10, "kv_cache": 5, "total_memory": 15}\n'
)


@pytest.mark.asyncio
async def test_hf_mem_estimate_parses_last_json_line_and_passes_ctx(monkeypatch):
    from cohezion.researcher import hf_mem_fit as ms

    seen: dict[str, list[str]] = {}

    async def fake_exec(*argv, **_kw):
        seen["argv"] = list(argv)
        return _FakeProc(0, _HF_MEM_STDOUT)

    monkeypatch.setattr(ms.shutil, "which", lambda _name: "/usr/bin/uvx")
    monkeypatch.setattr(ms.asyncio, "create_subprocess_exec", fake_exec)
    est = await ms.hf_mem_estimate("a/b")
    assert est is not None and est.total_bytes == 15  # the LAST json line, not the decoy
    argv = seen["argv"]
    assert argv[argv.index("--model-id") + 1] == "a/b"
    assert argv[argv.index("--max-model-len") + 1] == str(ms.FIT_MAX_MODEL_LEN)
    assert "--experimental" in argv  # without it hf-mem omits the KV cache entirely
    assert argv[argv.index("--from") + 1] == ms.HF_MEM_SPEC  # pinned, not floating


@pytest.mark.asyncio
async def test_hf_mem_estimate_nonzero_rc_returns_none(monkeypatch):
    from cohezion.researcher import hf_mem_fit as ms

    async def fake_exec(*_argv, **_kw):
        return _FakeProc(1, b"", b"httpx.HTTPStatusError: 401")

    monkeypatch.setattr(ms.shutil, "which", lambda _name: "/usr/bin/uvx")
    monkeypatch.setattr(ms.asyncio, "create_subprocess_exec", fake_exec)
    assert await ms.hf_mem_estimate("nobody/missing") is None


@pytest.mark.asyncio
async def test_hf_mem_estimate_timeout_kills_and_reaps_child(monkeypatch):
    """On timeout the child must be killed AND waited on — kill without wait
    leaves a zombie per timed-out candidate for the life of the daemon."""
    from cohezion.researcher import hf_mem_fit as ms

    proc = _FakeProc(0, b"", hang=True)

    async def fake_exec(*_argv, **_kw):
        return proc

    monkeypatch.setattr(ms.shutil, "which", lambda _name: "/usr/bin/uvx")
    monkeypatch.setattr(ms.asyncio, "create_subprocess_exec", fake_exec)
    monkeypatch.setattr(ms, "HF_MEM_TIMEOUT_S", 0.01)
    assert await ms.hf_mem_estimate("a/b") is None
    assert proc.killed and proc.waited


@pytest.mark.asyncio
async def test_hf_mem_estimate_cancellation_also_reaps_child(monkeypatch):
    """Cancellation is not a timeout: without the `finally`, a cancelled estimate
    left the child running. A completed child (returncode set) must NOT be killed."""
    from cohezion.researcher import hf_mem_fit as ms

    hung = _FakeProc(0, b"", hang=True)

    async def fake_exec(*_argv, **_kw):
        return hung

    monkeypatch.setattr(ms.shutil, "which", lambda _name: "/usr/bin/uvx")
    monkeypatch.setattr(ms.asyncio, "create_subprocess_exec", fake_exec)
    task = asyncio.ensure_future(ms.hf_mem_estimate("a/b"))
    await asyncio.sleep(0.01)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert hung.killed and hung.waited

    done = _FakeProc(0, _HF_MEM_STDOUT)

    async def fake_exec_done(*_argv, **_kw):
        return done

    monkeypatch.setattr(ms.asyncio, "create_subprocess_exec", fake_exec_done)
    assert (await ms.hf_mem_estimate("a/b")) is not None
    assert not done.killed  # exited normally: reaping a finished child would double-wait


@pytest.mark.asyncio
async def test_hf_mem_estimate_without_uvx_returns_none(monkeypatch):
    from cohezion.researcher import hf_mem_fit as ms

    monkeypatch.setattr(ms.shutil, "which", lambda _name: None)
    assert await ms.hf_mem_estimate("a/b") is None


def test_hf_headers_bearer_only_when_token_present(monkeypatch):
    from cohezion.researcher.lanes.model_scout import _hf_headers

    monkeypatch.delenv("HF_TOKEN", raising=False)
    monkeypatch.delenv("HF_API_TOKEN", raising=False)
    assert _hf_headers() == {}
    monkeypatch.setenv("HF_TOKEN", "hf_x")
    assert _hf_headers() == {"Authorization": "Bearer hf_x"}
