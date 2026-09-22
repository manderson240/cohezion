"""Work-queue actioner — drains APPLY research items into concrete artifacts.

2026-07-10: the research daemon's pipeline dead-ended at status ``reviewed`` —
2,875 items, 0 actioned (see vault report 2026-07-10-research-daemon-backlog-
diagnosis). This module is the missing consumer. Design reviewed in vault
research note 2026-07-10-daemon-consumer-design-v2 (+ 3 review corrections).

Per user decision (2026-07-10): actioning = ONE pipeline, deterministic fork:

    Route A "implement"  — tooling/config/prompt-pattern items → a real
        CompoundExecutor.execute_task cycle whose execute_fn runs LOCAL
        inference (GAIA SDK tier via :13305 when amd-gaia is installed,
        direct router chat otherwise) and yields an implementation note +
        falsifiable proposal appended to ~/.cohezion/ada_proposals.jsonl.
    Route B "experiment" — training/eval/skill-methodology items → same real
        cycle, but the artifact is a falsifiable experiment design written to
        the vault (experiments/proposed/) AND the proposals queue, for the
        autoresearch loop to consume.
    No keyword match     — item left untouched in ``reviewed`` (visible for
        manual triage; never silently dropped, never LLM-classified).

Idempotency & crash-safety (at-least-once semantics):
    - The ONLY queue mutation is ``PATCH /api/work-queue/{id}`` — the daemon's
      ``_save_queue`` is whole-file last-write-wins, so the actioner must never
      write work-queue.json directly.
    - PATCH to ``actioned`` happens ONLY after the artifact write succeeds; a
      failed item stays ``reviewed`` for retry and the batch continues (review
      correction #2: failure isolation means "next item", not "patch anyway").
    - Artifacts are dedup-keyed by ``item_id``: a crash between artifact and
      PATCH makes the re-run a safe no-op that just re-PATCHes.

Honesty: artifacts contain only what local inference actually produced; the
proposal verdict is always ``PROPOSED`` — never a claimed result.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import tempfile
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cohezion.security.guardrail_pipeline import CONTENT_GUARDS


logger = logging.getLogger(__name__)

PROPOSALS_PATH = Path.home() / ".cohezion" / "ada_proposals.jsonl"
VAULT_EXPERIMENTS_DIR = Path.home() / "vaults" / "cohezion-vault" / "experiments" / "proposed"
DEFAULT_API_BASE = "http://localhost:8080"
DEFAULT_MODEL = "Gemma-4-E4B-it-GGUF"  # iGPU lane, warm by default
INFERENCE_TIMEOUT_S = 120.0  # one stalled call must not wedge the batch
BATCH_SIZE = 50

# Deterministic triage (design §2 — no LLM, no tags field on real items:
# match over title + abstract + domain). Route B is checked FIRST: methodology
# keywords are the narrower class, and an item like "prompt tuning for evals"
# belongs with the experiment loop, not the implementation queue.
#
# Truncated stems (``quanti[sz]``, ``fine[- ]?tun``, ``orchestrat``) take a trailing
# ``\w*`` so they match their inflections at a word START only. Before 2026-09-22 they sat
# inside ``\b(...)\b`` with nothing after them, so ``quantiz`` required a word boundary
# right after the ``z`` and never matched "quantized"/"quantization" (same for
# "fine-tuning", "orchestration"). Whole words stay whole-word; ``distill`` gets its
# noun and and gerund only ("distilled water" is not ML).
_ROUTE_B_EXPERIMENT = re.compile(
    r"\b(train|training|fine[- ]?tun\w*|sft|rlhf|dpo|distill(?:ation|ing)?|"
    r"curriculum|eval|benchmark|skill-methodology|reward model|dataset)\b",
    re.IGNORECASE,
)
_ROUTE_A_IMPLEMENT = re.compile(
    r"\b(tool|toolchain|config|prompt|prompt-pattern|agent|inference|serving|quanti[sz]\w*|"
    r"cache|caching|rag|retrieval|routing|orchestrat\w*|mcp|sandbox|scheduler)\b",
    re.IGNORECASE,
)


# Bump when triage() logic changes in a way the regex patterns below do not capture
# (e.g. RC1's type=improvement short-circuit). Part of the triage-miss ledger key.
_TRIAGE_LOGIC_REVISION = 2
MISSES_FILENAME = "actioner_triage_misses.json"


def triage_rules_version() -> str:
    """Fingerprint of the triage rules. A recorded miss is valid only under this value."""
    material = "\x00".join(
        (str(_TRIAGE_LOGIC_REVISION), _ROUTE_B_EXPERIMENT.pattern, _ROUTE_A_IMPLEMENT.pattern)
    )
    return hashlib.sha256(material.encode()).hexdigest()[:16]


# The item fields triage() reads. A recorded miss is a verdict on THIS content, so an
# item edited or re-typed after it missed is re-triaged (adversarial review 2026-09-21).
_TRIAGE_FIELDS = ("type", "title", "abstract", "description", "domain")


def triage_content_fingerprint(item: dict[str, Any]) -> str:
    """Fingerprint of the fields triage() reads; the ledger value for a recorded miss."""
    material = "\x00".join(str(item.get(k, "")) for k in _TRIAGE_FIELDS)
    return hashlib.sha256(material.encode()).hexdigest()[:16]


def load_triage_misses(path: Path, rules_version: str) -> dict[str, str]:
    """Item ids that matched no rule under *rules_version* (id -> content fingerprint).

    A ledger written under different rules is ignored, so a rule change re-examines
    every previously unmatched item. Unreadable ledger -> empty (re-examine, never skip).
    """
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict) or data.get("rules_version") != rules_version:
        return {}
    misses = data.get("misses")
    return {str(k): str(v) for k, v in misses.items()} if isinstance(misses, dict) else {}


def load_failure_attempts(path: Path) -> dict[str, dict[str, Any]]:
    """Counted non-guardrail failures per item id: ``{id: {"fp", "attempts", "last_error"}}``.

    Stored in the same ledger file as the misses but NOT invalidated by a triage-rule
    change: a failure is a verdict on executing the item, not on routing it.
    """
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    failures = data.get("failures") if isinstance(data, dict) else None
    if not isinstance(failures, dict):
        return {}
    return {
        str(k): v
        for k, v in failures.items()
        if isinstance(v, dict) and isinstance(v.get("attempts"), int)
    }


def save_triage_misses(
    path: Path,
    rules_version: str,
    misses: dict[str, str],
    failures: dict[str, dict[str, Any]] | None = None,
) -> None:
    """Atomically replace the ledger (one write per run, never the work-queue file)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # Unique temp name: two concurrent runs must not interleave writes into one .tmp.
    with tempfile.NamedTemporaryFile(
        "w", dir=path.parent, prefix=path.name + ".", suffix=".tmp", delete=False
    ) as tmp:
        tmp.write(
            json.dumps(
                {"rules_version": rules_version, "misses": misses, "failures": failures or {}}
            )
        )
    os.replace(tmp.name, path)


# Non-guardrail failures are retried at most this many times per item content, then the
# item is terminal ``failed_permanent`` (skipped, NOT patched -- the card stays visible in
# ``reviewed`` for manual triage). 2026-09-21: one item produced 541 journey rows from an
# unbounded retry loop.
MAX_FAILURE_ATTEMPTS = 3

# Failures that say nothing about the item: the shared apparatus was down. Counting them
# would permanently fail every good card attempted during a model-load outage (observed
# live 2026-09-21: ``404 No model loaded: Gemma-4-E4B-it-GGUF``), so they never count.
_INFRA_FAILURE = re.compile(
    r"model_not_loaded|no model loaded|connection refused|connection reset|timed out|"
    r"timeout|urlerror|remote ?disconnected|remote end closed|temporary failure|"
    r"name or service not known|status 5\d\d|http error 5\d\d|service unavailable",
    re.IGNORECASE,
)


def is_infra_failure(err_msg: str) -> bool:
    """True when *err_msg* describes the inference/API apparatus, not the item."""
    return bool(_INFRA_FAILURE.search(err_msg))


class GuardrailBlocked(RuntimeError):
    """The compound cycle's input guardrail BLOCKED the item; carries which guard did it."""

    def __init__(self, message: str, guard_name: str = "", reason: str = "") -> None:
        super().__init__(message)
        self.guard_name = guard_name
        self.reason = reason


def guardrail_block_kind(exc: BaseException) -> str | None:
    """Classify a failure as a guardrail block: 'content', 'transient', or None (not a block).

    - 'content': a text-inspecting guard (``CONTENT_GUARDS``) judged the input -- the same
      text is blocked again every run, so the card is terminal-rejected (Learning 414).
    - 'transient': a state guard (``resource`` CPU/memory pressure, ``rate_limit`` quota)
      or a fail-closed guard *exception* -- says nothing about the item; retry later and
      never count it toward ``MAX_FAILURE_ATTEMPTS`` (same treatment as infra failures).
    A block whose guard is unknown (legacy executors that report only the message) keeps
    the historical terminal behaviour.
    """
    guard = getattr(exc, "guard_name", "") if isinstance(exc, GuardrailBlocked) else ""
    if guard:
        if str(getattr(exc, "reason", "")).startswith("Guardrail exception:"):
            return "transient"
        return "content" if guard in CONTENT_GUARDS else "transient"
    err_msg = str(exc)
    if "Input blocked by guardrails" in err_msg or "Potential injection pattern" in err_msg:
        return "content"
    return None


def triage(item: dict[str, Any]) -> str | None:
    """Route an item deterministically: 'experiment' (B), 'implement' (A), or None.

    None = no keyword match = leave the item untouched (visible, not dropped).
    """
    # RC1 (2026-08-26): an item already classified ``type=improvement`` +
    # ``relevance=APPLY`` has ALREADY been triaged upstream by the research
    # daemon. Re-triaging it with a research-TOPIC regex rejected 108/108 of
    # them, so none could reach ``actioned``, so compound_feeder found nothing
    # new and compound_daemon stalled indefinitely. Route them directly.
    if str(item.get("type", "")).strip().lower() == "improvement":
        return "implement"

    text = " ".join(str(item.get(k, "")) for k in ("title", "abstract", "description", "domain"))
    if _ROUTE_B_EXPERIMENT.search(text):
        return "experiment"
    if _ROUTE_A_IMPLEMENT.search(text):
        return "implement"
    return None


def load_actioned_ids(proposals_path: Path = PROPOSALS_PATH) -> set[str]:
    """Item ids already present in the proposals queue (the dedup key)."""
    ids: set[str] = set()
    if not proposals_path.exists():
        return ids
    for line in proposals_path.read_text().splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        item_id = entry.get("item_id")
        if item_id:
            ids.add(str(item_id))
    return ids


class WorkQueueAPI:
    """Thin stdlib client for the work-queue HTTP API (the only mutation path)."""

    def __init__(self, base_url: str = DEFAULT_API_BASE, timeout: float = 15.0):
        if not base_url.startswith(("http://", "https://")):
            raise ValueError(f"base_url must be http(s), got {base_url!r}")
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(  # noqa: S310 — scheme constrained to http(s) in __init__
            f"{self.base_url}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method=method,
        )
        # S310: scheme is constrained to http(s) in __init__.
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
            return json.loads(resp.read())

    def eligible_items(self) -> list[dict[str, Any]]:
        """APPLY items in reviewed/approved — the drain target, oldest first."""
        items: list[dict[str, Any]] = []
        for status in ("reviewed", "approved"):
            page = self._request("GET", f"/api/work-queue?relevance=APPLY&status={status}")
            items.extend(page.get("items", []))
        return sorted(items, key=lambda i: i.get("created_at", ""))

    def mark_actioned(self, item_id: str, route: str) -> dict:
        """Record WHICH lane actioned the card, without touching its content.

        This used to PATCH ``notes``, which is where the research analysis lives -- so
        actioning a card replaced multi-kilobyte findings with a 50-character status
        string. 764 of 6,110 cards were already destroyed that way. The route is
        machine bookkeeping and belongs in its own field; ``status`` alone already says
        the card was actioned.
        """
        return self._request(
            "PATCH",
            f"/api/work-queue/{item_id}",
            {"status": "actioned", "action_route": route},
        )

    def pending_items(self) -> list[dict[str, Any]]:
        """Items awaiting triage, oldest first.

        ``POST /api/work-queue`` creates every card as ``pending_review``, a status NO
        consumer polls: ``eligible_items`` above asks for reviewed/approved, and
        ``compound_feeder`` asks for actioned/approved. The research daemon classifies
        inline and writes ``reviewed`` directly, which is why only ITS items ever flow.
        This is the read side of the missing triage hop (see ``actioner.triage``).
        """
        page = self._request("GET", "/api/work-queue?status=pending_review")
        return sorted(page.get("items", []), key=lambda i: i.get("created_at", ""))

    def mark_reviewed(self, item_id: str, relevance: str, note: str) -> dict:
        """Promote a triaged item into the lane the actioner actually polls."""
        return self._request(
            "PATCH",
            f"/api/work-queue/{item_id}",
            {"status": "reviewed", "relevance": relevance, "notes": note},
        )

    def mark_rejected(self, item_id: str, note: str) -> dict:
        return self._request(
            "PATCH", f"/api/work-queue/{item_id}", {"status": "rejected", "notes": note}
        )


def default_chat_fn(model: str = DEFAULT_MODEL) -> Callable[[str], str]:
    """Local-inference chat callable: GAIA SDK tier when installed, router otherwise.

    Both paths hit the :13305 lemonade router ($0 local silicon). The GAIA tier
    is preferred (it carries the F0 card-sampling defaults); ``amd-gaia`` is an
    optional dependency, so fall back to a direct OpenAI-compatible call.
    """
    try:
        from cohezion.inference.gaia_adapter import build_gaia_llm_tier

        tier = build_gaia_llm_tier(model, max_tokens=2048)
        agent_prompt = tier.agent.prompt
        return lambda prompt: str(agent_prompt(prompt))
    except (RuntimeError, ImportError):
        pass

    def _router_chat(prompt: str) -> str:
        body = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 2048,  # generous — frugal caps truncate ($0 local)
        }
        req = urllib.request.Request(
            "http://localhost:13305/api/v1/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        # S310: fixed literal localhost URL (the :13305 router).
        with urllib.request.urlopen(req, timeout=INFERENCE_TIMEOUT_S) as resp:  # noqa: S310
            out = json.loads(resp.read())
        return str(out["choices"][0]["message"]["content"])

    return _router_chat


def _proposal_prompt(item: dict[str, Any], route: str) -> str:
    artifact = (
        "a falsifiable experiment design for our autoresearch loop"
        if route == "experiment"
        else "an implementation note for our engineering backlog"
    )
    return (
        f"You are triaging a research item for the Cohezion local-AI stack "
        f"(AMD Strix Halo, local lemonade inference, compound engineering loop).\n"
        f"Title: {item.get('title', '')}\n"
        f"Abstract: {item.get('abstract') or item.get('description') or '(none)'}\n"
        f"URL: {item.get('url', '')}\nDomain: {item.get('domain', '')}\n\n"
        f"Produce {artifact}. Reply with STRICT JSON, no markdown fences, keys:\n"
        f'{{"proposal": "<2-3 sentences: what to do in our stack>", '
        f'"falsifiable_step": "<one concrete measurable check that could FAIL>"}}'
    )


def _parse_proposal(raw: str) -> dict[str, str]:
    """Parse the model's JSON; fall back to using raw text as the proposal."""
    try:
        start, end = raw.index("{"), raw.rindex("}") + 1
        parsed = json.loads(raw[start:end])
        proposal = str(parsed.get("proposal", "")).strip()
        step = str(parsed.get("falsifiable_step", "")).strip()
        if proposal:
            return {"proposal": proposal, "falsifiable_step": step or "(model omitted)"}
    except ValueError:
        pass
    return {"proposal": raw.strip()[:1000], "falsifiable_step": "(unstructured output)"}


def _append_proposal(entry: dict[str, Any], proposals_path: Path) -> None:
    proposals_path.parent.mkdir(parents=True, exist_ok=True)
    with proposals_path.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def _write_vault_experiment(item: dict[str, Any], parsed: dict[str, str], vault_dir: Path) -> Path:
    vault_dir.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", str(item.get("title", "untitled")).lower())[:60].strip("-")
    path = vault_dir / f"{datetime.now(UTC).date()}-{item['id']}-{slug}.md"
    path.write_text(
        "---\n"
        f"type: experiment-proposal\ndate: {datetime.now(UTC).date()}\n"
        f"source_item: {item['id']}\nsource_url: {item.get('url', '')}\n"
        "status: PROPOSED — not run\ngenerator: work-queue actioner (local inference)\n"
        "---\n\n"
        f"# {item.get('title', 'untitled')}\n\n"
        f"## Proposal\n{parsed['proposal']}\n\n"
        f"## Falsifiable step\n{parsed['falsifiable_step']}\n"
    )
    return path


def _failure_reason(result: Any) -> str:
    """Return the real reason an execution failed.

    RC2 (2026-08-26): ``ExecutionResult`` has NO ``error`` field — the reason
    lives in ``metrics["error"]`` and ``output``. The previous
    ``getattr(result, "error", "")`` was a PHANTOM attribute read that returned
    "" for every failure, so a fully-blocked pipeline was indistinguishable
    from a slow one. Ordered most-specific first; ``error`` is kept last so
    objects that genuinely carry one (e.g. test doubles) still work.
    """
    metrics = getattr(result, "metrics", None)
    if isinstance(metrics, dict) and metrics.get("error"):
        return str(metrics["error"])
    for attr in ("output", "error"):
        value = str(getattr(result, attr, "") or "").strip()
        if value:
            return value
    return "unknown failure (execution reported no reason)"


def action_item(
    item: dict[str, Any],
    route: str,
    executor: Any,
    chat_fn: Callable[[str], str],
    *,
    proposals_path: Path = PROPOSALS_PATH,
    vault_dir: Path = VAULT_EXPERIMENTS_DIR,
) -> dict[str, Any]:
    """Run one REAL compound cycle for *item* and write its artifact.

    Raises on any failure (caller isolates per item); returns the artifact
    summary on success. Does NOT patch the queue — that is run_batch's job,
    strictly after this returns.
    """
    captured: dict[str, str] = {}

    def execute_fn(_guidance: str) -> tuple[str, dict]:
        # The execute_fn contract passes executor guidance; the actioner's prompt
        # is fully determined by the item + route, so guidance is unused.
        raw = chat_fn(_proposal_prompt(item, route))
        captured["raw"] = raw
        return raw, {"tier_used": "local", "route": route}

    result = executor.execute_task(
        task_description=f"Action research item {item['id']}: {item.get('title', '')[:80]}",
        skill_name="research-actioner",
        operation_type="generate",
        execute_fn=execute_fn,
    )
    if not getattr(result, "success", False):
        metrics = getattr(result, "metrics", None)
        if isinstance(metrics, dict) and metrics.get("blocked_by_guardrails"):
            raise GuardrailBlocked(
                f"compound cycle failed for {item['id']}: {_failure_reason(result)}",
                guard_name=str(metrics.get("blocked_by_guard") or ""),
                reason=str(metrics.get("blocked_guard_reason") or ""),
            )
        raise RuntimeError(f"compound cycle failed for {item['id']}: {_failure_reason(result)}")

    parsed = _parse_proposal(captured.get("raw", ""))
    entry = {
        "date": datetime.now(UTC).isoformat(),
        "source": item.get("url", ""),
        "proposal": parsed["proposal"],
        "falsifiable_step": parsed["falsifiable_step"],
        "verdict": "PROPOSED",  # honesty: never a claimed result
        "domain": item.get("domain", ""),
        "item_id": item["id"],
        "route": route,
    }
    artifact: dict[str, Any] = {"route": route, "proposal_entry": entry}
    if route == "experiment":
        artifact["vault_note"] = str(_write_vault_experiment(item, parsed, vault_dir))
    _append_proposal(entry, proposals_path)
    return artifact


def run_batch(
    executor: Any,
    api: WorkQueueAPI | None = None,
    chat_fn: Callable[[str], str] | None = None,
    *,
    batch_size: int = BATCH_SIZE,
    proposals_path: Path = PROPOSALS_PATH,
    vault_dir: Path = VAULT_EXPERIMENTS_DIR,
    misses_path: Path | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Drain up to *batch_size* eligible items. Returns an honest summary.

    Per-item failures are isolated: the item stays ``reviewed`` (no PATCH) and
    the batch continues. Items with no triage match are left untouched in the queue
    and recorded in the triage-miss ledger (default: next to *proposals_path*), so
    later runs skip them until the triage rules change (2026-09-21: every 5-min run
    was re-triaging the same ~2,771 unmatchable items). ``processed`` counts items
    actually triaged this run; ``skipped_known_miss`` counts ledger skips. The
    eligible-item list is still fetched each run.

    Non-guardrail failures are counted per item content (same ledger file); after
    ``MAX_FAILURE_ATTEMPTS`` the item is listed in ``failed_permanent`` and later runs
    skip it (``skipped_failed_permanent``) until its content changes. Infrastructure
    failures (``is_infra_failure``) never count -- an outage must not DLQ good cards.
    Guardrail blocks split by guard (``guardrail_block_kind``): content guards reject
    the card; resource/rate-limit blocks are listed in ``deferred_transient_guard`` and
    neither reject nor count.
    """
    api = api or WorkQueueAPI()
    chat_fn = chat_fn or default_chat_fn()
    actioned_ids = load_actioned_ids(proposals_path)
    misses_path = misses_path or proposals_path.with_name(MISSES_FILENAME)
    rules_version = triage_rules_version()
    known_misses = load_triage_misses(misses_path, rules_version)
    failures = load_failure_attempts(misses_path)
    failures_changed = False
    new_misses: dict[str, str] = {}
    seen_ids: set[str] = set()
    summary: dict[str, Any] = {
        "processed": 0,
        "actioned": [],
        "skipped_no_match": [],
        "skipped_known_miss": 0,
        "skipped_failed_permanent": 0,
        "deduped": [],
        "failed": {},
        "failed_permanent": [],
        "dry_run": dry_run,
    }

    attempts = 0
    walked_all = True
    for item in api.eligible_items():
        # batch_size caps ATTEMPTED items only — permanently-unmatched items at
        # the head of the oldest-first queue must not starve matchable ones
        # behind them (found live 2026-07-10: 3 no-match items ate a whole batch).
        if attempts >= batch_size:
            walked_all = False
            break
        item_id = str(item.get("id", ""))
        seen_ids.add(item_id)
        fingerprint = triage_content_fingerprint(item)
        if item_id and known_misses.get(item_id) == fingerprint:
            summary["skipped_known_miss"] += 1
            continue
        prior = failures.get(item_id)
        if prior and prior.get("fp") != fingerprint:
            prior = None  # content changed: a fresh item gets a fresh retry budget
        if prior and prior["attempts"] >= MAX_FAILURE_ATTEMPTS:
            summary["skipped_failed_permanent"] += 1
            continue
        summary["processed"] += 1
        route = triage(item)
        if route is None:
            summary["skipped_no_match"].append(item_id)
            if item_id:  # empty ids would all collide on one ledger key
                new_misses[item_id] = fingerprint
            continue
        attempts += 1
        if dry_run:
            summary["actioned"].append({"id": item_id, "route": route, "dry_run": True})
            continue
        try:
            if item_id in actioned_ids:
                # Crash-replay: artifact already exists — just re-PATCH (no-op action).
                summary["deduped"].append(item_id)
            else:
                action_item(
                    item,
                    route,
                    executor,
                    chat_fn,
                    proposals_path=proposals_path,
                    vault_dir=vault_dir,
                )
                actioned_ids.add(item_id)
            api.mark_actioned(item_id, route=route)
            summary["actioned"].append({"id": item_id, "route": route})
            if failures.pop(item_id, None) is not None:
                failures_changed = True
        except Exception as exc:
            err_msg = str(exc)
            logger.warning("actioner: item %s failed: %s", item_id, err_msg)
            block_kind = guardrail_block_kind(exc)
            if block_kind == "transient":
                # Resource/rate guard: system load, not the item. Retry next run, uncounted.
                summary["failed"][item_id] = err_msg
                summary.setdefault("deferred_transient_guard", []).append(item_id)
                continue
            # A content guardrail block is deterministic for this text: reject it so it
            # does not poison the queue and cause an infinite crash loop (Learning 414).
            if block_kind == "content":
                try:
                    api.mark_rejected(item_id, note=f"rejected by guardrail: {err_msg[:200]}")
                    summary.setdefault("rejected", []).append(item_id)
                except Exception as patch_exc:
                    logger.error(
                        "actioner: failed to mark item %s rejected: %s", item_id, patch_exc
                    )
                summary["failed"][item_id] = err_msg
                continue
            summary["failed"][item_id] = err_msg
            if item_id and not is_infra_failure(err_msg):
                count = (prior["attempts"] if prior else 0) + 1
                failures[item_id] = {
                    "fp": fingerprint,
                    "attempts": count,
                    "last_error": err_msg[:200],
                }
                failures_changed = True
                if count >= MAX_FAILURE_ATTEMPTS:
                    summary["failed_permanent"].append(item_id)
                    logger.warning(
                        "actioner: item %s failed_permanent after %d attempts", item_id, count
                    )
    stale_failures = failures.keys() - seen_ids if walked_all else set()
    if not dry_run and (
        new_misses or known_misses.keys() - seen_ids or failures_changed or stale_failures
    ):
        # Keep misses still in the eligible set (plus unseen ones if the batch cap cut the
        # walk short), so the ledger tracks the queue instead of growing forever.
        kept = {k: v for k, v in known_misses.items() if k in seen_ids or not walked_all}
        kept_failures = {k: v for k, v in failures.items() if k not in stale_failures}
        try:
            save_triage_misses(misses_path, rules_version, {**kept, **new_misses}, kept_failures)
        except OSError as exc:
            logger.warning("actioner: could not record triage misses: %s", exc)
    return summary
