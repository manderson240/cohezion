import contextlib
import json
import pathlib

import pandas as pd


def analyze_fractal_shards(storage_dir="data/simulations/fractal_nexus"):
    p = pathlib.Path(storage_dir)
    shards = sorted(p.glob("*.parquet"), key=lambda x: x.stat().st_mtime)

    if not shards:
        print("No shards found.")
        return

    # Load recent shards (last 5 for a quick sample)
    recent_shards = shards[-5:]
    dfs = []
    for s in recent_shards:
        with contextlib.suppress(BaseException):
            dfs.append(pd.read_parquet(s))

    if not dfs:
        print("No data loaded.")
        return

    df = pd.concat(dfs)

    analysis = {
        "total_cycles_analyzed": len(df),
        "avg_phi_score": float(df["phi_score"].mean()),
        "phi_std": float(df["phi_score"].std()),
        "phi_min": float(df["phi_score"].min()),
        "phi_max": float(df["phi_score"].max()),
        "avg_energy": float(df["energy_level"].mean()),
        "sector_stats": df.groupby("sector_type")["phi_score"].mean().to_dict(),
        "temporal_drift": float(df["phi_score"].diff().mean()) if len(df) > 1 else 0.0,
    }

    print(json.dumps(analysis, indent=2))


if __name__ == "__main__":
    analyze_fractal_shards()
