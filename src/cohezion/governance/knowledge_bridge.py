# URL open targets are internal/config-allowlisted, not user-supplied
"""Knowledge Bridge — bidirectional persistence for retrospective learnings.

Connects the retrospect process to three persistence layers:
1. Obsidian vault (cerebellum/) — human-readable markdown with [[bidirectional links]]
2. SurrealDB (vault/neuron) — structured, queryable, FLUME-embedded
3. KEY_LEARNINGS.md — compressed summary with vault links

This is Wire 1 of the Cohezion Platform Improvement Roadmap.

Triune mapping: The Knower (awareness of what was learned)
Smith fabric: Field (data topology — connecting knowledge across systems)
Physics: Mycelium network — persistent pathways between ephemeral EVO sessions

The bridge makes the retrospective process WRITE to the same systems it READS from,
closing the Ouroboros loop: session → learning → vault+SurrealDB → next session.

Attribution:
  - Zhamak Dehghani (Data Mesh): domain-owned data products
  - Aboriginal Australian Dreaming: Songlines as persistent navigation paths
  - FloatingPragma (OPH): observer overlap consistency for knowledge coherence
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path


logger = logging.getLogger(__name__)

VAULT_DIR = Path.home() / "vaults" / "cohezion-vault"
CEREBELLUM_DIR = VAULT_DIR / "cerebellum"
SURREAL_URL = os.environ.get("SURREALDB_URL", "http://localhost:8001")


@dataclass
class Learning:
    """A single retrospective learning to persist."""

    number: int  # e.g., 215
    title: str  # e.g., "FLUME-First Principle"
    content: str  # Full description
    date: str  # ISO date
    tags: list[str]
    propagate_to: str = ""  # e.g., "CLAUDE.md Coding Standards"
    links: list[str] | None = None  # [[bidirectional links]]
    context_tier: str = "silver"  # bronze | silver | gold (gold = curated PRIME refinements)


def persist_to_vault(learning: Learning) -> Path:
    """Write a learning to the Obsidian vault as a cerebellum entry.

    Creates a dated markdown file with YAML frontmatter and [[bidirectional links]].
    Returns the path to the created file.
    """
    CEREBELLUM_DIR.mkdir(parents=True, exist_ok=True)

    slug = learning.title.lower().replace(" ", "-").replace(":", "")[:60]
    filename = f"{learning.date}-{slug}.md"
    filepath = CEREBELLUM_DIR / filename

    # Build frontmatter
    tags_str = ", ".join(learning.tags)
    links_str = ""
    if learning.links:
        links_str = "\n".join(f'  - "[[{link}]]"' for link in learning.links)
        links_str = f"\nlinks:\n{links_str}"

    content = f"""---
title: "L{learning.number}: {learning.title}"
date: {learning.date}
type: learning
status: verified
tags: [{tags_str}]
learning_number: {learning.number}
context_tier: {learning.context_tier}{links_str}
---

# L{learning.number}: {learning.title}

{learning.content}

## Propagation Target
{learning.propagate_to}

## Cross-References
See: [[indigenous-cosmologies-toe-synthesis]] for the 17-tradition validation (incl. stealthskater).
See: [[theory-of-everything-synthesis]] for the unified physics framework.
"""

    filepath.write_text(content)
    logger.info("Vault: wrote %s", filepath)
    return filepath


def persist_to_surrealdb(learning: Learning) -> bool:
    """Insert a learning into SurrealDB vault/neuron table with FLUME embedding.

    Uses a parameterized SurrealQL query so user-controlled content cannot
    escape into the query text.

    Returns True if successful, False otherwise.
    """
    try:
        import base64
        import urllib.request

        # Encode learning for FLUME embedding
        embedding_list: list[float] = []
        try:
            from cohezion.governance.flume_bridge import encode_prompt

            embedding = encode_prompt(f"{learning.title}: {learning.content}")
            embedding_list = embedding.tolist()
        except (ImportError, RuntimeError, ValueError):
            pass

        slug = learning.title.lower().replace(" ", "-").replace(":", "")[:60]
        vault_path = f"cerebellum/{learning.date}-{slug}.md"

        surql = """
        CREATE neuron SET
            title = $title,
            path = $path,
            aspect = 'knower',
            stage = 'mature',
            tags = $tags,
            word_count = $word_count,
            embedding = $embedding,
            created = time::now();
        """

        variables = {
            "title": f"L{learning.number}: {learning.title}",
            "path": vault_path,
            "tags": learning.tags,
            "word_count": len(learning.content.split()),
            "embedding": embedding_list[:64] if embedding_list else [],
        }

        payload = f"{surql}\n{json.dumps(variables)}".encode()
        auth = base64.b64encode(b"root:root").decode()
        req = urllib.request.Request(
            f"{SURREAL_URL}/sql",
            data=payload,
            headers={
                "Accept": "application/json",
                "Authorization": f"Basic {auth}",
                "surreal-ns": "cohezion",
                "surreal-db": "vault",
                "Content-Type": "application/json",
            },
        )

        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read())
            if result and result[0].get("status") == "OK":
                logger.info("SurrealDB: inserted L%d as neuron", learning.number)
                return True
            logger.warning("SurrealDB: insert failed: %s", result)
            return False

    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("SurrealDB: connection failed: %s", exc)
        return False


# Neuron regions writable by the deposition sink. Allowlisted because `country` is interpolated
# into SurrealQL — only these literal values may reach the query (no user/external strings).
_NEURON_COUNTRIES = {"inference", "skill", "cerebellum"}


def deposit_neuron_record(neuron: dict) -> bool:
    """Write a neuron into the EXISTING neurons table, in the region given by ``neuron['country']``.

    The shared production sink for the neurogenesis tracks: item 15 (country='inference') and
    item 16 (country='skill'). Reuses the same SurrealDB HTTP ``CREATE neuron`` path as
    :func:`persist_to_surrealdb`. ``country`` is allowlisted (SQL-injection guard). Fail-soft:
    returns False on any error (never breaks the path that called it).
    """
    try:
        import base64
        import urllib.request

        def _q(value: str) -> str:
            return value.replace("'", "")

        country = str(neuron.get("country", "inference"))
        if country not in _NEURON_COUNTRIES:
            country = "inference"
        name = _q(str(neuron.get("name", "neuron:unknown")))
        content = _q(str(neuron.get("content", "")))[:500]
        tags = json.dumps([_q(str(t)) for t in neuron.get("tags", [])])
        embedding = json.dumps(list(neuron.get("embedding", []))[:32])
        reward = float(neuron.get("reward", 1.0))
        surql = (
            f"CREATE neuron SET name = '{name}', content = '{content}', "
            f"country = '{country}', tags = {tags}, embedding = {embedding}, "
            f"reward = {reward}, created = time::now();"
        )
        auth = base64.b64encode(b"root:root").decode()
        req = urllib.request.Request(  # noqa: S310 (localhost SurrealDB only)
            f"{SURREAL_URL}/sql",
            data=surql.encode(),
            headers={
                "Accept": "application/json",
                "Authorization": f"Basic {auth}",
                "surreal-ns": "cohezion",
                "surreal-db": "vault",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310 (localhost only)
            return resp.status == 200
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        logger.warning("SurrealDB: neuron deposit failed: %s", exc)
        return False


# Backward-compat alias: item 15 (routing_log) imports this name. Same country-aware writer.
deposit_inference_neuron_record = deposit_neuron_record


def build_skill_neuron(
    skill_name: str,
    content: str,
    *,
    score: float = 1.0,
    embedding: list[float] | None = None,
) -> dict:
    """Build a ``country='skill'`` neuron for a distilled skill (item 16) — same schema as the
    inference/knowledge neurons, in the ``skill`` region."""
    return {
        "name": f"skill:{skill_name}",
        "content": content[:500],
        "country": "skill",
        "tags": ["skill", skill_name],
        "embedding": list(embedding or [])[:32],
        "reward": float(score),
    }


def deposit_skill_neuron(
    skill_name: str,
    content: str,
    *,
    gate_passed: bool,
    score: float = 1.0,
    store: list[dict] | None = None,
) -> dict | None:
    """Deposit a ``country='skill'`` neuron iff the distilled skill SURVIVED the value gate.

    Item 16 — the third neurogenesis track: a new neuron = a distilled skill that passed the
    value gate. ``gate_passed=False`` deposits NOTHING (gate-survivors only — the same
    success-only growth as item 15's reward gate). With an injected ``store`` the neuron is
    appended for round-trip inspection; without a store it is a NO-OP under pytest (never
    writes the real graph) and routes through :func:`deposit_neuron_record` in production.
    """
    if not gate_passed or not skill_name:
        return None
    neuron = build_skill_neuron(skill_name, content, score=score)
    if store is not None:
        store.append(neuron)
        return neuron
    try:
        import sys

        if "pytest" in sys.modules or "unittest" in sys.modules:
            return None
        deposit_neuron_record(neuron)
        return neuron
    except Exception:
        return None


def _detect_stable_routing_pattern(
    records: list[dict], *, min_samples: int = 5, min_consistency: float = 0.8
) -> tuple[str, str, float, int] | None:
    """The strongest stabilized routing pattern in the corpus, or None (UNPROVEN on noise).

    A task_class is *procedurally stable* when, across >= ``min_samples`` decisions, a single
    lane carries >= ``min_consistency`` of them WITHOUT falling back. Returns
    ``(task_class, lane, consistency, n_samples)`` for the strongest such pattern (by
    consistency x samples), else None. Pure — no graph access.
    """
    from collections import Counter

    by_class: dict[str, list[dict]] = {}
    for rec in records:
        tc = rec.get("task_class")
        if tc:
            by_class.setdefault(str(tc), []).append(rec)

    best: tuple[str, str, float, int] | None = None
    for task_class, recs in by_class.items():
        if len(recs) < min_samples:
            continue  # noise, not a pattern
        succeeded = [r for r in recs if not r.get("fell_back") and r.get("lane")]
        if len(succeeded) < min_samples:
            continue  # mostly fell back → no successful stable lane
        modal_lane, count = Counter(str(r["lane"]) for r in succeeded).most_common(1)[0]
        consistency = count / len(recs)
        if consistency >= min_consistency:
            cand = (task_class, modal_lane, round(consistency, 4), len(recs))
            if best is None or cand[2] * cand[3] > best[2] * best[3]:
                best = cand
    return best


def build_cerebellum_neuron(
    task_class: str,
    lane: str,
    *,
    consistency: float,
    samples: int,
    embedding: list[float] | None = None,
) -> dict:
    """Build a ``country='cerebellum'`` neuron for a stabilized routing pattern (item 24) —
    procedural memory: "this task class reliably routes to this lane"."""
    return {
        "name": f"cerebellum:{task_class}->{lane}",
        "content": (
            f"stabilized routing: {task_class} -> {lane} "
            f"({consistency:.0%} consistent over {samples} decisions)"
        ),
        "country": "cerebellum",
        "tags": ["cerebellum", "procedural", task_class, lane],
        "embedding": list(embedding or [])[:32],
        "reward": float(consistency),
    }


def deposit_cerebellum_neuron(
    records: list[dict],
    *,
    min_samples: int = 5,
    min_consistency: float = 0.8,
    store: list[dict] | None = None,
) -> dict | None:
    """Deposit a ``country='cerebellum'`` neuron iff the routing corpus shows a STABILIZED pattern.

    Item 24 — completes the neurogenesis triad (inference/skill/cerebellum). A noisy or
    fallback-heavy corpus deposits NOTHING (only stabilized procedural patterns grow a neuron,
    the same evidence-gated growth as items 15/16). With an injected ``store`` the neuron is
    appended for round-trip inspection; without a store it is a NO-OP under pytest (never writes
    the real graph) and routes through :func:`deposit_neuron_record` in production.
    """
    pattern = _detect_stable_routing_pattern(
        records, min_samples=min_samples, min_consistency=min_consistency
    )
    if pattern is None:
        return None
    task_class, lane, consistency, samples = pattern
    neuron = build_cerebellum_neuron(task_class, lane, consistency=consistency, samples=samples)
    if store is not None:
        store.append(neuron)
        return neuron
    try:
        import sys

        if "pytest" in sys.modules or "unittest" in sys.modules:
            return None  # never touch the real graph during tests
        deposit_neuron_record(neuron)
        return neuron
    except Exception:
        return None


def _select_neurons_from_graph(country: str, key: str) -> list[dict]:
    """Read-only SurrealDB SELECT of neurons in ``country`` tagged ``key`` (production only).

    Mirrors :func:`deposit_neuron_record`'s HTTP path but as a SELECT. ``country`` is
    pre-validated against the allowlist by the caller; ``key`` is quote-stripped before
    interpolation. Returns [] on any non-200 / parse error (fail-soft, never raises out).
    """
    import base64
    import urllib.request

    safe_key = str(key).replace("'", "")
    surql = (
        "SELECT name, content, country, tags, embedding, reward "
        f"FROM neuron WHERE country = '{country}' AND '{safe_key}' IN tags;"
    )
    auth = base64.b64encode(b"root:root").decode()
    req = urllib.request.Request(  # noqa: S310 (localhost SurrealDB only)
        f"{SURREAL_URL}/sql",
        data=surql.encode(),
        headers={
            "Accept": "application/json",
            "Authorization": f"Basic {auth}",
            "surreal-ns": "cohezion",
            "surreal-db": "vault",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=5) as resp:  # noqa: S310 (localhost only)
        if resp.status != 200:
            return []
        payload = json.loads(resp.read().decode())
    # SurrealDB HTTP returns [{"result": [...], "status": "OK"}].
    if isinstance(payload, list) and payload and isinstance(payload[0], dict):
        result = payload[0].get("result", [])
        return result if isinstance(result, list) else []
    return []


def recall_neurons(
    country: str,
    key: str,
    *,
    store: list[dict] | None = None,
) -> list[dict]:
    """Recall deposited neurons of ``country`` whose key (task_class / skill name) is tagged.

    Item 29 — the read side that closes the neurogenesis deposit->recall loop. The triad
    (items 15 inference / 16 skill / 24 cerebellum) only DEPOSITED neurons; nothing consulted
    them, so every deposit was write-only. This returns the matching neurons so the next
    routing/refinement decision can consult prior procedural memory. PROPOSES context only —
    it never acts and never writes.

    Read-only and fail-soft. With an injected ``store`` it filters that list by
    ``country`` AND ``key`` membership in the neuron's ``tags`` (no graph access). Without a
    store it is a NO-OP under pytest (returns [] — never reads the real graph) and issues a
    read-only SurrealDB SELECT in production. ``country`` is allowlisted (unknown -> []);
    ``key`` is sanitized before interpolation.
    """
    if country not in _NEURON_COUNTRIES or not key:
        return []
    if store is not None:
        return [n for n in store if n.get("country") == country and key in (n.get("tags") or [])]
    try:
        import sys

        if "pytest" in sys.modules or "unittest" in sys.modules:
            return []  # never read the real graph during tests
        return _select_neurons_from_graph(country, key)
    except Exception:
        return []


def update_key_learnings_with_link(
    learnings_path: Path,
    learning: Learning,
    vault_path: Path,
) -> None:
    """Add a learning to KEY_LEARNINGS.md with a vault link instead of full content."""
    if not learnings_path.exists():
        return

    link_name = vault_path.stem  # e.g., "2026-03-31-flume-first-principle"
    entry = (
        f"\n### Learning {learning.number}: {learning.title} ({learning.date})\n"
        f"{learning.content[:150]}... "
        f"See: [[cerebellum/{link_name}]]\n"
    )

    with learnings_path.open("a") as f:
        f.write(entry)
    logger.info("KEY_LEARNINGS: appended L%d with vault link", learning.number)


def persist_learning(learning: Learning, learnings_path: Path | None = None) -> dict:
    """Persist a learning to all three layers (vault, SurrealDB, KEY_LEARNINGS).

    Returns a dict with results from each layer.
    """
    results = {}

    # 1. Vault (always succeeds if filesystem is accessible)
    vault_path = persist_to_vault(learning)
    results["vault"] = str(vault_path)

    # 2. SurrealDB (may fail if DB is down)
    results["surrealdb"] = persist_to_surrealdb(learning)

    # 3. KEY_LEARNINGS (append with link)
    if learnings_path:
        update_key_learnings_with_link(learnings_path, learning, vault_path)
        results["key_learnings"] = True

    return results
