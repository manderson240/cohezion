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

import json
import logging
import re
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


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
_ROUTE_B_EXPERIMENT = re.compile(
    r"\b(train|training|fine-?tun|sft|rlhf|dpo|distill|curriculum|eval|benchmark|"
    r"skill-methodology|reward model|dataset)\b",
    re.IGNORECASE,
)
_ROUTE_A_IMPLEMENT = re.compile(
    r"\b(tool|toolchain|config|prompt|prompt-pattern|agent|inference|serving|quantiz|"
    r"cache|caching|rag|retrieval|routing|orchestrat|mcp|sandbox|scheduler)\b",
    re.IGNORECASE,
)


def triage(item: dict[str, Any]) -> str | None:
    """Route an item deterministically: 'experiment' (B), 'implement' (A), or None.

    None = no keyword match = leave the item untouched (visible, not dropped).
    """
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

    def mark_actioned(self, item_id: str, note: str) -> dict:
        return self._request(
            "PATCH", f"/api/work-queue/{item_id}", {"status": "actioned", "notes": note}
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
    except (ValueError, json.JSONDecodeError):
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
        raise RuntimeError(
            f"compound cycle failed for {item['id']}: {getattr(result, 'error', '')}"
        )

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
    dry_run: bool = False,
) -> dict[str, Any]:
    """Drain up to *batch_size* eligible items. Returns an honest summary.

    Per-item failures are isolated: the item stays ``reviewed`` (no PATCH) and
    the batch continues. Items with no triage match are left untouched.
    """
    api = api or WorkQueueAPI()
    chat_fn = chat_fn or default_chat_fn()
    actioned_ids = load_actioned_ids(proposals_path)
    summary: dict[str, Any] = {
        "processed": 0,
        "actioned": [],
        "skipped_no_match": [],
        "deduped": [],
        "failed": {},
        "dry_run": dry_run,
    }

    attempts = 0
    for item in api.eligible_items():
        # batch_size caps ATTEMPTED items only — permanently-unmatched items at
        # the head of the oldest-first queue must not starve matchable ones
        # behind them (found live 2026-07-10: 3 no-match items ate a whole batch).
        if attempts >= batch_size:
            break
        summary["processed"] += 1
        item_id = str(item.get("id", ""))
        route = triage(item)
        if route is None:
            summary["skipped_no_match"].append(item_id)
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
            api.mark_actioned(item_id, note=f"actioned via {route} route (work-queue actioner)")
            summary["actioned"].append({"id": item_id, "route": route})
        except Exception as exc:
            logger.warning("actioner: item %s failed, left in place: %s", item_id, exc)
            summary["failed"][item_id] = str(exc)
    return summary
