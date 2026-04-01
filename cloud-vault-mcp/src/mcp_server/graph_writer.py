"""Shared graph write API for neuron + synapse operations.

Used by autoresearch, Ralph Loop, scout, and any system that needs to
write discoveries back to the neuron graph in SurrealDB.

All operations are non-blocking (try/except), idempotent (UPSERT), and
use the same activation/stage formulas as sync_graphrag_to_neurons.py.
"""

import logging
import math
import os
import re
from datetime import date
from typing import Any

import httpx


logger = logging.getLogger(__name__)

SURREALDB_URL = os.environ.get("SURREALDB_URL", "http://localhost:8001")
NAMESPACE = os.environ.get("SURREALDB_NAMESPACE", "cohezion")
DATABASE = os.environ.get("SURREALDB_DATABASE", "vault")
AUTH = (
    os.environ.get("SURREALDB_USERNAME", "root"),
    os.environ.get("SURREALDB_PASSWORD", "root"),
)

LAMBDA_DECAY = 0.05


# ── Helpers ──────────────────────────────────────────────────────────────────


def slugify(text: str) -> str:
    """Convert text to valid SurrealDB ID component."""
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s-]+", "_", slug)
    return slug.strip("_")


def escape_sql(text: str) -> str:
    """Escape for SurrealQL string literals."""
    return text.replace("\\", "\\\\").replace("'", "\\'")[:2000]


def validate_surreal_id(identifier: str) -> str:
    """Validate a SurrealDB record identifier (e.g. 'neuron:some_slug').

    Prevents SQL injection via bare identifiers in UPSERT/RELATE statements.
    Only allows alphanumeric characters, underscores, hyphens, colons, and dots.
    """
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_:.\-]*$", identifier):
        raise ValueError(f"Invalid SurrealDB identifier: {identifier!r}")
    return identifier


def escape_tag_list(tags: list[str]) -> str:
    """Safely serialize a tag list for SurrealQL.

    Escapes each tag as a single-quoted string literal instead of
    relying on Python list repr interpolation.
    """
    escaped = [f"'{escape_sql(str(t))}'" for t in tags]
    return f"[{', '.join(escaped)}]"


def compute_stage(word_count: int) -> str:
    if word_count < 100:
        return "embryo"
    elif word_count < 400:
        return "growing"
    return "mature"


def compute_activation(word_count: int, stage: str, tags: list, created_at: str = "") -> float:
    """Composite activation score matching reactor.py."""
    stage_scores = {"embryo": 0.1, "seedling": 0.3, "growing": 0.6, "mature": 1.0}
    stage_score = stage_scores.get(stage, 0.2)
    word_score = min(word_count / 400.0, 1.0)
    tag_score = min(len(tags) / 4.0, 1.0)
    completion = 0.5 * word_score + 0.3 * stage_score + 0.2 * tag_score

    recency = 0.0
    if created_at:
        try:
            d = date.fromisoformat(str(created_at)[:10])
            days = (date.today() - d).days
            recency = math.exp(-LAMBDA_DECAY * max(days, 0))
        except (ValueError, TypeError):
            pass

    return round(0.7 * completion + 0.3 * recency, 4)


# ── SurrealDB HTTP ──────────────────────────────────────────────────────────


async def _query(client: httpx.AsyncClient, sql: str) -> list[dict]:
    """Execute SurrealQL, return results."""
    resp = await client.post(
        f"{SURREALDB_URL}/sql",
        headers={
            "Content-Type": "text/plain",
            "Accept": "application/json",
            "surreal-ns": NAMESPACE,
            "surreal-db": DATABASE,
        },
        auth=AUTH,
        content=sql,
        timeout=10.0,
    )
    resp.raise_for_status()
    return resp.json()


# ── Public API ───────────────────────────────────────────────────────────────


async def upsert_neuron(
    neuron_id: str,
    title: str,
    path: str = "",
    cluster: str = "",
    aspect: str = "connective",
    tags: list[str] | None = None,
    content: str = "",
) -> bool:
    """Upsert a neuron with computed activation and stage.

    Args:
        neuron_id: Full SurrealDB ID (e.g. "neuron:ksearch_gemm_root_md")
        title: Display title
        path: Vault-relative path (optional)
        cluster: Cluster ID (cortex, cerebellum, autoresearch, scout, etc.)
        aspect: knower | thinker | connective
        tags: List of tag strings
        content: Text content for word count computation

    Returns:
        True if successful
    """
    safe_id = validate_surreal_id(neuron_id)
    tags = tags or []
    word_count = len(content.split()) if content else 0
    stage = compute_stage(word_count)
    activation = compute_activation(word_count, stage, tags, date.today().isoformat())

    sql = f"""UPSERT {safe_id} SET
        title = '{escape_sql(title)}',
        path = '{escape_sql(path)}',
        cluster_id = '{escape_sql(cluster)}',
        aspect = '{escape_sql(aspect)}',
        stage = '{stage}',
        word_count = {word_count},
        activation = {activation},
        dim_completion = {round(min(word_count / 400.0, 1.0) * 0.5 + {"embryo": 0.1, "seedling": 0.3, "growing": 0.6, "mature": 1.0}.get(stage, 0.2) * 0.3 + min(len(tags) / 4.0, 1.0) * 0.2, 4)},
        dim_recency = 0.0,
        dim_bridging = 0.0,
        tags = {escape_tag_list(tags)},
        synapse_in = 0,
        synapse_out = 0,
        modified = time::now(),
        last_fired = time::now();"""

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            results = await _query(client, sql)
            ok = any(r.get("status") == "OK" for r in results)
            if ok:
                logger.info(f"Upserted {neuron_id} (cluster={cluster})")
            else:
                logger.warning(f"Upsert may have failed for {neuron_id}: {results}")
            return ok
    except Exception as e:
        logger.warning(f"graph_writer.upsert_neuron failed (non-blocking): {e}")
        return False


async def create_synapse(
    from_id: str,
    to_id: str,
    link_type: str = "explicit",
    reason: str = "",
) -> bool:
    """Create a synapse edge between two neurons.

    Args:
        from_id: Source neuron ID
        to_id: Target neuron ID
        link_type: explicit | latent | dream | songline (schema-enforced)
        reason: Human-readable reason for the connection

    Note: SurrealDB schema restricts link_type to [explicit, latent, dream, songline].
    Non-standard types are mapped to 'latent' with the original type in the reason.
    """
    # Map non-schema types to 'latent' (closest semantic match for inferred connections)
    ALLOWED_TYPES = {"explicit", "latent", "dream", "songline"}
    actual_type = link_type if link_type in ALLOWED_TYPES else "latent"
    if link_type not in ALLOWED_TYPES:
        reason = f"[{link_type}] {reason}"

    safe_from = validate_surreal_id(from_id)
    safe_to = validate_surreal_id(to_id)
    reason_esc = escape_sql(reason)
    sql = f"""RELATE {safe_from}->synapse->{safe_to} SET
        link_type = '{actual_type}',
        reason = '{reason_esc}',
        created = time::now();"""

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            results = await _query(client, sql)
            ok = any(r.get("status") == "OK" for r in results)
            if ok:
                logger.info(f"Synapse: {from_id} →[{link_type}]→ {to_id}")
            return ok
    except Exception as e:
        logger.warning(f"graph_writer.create_synapse failed (non-blocking): {e}")
        return False


async def annotate_neuron(
    neuron_id: str,
    agent_notes: str = "",
    increment_access: bool = True,
) -> bool:
    """Annotate a neuron with metadata (does not touch structural fields).

    Args:
        neuron_id: Target neuron ID
        agent_notes: Free-form notes to append
        increment_access: Whether to increment access_count by 1
    """
    # Neuron table is SCHEMAFUL — only use defined fields.
    # last_fired = access timestamp, activation bump = recency signal.
    safe_id = validate_surreal_id(neuron_id)
    sql = f"UPDATE {safe_id} SET last_fired = time::now(), modified = time::now();"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            results = await _query(client, sql)
            return any(r.get("status") == "OK" for r in results)
    except Exception as e:
        logger.warning(f"graph_writer.annotate_neuron failed (non-blocking): {e}")
        return False


async def batch_upsert_neurons(neurons: list[dict[str, Any]]) -> int:
    """Batch upsert multiple neurons.

    Each dict should have: neuron_id, title, and optionally:
    path, cluster, aspect, tags, content.

    Returns count of successfully upserted neurons.
    """
    if not neurons:
        return 0

    statements = []
    for n in neurons:
        tags = n.get("tags", [])
        content = n.get("content", "")
        word_count = len(content.split()) if content else 0
        stage = compute_stage(word_count)
        activation = compute_activation(word_count, stage, tags, date.today().isoformat())

        safe_id = validate_surreal_id(n['neuron_id'])
        stmt = f"""UPSERT {safe_id} SET
            title = '{escape_sql(n["title"])}',
            path = '{escape_sql(n.get("path", ""))}',
            cluster_id = '{escape_sql(n.get("cluster", ""))}',
            aspect = '{escape_sql(n.get("aspect", "connective"))}',
            stage = '{stage}',
            word_count = {word_count},
            activation = {activation},
            tags = {escape_tag_list(tags)},
            modified = time::now(),
            last_fired = time::now();"""
        statements.append(stmt)

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            sql = "\n".join(statements)
            results = await _query(client, sql)
            count = sum(1 for r in results if r.get("status") == "OK")
            logger.info(f"Batch upserted {count}/{len(neurons)} neurons")
            return count
    except Exception as e:
        logger.warning(f"graph_writer.batch_upsert_neurons failed (non-blocking): {e}")
        return 0
