#!/usr/bin/env python3
"""
Vault Keeper Cycle — autonomous vault maintenance.
Runs Health → Waking → Dreaming in sequence.
Invoked 4x/day via systemd timer.
"""

import logging
import os
import sys
import textwrap
from datetime import UTC, date, datetime
from pathlib import Path

import httpx
import numpy as np


# ── Config ──────────────────────────────────────────────────────────────────
VAULT_PATH = Path("~/vaults/cohezion-vault").expanduser()
SURREALDB_URL = os.getenv("SURREALDB_URL", "http://localhost:8001")
SURREALDB_NS = "cohezion"
SURREALDB_DB = "vault"
SURREALDB_USER = os.getenv("SURREALDB_USER", "root")
SURREALDB_PASS = os.getenv("SURREALDB_PASS", "root")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
DREAM_MODEL = os.getenv("VAULT_KEEPER_MODEL", "nemotron-3-super:cloud")
LOG_PATH = VAULT_PATH / "metabolism" / "vault-keeper.log"
CLOUD_VAULT_SRC = Path("~/dev/cohezion/cloud-vault-mcp/src").expanduser()
MAX_DREAM_SYNAPSES = 5

# ── Logging ──────────────────────────────────────────────────────────────────
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_PATH, mode="a"),
    ],
)
logger = logging.getLogger("vault-keeper")


# ── SurrealDB helpers ─────────────────────────────────────────────────────────
def surql(query: str, timeout: int = 30) -> list[dict]:
    resp = httpx.post(
        f"{SURREALDB_URL}/sql",
        content=query,
        headers={
            "Content-Type": "text/plain",
            "Accept": "application/json",
            "Surreal-NS": SURREALDB_NS,
            "Surreal-DB": SURREALDB_DB,
        },
        auth=(SURREALDB_USER, SURREALDB_PASS),
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def get_results(rows: list[dict]) -> list[dict]:
    out = []
    for row in rows:
        if row.get("status") == "OK" and isinstance(row.get("result"), list):
            out.extend(row["result"])
    return out


def first_count(rows: list[dict]) -> int:
    results = get_results(rows)
    if results and "count" in results[0]:
        return results[0]["count"]
    return len(results)


# ── Embedding helpers ─────────────────────────────────────────────────────────
def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Compute cosine similarity between two normalized vectors."""
    return float(np.dot(a, b))


def get_embedding(text: str) -> np.ndarray | None:
    """Get embedding via Ollama nomic-embed-text."""
    try:
        resp = httpx.post(
            f"{OLLAMA_URL}/api/embed",
            json={"model": "nomic-embed-text", "input": text},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        vec = np.array(data["embeddings"][0], dtype=np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec
    except Exception:
        return None


# ── Ollama helpers ─────────────────────────────────────────────────────────────
def ollama_available() -> bool:
    try:
        resp = httpx.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        return resp.status_code == 200
    except Exception:
        return False


def ollama_generate(prompt: str, temperature: float = 0.8, timeout: int = 120) -> str:
    resp = httpx.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": DREAM_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json().get("response", "")


# ── HIHO Metrics ───────────────────────────────────────────────────────────────
def compute_hiho_metrics(n_neurons: int, n_synapses: int) -> dict:
    """Calculate HIHO-weighted graph health metrics.

    Weights: connectivity 0.3, reciprocity 0.2, freshness 0.2, anti-orphan 0.3
    Target: 0.5 +/- 0.15 (HIHO equilibrium)
    """
    if n_neurons == 0:
        return {
            "hiho_score": 0.0,
            "status": "critical",
            "neurons": 0,
            "synapses": 0,
            "orphans": 0,
            "orphan_ratio": 1.0,
            "connectivity": 0.0,
            "reciprocity": 0.0,
            "freshness": 0.0,
        }

    # Connected nodes (have at least one synapse)
    try:
        connected = get_results(
            surql(
                "SELECT count() FROM neuron WHERE ->synapse = true OR <-synapse = true GROUP ALL;"
            )
        )
        n_connected = connected[0].get("count", 0) if connected else 0
    except Exception:
        n_connected = n_synapses  # Fallback: assume each synapse connects at least one node

    # Orphan ratio
    orphans = n_neurons - n_connected
    orphan_ratio = orphans / n_neurons

    # Connectivity (nodes with 2+ backlinks)
    try:
        well_connected = get_results(
            surql("SELECT count() FROM neuron WHERE count(<-synapse) >= 2 GROUP ALL;")
        )
        n_well_connected = well_connected[0].get("count", 0) if well_connected else 0
        connectivity = n_well_connected / n_neurons
    except Exception:
        connectivity = n_connected / n_neurons if n_neurons > 0 else 0.0

    # Reciprocity (bidirectional links - approximate)
    try:
        bidirectional = get_results(
            surql("SELECT count() FROM synapse WHERE out -> synapse -> in = true GROUP ALL;")
        )
        n_bidirectional = bidirectional[0].get("count", 0) if bidirectional else 0
        reciprocity = n_bidirectional / n_synapses if n_synapses > 0 else 0.0
    except Exception:
        reciprocity = 0.0

    # Freshness (notes updated <30 days - use created as proxy)
    try:
        recent = get_results(
            surql("SELECT count() FROM neuron WHERE created > time::now() - 30d GROUP ALL;")
        )
        n_recent = recent[0].get("count", 0) if recent else 0
        freshness = n_recent / n_neurons
    except Exception:
        freshness = 0.0

    # HIHO score (target: 0.5 +/- 0.15)
    hiho = 0.3 * connectivity + 0.2 * reciprocity + 0.2 * freshness + 0.3 * (1 - orphan_ratio)

    # Status classification
    if 0.35 <= hiho <= 0.65:
        status = "healthy"
    elif 0.2 <= hiho <= 0.8:
        status = "degraded"
    else:
        status = "critical"

    return {
        "hiho_score": round(hiho, 3),
        "status": status,
        "neurons": n_neurons,
        "synapses": n_synapses,
        "orphans": orphans,
        "orphan_ratio": round(orphan_ratio, 3),
        "connectivity": round(connectivity, 3),
        "reciprocity": round(reciprocity, 3),
        "freshness": round(freshness, 3),
    }


# ── Mode 1: Health ────────────────────────────────────────────────────────────
def run_health() -> dict:
    logger.info("=== HEALTH CHECK ===")
    report = {"date": str(date.today()), "ok": True, "issues": []}

    # SurrealDB reachable?
    try:
        surql("SELECT count() FROM neuron GROUP ALL;")
        logger.info("SurrealDB: OK")
    except Exception as e:
        report["ok"] = False
        report["surrealdb_down"] = True
        logger.error("SurrealDB: UNREACHABLE — %s", e)
        return report

    # Graph counts
    counts = get_results(
        surql("SELECT count() FROM neuron GROUP ALL; SELECT count() FROM synapse GROUP ALL;")
    )
    n_neurons = counts[0].get("count", 0) if counts else 0
    n_synapses = counts[1].get("count", 0) if len(counts) > 1 else 0
    ratio = round(n_synapses / n_neurons, 2) if n_neurons else 0
    logger.info("Graph: %d neurons | %d synapses | ratio %.2f", n_neurons, n_synapses, ratio)
    report.update({"neurons": n_neurons, "synapses": n_synapses, "ratio": ratio})

    # Orphan detection
    orphans = get_results(
        surql(
            "SELECT id, title FROM neuron "
            "WHERE ->(synapse WHERE true) = [] AND <-(synapse WHERE true) = [] LIMIT 20;"
        )
    )
    if orphans:
        pct = round(len(orphans) / n_neurons * 100, 1) if n_neurons else 0
        logger.info(
            "Orphan neurons: %d (%.1f%%): %s",
            len(orphans),
            pct,
            [n.get("title", n.get("id")) for n in orphans[:5]],
        )
        if pct > 10:
            report["issues"].append(f"{len(orphans)} isolated neurons ({pct}%)")
    report["orphans"] = orphans

    # HIHO-weighted graph health metrics
    try:
        hiho_metrics = compute_hiho_metrics(n_neurons, n_synapses)
        report["hiho"] = hiho_metrics
        status_emoji = {"healthy": "✅", "degraded": "⚠️", "critical": "🔴"}.get(
            hiho_metrics["status"], "❓"
        )
        logger.info(
            "HIHO Score: %.3f %s (connectivity=%.2f, reciprocity=%.2f, freshness=%.2f, orphan_ratio=%.2f)",
            hiho_metrics["hiho_score"],
            status_emoji,
            hiho_metrics["connectivity"],
            hiho_metrics["reciprocity"],
            hiho_metrics["freshness"],
            hiho_metrics["orphan_ratio"],
        )
        if hiho_metrics["status"] != "healthy":
            report["issues"].append(
                f"HIHO {hiho_metrics['status']} ({hiho_metrics['hiho_score']:.3f})"
            )
    except Exception as e:
        logger.warning("Failed to compute HIHO metrics: %s", e)

    # Concept/paper sync
    try:
        if CLOUD_VAULT_SRC not in sys.path:
            sys.path.insert(0, str(CLOUD_VAULT_SRC))
        from mcp_server.surrealdb_sync import SurrealDBSync

        sync = SurrealDBSync(
            vault_path=str(VAULT_PATH),
            surrealdb_url=SURREALDB_URL,
            namespace=SURREALDB_NS,
            database=SURREALDB_DB,
            username=SURREALDB_USER,
            password=SURREALDB_PASS,
        )
        imported_concepts = sync.bulk_import_concepts()
        imported_papers = sync.bulk_import_papers()
        if imported_concepts or imported_papers:
            logger.info("Synced: +%d concepts, +%d papers", imported_concepts, imported_papers)
    except Exception as e:
        logger.warning("Sync skipped: %s", e)

    return report


# ── Mode 2: Waking (latent synapse discovery) ────────────────────────────────
def run_waking(orphans: list[dict]) -> int:
    if not orphans:
        logger.info("=== WAKING: no orphans, skipping ===")
        return 0
    logger.info("=== WAKING: %d orphans to connect ===", len(orphans))
    written = 0

    # For each orphan, search for semantically related neurons
    existing_ids = {n["id"] for n in get_results(surql("SELECT id FROM neuron;"))}

    for neuron in orphans[:5]:  # max 5 per cycle
        nid = neuron.get("id")
        title = neuron.get("title", nid)
        if not nid:
            continue

        # Find neighbors based on title keywords
        keywords = title.lower().replace("-", " ").replace("_", " ").split()[:3]
        if not keywords:
            continue

        # Look for neurons whose titles contain overlapping keywords
        candidates = get_results(
            surql(
                f"SELECT id, title FROM neuron WHERE id != {nid} "
                f"AND (string::lowercase(title) CONTAINS '{keywords[0]}') LIMIT 3;"
            )
        )

        for candidate in candidates:
            cid = candidate.get("id")
            if not cid or cid not in existing_ids:
                continue
            # Check no synapse already exists
            existing = get_results(
                surql(f"SELECT id FROM synapse WHERE in = {nid} AND out = {cid};")
            )
            if existing:
                continue
            reason = f"Both '{title}' and '{candidate.get('title', cid)}' share thematic overlap — connected via vault-keeper waking mode"
            try:
                surql(
                    f"RELATE {nid}->synapse->{cid} SET link_type = 'latent', "
                    f"reason = '{reason.replace(chr(39), chr(92) + chr(39))}', created = time::now();"
                )
                logger.info("Latent synapse: %s -> %s", nid, cid)
                written += 1
            except Exception as e:
                logger.warning("Failed to write synapse %s->%s: %s", nid, cid, e)

    logger.info("Waking: wrote %d latent synapses", written)
    return written


# ── Mode 3: Dreaming ──────────────────────────────────────────────────────────
def run_dreaming() -> int:
    logger.info("=== DREAMING ===")
    if not ollama_available():
        logger.info("Ollama unavailable, skipping dream session")
        return 0

    # Get physics and indigenous concept nodes for TOE dreaming
    physics_concepts = get_results(
        surql(
            "SELECT id, title FROM neuron WHERE "
            "(string::lowercase(title) CONTAINS 'physics') OR "
            "(string::lowercase(title) CONTAINS 'quantum') OR "
            "(string::lowercase(title) CONTAINS 'entropy') OR "
            "(string::lowercase(title) CONTAINS 'field') OR "
            "(string::lowercase(title) CONTAINS 'symmetry') OR "
            "(string::lowercase(title) CONTAINS 'spacetime') OR "
            "(string::lowercase(title) CONTAINS 'tensor') OR "
            "(string::lowercase(title) CONTAINS 'manifold') OR "
            "(string::lowercase(title) CONTAINS 'gauge') OR "
            "(string::lowercase(title) CONTAINS 'energy') OR "
            "(string::lowercase(title) CONTAINS 'cosmology') "
            "LIMIT 15;"
        )
    )

    indigenous_concepts = get_results(
        surql(
            "SELECT id, title FROM neuron WHERE "
            "(string::lowercase(title) CONTAINS 'dreaming') OR "
            "(string::lowercase(title) CONTAINS 'songline') OR "
            "(string::lowercase(title) CONTAINS 'country') OR "
            "(string::lowercase(title) CONTAINS 'aboriginal') OR "
            "(string::lowercase(title) CONTAINS 'indigenous') OR "
            "(string::lowercase(title) CONTAINS 'first nations') OR "
            "(string::lowercase(title) CONTAINS 'ancestor') OR "
            "(string::lowercase(title) CONTAINS 'creation') OR "
            "(string::lowercase(title) CONTAINS 'mob') "
            "LIMIT 15;"
        )
    )

    # Fall back to random sampling if domain concepts insufficient
    if len(physics_concepts) < 3 or len(indigenous_concepts) < 3:
        logger.info("Insufficient domain concepts, falling back to random sampling")
        neurons = get_results(surql("SELECT id, title FROM neuron ORDER BY rand() LIMIT 20;"))
        if len(neurons) < 4:
            logger.info("Too few neurons for dreaming (%d)", len(neurons))
            return 0
        mid = len(neurons) // 2
        group_a = neurons[:mid]
        group_b = neurons[mid:]
    else:
        logger.info(
            "TOE dreaming mode: %d physics × %d indigenous concepts",
            len(physics_concepts),
            len(indigenous_concepts),
        )
        group_a = physics_concepts[:10]
        group_b = indigenous_concepts[:10]

    written = 0
    max_attempts = min(5, len(group_a) * len(group_b))

    import random

    # Generate all cross-group pairs
    pairs = [(a, b) for a in group_a for b in group_b if a["id"] != b["id"]]

    # Calculate embeddings and find resonant pairs
    resonant_pairs = []
    for neuron_a, neuron_b in pairs:
        title_a = neuron_a.get("title", "")
        title_b = neuron_b.get("title", "")

        emb_a = get_embedding(title_a)
        emb_b = get_embedding(title_b)

        if emb_a is not None and emb_b is not None:
            similarity = cosine_similarity(emb_a, emb_b)
            if similarity > 0.5:  # Structural resonance threshold
                resonant_pairs.append((neuron_a, neuron_b, similarity))

    # Sort by similarity (highest first) and limit attempts
    resonant_pairs.sort(key=lambda x: x[2], reverse=True)
    selected_pairs = (
        resonant_pairs[:max_attempts]
        if resonant_pairs
        else random.sample(pairs, min(max_attempts, len(pairs)))
    )

    for item in selected_pairs:
        if written >= MAX_DREAM_SYNAPSES:
            break

        if len(item) == 3:
            neuron_a, neuron_b, similarity = item
        else:
            neuron_a, neuron_b = item
            similarity = None

        nid_a, title_a = neuron_a["id"], neuron_a.get("title", "?")
        nid_b, title_b = neuron_b["id"], neuron_b.get("title", "?")

        # Skip if already connected
        existing = get_results(
            surql(
                f"SELECT id FROM synapse WHERE (in = {nid_a} AND out = {nid_b}) OR (in = {nid_b} AND out = {nid_a});"
            )
        )
        if existing:
            continue

        # TOE-specific prompt asking for testable predictions
        domain_context = ""
        if similarity:
            domain_context = f"\n    These concepts show structural resonance (similarity: {similarity:.2f}) in latent space."

        prompt = textwrap.dedent(f"""
            Physics/First Nations TOE Bridge:
            Concept A: '{title_a}'
            Concept B: '{title_b}'{domain_context}

            These traditions may share deep structural resonance. Your task:
            1. What specific mechanism transfers between these domains?
            2. What structural pattern connects them?
            3. What testable observation or prediction validates this resonance?

            Be precise — no vague analogies. Frame as: "If this resonance is real, then observing X should reveal Y."
            Respond in 2-3 sentences maximum.
        """).strip()

        try:
            response = ollama_generate(prompt, temperature=0.8, timeout=60)
        except Exception as e:
            logger.warning("Ollama failed for %s × %s: %s", title_a, title_b, e)
            continue

        if not response or len(response) < 30:
            continue

        # Score dream quality (0.0-1.0) with TOE-specific weighting
        quality_score = 0.0
        specificity_words = ["because", "when", "mechanism", "pattern", "structural", "transfer"]
        quality_score += sum(0.08 for w in specificity_words if w in response.lower())
        if "example" in response.lower() or "for instance" in response.lower():
            quality_score += 0.2
        if (
            "observing" in response.lower()
            or "prediction" in response.lower()
            or "testable" in response.lower()
        ):
            quality_score += 0.15  # Bonus for testable predictions
        word_count = len(response.split())
        if 30 <= word_count <= 150:
            quality_score += 0.2
        quality_score = min(quality_score, 1.0)

        # Only write if quality is sufficient
        if quality_score < 0.3:
            logger.debug(
                "Skipping low quality dream (score=%.2f): %s", quality_score, response[:80]
            )
            continue

        resonance = response[:500].replace("'", "\\'")
        try:
            surql(
                f"RELATE {nid_a}->synapse->{nid_b} SET link_type = 'dream', "
                f"resonance = '{resonance}', quality_score = {quality_score}, "
                f"similarity = {similarity or 0.0}, created = time::now();"
            )
            logger.info(
                "TOE dream synapse: %s × %s (score=%.2f, sim=%.2f)",
                title_a,
                title_b,
                quality_score,
                similarity or 0.0,
            )
            written += 1
        except Exception as e:
            logger.warning("Failed to write dream synapse: %s", e)

    logger.info("Dreaming: wrote %d TOE dream synapses", written)
    return written


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    start = datetime.now(UTC).isoformat()
    logger.info("Vault Keeper Cycle started: %s", start)

    health = run_health()

    if health.get("surrealdb_down"):
        logger.error("Aborting: SurrealDB unavailable")
        sys.exit(1)

    orphans = health.get("orphans", [])
    latent_written = run_waking(orphans)
    dream_written = run_dreaming()

    logger.info(
        "Cycle complete | neurons=%d synapses=%d latent_added=%d dreams_added=%d issues=%s",
        health.get("neurons", 0),
        health.get("synapses", 0),
        latent_written,
        dream_written,
        health.get("issues") or "none",
    )


if __name__ == "__main__":
    main()
