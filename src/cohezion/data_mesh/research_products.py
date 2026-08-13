"""Research-brief DataProducts — turn local-inference research briefs into
first-class, actionable datamesh artifacts instead of orphan vault `.md` files.

Cohezion's local fleet (deepseek-r1 on the XDNA2 NPU via :13305) writes research
briefs to ~/vaults/cohezion-vault/reports/*-lemonade-research.md. Each brief has
YAML frontmatter (title/date/tags/model/source) and a body with a "Relevance"
section and a "Verdict" line. Left alone they rot as human-readable orphans.

This module parses a brief into a ``ResearchFinding`` DataProduct and, for
actionable + high-confidence findings, cards a ``research-finding`` kanban_item
(via the existing ``kanban_bridge``). It embodies "use Cohezion to make Cohezion
better": the vault `.md` stays as the human copy; the DataProduct is the machine
copy the datamesh can act on.

Design (matches sibling ``inference_products.py``):
  - Pure, offline parse/classify logic — no network, unit-testable.
  - Two guards borrowed from measurement-integrity discipline:
      * CONTAMINATION GUARD — flag briefs whose "relevance" merely echoes
        Cohezion-internal names (SkillRefiner / SkillConsensusVoter / 215 PRIME)
        AS IF the EXTERNAL source possessed them. These are prompt-echo
        hallucinations (this really happened with the Ai-Agent-Skills brief),
        so they are marked confidence=low and NEVER auto-carded.
      * VERDICT → ACTIONABILITY — integrate/adopt/experiment => actionable;
        watch/bookmark/monitor => monitor; ignore => drop.
  - Side effects (SurrealDB event, kanban card) live behind thin functions the
    tests skip / inject. Carding is idempotent on the brief's source URL,
    checked against the SAME sink ``persist_item`` writes to.

Additive: imports and uses ``data_product``, ``kanban_bridge`` and the
``event_bridge`` SurrealDB pattern — modifies none of them.
"""

from __future__ import annotations

import base64
import json
import logging
import re
import time
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cohezion.data_mesh.data_product import (
    DataProduct,
    DataProductSchema,
    DataProductStatus,
    DataQualityTier,
)
from cohezion.data_mesh.kanban_bridge import persist_item


logger = logging.getLogger(__name__)

# Default location of the local-fleet research briefs.
DEFAULT_REPORTS_DIR = Path.home() / "vaults" / "cohezion-vault" / "reports"
_BRIEF_GLOB = "20*-lemonade-research.md"

# SurrealDB (mirrors event_bridge.py — kept local so this module stays additive
# and does not need a live EventBus/subscriber to leave a durable audit trail).
_SURREAL_URL = "http://127.0.0.1:8001/sql"
_SURREAL_AUTH = base64.b64encode(b"root:root").decode()
_SURREAL_HEADERS = {
    "surreal-ns": "cohezion",
    "surreal-db": "main",
    "Content-Type": "text/plain",
    "Authorization": f"Basic {_SURREAL_AUTH}",
}

# Tags that carry no domain signal — every brief has these.
_BOILERPLATE_TAGS = {"research", "lemonade", "npu", "local-inference", "paper"}

# --- verdict → actionability ------------------------------------------------

# Order matters: 'drop' signals win over positive ones so an explicit "ignore"
# is never up-classified by an incidental "adopt" elsewhere in the sentence.
_DROP_WORDS = ("ignore", "not relevant", "irrelevant", "skip", "drop", "no value")
_ACTIONABLE_WORDS = ("integrate", "adopt", "experiment", "import", "implement")
_MONITOR_WORDS = (
    "context-only",
    "context only",
    "watch",
    "bookmark",
    "monitor",
    "yes",
    "revisit",
    "later",
)
# Some briefs prefix the verdict with the full options menu (the model was told
# to choose one of "act / watch / context-only / ignore"). Strip the menu so its
# words don't spuriously classify the finding — the real choice follows it.
_OPTIONS_MENU_RE = re.compile(
    r"\bact\b\s*/\s*watch\s*/\s*context[\s-]?only\s*/\s*ignore\b", re.IGNORECASE
)


# Negation is invisible to substring matching: "adopt nothing" and "nothing to
# import" both contain an actionable word, so a verdict saying TAKE NOTHING used
# to classify as 'actionable' and auto-card itself to kanban as work to do — the
# exact inverse of the finding. Negators are therefore matched per CLAUSE: an
# actionable word only counts if its own clause carries no negator.
_NEGATORS = (
    "nothing",
    "not ",
    "n't",
    "no need",
    "avoid",
    "without",
    "rather than",
    "instead of",
    "neither",
    "none of",
)
# Clause boundaries — negation does not reach across them ("Integrate X; do not
# adopt Y" is still actionable on the first clause).
_CLAUSE_SPLIT_RE = re.compile(r"[;,.\n]| but | however | though ")


def _has_unnegated(clauses: list[str], words: tuple[str, ...]) -> bool:
    """True if any clause contains one of ``words`` AND carries no negator."""
    return any(any(w in c for w in words) and not any(n in c for n in _NEGATORS) for c in clauses)


def classify_actionability(verdict_text: str) -> str:
    """Map free-text verdict → {actionable, monitor, drop}.

    Empty / unrecognised verdicts default to 'monitor' (conservative: never
    auto-card something we could not read a decision from). Negated actionable
    phrasing ("adopt nothing") is NOT actionable.
    """
    v = _OPTIONS_MENU_RE.sub(" ", verdict_text.lower())
    if any(w in v for w in _DROP_WORDS):
        return "drop"
    clauses = _CLAUSE_SPLIT_RE.split(v)
    if _has_unnegated(clauses, _ACTIONABLE_WORDS):
        return "actionable"
    if any(w in v for w in _MONITOR_WORDS):
        return "monitor"
    return "monitor"


# --- contamination guard ----------------------------------------------------

# Cohezion-internal proper nouns. If a brief attributes THESE to the external
# source, it is echoing the prompt rather than reporting the source.
_INTERNAL_MARKERS = (
    "skillrefiner",
    "skillconsensusvoter",
    "skill_registry",
    "journeytracker",
    "215 skill",
    "prime",
)
# Verbs that assert the *subject of the sentence* possesses/uses the marker.
_POSSESSION_VERBS = (
    r"uses?",
    r"using",
    r"used",
    r"employs?",
    r"implements?",
    r"includes?",
    r"contains?",
    r"features?",
    r"provides?",
    r"offers?",
    r"organized",
    r"organizes",
    r"stores?",
    r"stored",
    r"states?",
    r"built (?:on|with)",
    r"is in use",
    r"has",
    r"have",
)
_POSSESSION_RE = re.compile(r"\b(?:" + "|".join(_POSSESSION_VERBS) + r")\b")
# If the sentence names our side, it is a comparison, not a claim about the repo.
_COHEZION_CUES = ("your", "our ", "cohezion", "existing", "we ", "we've")


def _detect_prompt_echo(relevance: str) -> bool:
    """True if the relevance text attributes a Cohezion-internal artifact to the
    external source (marker + possession verb + no Cohezion-side cue in the same
    sentence). Three-way conjunction avoids false-positives on legitimate
    "your existing SkillConsensusVoter" comparisons.
    """
    for sentence in re.split(r"[.\n]+", relevance):
        low = sentence.lower()
        if not any(m in low for m in _INTERNAL_MARKERS):
            continue
        if not _POSSESSION_RE.search(low):
            continue
        if any(cue in low for cue in _COHEZION_CUES):
            continue
        return True
    return False


# --- frontmatter / section parsing ------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _parse_frontmatter(text: str) -> dict[str, Any]:
    """Minimal YAML-frontmatter reader (no yaml dep needed for these flat docs)."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}
    out: dict[str, Any] = {}
    for line in m.group(1).splitlines():
        if ":" not in line:
            continue
        key, _, val = line.partition(":")
        key = key.strip()
        val = val.strip()
        if val.startswith("[") and val.endswith("]"):
            out[key] = [t.strip() for t in val[1:-1].split(",") if t.strip()]
        else:
            out[key] = val
    return out


def _extract_section(body: str, keyword: str) -> str:
    """Return the text of the first markdown header containing ``keyword`` up to
    the next header of the same-or-higher level (or end of doc). Case-insensitive.
    """
    lines = body.splitlines()
    start = None
    start_level = 0
    for i, line in enumerate(lines):
        hm = re.match(r"^(#{1,6})\s+(.*)$", line)
        if hm and keyword.lower() in hm.group(2).lower():
            start = i + 1
            start_level = len(hm.group(1))
            break
    if start is None:
        return ""
    collected: list[str] = []
    for line in lines[start:]:
        hm = re.match(r"^(#{1,6})\s+", line)
        if hm and len(hm.group(1)) <= start_level:
            break
        collected.append(line)
    return "\n".join(collected).strip()


def _normalise_licence(value: str) -> str:
    """Canonical form for comparison, so cosmetic differences are not 'divergence'.

    Case, surrounding whitespace and the ubiquitous '-only'/'-or-later' suffixes are
    noise; 'NOASSERTION'/'NONE'/'UNKNOWN' all mean the platform could not determine it
    and are folded together. Anything else is compared verbatim -- deliberately, since
    guessing equivalences between real licences is exactly the judgement a human must
    make.
    """
    v = value.strip().upper().replace("_", "-")
    if v in {"NOASSERTION", "NONE", "UNKNOWN", "N/A", "-"}:
        return "UNDETERMINED"
    for suffix in ("-ONLY", "-OR-LATER"):
        if v.endswith(suffix):
            v = v[: -len(suffix)]
    return v


def _parse_licence(fm: dict[str, Any], body: str) -> tuple[str, str]:
    """Read licence_tag / licence_actual from frontmatter, then from a Licence section.

    Frontmatter wins: it is the machine-written value. The section fallback exists so
    briefs already written in prose are not silently dropped on the floor during the
    migration away from prose.
    """
    tag = str(fm.get("licence_tag") or fm.get("license_tag") or "").strip()
    actual = str(fm.get("licence_actual") or fm.get("license_actual") or "").strip()
    if tag and actual:
        return tag, actual

    section = _extract_section(body, "licence") or _extract_section(body, "license")
    if section:
        for line in section.splitlines():
            m = re.match(r"^\s*[-*]?\s*(licen[cs]e[_ ]?(tag|actual))\s*[:=]\s*(.+)$", line, re.I)
            if not m:
                continue
            which, val = m.group(2).lower(), m.group(3).strip().strip("`*_")
            if which == "tag" and not tag:
                tag = val
            elif which == "actual" and not actual:
                actual = val
    return tag, actual


def _slug(source: str, path: Path) -> str:
    """Deterministic finding id — stable across re-runs so the kanban UPSERT is
    naturally idempotent. Derived from the brief filename.
    """
    stem = path.stem
    stem = re.sub(r"^\d{6,8}-", "", stem)  # drop leading YYYYMMDD-
    stem = re.sub(r"-(lemonade-)?research$", "", stem)  # drop trailing -research
    stem = re.sub(r"[^a-z0-9]+", "-", stem.lower()).strip("-")
    return f"research-{stem or 'brief'}"


# --- the DataProduct --------------------------------------------------------


@dataclass
class ResearchFinding:
    """A parsed research brief as a first-class datamesh finding."""

    finding_id: str
    title: str
    source: str
    date: str
    tags: list[str]
    model: str
    verdict_text: str
    relevance: str
    body: str
    actionability: str  # actionable | monitor | drop
    confidence: str = "high"  # high | low
    confidence_reason: str = ""  # '' | 'prompt-echo'
    path: str = ""

    # --- licence, as FIELDS rather than prose (card 55cb4f3b9de1) -------------
    # Two separate facts that a single "license" string conflates, and the
    # conflation is the whole problem:
    #
    #   licence_tag     what the PLATFORM reports  (GitHub's SPDX detection)
    #   licence_actual  what the repo IS after reading its licence files
    #
    # Measured on 2026-08-11 across five triaged subjects, these DIVERGED in two,
    # and both divergences were adoption-blocking:
    #   archestra-ai  tag=NOASSERTION  actual=AGPL-3.0-only + Enterprise (dual)
    #   GeoPT         tag=<none>       actual=NONE -> all rights reserved, while
    #                                  containing files copied from MIT code
    #   Memoria       tag=Apache-2.0   actual=Apache-2.0        (agree)
    #   AirfRANS      tag=ODbL-1.0     actual=ODbL-1.0          (agree, but a
    #                                  DATABASE licence -- different obligations)
    #   Transolver    tag=MIT          actual=MIT               (agree)
    #
    # Why fields and not prose: the prior hand-kept tally of this same question
    # drifted -- it reported "5 of 8" when the truth was "4 of 11". A tally over
    # prose requires a human to re-count and silently rots; a field is counted
    # mechanically and cannot.
    licence_tag: str = ""  # as reported by the platform; "" = not recorded
    licence_actual: str = ""  # as read from the repo; "" = not verified

    @property
    def licence_divergence(self) -> bool:
        """True when the reported tag and the verified terms disagree.

        The single most decision-relevant bit, and the reason both are stored.
        Requires BOTH to be present: an unverified licence is UNKNOWN, not
        agreement, so a missing licence_actual must never read as "no problem".
        """
        if not self.licence_tag or not self.licence_actual:
            return False
        return _normalise_licence(self.licence_tag) != _normalise_licence(self.licence_actual)

    @property
    def licence_verified(self) -> bool:
        """True only when someone actually read the repo's licence files."""
        return bool(self.licence_actual)

    @property
    def domain(self) -> str:
        """First non-boilerplate tag, else 'research'."""
        for t in self.tags:
            if t.lower() not in _BOILERPLATE_TAGS:
                return t
        return "research"

    @property
    def should_card(self) -> bool:
        """Only actionable + high-confidence findings become kanban cards."""
        return self.actionability == "actionable" and self.confidence == "high"

    def to_data_product(self) -> DataProduct:
        """Project this finding as a canonical ``DataProduct`` (owner_domain='research')."""
        tier = DataQualityTier.SILVER if self.confidence == "high" else DataQualityTier.BRONZE
        return DataProduct(
            product_id=self.finding_id.replace("research-", "research.", 1),
            name=self.title,
            description=(
                f"Research finding [{self.actionability}/{self.confidence}] from "
                f"{self.source}. Verdict: {self.verdict_text[:160]}"
            ),
            owner_domain="research",
            schema=DataProductSchema(
                fields={
                    "source": "str — origin URL",
                    "verdict": "str — model's adopt/watch/ignore call",
                    "actionability": "str — actionable|monitor|drop",
                    "confidence": "str — high|low (low = prompt-echo hallucination)",
                    "relevance": "str — why it matters to Cohezion",
                }
            ),
            quality_tier=tier,
            status=DataProductStatus.ACTIVE,
            mcp_tool_name=None,
        )

    def to_kanban_item(self) -> dict[str, Any]:
        """Shape a ``kanban_item`` dict for ``kanban_bridge.persist_item``."""
        return {
            "id": self.finding_id,
            "type": "research-finding",
            "domain": self.domain,
            "relevance": self.actionability,
            "title": self.title,
            "url": self.source,
            "status": "pending_review",
            "created_at": self.date,
            "description": self.verdict_text[:280],
            "notes": self.relevance[:600],
        }


# --- parse ------------------------------------------------------------------


def parse_brief(path: str | Path) -> ResearchFinding | None:
    """Parse one research brief `.md` into a ``ResearchFinding``.

    Pure + offline. Returns None if the file is not a research brief (no
    frontmatter with a title/source).
    """
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning("research_products: cannot read %s: %s", p, exc)
        return None

    fm = _parse_frontmatter(text)
    title = str(fm.get("title", "")).strip()
    source = str(fm.get("source", "")).strip()
    if not title or not source:
        return None

    body = _FRONTMATTER_RE.sub("", text, count=1)
    relevance = _extract_section(body, "relevance")
    verdict_text = _extract_section(body, "verdict")
    tags = fm.get("tags", [])
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    actionability = classify_actionability(verdict_text)
    contaminated = _detect_prompt_echo(relevance or body)
    licence_tag, licence_actual = _parse_licence(fm, body)

    return ResearchFinding(
        finding_id=_slug(source, p),
        title=title,
        source=source,
        date=str(fm.get("date", "")).strip(),
        tags=list(tags),
        model=str(fm.get("model", "")).strip(),
        verdict_text=verdict_text,
        relevance=relevance,
        body=body.strip(),
        actionability=actionability,
        confidence="low" if contaminated else "high",
        confidence_reason="prompt-echo" if contaminated else "",
        path=str(p),
        licence_tag=licence_tag,
        licence_actual=licence_actual,
    )


# --- side effects (injectable / skippable) ----------------------------------


def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


def _emit_data_product_event(finding: ResearchFinding) -> bool:
    """Persist a DATA_PRODUCT_CREATED row to SurrealDB (fail-open).

    Mirrors ``event_bridge.DataMeshEventBridge`` write shape so the finding is a
    durable datamesh artifact even when run as a standalone batch (no live bus).
    """
    dp = finding.to_data_product()
    payload = json.dumps(
        {
            "product_id": dp.product_id,
            "name": dp.name,
            "source": finding.source,
            "actionability": finding.actionability,
            "confidence": finding.confidence,
            "confidence_reason": finding.confidence_reason,
            "domain": finding.domain,
        }
    )
    # `timestamp` is TYPE float and REQUIRED on data_product_event (no DEFAULT). Omitting it
    # made SurrealDB reject EVERY write with "Couldn't coerce value for field `timestamp` ...
    # Expected `float` but found `NONE`" -- while the caller reported success, because
    # SurrealDB answers HTTP 200 for QUERY errors and the check below was `status == 200`.
    # Verified 2026-07-30: zero rows had ever been written by this function.
    sql = (
        "CREATE data_product_event SET "
        'event_type = "DATA_PRODUCT_CREATED", '
        'source = "research", '
        f"timestamp = {time.time()}, "
        f'payload = "{_escape(payload)}", '
        "priority = 0;"
    )
    try:
        req = urllib.request.Request(
            _SURREAL_URL, data=sql.encode(), headers=_SURREAL_HEADERS, method="POST"
        )
        with urllib.request.urlopen(req, timeout=3) as resp:  # noqa: S310
            # HTTP status alone is NOT a success signal for SurrealDB: it answers 200 for
            # query errors, putting the failure in the body. Require status == "OK" AND a
            # non-empty result, or a rejected write reports success forever.
            body = json.loads(resp.read().decode())
        return bool(
            isinstance(body, list) and body[0].get("status") == "OK" and body[0].get("result")
        )
    except Exception as exc:  # fail-open: audit is best-effort
        logger.debug("research_products: event emit failed for %s: %s", finding.finding_id, exc)
        return False


def _existing_card_urls() -> set[str]:
    """Read the URLs of already-carded research findings from SurrealDB — the
    SAME sink ``persist_item`` writes to (kanban_item). Fail-open → empty set.
    """
    sql = "SELECT url FROM kanban_item WHERE type = 'research-finding';"
    try:
        req = urllib.request.Request(
            _SURREAL_URL, data=sql.encode(), headers=_SURREAL_HEADERS, method="POST"
        )
        with urllib.request.urlopen(req, timeout=3) as resp:  # noqa: S310
            results = json.loads(resp.read().decode())
        if isinstance(results, list) and results:
            rows = results[0].get("result", []) or []
            return {r["url"] for r in rows if r.get("url")}
    except Exception as exc:
        logger.debug("research_products: existing-card lookup failed: %s", exc)
    return set()


def card_finding(
    finding: ResearchFinding,
    *,
    existing_urls: set[str] | None = None,
    persist: Callable[[dict[str, Any]], dict[str, bool]] = persist_item,
) -> bool:
    """Idempotently card a finding as a ``research-finding`` kanban_item.

    Skips (returns False) if a card with the same source URL already exists.
    ``existing_urls`` is injectable for offline tests; in production it is read
    from the same SurrealDB table ``persist`` writes to.
    """
    urls = existing_urls if existing_urls is not None else _existing_card_urls()
    if finding.source in urls:
        logger.debug("research_products: %s already carded (url match) — skip", finding.finding_id)
        return False
    persist(finding.to_kanban_item())
    return True


# --- orchestration ----------------------------------------------------------


def ingest_brief(
    path: str | Path,
    *,
    do_side_effects: bool = True,
    existing_urls: set[str] | None = None,
) -> ResearchFinding | None:
    """Parse a brief and (optionally) emit it as a DataProduct + card it.

    - drop findings: neither emitted nor carded.
    - monitor / low-confidence findings: emitted as a DataProduct, not carded.
    - actionable + high-confidence findings: emitted AND carded (idempotent).
    """
    finding = parse_brief(path)
    if finding is None:
        return None
    if do_side_effects and finding.actionability != "drop":
        _emit_data_product_event(finding)
        if finding.should_card:
            card_finding(finding, existing_urls=existing_urls)
    return finding


def ingest_all_briefs(reports_dir: str | Path = DEFAULT_REPORTS_DIR) -> dict[str, Any]:
    """Batch-process every research brief in ``reports_dir``.

    Returns a summary: counts by actionability/confidence and which findings
    were carded. Idempotent — re-running does not double-card.
    """
    d = Path(reports_dir)
    summary: dict[str, Any] = {
        "total": 0,
        "actionable": 0,
        "monitor": 0,
        "drop": 0,
        "low_confidence": 0,
        "carded": [],
    }
    existing = _existing_card_urls()
    for brief in sorted(d.glob(_BRIEF_GLOB)):
        finding = parse_brief(brief)
        if finding is None:
            continue
        summary["total"] += 1
        summary[finding.actionability] += 1
        if finding.confidence == "low":
            summary["low_confidence"] += 1
        if finding.actionability != "drop":
            _emit_data_product_event(finding)
            if finding.should_card and card_finding(finding, existing_urls=existing):
                summary["carded"].append(finding.finding_id)
                existing.add(finding.source)
    return summary


if __name__ == "__main__":  # pragma: no cover
    result = ingest_all_briefs()
    print(json.dumps(result, indent=2))
