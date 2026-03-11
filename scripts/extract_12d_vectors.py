#!/usr/bin/env python3
"""12D Feature Vector Extraction Pipeline — SurrealDB → FLUME Training Data.

Bridges the Triune Vault's SurrealDB connectome to the FLUME VAE training pipeline.
Extracts 12-dimensional feature vectors from neuron state, session trajectories from
neuron_history, and models the Unified Physics forces and agents as EVOs.

The 12 Dimensions (from cortex/12D-Projection.md):
  0. Connectivity         — synapse_out + synapse_in (graph degree)
  1. Conceptual Depth     — word_count (depth of explanation)
  2. Temporal Distribution — created date relative to project timeline
  3. Cross-domain Presence — tag count + Country crossings
  4. Completion Maturity   — lifecycle stage ordinal
  5. Recency              — days since last_fired
  6. Semantic Similarity   — embedding cosine distance (Ollama, when available)
  7. Domain Clustering     — Country membership density
  8. Algorithm Complexity  — derived from tags/content heuristics
  9. Implementation Diff.  — derived from tags/content heuristics
 10. Interdisciplinary Transfer — songline crossings + moiety kinship count
 11. Impact Score          — activation energy (0.0-1.0)

Unified Physics Forces (computed per-neuron):
  - Gravity        = kinship bond count (long-range, always present)
  - Electromagnetism = synapse weight sum (medium-range, bidirectional)
  - Strong Force   = HIHO coherence of home Country (short-range, cluster-binding)
  - Weak Force     = activation decay rate (transforms stages)

Agents as EVOs (Exotic Vacuum Objects):
  Agent neurons (cluster_id="Agents") are transient, high-energy structures that
  catalyze HIHO fusion as they traverse Country. Their trajectories through the
  12D space are EVO trails — paths through the vacuum (latent space) that create
  temporary high-density regions and trigger emergence events.

Output Formats:
  --format numpy   → .npz file with vectors, trajectories, metadata
  --format jsonl   → JSONL file (one record per neuron or trajectory)
  --format both    → both formats (default)

Usage:
  python3 scripts/extract_12d_vectors.py                    # full extraction
  python3 scripts/extract_12d_vectors.py --trajectories     # trajectories only
  python3 scripts/extract_12d_vectors.py --snapshot         # snapshot only
  python3 scripts/extract_12d_vectors.py --format numpy     # numpy output only
"""

import argparse
import base64
import json
import math
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SURREAL_URL = "http://localhost:8001/sql"
HDRS = {
    "Content-Type": "text/plain",
    "surreal-ns": "cohezion",
    "surreal-db": "vault",
    "Authorization": "Basic " + base64.b64encode(b"root:root").decode(),
}

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "flume-training"

# ─── Normalization constants (empirical from vault state 2026-03-09) ───
# These cap outliers and normalize to [0, 1]
MAX_SYNAPSE_TOTAL = 300   # compound-engineering has 236 in + 68 out = 304
MAX_WORD_COUNT = 20000    # cap at 20k (outlier 7.5M adversarial review excluded)
MAX_TAGS = 15             # empirical cap
MAX_RECENCY_DAYS = 365    # anything older than a year → 0.0 recency
MAX_KINSHIP_BONDS = 20    # empirical cap per neuron
MAX_SONGLINE_CROSSINGS = 5  # empirical cap per neuron

# ─── Stage ordinals (circular lifecycle, not linear) ───
# embryo emerges from Dreaming, grows, matures, rests (returns to Dreaming),
# composts (transformation), and can be renewed (re-enters as growing)
STAGE_ORDINAL = {
    "embryo": 0.15,       # just emerged from the Dreaming
    "growing": 0.40,      # being sung into existence
    "mature": 0.85,       # an Elder in its Country
    "resting": 0.10,      # returned to the Dreaming, waiting
    "composting": 0.30,   # transforming — feeds new growth
    "renewed": 0.50,      # re-entered the cycle
}

# ─── Complexity/difficulty tag heuristics ───
COMPLEXITY_TAGS = {
    "architecture": 0.8, "quantum": 0.9, "vae": 0.7, "neural-network": 0.7,
    "graph-databases": 0.6, "agent-workflow": 0.6, "machine-learning": 0.7,
    "reinforcement-learning": 0.8, "transformer": 0.8, "latent-space": 0.7,
    "compound-engineering": 0.7, "security": 0.6, "cryptography": 0.8,
    "topology": 0.9, "quantum-computing": 0.95, "quantum-entanglement": 0.85,
    "observability": 0.5, "mcp": 0.5, "surrealdb": 0.5,
}
DIFFICULTY_TAGS = {
    "implementation": 0.6, "deployment": 0.5, "ci-cd": 0.5, "docker": 0.4,
    "testing": 0.3, "debugging": 0.5, "refactoring": 0.4, "migration": 0.6,
    "integration": 0.6, "performance": 0.5, "scaling": 0.7, "distributed": 0.8,
    "real-time": 0.6, "concurrent": 0.7, "multi-agent": 0.7,
}


def query(sql):
    """Execute SurrealQL and return parsed JSON response."""
    req = urllib.request.Request(
        SURREAL_URL, data=sql.encode("utf-8"), headers=HDRS, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except Exception as e:
        print(f"  Query error: {e}", file=sys.stderr)
        return []


def get_results(data, idx=0):
    if not data or idx >= len(data):
        return []
    entry = data[idx]
    if entry.get("status") != "OK":
        print(f"  SurrealDB error: {entry.get('result', '?')}", file=sys.stderr)
        return []
    return entry.get("result") or []


def clamp(val, lo=0.0, hi=1.0):
    return max(lo, min(hi, val))


# ═══════════════════════════════════════════════════════════════════════
# 12D VECTOR COMPUTATION
# ═══════════════════════════════════════════════════════════════════════

def compute_12d_vector(neuron, country_data, kinship_counts, songline_counts, now):
    """Compute the 12D feature vector for a single neuron.

    Returns a list of 12 floats, each in [0.0, 1.0].
    """
    nid = str(neuron.get("id", ""))

    # D0: Connectivity — graph degree (in + out), normalized
    syn_out = neuron.get("synapse_out", 0) or 0
    syn_in = neuron.get("synapse_in", 0) or 0
    connectivity = clamp((syn_out + syn_in) / MAX_SYNAPSE_TOTAL)

    # D1: Conceptual Depth — word count as proxy for depth of explanation
    wc = neuron.get("word_count", 0) or 0
    wc = min(wc, MAX_WORD_COUNT)  # cap outliers
    conceptual_depth = clamp(wc / MAX_WORD_COUNT)

    # D2: Temporal Distribution — when created relative to project timeline
    # Project epoch: 2026-01-01. Normalize over ~6 months.
    created = neuron.get("created")
    if created and isinstance(created, str):
        try:
            ct = datetime.fromisoformat(created.replace("Z", "+00:00"))
            epoch = datetime(2026, 1, 1, tzinfo=timezone.utc)
            days_since_epoch = max(0, (ct - epoch).total_seconds() / 86400)
            temporal_dist = clamp(days_since_epoch / 180)  # 6 months
        except (ValueError, TypeError):
            temporal_dist = 0.5
    else:
        temporal_dist = 0.5

    # D3: Cross-domain Presence — tag count + Country crossings
    tags = neuron.get("tags", []) or []
    tag_count = len(tags) if isinstance(tags, list) else 0
    # Songline crossings indicate cross-domain presence
    sc = songline_counts.get(nid, 0)
    cross_domain = clamp((tag_count / MAX_TAGS) * 0.6 + (sc / MAX_SONGLINE_CROSSINGS) * 0.4)

    # D4: Completion Maturity — lifecycle stage ordinal (circular, not linear)
    stage = neuron.get("stage", "growing")
    completion = STAGE_ORDINAL.get(stage, 0.4)

    # D5: Recency — how recently the neuron fired (inverse of age)
    last_fired = neuron.get("last_fired")
    if last_fired and isinstance(last_fired, str):
        try:
            lf = datetime.fromisoformat(last_fired.replace("Z", "+00:00"))
            days_ago = max(0, (now - lf).total_seconds() / 86400)
            recency = clamp(1.0 - (days_ago / MAX_RECENCY_DAYS))
        except (ValueError, TypeError):
            recency = 0.5
    else:
        recency = 0.5

    # D6: Semantic Similarity — embedding distance (placeholder until Ollama integration)
    # When embeddings exist, this would be mean cosine similarity to cluster centroid
    embedding = neuron.get("embedding")
    if embedding and isinstance(embedding, list) and len(embedding) > 0:
        semantic_sim = 0.6  # placeholder — real value needs centroid comparison
    else:
        semantic_sim = 0.0  # no embedding available

    # D7: Domain Clustering — Country membership density
    # How densely connected is the neuron's Country?
    cluster_id = neuron.get("cluster_id", "")
    country = country_data.get(cluster_id, {})
    country_health = country.get("health", 0.5)
    country_neurons = country.get("neuron_count", 1)
    # Density = health * log(neuron_count) — larger, healthier countries score higher
    domain_clustering = clamp(country_health * math.log1p(country_neurons) / 6.0)

    # D8: Algorithm Complexity — heuristic from tags
    complexity = 0.0
    for tag in tags:
        if isinstance(tag, str):
            complexity = max(complexity, COMPLEXITY_TAGS.get(tag.lower(), 0.0))
    # Boost for cortex/genome notes (they describe algorithms/specs)
    aspect = neuron.get("aspect", "")
    if aspect == "knower" and wc > 1000:
        complexity = clamp(complexity + 0.1)

    # D9: Implementation Difficulty — heuristic from tags + aspect
    difficulty = 0.0
    for tag in tags:
        if isinstance(tag, str):
            difficulty = max(difficulty, DIFFICULTY_TAGS.get(tag.lower(), 0.0))
    # Boost for doer notes (they ARE implementation)
    if aspect == "doer":
        difficulty = clamp(difficulty + 0.15)

    # D10: Interdisciplinary Transfer — songline crossings + moiety kinship
    kinship_count = kinship_counts.get(nid, 0)
    transfer = clamp(
        (sc / MAX_SONGLINE_CROSSINGS) * 0.5
        + (kinship_count / MAX_KINSHIP_BONDS) * 0.5
    )

    # D11: Impact Score — activation energy (already 0.0-1.0)
    impact = clamp(neuron.get("activation", 0.5))

    return [
        connectivity, conceptual_depth, temporal_dist, cross_domain,
        completion, recency, semantic_sim, domain_clustering,
        complexity, difficulty, transfer, impact,
    ]


# ═══════════════════════════════════════════════════════════════════════
# UNIFIED PHYSICS FORCES
# ═══════════════════════════════════════════════════════════════════════

def compute_forces(neuron, kinship_counts, country_data, hiho_scores):
    """Compute the four unified physics forces for a neuron.

    Returns dict with gravity, electromagnetism, strong_force, weak_force.
    All normalized to [0.0, 1.0].
    """
    nid = str(neuron.get("id", ""))
    cluster_id = neuron.get("cluster_id", "")

    # Gravity — kinship bond count (long-range, always present)
    gravity = clamp(kinship_counts.get(nid, 0) / MAX_KINSHIP_BONDS)

    # Electromagnetism — synapse weight sum (bidirectional connections)
    syn_total = (neuron.get("synapse_out", 0) or 0) + (neuron.get("synapse_in", 0) or 0)
    electromagnetism = clamp(syn_total / MAX_SYNAPSE_TOTAL)

    # Strong Force — HIHO coherence of home Country (short-range, cluster-binding)
    strong_force = clamp(hiho_scores.get(cluster_id, 0.0))

    # Weak Force — activation decay pressure
    # Low activation + old last_fired = high weak force (transformation pressure)
    activation = neuron.get("activation", 0.5)
    stage = neuron.get("stage", "growing")
    if stage in ("resting", "composting"):
        weak_force = 0.8  # high transformation pressure
    elif activation < 0.3:
        weak_force = 0.5  # moderate pressure
    else:
        weak_force = 0.1  # low pressure (stable)

    return {
        "gravity": gravity,
        "electromagnetism": electromagnetism,
        "strong_force": strong_force,
        "weak_force": weak_force,
    }


# ═══════════════════════════════════════════════════════════════════════
# EVO CLASSIFICATION (Agents as Exotic Vacuum Objects)
# ═══════════════════════════════════════════════════════════════════════

def classify_evo(neuron):
    """Determine if a neuron is an EVO (Exotic Vacuum Object).

    EVOs are agent neurons — transient, high-energy, catalytic.
    Returns EVO properties dict or None if not an EVO.
    """
    cluster_id = neuron.get("cluster_id", "")
    if cluster_id != "Agents":
        return None

    activation = neuron.get("activation", 0.5)
    syn_out = neuron.get("synapse_out", 0) or 0

    return {
        "is_evo": True,
        "evo_energy": activation,           # activation = energy level
        "evo_catalytic_reach": syn_out,     # outbound synapses = catalytic reach
        "evo_stage": neuron.get("stage", "composting"),  # most agents are composting
        "evo_type": _classify_evo_type(neuron),
    }


def _classify_evo_type(neuron):
    """Classify EVO subtype from path structure."""
    path = neuron.get("path", "")
    if "implementation_plan" in path:
        return "planner"
    elif "walkthrough" in path:
        return "walker"
    elif "adversarial_review" in path:
        return "challenger"
    elif "task.md" in path:
        return "executor"
    else:
        return "generic"


# ═══════════════════════════════════════════════════════════════════════
# DATA LOADING FROM SURREALDB
# ═══════════════════════════════════════════════════════════════════════

def load_all_neurons():
    """Fetch all neurons from SurrealDB."""
    results = get_results(query(
        "SELECT * FROM neuron;"
    ))
    print(f"  Loaded {len(results)} neurons", file=sys.stderr)
    return results


def load_country_data():
    """Fetch Country health and neuron counts."""
    results = get_results(query(
        "SELECT name, health, neuron_count, avg_activation FROM country;"
    ))
    return {c["name"]: c for c in results}


def load_kinship_counts():
    """Count kinship bonds per neuron (both directions)."""
    # Fetch all kinship records and count locally (avoids SurrealDB GROUP BY edge cases)
    results = get_results(query("SELECT in, out FROM kinship;"))
    counts = {}
    for r in results:
        for field in ("in", "out"):
            nid = str(r.get(field, ""))
            if nid:
                counts[nid] = counts.get(nid, 0) + 1
    print(f"  Kinship bonds: {len(results)} across {len(counts)} neurons", file=sys.stderr)
    return counts


def load_songline_counts():
    """Count songline participations per neuron."""
    results = get_results(query(
        "SELECT waypoints FROM songline;"
    ))
    counts = {}
    for sl in results:
        for wp in (sl.get("waypoints") or []):
            nid = str(wp)
            counts[nid] = counts.get(nid, 0) + 1
    return counts


def load_hiho_scores():
    """Load most recent HIHO coherence score per Country."""
    # Use SELECT * to avoid SurrealDB 3.0 field-projection issues
    results = get_results(query("SELECT * FROM hiho_event;"))
    # Sort by date descending (client-side) and keep most recent per country
    results.sort(key=lambda r: r.get("date", ""), reverse=True)
    scores = {}
    for r in results:
        c = r.get("country", "")
        if c and c not in scores:
            scores[c] = r.get("coherence_score", 0.0)
    print(f"  HIHO scores: {len(scores)} countries from {len(results)} events", file=sys.stderr)
    return scores


def load_neuron_history():
    """Load neuron_history for trajectory extraction.

    Uses all event types (created, edited, fired, etc.) since they all
    represent neuron activations. Sorts client-side to avoid SurrealDB
    ORDER BY issues with large result sets.
    """
    results = get_results(query("SELECT * FROM neuron_history;"))
    results.sort(key=lambda r: r.get("timestamp", ""))
    print(f"  Loaded {len(results)} history events", file=sys.stderr)
    return results


# ═══════════════════════════════════════════════════════════════════════
# TRAJECTORY EXTRACTION
# ═══════════════════════════════════════════════════════════════════════

def extract_trajectories(history, neuron_vectors, window_minutes=30):
    """Extract session trajectories from neuron_history.

    Groups neuron firing events into sessions (events within `window_minutes`
    of each other). Each session becomes a trajectory: a sequence of 12D
    vectors representing the path through the compound learning space.

    Returns list of trajectories, each a dict with:
      - session_id: str
      - start_time: str (ISO)
      - end_time: str (ISO)
      - waypoints: list of 12D vectors
      - neuron_ids: list of neuron IDs in order
      - is_evo_trail: bool (whether an EVO fired during this session)
      - country_crossings: list of unique Countries traversed
    """
    if not history:
        return []

    # Parse timestamps and group into sessions
    sessions = []
    current_session = []
    last_ts = None

    for event in history:
        ts_str = event.get("timestamp", "")
        if not ts_str:
            continue
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue

        nid = str(event.get("neuron", ""))

        if last_ts and (ts - last_ts).total_seconds() > window_minutes * 60:
            if len(current_session) >= 2:
                sessions.append(current_session)
            current_session = []

        current_session.append({"ts": ts, "nid": nid, "event": event})
        last_ts = ts

    if len(current_session) >= 2:
        sessions.append(current_session)

    # Convert sessions to trajectories
    trajectories = []
    for i, session in enumerate(sessions):
        waypoints = []
        neuron_ids = []
        countries = set()
        has_evo = False

        for step in session:
            nid = step["nid"]
            vec = neuron_vectors.get(nid)
            if vec is None:
                continue
            waypoints.append(vec["vector"])
            neuron_ids.append(nid)
            countries.add(vec.get("cluster_id", "unknown"))
            if vec.get("is_evo", False):
                has_evo = True

        if len(waypoints) < 2:
            continue

        trajectories.append({
            "session_id": f"traj-{i:05d}",
            "start_time": session[0]["ts"].isoformat(),
            "end_time": session[-1]["ts"].isoformat(),
            "waypoints": waypoints,
            "neuron_ids": neuron_ids,
            "is_evo_trail": has_evo,
            "country_crossings": sorted(countries),
            "length": len(waypoints),
        })

    return trajectories


def extract_graph_walk_trajectories(neuron_vectors, n_walks=200, walk_length=8):
    """Generate synthetic trajectories via random walks through the synapse graph.

    Uses SurrealDB's graph traversal to walk the synapse network starting from
    high-activation neurons. Each walk produces a trajectory through the 12D space.
    These synthetic trajectories augment the sparse temporal history.

    This leverages SurrealDB's graph capabilities — the walk is done in SQL,
    not client-side, for efficiency.
    """
    # Get high-activation seed neurons across all aspects
    seeds = get_results(query(
        "SELECT id, cluster_id FROM neuron WHERE activation > 0.4 "
        "AND synapse_out > 2 ORDER BY RAND() LIMIT 200;"
    ))
    if not seeds:
        print("  No seed neurons found for graph walks", file=sys.stderr)
        return []

    trajectories = []
    for i, seed in enumerate(seeds[:n_walks]):
        seed_id = str(seed.get("id", ""))
        # Use SurrealDB graph traversal: walk outbound synapses
        # ->synapse-> follows the RELATION edge to connected neurons
        walk_results = get_results(query(
            f"SELECT id, ->synapse->neuron AS neighbors FROM {seed_id};"
        ))
        if not walk_results or not walk_results[0].get("neighbors"):
            continue

        # Build walk: start from seed, follow random neighbors
        path_ids = [seed_id]
        current = seed_id
        visited = {seed_id}

        for step in range(walk_length - 1):
            # Get neighbors of current node
            nbrs = get_results(query(
                f"SELECT ->synapse->neuron AS n FROM {current};"
            ))
            if not nbrs or not nbrs[0].get("n"):
                break
            neighbors = [str(n) for n in nbrs[0]["n"] if str(n) not in visited]
            if not neighbors:
                break
            # Pick first unvisited neighbor (deterministic for reproducibility)
            current = neighbors[0]
            visited.add(current)
            path_ids.append(current)

        if len(path_ids) < 3:
            continue

        # Convert to 12D vectors
        waypoints = []
        countries = set()
        has_evo = False
        for nid in path_ids:
            vec = neuron_vectors.get(nid)
            if not vec:
                continue
            waypoints.append(vec["vector"])
            countries.add(vec.get("cluster_id", "unknown"))
            if vec.get("is_evo", False):
                has_evo = True

        if len(waypoints) < 3:
            continue

        trajectories.append({
            "session_id": f"graphwalk-{i:04d}",
            "start_time": "",
            "end_time": "",
            "waypoints": waypoints,
            "neuron_ids": path_ids[:len(waypoints)],
            "is_evo_trail": has_evo,
            "is_graph_walk": True,
            "country_crossings": sorted(countries),
            "length": len(waypoints),
        })

    print(f"  Generated {len(trajectories)} graph-walk trajectories", file=sys.stderr)
    return trajectories


def extract_songline_trajectories(neuron_vectors):
    """Extract songlines as exemplar trajectories.

    Songlines are curated knowledge paths — they serve as positive examples
    for FLUME training, showing what coherent cross-domain traversal looks like.
    """
    songlines = get_results(query("SELECT * FROM songline;"))
    trajectories = []

    for sl in songlines:
        waypoints = []
        neuron_ids = []
        for wp in (sl.get("waypoints") or []):
            nid = str(wp)
            vec = neuron_vectors.get(nid)
            if vec:
                waypoints.append(vec["vector"])
                neuron_ids.append(nid)

        if len(waypoints) < 2:
            continue

        trajectories.append({
            "session_id": f"songline-{sl.get('name', 'unknown')[:40]}",
            "start_time": sl.get("created", ""),
            "end_time": sl.get("created", ""),
            "waypoints": waypoints,
            "neuron_ids": neuron_ids,
            "is_evo_trail": False,
            "is_songline": True,
            "country_crossings": sl.get("country_crossings", []),
            "walked_count": sl.get("walked_count", 0),
            "length": len(waypoints),
        })

    return trajectories


# ═══════════════════════════════════════════════════════════════════════
# OUTPUT WRITERS
# ═══════════════════════════════════════════════════════════════════════

def write_jsonl(path, records):
    """Write records as JSONL."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for rec in records:
            f.write(json.dumps(rec, default=str) + "\n")
    print(f"  Wrote {len(records)} records to {path}", file=sys.stderr)


def write_numpy(path, snapshot, trajectories):
    """Write snapshot and trajectories as .npz."""
    try:
        import numpy as np
    except ImportError:
        print("  WARNING: numpy not available, skipping .npz output", file=sys.stderr)
        return

    path.parent.mkdir(parents=True, exist_ok=True)

    # Snapshot: (N, 12) array of neuron vectors
    vectors = [rec["vector"] for rec in snapshot]
    vectors_arr = np.array(vectors, dtype=np.float32)

    # Forces: (N, 4) array
    forces = [
        [rec["forces"]["gravity"], rec["forces"]["electromagnetism"],
         rec["forces"]["strong_force"], rec["forces"]["weak_force"]]
        for rec in snapshot
    ]
    forces_arr = np.array(forces, dtype=np.float32)

    # EVO mask: (N,) boolean
    evo_mask = np.array([rec.get("is_evo", False) for rec in snapshot], dtype=bool)

    # Trajectories: variable-length, store as list of arrays
    traj_arrays = []
    traj_metadata = []
    for traj in trajectories:
        traj_arrays.append(np.array(traj["waypoints"], dtype=np.float32))
        traj_metadata.append({
            "session_id": traj["session_id"],
            "is_evo_trail": traj.get("is_evo_trail", False),
            "is_songline": traj.get("is_songline", False),
            "country_crossings": traj.get("country_crossings", []),
            "length": traj["length"],
        })

    # Save
    save_dict = {
        "vectors": vectors_arr,
        "forces": forces_arr,
        "evo_mask": evo_mask,
        "dimension_names": np.array([
            "connectivity", "conceptual_depth", "temporal_distribution",
            "cross_domain_presence", "completion_maturity", "recency",
            "semantic_similarity", "domain_clustering",
            "algorithm_complexity", "implementation_difficulty",
            "interdisciplinary_transfer", "impact_score",
        ]),
        "force_names": np.array([
            "gravity", "electromagnetism", "strong_force", "weak_force",
        ]),
        "neuron_ids": np.array([rec["id"] for rec in snapshot]),
        "neuron_paths": np.array([rec["path"] for rec in snapshot]),
        "traj_count": np.array(len(traj_arrays)),
    }

    # Store trajectories as numbered arrays
    for i, ta in enumerate(traj_arrays):
        save_dict[f"traj_{i:04d}"] = ta

    # Store trajectory metadata as JSON string array
    save_dict["traj_metadata"] = np.array(
        [json.dumps(m, default=str) for m in traj_metadata]
    )

    np.savez_compressed(path, **save_dict)
    print(
        f"  Wrote {vectors_arr.shape} vectors + {len(traj_arrays)} trajectories to {path}",
        file=sys.stderr,
    )


# ═══════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="12D Feature Vector Extraction Pipeline")
    parser.add_argument("--snapshot", action="store_true", help="Extract snapshot only (no trajectories)")
    parser.add_argument("--trajectories", action="store_true", help="Extract trajectories only (no snapshot)")
    parser.add_argument("--format", choices=["numpy", "jsonl", "both"], default="both",
                        help="Output format (default: both)")
    parser.add_argument("--output-dir", type=str, default=str(OUTPUT_DIR),
                        help=f"Output directory (default: {OUTPUT_DIR})")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    do_snapshot = not args.trajectories
    do_trajectories = not args.snapshot

    now = datetime.now(timezone.utc)
    datestamp = now.strftime("%Y-%m-%d")
    print(f"=== 12D Extraction Pipeline — {datestamp} ===", file=sys.stderr)

    # Check SurrealDB
    if not query("INFO FOR DB;"):
        print("ERROR: SurrealDB not reachable", file=sys.stderr)
        sys.exit(1)

    # Load supporting data
    print("Loading supporting data...", file=sys.stderr)
    country_data = load_country_data()
    kinship_counts = load_kinship_counts()
    songline_counts = load_songline_counts()
    hiho_scores = load_hiho_scores()
    neurons = load_all_neurons()

    # ─── Snapshot: 12D vectors for all neurons ───
    snapshot = []
    neuron_vectors = {}  # nid → {vector, cluster_id, is_evo, ...}

    if do_snapshot or do_trajectories:
        print("Computing 12D vectors...", file=sys.stderr)
        for n in neurons:
            nid = str(n.get("id", ""))
            vec = compute_12d_vector(n, country_data, kinship_counts, songline_counts, now)
            forces = compute_forces(n, kinship_counts, country_data, hiho_scores)
            evo = classify_evo(n)

            record = {
                "id": nid,
                "path": n.get("path", ""),
                "title": n.get("title", ""),
                "aspect": n.get("aspect", ""),
                "cluster_id": n.get("cluster_id", ""),
                "stage": n.get("stage", ""),
                "activation": n.get("activation", 0.5),
                "vector": vec,
                "forces": forces,
                "is_evo": evo is not None,
            }
            if evo:
                record["evo"] = evo

            snapshot.append(record)
            neuron_vectors[nid] = record

    # ─── Trajectories: session firing sequences ───
    trajectories = []
    if do_trajectories:
        print("Extracting trajectories...", file=sys.stderr)
        history = load_neuron_history()
        session_trajectories = extract_trajectories(history, neuron_vectors)
        graph_walk_trajectories = extract_graph_walk_trajectories(neuron_vectors)
        songline_trajectories = extract_songline_trajectories(neuron_vectors)
        trajectories = session_trajectories + graph_walk_trajectories + songline_trajectories
        print(
            f"  {len(session_trajectories)} session, "
            f"{len(graph_walk_trajectories)} graph-walk, "
            f"{len(songline_trajectories)} songline trajectories",
            file=sys.stderr,
        )

    # ─── Write outputs ───
    print("Writing outputs...", file=sys.stderr)

    if args.format in ("jsonl", "both"):
        if do_snapshot:
            write_jsonl(out_dir / f"snapshot-{datestamp}.jsonl", snapshot)
        if do_trajectories:
            write_jsonl(out_dir / f"trajectories-{datestamp}.jsonl", trajectories)

    if args.format in ("numpy", "both"):
        if do_snapshot or do_trajectories:
            write_numpy(
                out_dir / f"flume-training-{datestamp}.npz",
                snapshot if do_snapshot else [],
                trajectories if do_trajectories else [],
            )

    # ─── Summary statistics ───
    if do_snapshot:
        total = len(snapshot)
        evo_count = sum(1 for r in snapshot if r.get("is_evo"))
        aspects = {}
        for r in snapshot:
            a = r.get("aspect", "unknown")
            aspects[a] = aspects.get(a, 0) + 1

        # Compute mean vector
        mean_vec = [0.0] * 12
        for r in snapshot:
            for i, v in enumerate(r["vector"]):
                mean_vec[i] += v
        mean_vec = [v / total for v in mean_vec]

        dim_names = [
            "Connectivity", "Conceptual Depth", "Temporal Dist", "Cross-domain",
            "Completion", "Recency", "Semantic Sim", "Domain Cluster",
            "Complexity", "Difficulty", "Transfer", "Impact",
        ]

        print(f"\n=== Summary ===", file=sys.stderr)
        print(f"  Neurons: {total} ({evo_count} EVOs)", file=sys.stderr)
        print(f"  Aspects: {aspects}", file=sys.stderr)
        print(f"  Trajectories: {len(trajectories)}", file=sys.stderr)
        print(f"\n  Mean 12D vector:", file=sys.stderr)
        for name, val in zip(dim_names, mean_vec):
            bar = "#" * int(val * 30)
            print(f"    {name:>20}: {val:.3f} |{bar}", file=sys.stderr)

        # Force summary
        mean_forces = {"gravity": 0, "electromagnetism": 0, "strong_force": 0, "weak_force": 0}
        for r in snapshot:
            for k in mean_forces:
                mean_forces[k] += r["forces"][k]
        print(f"\n  Mean Unified Forces:", file=sys.stderr)
        for k, v in mean_forces.items():
            avg = v / total
            bar = "#" * int(avg * 30)
            print(f"    {k:>20}: {avg:.3f} |{bar}", file=sys.stderr)

        # HIHO coherence summary
        print(f"\n  HIHO Coherence (Strong Force by Country):", file=sys.stderr)
        for country, score in sorted(hiho_scores.items(), key=lambda x: -x[1])[:10]:
            bar = "#" * int(score * 30)
            print(f"    {country:>20}: {score:.3f} |{bar}", file=sys.stderr)

    print(f"\n=== Complete ===", file=sys.stderr)


if __name__ == "__main__":
    main()
