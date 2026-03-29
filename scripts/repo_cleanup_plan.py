"""Repository cleanup and improvement plan using compound pipeline.

Identifies and categorizes cleanup opportunities for targeted refinement.
"""

import json
import subprocess
from pathlib import Path


def get_untracked_files():
    """Get list of untracked files."""
    result = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd="/home/mike-anderson/dev/cohezion",
        capture_output=True,
        text=True,
    )
    files = result.stdout.strip().split("\n") if result.stdout.strip() else []
    return [f for f in files if f]


def categorize_files(files):
    """Categorize untracked files."""
    categories = {
        "build_artifacts": [],
        "cache_files": [],
        "generated_output": [],
        "data_files": [],
        "config_samples": [],
        "documentation": [],
        "other": [],
    }

    for f in files:
        f_lower = f.lower()

        if any(pattern in f_lower for pattern in ["__pycache__", ".egg", "build/", "dist/", ".so"]):
            categories["build_artifacts"].append(f)
        elif any(pattern in f_lower for pattern in [".cache", ".pyc", ".pyo", ".pyd"]):
            categories["cache_files"].append(f)
        elif any(pattern in f_lower for pattern in ["output", "result", "export", "render"]):
            categories["generated_output"].append(f)
        elif any(pattern in f_lower for pattern in [".csv", ".json", ".npy", ".db"]):
            categories["data_files"].append(f)
        elif any(pattern in f_lower for pattern in ["example", "sample", ".template"]):
            categories["config_samples"].append(f)
        elif f.endswith(".md") or f.endswith(".rst") or f.endswith(".txt"):
            categories["documentation"].append(f)
        else:
            categories["other"].append(f)

    return {k: v for k, v in categories.items() if v}


def main():
    """Generate cleanup plan."""
    print("\n" + "=" * 70)
    print("REPOSITORY CLEANUP PLAN")
    print("=" * 70)

    files = get_untracked_files()
    categorized = categorize_files(files)

    print(f"\nTotal untracked files: {len(files)}")
    print("\nBreakdown by category:")
    for category, items in categorized.items():
        print(f"  {category}: {len(items)} files")

    # Generate cleanup tasks
    plan = {
        "immediate_cleanup": [],
        "review_and_decide": [],
        "documentation_additions": [],
    }

    # 1. Safe cleanup (artifacts, cache)
    if "build_artifacts" in categorized:
        plan["immediate_cleanup"].append(
            {
                "category": "build_artifacts",
                "count": len(categorized["build_artifacts"]),
                "action": "Remove build artifacts and compiled files",
                "command": "# Add to .gitignore: __pycache__/, *.egg-info/, dist/, build/",
            }
        )

    if "cache_files" in categorized:
        plan["immediate_cleanup"].append(
            {
                "category": "cache_files",
                "count": len(categorized["cache_files"]),
                "action": "Remove Python cache files",
                "command": "find . -type d -name __pycache__ -exec rm -rf {} +",
            }
        )

    # 2. Review (generated output, data)
    if "generated_output" in categorized:
        plan["review_and_decide"].append(
            {
                "category": "generated_output",
                "count": len(categorized["generated_output"]),
                "files_sample": categorized["generated_output"][:3],
                "action": "Review and either add to .gitignore or commit if needed",
            }
        )

    if "data_files" in categorized:
        plan["review_and_decide"].append(
            {
                "category": "data_files",
                "count": len(categorized["data_files"]),
                "files_sample": categorized["data_files"][:3],
                "action": "Ensure data files are in .gitignore or committed intentionally",
            }
        )

    # 3. Documentation
    if "documentation" in categorized:
        plan["documentation_additions"].append(
            {
                "action": "Add new documentation files",
                "files": categorized["documentation"][:5],
            }
        )

    # 4. Missing files
    repo = Path("/home/mike-anderson/dev/cohezion")
    missing = []
    if not (repo / "README.md").exists():
        missing.append(
            {
                "file": "README.md",
                "priority": "HIGH",
                "content": "Project overview, setup, usage instructions",
            }
        )

    if missing:
        plan["documentation_additions"].append(
            {
                "create": missing,
            }
        )

    # Print plan
    print("\n" + "=" * 70)
    print("CLEANUP PLAN")
    print("=" * 70)

    print("\n1️⃣  IMMEDIATE CLEANUP (Safe to remove):")
    if plan["immediate_cleanup"]:
        for item in plan["immediate_cleanup"]:
            print(f"\n  • {item['action']}")
            print(f"    Count: {item['count']} files")
            if "command" in item:
                print(f"    Command: {item['command']}")
    else:
        print("  ✅ No immediate cleanup needed")

    print("\n2️⃣  REVIEW AND DECIDE (May need to keep):")
    if plan["review_and_decide"]:
        for item in plan["review_and_decide"]:
            print(f"\n  • {item['action']}")
            print(f"    Category: {item['category']}")
            print(f"    Count: {item['count']} files")
            if "files_sample" in item:
                print(f"    Sample: {', '.join(item['files_sample'][:2])}")
    else:
        print("  ✅ No files to review")

    print("\n3️⃣  DOCUMENTATION ADDITIONS:")
    if plan["documentation_additions"]:
        for item in plan["documentation_additions"]:
            if "create" in item:
                print("\n  • Create missing files:")
                for f in item["create"]:
                    print(f"    - {f['file']} ({f['priority']}): {f['content']}")
            elif "action" in item:
                print(f"\n  • {item['action']}")
                if "files" in item:
                    print(f"    Files: {', '.join(item['files'][:3])}")
    else:
        print("  ✅ No documentation additions needed")

    # Summary and next steps
    print("\n" + "=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print("""
1. Review build_artifacts and cache files - safe to remove
2. Decide on generated_output and data_files - keep or ignore?
3. Create README.md with project overview
4. Update .gitignore with appropriate patterns
5. Commit changes with clear messages
6. Run full test suite to verify
7. Update documentation with latest changes
    """)

    # Save plan to JSON
    plan_file = Path("/home/mike-anderson/dev/cohezion/cleanup_plan.json")
    with open(plan_file, "w") as f:
        json.dump(
            {
                "total_untracked": len(files),
                "categorization": {k: len(v) for k, v in categorized.items()},
                "plan": plan,
            },
            f,
            indent=2,
        )

    print(f"\nPlan saved to: {plan_file}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
