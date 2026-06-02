"""AnomalyQuarantine — Anomaly Gate Phases 4-5: graph quarantine + analyst handoff.

The final stage of the Anomaly Gate. A *surviving* anomaly (the deterministic gate flagged it and the
local-inference Skeptic could not refute it — ``adjudicate(...)['final'] == 'human_review'``) is not
silently merged into the baseline. It is structurally isolated and surfaced to a human:

  * Phase 4 — Graph quarantine (SurrealDB): write a ``type: anomaly`` node and RELATE edges linking it
    to the parameters, code state, and theoretical frameworks that generated it, so the anomaly is
    queryable and provenance-traced but does not contaminate baseline logic.
  * Phase 5 — Analyst handoff (Obsidian): emit a human-readable markdown file tagged
    ``#anomaly-review`` / ``#requires-human-validation`` with the inputs, the anomalous outputs, and
    the Skeptic's (failed) refutation — a clean, versioned trail of exactly what broke the boundaries.

Dependency-light and testable: the SurrealDB write goes through an injectable ``surreal_writer``
(defaults to the localhost HTTP bus pattern used elsewhere) and the markdown to an injectable
``vault_dir``; both can be faked in tests. Only ``human_review`` adjudications are quarantined —
REJECT/STANDARD/refuted results never reach this stage.
"""

from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


__all__ = ["AnomalyQuarantine", "QuarantineRecord"]

_BUS = "http://localhost:8001/sql"
_BUS_HEADERS = {"surreal-ns": "cohezion", "surreal-db": "main", "Content-Type": "text/plain"}
_DEFAULT_VAULT = Path.home() / "vaults" / "cohezion-vault" / "anomalies"


def _http_surreal(sql: str) -> bool:
    """Default SurrealDB writer via the localhost HTTP bus. Returns True on success."""
    try:
        req = urllib.request.Request(  # noqa: S310 — fixed localhost SurrealDB bus URL
            _BUS,
            data=sql.encode(),
            headers={**_BUS_HEADERS, "Authorization": "Basic cm9vdDpyb290"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=6).read()  # noqa: S310 — controlled localhost URL
        return True
    except Exception:
        return False


@dataclass(frozen=True)
class QuarantineRecord:
    anomaly_id: str
    domain: str
    surreal_ok: bool
    markdown_path: str
    quarantined: bool
    reason: str = ""

    def to_dict(self) -> dict:
        return {
            "anomaly_id": self.anomaly_id,
            "domain": self.domain,
            "surreal_ok": self.surreal_ok,
            "markdown_path": self.markdown_path,
            "quarantined": self.quarantined,
            "reason": self.reason,
        }


class AnomalyQuarantine:
    """Isolate a surviving anomaly into SurrealDB (P4) and Obsidian (P5).

    Parameters
    ----------
    surreal_writer:
        Callable ``sql -> bool`` writing to SurrealDB (default: localhost HTTP bus).
    vault_dir:
        Directory for the Obsidian handoff markdown (default: ~/vaults/cohezion-vault/anomalies).
    """

    def __init__(
        self,
        surreal_writer: Callable[[str], bool] | None = None,
        vault_dir: Path | str | None = None,
    ) -> None:
        self._write = surreal_writer or _http_surreal
        self._vault = Path(vault_dir) if vault_dir is not None else _DEFAULT_VAULT

    def quarantine(
        self,
        adjudication: dict,
        *,
        anomaly_id: str,
        params: dict | None = None,
        code_ref: str = "",
        frameworks: list[str] | None = None,
    ) -> QuarantineRecord:
        """Quarantine a surviving anomaly. No-op (quarantined=False) unless final == 'human_review'.

        ``anomaly_id`` is caller-supplied (deterministic; e.g. from an error_signature + run id) so the
        quarantine is idempotent and reproducible — no wall-clock in the key.
        """
        verdict = adjudication.get("verdict", {})
        domain = verdict.get("domain", "unknown")
        if adjudication.get("final") != "human_review":
            return QuarantineRecord(
                anomaly_id,
                domain,
                surreal_ok=False,
                markdown_path="",
                quarantined=False,
                reason=f"not a surviving anomaly (final={adjudication.get('final')})",
            )
        params = params or {}
        frameworks = frameworks or []
        skeptic = adjudication.get("skeptic", {})

        # Phase 4 — graph quarantine: type:anomaly node + RELATE edges to frameworks.
        node = {
            "type": "anomaly",
            "domain": domain,
            "physical_failed": verdict.get("physical_failed", []),
            "skeptic_note": skeptic.get("note", ""),
            "params": params,
            "code_ref": code_ref,
            "frameworks": frameworks,
        }
        sql = f"UPSERT anomaly:{_ident(anomaly_id)} CONTENT {json.dumps(node)};"
        for fw in frameworks:
            sql += (
                f" UPSERT framework:{_ident(fw)} SET name={json.dumps(fw)};"
                f" RELATE anomaly:{_ident(anomaly_id)}->generated_under->framework:{_ident(fw)};"
            )
        surreal_ok = self._write(sql)

        # Phase 5 — analyst handoff: Obsidian markdown with review tags.
        md_path = self._write_markdown(
            anomaly_id, domain, verdict, skeptic, params, code_ref, frameworks
        )

        return QuarantineRecord(
            anomaly_id,
            domain,
            surreal_ok=surreal_ok,
            markdown_path=str(md_path),
            quarantined=True,
            reason="surviving anomaly quarantined (graph + obsidian)",
        )

    def _write_markdown(
        self, anomaly_id, domain, verdict, skeptic, params, code_ref, frameworks
    ) -> Path:
        self._vault.mkdir(parents=True, exist_ok=True)
        path = self._vault / f"anomaly-{_ident(anomaly_id)}.md"
        fw_links = " ".join(f"[[{f}]]" for f in frameworks) if frameworks else "—"
        body = f"""---
type: anomaly
domain: {domain}
anomaly_id: {anomaly_id}
surreal_id: anomaly:{_ident(anomaly_id)}
tags: [anomaly-review, requires-human-validation]
---
# Anomaly: {domain} / {anomaly_id}

**Status:** survived the adversarial Skeptic — requires human validation.

## Physical invariant(s) violated (integrity held)
{", ".join(verdict.get("physical_failed", [])) or "—"}

## Gate reason
{verdict.get("reason", "")}

## Skeptic (could not refute)
- model: {skeptic.get("model", "—")}
- note: {skeptic.get("note", "—")}
- refutation: {skeptic.get("refutation") or "none — not dismissable by the standard model"}

## Inputs / parameters
```json
{json.dumps(params, indent=2)}
```

## Code state
{code_ref or "—"}

## Theoretical frameworks
{fw_links}
"""
        path.write_text(body, encoding="utf-8")
        return path


def _ident(s: str) -> str:
    """Sanitize a string into a SurrealDB-safe / filename-safe identifier."""
    return "".join(c if c.isalnum() else "_" for c in str(s))[:80] or "anon"
