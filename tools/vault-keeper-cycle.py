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

    # Sample neurons from the graph
    neurons = get_results(surql("SELECT id, title FROM neuron ORDER BY rand() LIMIT 20;"))
    if len(neurons) < 4:
        logger.info("Too few neurons for dreaming (%d)", len(neurons))
        return 0

    # Split into two random groups
    mid = len(neurons) // 2
    group_a = neurons[:mid]
    group_b = neurons[mid:]

    written = 0
    attempts = 0
    max_attempts = min(5, len(group_a) * len(group_b))

    import random

    pairs = [(a, b) for a in group_a for b in group_b if a["id"] != b["id"]]
    random.shuffle(pairs)

    for neuron_a, neuron_b in pairs[:max_attempts]:
        if written >= MAX_DREAM_SYNAPSES:
            break

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

        prompt = textwrap.dedent(f"""
            Given concept A: '{title_a}' and concept B: '{title_b}', describe any non-obvious structural or mechanistic resonances between them.
            What specific mechanism transfers between these domains? Give one concrete example of how knowing this connection would be useful.
            Be precise — no vague analogies. Respond in 2-3 sentences maximum.
        """).strip()

        try:
            response = ollama_generate(prompt, temperature=0.8, timeout=60)
        except Exception as e:
            logger.warning("Ollama failed for %s × %s: %s", title_a, title_b, e)
            continue

        if not response or len(response) < 30:
            continue

        # Score dream quality (0.0-1.0)
        quality_score = 0.0
        specificity_words = ["because", "when", "mechanism", "pattern", "structural", "transfer"]
        quality_score += sum(0.08 for w in specificity_words if w in response.lower())
        if "example" in response.lower() or "for instance" in response.lower():
            quality_score += 0.2
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
                f"resonance = '{resonance}', quality_score = {quality_score}, created = time::now();"
            )
            logger.info("Dream synapse: %s × %s (score=%.2f)", title_a, title_b, quality_score)
            written += 1
        except Exception as e:
            logger.warning("Failed to write dream synapse: %s", e)

    logger.info("Dreaming: wrote %d dream synapses", written)
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
