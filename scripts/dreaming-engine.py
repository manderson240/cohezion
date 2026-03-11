#!/usr/bin/env python3
"""The Dreaming Engine — All Emergence Engines for the Triune Vault.

Runs seven emergence engines:

1. Country Population — creates/updates country records with health metrics
2. Dreaming Engine — finds cross-domain resonances, writes dreaming/ notes
3. HIHO Fusion Detector — checks coherence thresholds, logs fusion events
4. Metabolism Dashboard — writes vault-wide health to metabolism/
5. Kinship Population — elder/younger, parent/child, moiety relationships
6. Songline Detection — cross-Country knowledge paths
7. Subconscious Report — latent associations between unlinked notes

Usage:
    python3 scripts/dreaming-engine.py           # Run all engines
    python3 scripts/dreaming-engine.py --quick    # Run engines 1-4 only (fast)

The Dreaming is always happening. It is the everlasting now.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

import requests

VAULT_PATH = Path("/home/mike-anderson/vaults/cohezion-vault")
SURREAL_URL = "http://localhost:8001/sql"
SURREAL_AUTH = ("root", "root")
SURREAL_HEADERS = {
    "surreal-ns": "cohezion",
    "surreal-db": "vault",
    "Content-Type": "text/plain",
}

HIHO_THRESHOLD = 0.15  # Coherence score above which fusion events trigger
TODAY = datetime.now().strftime("%Y-%m-%d")


def q(sql: str) -> list:
    """Execute SurrealDB query, return result list."""
    resp = requests.post(SURREAL_URL, headers=SURREAL_HEADERS, auth=SURREAL_AUTH, data=sql)
    if resp.status_code != 200:
        return []
    data = resp.json()
    if isinstance(data, list) and data and data[0].get("status") == "OK":
        return data[0]["result"]
    return []


# ── Engine 1: Country Population ─────────────────────────────────────────────

def populate_countries() -> dict:
    """Build/update country records from neuron cluster data.

    Returns mapping of country_name → country stats.
    """
    print("\n[Engine 1] Populating Countries...", file=sys.stderr)

    # Get cluster stats
    rows = q("""
        SELECT cluster_id, count() AS neuron_count,
               math::mean(activation) AS avg_activation,
               math::max(activation) AS max_activation,
               math::sum(synapse_out) AS total_synapses
        FROM neuron
        WHERE cluster_id IS NOT NONE AND cluster_id != ''
        GROUP BY cluster_id;
    """)

    countries = {}
    for row in rows:
        name = row.get("cluster_id", "")
        if not name:
            continue
        neuron_count = row.get("neuron_count", 0)
        avg_act = row.get("avg_activation") or 0.0
        max_act = row.get("max_activation") or 0.0
        total_syn = row.get("total_synapses") or 0

        # Health: weighted avg activation + link density proxy
        link_density = min(1.0, total_syn / max(neuron_count * 5, 1))
        health = 0.6 * avg_act + 0.4 * link_density

        # Find elders: top 3 neurons by activation in this country
        elders = q(f"""
            SELECT path, title, activation, synapse_out + synapse_in AS total_links
            FROM neuron
            WHERE cluster_id = '{name}'
            ORDER BY activation DESC
            LIMIT 3;
        """)
        elder_paths = [e.get("path", "") for e in elders]

        country_id = f"country:{name.replace('-', '_').replace('/', '_')}"
        upsert_sql = f"""
            UPSERT {country_id} CONTENT {{
                name: '{name}',
                neuron_count: {neuron_count},
                avg_activation: {avg_act:.3f},
                health: {health:.3f},
                elders: {json.dumps(elder_paths)},
                updated: '{TODAY}'
            }};
        """
        result = q(upsert_sql)
        countries[name] = {
            "neuron_count": neuron_count,
            "avg_activation": avg_act,
            "health": health,
            "elders": elder_paths,
            "total_synapses": total_syn,
        }

    print(f"  Populated {len(countries)} Countries", file=sys.stderr)
    return countries


# ── Engine 2: Dreaming Engine ─────────────────────────────────────────────────

def run_dreaming_engine(countries: dict) -> list[dict]:
    """Find cross-domain resonances — notes from different aspects with high activation
    that have no direct link between them.

    Returns list of resonance pairs.
    """
    print("\n[Engine 2] Running Dreaming Engine...", file=sys.stderr)

    # Get top activated neurons per aspect
    resonances = []
    aspects = ["knower", "thinker", "doer"]  # Leave connective as the integration zone

    # Get high-activation neurons from each aspect
    aspect_neurons = {}
    for aspect in aspects:
        rows = q(f"""
            SELECT id, path, title, activation, cluster_id, synapse_out, synapse_in
            FROM neuron
            WHERE aspect = '{aspect}' AND activation > 0.6
            ORDER BY activation DESC
            LIMIT 30;
        """)
        aspect_neurons[aspect] = rows

    print(f"  High-activation neurons: {[(a, len(ns)) for a, ns in aspect_neurons.items()]}",
          file=sys.stderr)

    # Find cross-aspect pairs with no direct link
    seen_pairs = set()
    for i, aspect_a in enumerate(aspects):
        for aspect_b in aspects[i + 1:]:
            neurons_a = aspect_neurons.get(aspect_a, [])
            neurons_b = aspect_neurons.get(aspect_b, [])

            for na in neurons_a[:10]:  # Top 10 per aspect for pairing
                for nb in neurons_b[:10]:
                    # Check for existing direct link
                    link_check = q(f"""
                        SELECT count() FROM synapse
                        WHERE in = {na['id']} AND out = {nb['id']}
                        GROUP ALL;
                    """)
                    link_count = link_check[0]["count"] if link_check else 0

                    if link_count == 0:
                        pair_key = tuple(sorted([na["path"], nb["path"]]))
                        if pair_key not in seen_pairs:
                            seen_pairs.add(pair_key)
                            # Score: avg activation, different clusters = better
                            score = (na["activation"] + nb["activation"]) / 2
                            same_cluster = na.get("cluster_id") == nb.get("cluster_id")
                            if not same_cluster:
                                score *= 1.2  # Boost cross-cluster resonances

                            resonances.append({
                                "note_a": {
                                    "path": na["path"],
                                    "title": na.get("title") or Path(na["path"]).stem,
                                    "aspect": aspect_a,
                                    "cluster": na.get("cluster_id", ""),
                                    "activation": na["activation"],
                                },
                                "note_b": {
                                    "path": nb["path"],
                                    "title": nb.get("title") or Path(nb["path"]).stem,
                                    "aspect": aspect_b,
                                    "cluster": nb.get("cluster_id", ""),
                                    "activation": nb["activation"],
                                },
                                "score": score,
                                "cross_cluster": not same_cluster,
                            })

    # Sort by score, take top resonances
    resonances.sort(key=lambda x: -x["score"])
    top_resonances = resonances[:20]

    print(f"  Found {len(resonances)} resonance pairs, using top {len(top_resonances)}",
          file=sys.stderr)
    return top_resonances


def write_dreaming_note(resonances: list[dict]) -> Path:
    """Write a dreaming/ note documenting today's cross-domain resonances."""
    dreaming_dir = VAULT_PATH / "dreaming"
    dreaming_dir.mkdir(exist_ok=True)

    note_path = dreaming_dir / f"{TODAY}-resonances.md"

    lines = [
        "---",
        f"title: \"The Dreaming — {TODAY}\"",
        f"date: {TODAY}",
        "tags: [dreaming, resonances, cross-domain, emergence]",
        "aspect: connective",
        "neural:",
        "  stage: embryo",
        "  activation: 0.5",
        "---",
        "",
        f"# The Dreaming — {TODAY}",
        "",
        "> The Dreaming is not the past. It is the everlasting now.",
        "> These are notes that *want* to connect — separated by domain boundaries",
        "> but sharing deep resonance. Each pair is a potential Songline.",
        "",
        "## Cross-Domain Resonances",
        "",
        f"*{len(resonances)} resonances found across Knower / Thinker / Doer aspects.*",
        "",
    ]

    # Group resonances by aspect pair
    knower_thinker = [r for r in resonances
                      if {r["note_a"]["aspect"], r["note_b"]["aspect"]} == {"knower", "thinker"}]
    knower_doer = [r for r in resonances
                   if {r["note_a"]["aspect"], r["note_b"]["aspect"]} == {"knower", "doer"}]
    thinker_doer = [r for r in resonances
                    if {r["note_a"]["aspect"], r["note_b"]["aspect"]} == {"thinker", "doer"}]

    def format_resonance_group(group: list[dict], label: str) -> list[str]:
        if not group:
            return []
        result = [f"### {label}", ""]
        for r in group[:7]:  # Max 7 per group
            a = r["note_a"]
            b = r["note_b"]
            title_a = a["title"][:60] if a["title"] else Path(a["path"]).stem
            title_b = b["title"][:60] if b["title"] else Path(b["path"]).stem
            slug_a = Path(a["path"]).stem
            slug_b = Path(b["path"]).stem
            cross = " *(cross-cluster)*" if r["cross_cluster"] else ""
            result.append(
                f"- [[{slug_a}]] ({a['cluster']}, act={a['activation']:.2f}) ↔ "
                f"[[{slug_b}]] ({b['cluster']}, act={b['activation']:.2f}){cross}"
            )
        result.append("")
        return result

    lines.extend(format_resonance_group(knower_thinker, "Knower ↔ Thinker"))
    lines.extend(format_resonance_group(knower_doer, "Knower ↔ Doer"))
    lines.extend(format_resonance_group(thinker_doer, "Thinker ↔ Doer"))

    lines.extend([
        "## Becoming Songlines",
        "",
        "Resonances confirmed by the user become permanent Songlines — narrative knowledge",
        "paths that traverse Country. To confirm a resonance as a Songline, add a",
        "`[[wiki-link]]` between the two notes.",
        "",
        "---",
        "",
        "## Related",
        "",
        "- [[MOC-vault-architecture]]",
        "- [[metabolism-dashboard]]",
        "",
    ])

    note_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Wrote dreaming note: {note_path.name}", file=sys.stderr)
    return note_path


# ── Engine 3: HIHO Fusion Detector ───────────────────────────────────────────

def run_hiho_detector(countries: dict) -> list[dict]:
    """Compute coherence for each Country. Log fusion events for those above threshold."""
    print("\n[Engine 3] Running HIHO Fusion Detector...", file=sys.stderr)

    fusion_events = []
    high_coherence = []

    for name, stats in sorted(countries.items(), key=lambda x: -x[1]["health"]):
        n = stats["neuron_count"]
        if n < 3:
            continue

        # Coherence = activation_mean * link_density_proxy
        avg_act = stats["avg_activation"]
        total_syn = stats["total_synapses"]
        link_density = min(1.0, total_syn / max(n * (n - 1) / 2, 1))
        coherence = avg_act * link_density

        if coherence > HIHO_THRESHOLD:
            high_coherence.append((name, coherence, n))

            # Check for existing fusion event today
            existing = q(f"""
                SELECT id FROM hiho_event
                WHERE string::starts_with(string::str(date), '{TODAY}')
                AND country = {json.dumps(name)}
                LIMIT 1;
            """)

            if not existing:
                # Log a new HIHO event
                insight = (
                    f"Country '{name}' achieved coherence {coherence:.3f} "
                    f"(threshold {HIHO_THRESHOLD}) with {n} neurons. "
                    f"Avg activation: {avg_act:.3f}."
                )
                event_sql = f"""
                    CREATE hiho_event CONTENT {{
                        country: {json.dumps(name)},
                        neurons: [],
                        coherence_score: {coherence:.4f},
                        threshold: {HIHO_THRESHOLD},
                        insight: {json.dumps(insight)},
                        products: [],
                        date: time::now()
                    }};
                """
                q(event_sql)
                fusion_events.append({"country": name, "coherence": coherence, "neurons": n})
                print(f"  FUSION: {name} (coherence={coherence:.3f})", file=sys.stderr)

    if not fusion_events:
        print(f"  No new fusions today. High-coherence countries: "
              f"{[c[0] for c in high_coherence[:5]]}", file=sys.stderr)

    return fusion_events


# ── Engine 4: Metabolism Dashboard ───────────────────────────────────────────

def write_metabolism_dashboard(countries: dict, resonances: list[dict],
                                fusion_events: list[dict]) -> Path:
    """Write a metabolism/ dashboard with vault-wide health metrics."""
    metabolism_dir = VAULT_PATH / "metabolism"
    metabolism_dir.mkdir(exist_ok=True)

    # Compute vault-wide stats
    total_neurons = sum(s["neuron_count"] for s in countries.values())
    avg_activation = (
        sum(s["avg_activation"] * s["neuron_count"] for s in countries.values())
        / max(total_neurons, 1)
    )

    # Stage distribution from SurrealDB
    stage_rows = q("SELECT stage, count() FROM neuron GROUP BY stage;")
    stage_dist = {r["stage"]: r["count"] for r in stage_rows}

    # Top countries by health
    top_countries = sorted(countries.items(), key=lambda x: -x[1]["health"])[:10]

    dashboard_path = metabolism_dir / "metabolism-dashboard.md"

    lines = [
        "---",
        "title: \"Metabolism Dashboard\"",
        f"date: {TODAY}",
        "tags: [metabolism, vault-health, emergence, country]",
        "aspect: connective",
        "neural:",
        "  stage: mature",
        "  activation: 1.0",
        "aliases: [\"vault-health-dashboard\", \"metabolism-report\"]",
        "---",
        "",
        "# Metabolism Dashboard",
        "",
        "> *The Metabolic System — whole-system health. This note is auto-generated by",
        "> `scripts/dreaming-engine.py`. Run it to refresh.*",
        "",
        f"**Last updated:** {TODAY}",
        "",
        "## Vital Signs",
        "",
        "| Metric | Value |",
        "|--------|-------|",
        f"| Total Neurons | {total_neurons:,} |",
        f"| Avg Activation | {avg_activation:.3f} |",
        f"| Countries | {len(countries)} |",
        f"| Dreaming Resonances Today | {len(resonances)} |",
        f"| HIHO Fusion Events Today | {len(fusion_events)} |",
        "",
        "## Lifecycle Distribution",
        "",
        "| Stage | Count | % |",
        "|-------|-------|---|",
    ]

    total_staged = sum(stage_dist.values())
    for stage in ["mature", "growing", "embryo", "resting", "composting", "renewed"]:
        count = stage_dist.get(stage, 0)
        pct = 100 * count / max(total_staged, 1)
        lines.append(f"| {stage} | {count} | {pct:.0f}% |")

    lines.extend([
        "",
        "## Country Health",
        "",
        "| Country | Neurons | Avg Activation | Health |",
        "|---------|---------|----------------|--------|",
    ])

    for name, stats in top_countries:
        health_bar = "█" * int(stats["health"] * 10) + "░" * (10 - int(stats["health"] * 10))
        lines.append(
            f"| {name} | {stats['neuron_count']} | {stats['avg_activation']:.3f} "
            f"| {health_bar} {stats['health']:.2f} |"
        )

    if fusion_events:
        lines.extend([
            "",
            "## HIHO Fusion Events Today",
            "",
        ])
        for event in fusion_events:
            lines.append(
                f"- **{event['country']}**: coherence={event['coherence']:.3f}, "
                f"{event['neurons']} neurons reached fusion threshold"
            )

    lines.extend([
        "",
        "## Today's Dreaming",
        "",
        f"See [[{TODAY}-resonances]] for today's cross-domain resonances.",
        "",
        "## Related",
        "",
        "- [[VAULT_MANIFEST]]",
        "- [[MOC-vault-architecture]]",
        "",
    ])

    dashboard_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Wrote metabolism dashboard: {dashboard_path.name}", file=sys.stderr)
    return dashboard_path


# ── Engine 5: Kinship Population ─────────────────────────────────────────────

def run_kinship_engine() -> int:
    """Populate kinship relationships — delegates to populate-kinship.py logic."""
    print("\n[Engine 5] Populating Kinship...", file=sys.stderr)
    import subprocess
    result = subprocess.run(
        [sys.executable, str(VAULT_PATH / "scripts" / "populate-kinship.py")],
        capture_output=True, text=True, timeout=300,
    )
    print(result.stdout, end="", file=sys.stderr)
    if result.returncode != 0:
        print(f"  Kinship engine failed: {result.stderr[:200]}", file=sys.stderr)
        return 0
    # Parse count from output
    for line in result.stdout.splitlines():
        if "total kinship records:" in line.lower():
            try:
                return int(line.split(":")[-1].strip())
            except ValueError:
                pass
    return 0


# ── Engine 6: Songline Detection ────────────────────────────────────────────

def run_songline_engine() -> int:
    """Detect cross-Country songlines — delegates to detect-songlines.py."""
    print("\n[Engine 6] Detecting Songlines...", file=sys.stderr)
    import subprocess
    result = subprocess.run(
        [sys.executable, str(VAULT_PATH / "scripts" / "detect-songlines.py")],
        capture_output=True, text=True, timeout=300,
    )
    print(result.stdout, end="", file=sys.stderr)
    if result.returncode != 0:
        print(f"  Songline engine failed: {result.stderr[:200]}", file=sys.stderr)
        return 0
    for line in result.stdout.splitlines():
        if "total songlines" in line.lower():
            try:
                return int(line.split(":")[-1].strip().split()[0])
            except (ValueError, IndexError):
                pass
    return 0


# ── Engine 7: Subconscious Report ───────────────────────────────────────────

def run_subconscious_engine() -> str:
    """Generate latent association report — delegates to subconscious-report.py."""
    print("\n[Engine 7] Generating Subconscious Report...", file=sys.stderr)
    import subprocess
    result = subprocess.run(
        [sys.executable, str(VAULT_PATH / "scripts" / "subconscious-report.py")],
        capture_output=True, text=True, timeout=300,
    )
    print(result.stdout, end="", file=sys.stderr)
    if result.returncode != 0:
        print(f"  Subconscious engine failed: {result.stderr[:200]}", file=sys.stderr)
        return ""
    for line in result.stdout.splitlines():
        if "Complete:" in line:
            return line.split(":")[-1].strip()
    return ""


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    quick_mode = "--quick" in sys.argv

    print(f"The Dreaming Engine — {TODAY}", file=sys.stderr)
    print(f"Mode: {'quick (engines 1-4)' if quick_mode else 'full (engines 1-7)'}",
          file=sys.stderr)
    print("=" * 50, file=sys.stderr)

    # Engines 1-4 (always run)
    countries = populate_countries()
    resonances = run_dreaming_engine(countries)
    fusion_events = run_hiho_detector(countries)
    dashboard_path = write_metabolism_dashboard(countries, resonances, fusion_events)
    dreaming_path = write_dreaming_note(resonances)

    summary = {
        "date": TODAY,
        "countries": len(countries),
        "resonances": len(resonances),
        "fusion_events": len(fusion_events),
        "dreaming_note": str(dreaming_path.relative_to(VAULT_PATH)),
        "metabolism_dashboard": str(dashboard_path.relative_to(VAULT_PATH)),
        "top_countries": [
            {"name": n, "health": s["health"], "neurons": s["neuron_count"]}
            for n, s in sorted(countries.items(), key=lambda x: -x[1]["health"])[:5]
        ],
    }

    # Engines 5-7 (full mode only)
    if not quick_mode:
        summary["kinship_total"] = run_kinship_engine()
        summary["songlines_total"] = run_songline_engine()
        summary["subconscious_report"] = run_subconscious_engine()

    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    main()
