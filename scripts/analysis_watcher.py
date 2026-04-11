#!/usr/bin/env python3
"""Analysis Watcher - Real-time Ollama narrative generation for mass simulations.

Polls SurrealDB for completed universe summaries and generates journey
narratives using phi3:mini via the local Ollama HTTP API.

Runs as a separate process alongside mass_sim_driver.py. Communicates
only through SurrealDB (no shared memory or IPC).

Usage:
    uv run python scripts/analysis_watcher.py --run-id mass_sim_1738800000
    uv run python scripts/analysis_watcher.py --auto  # discovers latest run
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import logging
import os
import signal
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import httpx


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger("analysis_watcher")

# Suppress verbose SurrealDB response logging (floods watcher output)
logging.getLogger("cohezion.core.persistence.surreal_client").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "phi3:mini")
POLL_INTERVAL_S = int(os.environ.get("WATCHER_POLL_INTERVAL", "30"))
IDLE_TIMEOUT_S = int(os.environ.get("WATCHER_IDLE_TIMEOUT", "600"))
OLLAMA_TIMEOUT_S = int(os.environ.get("OLLAMA_TIMEOUT", "180"))
MAX_CONSECUTIVE_FAILURES = 10
MIN_AVAILABLE_RAM_GB = 15


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class UniverseSummary:
    """Parsed universe summary from SurrealDB."""

    universe_id: str
    seed: int
    mean_coherence: float
    pct_within_bounds: float
    mean_norm: float
    elapsed_seconds: float
    n_agents: int
    n_epochs: int
    created_at: str


@dataclass
class PopulationStats:
    """Running statistics across all analyzed universes."""

    coherences: list[float] = field(default_factory=list)
    bounds_pcts: list[float] = field(default_factory=list)
    norms: list[float] = field(default_factory=list)
    elapsed: list[float] = field(default_factory=list)

    def add(self, summary: UniverseSummary) -> None:
        self.coherences.append(summary.mean_coherence)
        self.bounds_pcts.append(summary.pct_within_bounds)
        self.norms.append(summary.mean_norm)
        self.elapsed.append(summary.elapsed_seconds)

    @property
    def count(self) -> int:
        return len(self.coherences)

    def mean(self, values: list[float]) -> float:
        return sum(values) / len(values) if values else 0.0

    def std(self, values: list[float]) -> float:
        if len(values) < 2:
            return 0.0
        m = self.mean(values)
        return (sum((x - m) ** 2 for x in values) / (len(values) - 1)) ** 0.5

    def summary_str(self) -> str:
        return (
            f"Population ({self.count} universes): "
            f"coherence={self.mean(self.coherences):.4f} +/- {self.std(self.coherences):.4f}, "
            f"within_bounds={self.mean(self.bounds_pcts):.1%} +/- {self.std(self.bounds_pcts):.1%}, "
            f"norm={self.mean(self.norms):.4f} +/- {self.std(self.norms):.4f}"
        )


# ---------------------------------------------------------------------------
# Memory guard
# ---------------------------------------------------------------------------


def get_available_ram_gb() -> float:
    """Read available RAM from /proc/meminfo (Linux only)."""
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    kb = int(line.split()[1])
                    return kb / (1024 * 1024)
    except (OSError, ValueError, IndexError):
        pass
    return 999.0  # Assume plenty if we can't read


def ram_is_safe() -> bool:
    """Check if enough RAM is available for Ollama inference."""
    available = get_available_ram_gb()
    if available < MIN_AVAILABLE_RAM_GB:
        logger.warning(
            f"Low RAM: {available:.1f} GB available (need {MIN_AVAILABLE_RAM_GB} GB). Skipping Ollama call."
        )
        return False
    return True


# ---------------------------------------------------------------------------
# Ollama client
# ---------------------------------------------------------------------------


async def check_ollama_health(client: httpx.AsyncClient) -> bool:
    """Check if Ollama is running and responsive."""
    try:
        resp = await client.get(f"{OLLAMA_URL}/api/tags", timeout=5.0)
        return resp.status_code == 200
    except (httpx.ConnectError, httpx.TimeoutException):
        return False


async def call_ollama(client: httpx.AsyncClient, prompt: str) -> str | None:
    """Call Ollama API with phi3:mini. Returns response text or None on failure."""
    if not ram_is_safe():
        return None

    try:
        resp = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "num_predict": 256,
                },
            },
            timeout=OLLAMA_TIMEOUT_S,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "")
    except httpx.TimeoutException:
        logger.warning(f"Ollama timed out after {OLLAMA_TIMEOUT_S}s")
        return None
    except (httpx.HTTPStatusError, httpx.ConnectError) as e:
        logger.warning(f"Ollama call failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------


def build_universe_prompt(summary: UniverseSummary, pop_stats: PopulationStats) -> str:
    """Build analysis prompt for a single universe."""
    pop_context = ""
    if pop_stats.count > 0:
        pop_context = (
            f"\nPopulation context ({pop_stats.count} universes analyzed so far):\n"
            f"  Mean coherence: {pop_stats.mean(pop_stats.coherences):.4f} "
            f"(std: {pop_stats.std(pop_stats.coherences):.4f})\n"
            f"  Mean within-bounds: {pop_stats.mean(pop_stats.bounds_pcts):.1%}\n"
            f"  Mean norm: {pop_stats.mean(pop_stats.norms):.4f}\n"
        )

    return f"""Analyze this FLUME simulation universe. HIHO target=0.5, bounds=[0.3,0.7].

{summary.universe_id} (seed={summary.seed}): {summary.n_agents} agents, {summary.n_epochs} epochs
Coherence={summary.mean_coherence:.4f}, within_bounds={summary.pct_within_bounds:.1%}, norm={summary.mean_norm:.4f}, time={summary.elapsed_seconds:.1f}s
{pop_context}
Reply with exactly these sections (1-2 sentences each):
NARRATIVE: Scientific story of this universe's journey.
HIHO_ASSESSMENT: Rate excellent/good/fair/poor with reason.
ANOMALY_FLAGS: List anomalies or "none".
POPULATION_COMPARISON: Compare to population stats above."""


def build_synthesis_prompt(pop_stats: PopulationStats) -> str:
    """Build cross-universe synthesis prompt."""
    return f"""You are writing a final synthesis report for a COHEZION FLUME mass simulation.
{pop_stats.count} universes were simulated, each with unique random weight seeds.
The system targets HIHO coherence of 0.5 (Half-In-Half-Out equilibrium).

Population statistics:
  Mean coherence: {pop_stats.mean(pop_stats.coherences):.4f} (std: {pop_stats.std(pop_stats.coherences):.4f})
  Mean within-bounds [0.3, 0.7]: {pop_stats.mean(pop_stats.bounds_pcts):.1%} (std: {pop_stats.std(pop_stats.bounds_pcts):.1%})
  Mean norm: {pop_stats.mean(pop_stats.norms):.4f} (std: {pop_stats.std(pop_stats.norms):.4f})
  Mean simulation time: {pop_stats.mean(pop_stats.elapsed):.1f}s

  Best coherence: {max(pop_stats.coherences):.4f}
  Worst coherence: {min(pop_stats.coherences):.4f}
  Best within-bounds: {max(pop_stats.bounds_pcts):.1%}
  Worst within-bounds: {min(pop_stats.bounds_pcts):.1%}

Write a synthesis report (3-5 paragraphs) covering:
1. Overall HIHO stability assessment across the population
2. Variance analysis: how consistent is coherence across random seeds?
3. Outlier analysis: any universes that diverged significantly?
4. Implications for the FLUME framework's robustness
5. Recommendations for the next simulation run"""


# ---------------------------------------------------------------------------
# Response parser
# ---------------------------------------------------------------------------


def parse_narrative_response(raw: str) -> dict:
    """Parse structured Ollama response into sections."""
    sections = {
        "narrative": "",
        "hiho_assessment": "",
        "anomaly_flags": [],
        "population_comparison": "",
    }

    current_key = None
    current_lines: list[str] = []

    for line in raw.split("\n"):
        stripped = line.strip()
        upper = stripped.upper()

        if upper.startswith("NARRATIVE:"):
            if current_key:
                sections[current_key] = _flush(current_key, current_lines)
            current_key = "narrative"
            current_lines = [stripped[len("NARRATIVE:") :].strip()]
        elif upper.startswith("HIHO_ASSESSMENT:"):
            if current_key:
                sections[current_key] = _flush(current_key, current_lines)
            current_key = "hiho_assessment"
            current_lines = [stripped[len("HIHO_ASSESSMENT:") :].strip()]
        elif upper.startswith("ANOMALY_FLAGS:"):
            if current_key:
                sections[current_key] = _flush(current_key, current_lines)
            current_key = "anomaly_flags"
            current_lines = [stripped[len("ANOMALY_FLAGS:") :].strip()]
        elif upper.startswith("POPULATION_COMPARISON:"):
            if current_key:
                sections[current_key] = _flush(current_key, current_lines)
            current_key = "population_comparison"
            current_lines = [stripped[len("POPULATION_COMPARISON:") :].strip()]
        elif current_key:
            current_lines.append(stripped)

    # Flush last section
    if current_key:
        sections[current_key] = _flush(current_key, current_lines)

    return sections


def _flush(key: str, lines: list[str]) -> str | list[str]:
    """Flush accumulated lines into the right type."""
    text = " ".join(line for line in lines if line).strip()
    if key == "anomaly_flags":
        if not text or text.lower() in ("none", "none.", "n/a"):
            return []
        return [f.strip() for f in text.split(",") if f.strip()]
    return text


# ---------------------------------------------------------------------------
# SurrealDB polling
# ---------------------------------------------------------------------------


async def connect_db():
    """Connect to SurrealDB using the project's SurrealClient."""
    from cohezion.core.persistence.surreal_client import SurrealClient

    client = SurrealClient(
        url="ws://localhost:8000/rpc",
        namespace="cohezion",
        database="universe",
    )
    connected = await client.connect()
    if not connected:
        raise ConnectionError("Failed to connect to SurrealDB")
    return client


def _extract_rows(result: list) -> list[dict]:
    """Extract row dicts from SurrealDB query response.

    The SDK returns different shapes depending on version:
      - Newer SDK: flat list of row dicts  [{row1}, {row2}, ...]
      - Older SDK: nested [[{row1}, ...]]  or [{"result": [{row1}, ...]}]
    """
    if not result:
        return []
    first = result[0]
    if isinstance(first, list):
        # Nested: [[rows]]
        return first
    if isinstance(first, dict) and "result" in first:
        # Wrapped: [{"result": [rows], "status": "OK"}]
        return first["result"]
    # Flat: [{row1}, {row2}, ...] — the result IS the rows
    return result


async def discover_latest_run(db) -> str | None:
    """Find the most recent mass_sim_run in SurrealDB."""
    try:
        result = await db.query("SELECT id FROM mass_sim_run ORDER BY created_at DESC LIMIT 1")
        rows = _extract_rows(result) if result and isinstance(result, list) else []
        if rows:
            run_id = rows[0].get("id", "")
            # Strip table prefix if present (e.g., "mass_sim_run:mass_sim_123" -> "mass_sim_123")
            if ":" in str(run_id):
                run_id = str(run_id).split(":")[-1]
            return run_id
    except Exception as e:
        logger.error(f"Failed to discover latest run: {e}")
    return None


def _row_to_summary(row: dict) -> UniverseSummary | None:
    """Convert a row dict to UniverseSummary, or None if invalid."""
    uid = row.get("universe_id", "")
    if not uid:
        return None
    return UniverseSummary(
        universe_id=uid,
        seed=row.get("seed", 0),
        mean_coherence=row.get("mean_coherence", 0.0),
        pct_within_bounds=row.get("pct_within_bounds", 0.0),
        mean_norm=row.get("mean_norm", 0.0),
        elapsed_seconds=row.get("elapsed_seconds", 0.0),
        n_agents=row.get("n_agents", 0),
        n_epochs=row.get("n_epochs", 0),
        created_at=row.get("created_at", ""),
    )


async def fetch_new_summaries(
    db, run_id: str, seen_universe_ids: set[str]
) -> list[UniverseSummary]:
    """Fetch universe summaries we haven't processed yet.

    Tries SurrealDB first, falls back to JSONL files if DB query fails
    (e.g., WebSocket keepalive timeout on long-running connections).
    """
    summaries: list[UniverseSummary] = []

    # Try SurrealDB first
    try:
        result = await db.query(
            "SELECT * FROM sim_universe_summary WHERE run_id = $run_id ORDER BY created_at ASC",
            {"run_id": run_id},
        )
        if result and isinstance(result, list):
            rows = _extract_rows(result)
            for row in rows:
                s = _row_to_summary(row)
                if s and s.universe_id not in seen_universe_ids:
                    summaries.append(s)
    except Exception as e:
        logger.warning(f"SurrealDB query failed: {e}")

    # JSONL supplement: always check JSONL too (sim writes here when DB connection dies)
    seen_so_far = seen_universe_ids | {s.universe_id for s in summaries}
    jsonl_path = Path("data/mass_sim/checkpoints/jsonl/sim_universe_summary.jsonl")
    if jsonl_path.exists():
        import json

        try:
            with open(jsonl_path) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    if row.get("run_id") != run_id:
                        continue
                    s = _row_to_summary(row)
                    if s and s.universe_id not in seen_so_far:
                        seen_so_far.add(s.universe_id)
                        summaries.append(s)
        except Exception as e:
            logger.warning(f"JSONL read failed: {e}")

    return summaries


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


async def store_narrative(db, run_id: str, universe_id: str, narrative: dict) -> None:
    """Store narrative to SurrealDB with JSONL fallback."""
    record = {
        "run_id": run_id,
        "universe_id": universe_id,
        "narrative": narrative.get("narrative", ""),
        "hiho_assessment": narrative.get("hiho_assessment", ""),
        "anomaly_flags": narrative.get("anomaly_flags", []),
        "population_comparison": narrative.get("population_comparison", ""),
        "model": narrative.get("model", OLLAMA_MODEL),
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    try:
        await db.query(
            "CREATE sim_journey_narrative CONTENT $data",
            {"data": record},
        )
    except Exception as e:
        # JSONL fallback
        logger.warning(f"DB narrative write failed, using JSONL fallback: {e}")
        fallback_dir = Path("data/mass_sim/checkpoints/jsonl")
        fallback_dir.mkdir(parents=True, exist_ok=True)
        import json

        with open(fallback_dir / "sim_journey_narrative.jsonl", "a") as f:
            f.write(json.dumps(record, default=str) + "\n")


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

_shutdown = False


def _signal_handler(sig, frame):
    global _shutdown
    logger.info(f"Signal {sig} received, shutting down gracefully...")
    _shutdown = True


async def run_watcher(run_id: str) -> None:
    """Main watcher loop: poll -> analyze -> persist."""
    global _shutdown

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    logger.info("=" * 60)
    logger.info("ANALYSIS WATCHER")
    logger.info(f"  Run ID: {run_id}")
    logger.info(f"  Model: {OLLAMA_MODEL}")
    logger.info(f"  Poll interval: {POLL_INTERVAL_S}s")
    logger.info(f"  Idle timeout: {IDLE_TIMEOUT_S}s")
    logger.info("=" * 60)

    # Connect to SurrealDB
    try:
        db = await connect_db()
    except Exception as e:
        logger.error(f"Cannot connect to SurrealDB: {e}. Aborting.")
        return

    # Check Ollama
    async with httpx.AsyncClient() as http:
        if not await check_ollama_health(http):
            logger.error("Ollama is not running. Aborting.")
            return
        logger.info(f"Ollama healthy at {OLLAMA_URL}")

    # State
    seen: set[str] = set()
    pop_stats = PopulationStats()
    consecutive_failures = 0
    last_activity = time.time()
    total_narratives = 0

    async with httpx.AsyncClient() as http:
        while not _shutdown:
            # Fetch new universes
            new_summaries = await fetch_new_summaries(db, run_id, seen)

            if new_summaries:
                last_activity = time.time()
                logger.info(
                    f"Found {len(new_summaries)} new universe(s) (total seen: {len(seen) + len(new_summaries)})"
                )

                for summary in new_summaries:
                    if _shutdown:
                        break

                    seen.add(summary.universe_id)
                    pop_stats.add(summary)

                    # Generate narrative via Ollama
                    prompt = build_universe_prompt(summary, pop_stats)
                    raw_response = await call_ollama(http, prompt)

                    if raw_response:
                        narrative = parse_narrative_response(raw_response)
                        narrative["model"] = OLLAMA_MODEL
                        narrative["raw_response"] = raw_response

                        # Persist
                        try:
                            await store_narrative(db, run_id, summary.universe_id, narrative)
                            total_narratives += 1
                            consecutive_failures = 0
                            logger.info(
                                f"  [{summary.universe_id}] coherence={summary.mean_coherence:.4f} -> narrative stored"
                            )
                        except Exception as e:
                            logger.warning(f"  Failed to store narrative: {e}")
                            consecutive_failures += 1
                    else:
                        consecutive_failures += 1
                        logger.warning(
                            f"  [{summary.universe_id}] Ollama returned nothing "
                            f"(failures: {consecutive_failures}/{MAX_CONSECUTIVE_FAILURES})"
                        )

                    # Circuit breaker
                    if consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                        logger.error(
                            f"Circuit breaker: {MAX_CONSECUTIVE_FAILURES} consecutive Ollama failures. Exiting."
                        )
                        _shutdown = True
                        break

                logger.info(f"  {pop_stats.summary_str()}")
            else:
                # No new data — check idle timeout
                idle_seconds = time.time() - last_activity
                if idle_seconds > IDLE_TIMEOUT_S:
                    logger.info(
                        f"No new data for {idle_seconds:.0f}s (timeout: {IDLE_TIMEOUT_S}s). Running final synthesis."
                    )
                    break

            if not _shutdown:
                await asyncio.sleep(POLL_INTERVAL_S)

    # Final cross-universe synthesis
    if pop_stats.count > 1 and not (consecutive_failures >= MAX_CONSECUTIVE_FAILURES):
        logger.info("Generating cross-universe synthesis...")
        async with httpx.AsyncClient() as http:
            synthesis_prompt = build_synthesis_prompt(pop_stats)
            synthesis_raw = await call_ollama(http, synthesis_prompt)

            if synthesis_raw:
                synthesis = {
                    "narrative": synthesis_raw,
                    "hiho_assessment": f"Population synthesis across {pop_stats.count} universes",
                    "anomaly_flags": [],
                    "population_comparison": pop_stats.summary_str(),
                    "model": OLLAMA_MODEL,
                }
                try:
                    await store_narrative(db, run_id, "__synthesis__", synthesis)
                    logger.info("Cross-universe synthesis stored.")
                except Exception as e:
                    logger.warning(f"Failed to store synthesis: {e}")
            else:
                logger.warning("Synthesis generation failed (Ollama unavailable)")

    # Cleanup
    with contextlib.suppress(Exception):
        await db.close()

    logger.info("=" * 60)
    logger.info("ANALYSIS WATCHER COMPLETE")
    logger.info(f"  Universes analyzed: {len(seen)}")
    logger.info(f"  Narratives stored: {total_narratives}")
    if pop_stats.count > 0:
        logger.info(f"  {pop_stats.summary_str()}")
    logger.info("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analysis Watcher - Real-time Ollama narrative generation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Specific run ID to watch (e.g., mass_sim_1738800000)",
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Auto-discover the latest run from SurrealDB",
    )
    parser.add_argument(
        "--poll-interval",
        type=int,
        default=POLL_INTERVAL_S,
        help=f"Seconds between polls (default: {POLL_INTERVAL_S})",
    )
    parser.add_argument(
        "--idle-timeout",
        type=int,
        default=IDLE_TIMEOUT_S,
        help=f"Seconds of no new data before final synthesis (default: {IDLE_TIMEOUT_S})",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=OLLAMA_MODEL,
        help=f"Ollama model to use (default: {OLLAMA_MODEL})",
    )
    return parser.parse_args()


async def async_main() -> int:
    global POLL_INTERVAL_S, IDLE_TIMEOUT_S, OLLAMA_MODEL

    args = parse_args()

    # Apply CLI overrides to globals
    POLL_INTERVAL_S = args.poll_interval
    IDLE_TIMEOUT_S = args.idle_timeout
    OLLAMA_MODEL = args.model

    # Determine run_id
    run_id = args.run_id

    if not run_id and args.auto:
        logger.info("Auto-discovering latest run from SurrealDB...")
        try:
            db = await connect_db()
            run_id = await discover_latest_run(db)
            await db.close()
        except Exception as e:
            logger.error(f"Auto-discovery failed: {e}")
            return 1

    if not run_id:
        # Wait for a run to appear (the sim may not have started yet)
        logger.info("No run_id provided. Waiting for a run to appear in SurrealDB...")
        for _attempt in range(60):  # Wait up to 5 minutes
            try:
                db = await connect_db()
                run_id = await discover_latest_run(db)
                await db.close()
                if run_id:
                    break
            except Exception:
                pass
            await asyncio.sleep(5)

        if not run_id:
            logger.error("No run found after 5 minutes. Aborting.")
            return 1

    logger.info(f"Watching run: {run_id}")
    await run_watcher(run_id)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(async_main()))
