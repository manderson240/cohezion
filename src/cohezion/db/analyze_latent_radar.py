import json
import os
from pathlib import Path
from datetime import datetime
import numpy as np

def analyze_journeys():
    journey_dir = Path("src/cohezion/knowledge_graph/universe_nodes/journeys")
    files = list(journey_dir.glob("*.json"))

    stats = []

    for f in files:
        try:
            with open(f, 'r') as jf:
                data = json.load(jf)

            journey_id = data.get("journey_id")
            started_at = data.get("started_at")
            steps = data.get("steps", [])

            if not steps:
                continue

            # Extract physics states
            states = [s.get("physics_state", {}) for s in steps]

            # Aggregate metrics
            coherences = [s.get("coherence", 0.5) for s in states]
            masses = [s.get("mass", 0.0) for s in states]
            novelties = [s.get("novelty", 0.0) for s in states]

            # Spatial drift (Euclidean distance from start in X,Y,Z)
            start_xyz = np.array([states[0].get("x", 0), states[0].get("y", 0), states[0].get("z", 0)])
            end_xyz = np.array([states[-1].get("x", 0), states[-1].get("y", 0), states[-1].get("z", 0)])
            drift = np.linalg.norm(end_xyz - start_xyz)

            stats.append({
                "id": journey_id,
                "time": started_at,
                "avg_coherence": np.mean(coherences),
                "max_coherence": np.max(coherences),
                "min_coherence": np.min(coherences),
                "avg_mass": np.mean(masses),
                "avg_novelty": np.mean(novelties),
                "total_drift": drift,
                "step_count": len(steps)
            })
        except Exception as e:
            print(f"Error processing {f}: {e}")

    # Sort by timestamp
    stats.sort(key=lambda x: x["time"])

    # Calculate global trends
    avg_coherence = np.mean([s["avg_coherence"] for s in stats])
    avg_drift = np.mean([s["total_drift"] for s in stats])

    # Identify "Stability Wells" (High coherence, low drift)
    wells = [s for s in stats if s["avg_coherence"] > 0.8 and s["total_drift"] < 0.1]

    # Identify "Collapse Zones" (Low coherence, high drift)
    collapses = [s for s in stats if s["avg_coherence"] < 0.7 or s["total_drift"] > 1.0]

    report = {
        "global_avg_coherence": avg_coherence,
        "global_avg_drift": avg_drift,
        "stability_wells_count": len(wells),
        "collapse_zones_count": len(collapses),
        "top_wells": wells[:5],
        "top_collapses": collapses[:5],
        "total_journeys_analyzed": len(stats)
    }

    output_path = Path("src/cohezion/knowledge_graph/latent_radar_report.json")
    with open(output_path, 'w') as out:
        json.dump(report, out, indent=2)

    print(f"✅ Latent Radar Analysis complete. Report saved to {output_path}")

if __name__ == "__main__":
    analyze_journeys()
