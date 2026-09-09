#!/usr/bin/env python3
"""Demonstration: Sheaf Cohomology Gluer & Kaggle Skills Integration via Local Models."""

import os
import time
from cohezion.competitions.arc.sheaf_cohomology_solver import check_sheaf_gluing_consistency

def main():
    print("\n" + "=" * 105)
    print("🌐 INTEGRATED SHEAF COHOMOLOGY GLUER & OFFICIAL KAGGLE SKILLS INTEGRATION")
    print("=" * 105)

    # 1. Sheaf Cohomology Consistency Test
    p1 = ((0, 2, 0, 2), [[1, 2], [3, 4]])
    p2 = ((1, 3, 1, 3), [[4, 5], [6, 7]])  # Intersects at (1, 1) -> both have 4
    p3_bad = ((1, 3, 1, 3), [[9, 5], [6, 7]]) # Intersects at (1, 1) -> mismatch (4 vs 9)

    t0 = time.perf_counter()
    valid_ok = check_sheaf_gluing_consistency([p1, p2])
    valid_bad = check_sheaf_gluing_consistency([p1, p3_bad])
    dt_us = (time.perf_counter() - t0) * 1_000_000.0

    print(f"• Sheaf Cohomology Obstruction Test (Executed in {dt_us:.2f} µs):")
    print(f"  ├─ Patch 1 + Patch 2 (Agrees on Intersection) : {'✅ CONSISTENT (Glued)' if valid_ok else '❌ CONFLICT'}")
    print(f"  └─ Patch 1 + Patch 3 (Mismatch at Intersection): {'✅ CONSISTENT' if valid_bad else '❌ OBSTRUCTION DETECTED (Pruned)'}")

    # 2. Kaggle Skills Repository Audit
    kaggle_skills_path = "src/cohezion/skills/kaggle/kaggle-skills-repo"
    subdirs = [d for d in os.listdir(kaggle_skills_path) if os.path.isdir(os.path.join(kaggle_skills_path, d)) and not d.startswith(".")]

    print(f"\n• Official Kaggle Skills Integrated ({len(subdirs)} packages discovered):")
    for s in subdirs:
        print(f"  ├─ 📦 `{s}`")

    print("\n" + "=" * 105)
    print("🎉 SHEAF COHOMOLOGY & KAGGLE SKILLS DEPLOYMENT COMPLETE!")
    print("=" * 105 + "\n")

if __name__ == "__main__":
    main()
