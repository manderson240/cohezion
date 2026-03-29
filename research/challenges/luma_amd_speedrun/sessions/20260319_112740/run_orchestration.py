#!/usr/bin/env python3
"""
Orchestration Driver — Session 20260319

Coordinates the multi-agent kernel optimization campaign.
Manages:
- Variant generation (done externally)
- Submission to MI355X via popcorn-cli
- Result collection and world model updates
- V-score tracking and stagnation detection

Usage:
    python run_orchestration.py submit --kernel mla
    python run_orchestration.py results --kernel mla
    python run_orchestration.py update-world-model --kernel mla --result-file results.json
"""

import argparse
import json
from datetime import datetime
from pathlib import Path


SESSION_DIR = Path(__file__).parent
CHALLENGERS_DIR = SESSION_DIR / "challengers"
WORLD_MODEL_FILE = SESSION_DIR / "world-model" / "hypotheses.json"
VAULT_DIR = SESSION_DIR / "vault"

# Competition kernels
KERNELS = ["mla", "gemm", "moe"]


def load_world_model():
    """Load current world model state."""
    with open(WORLD_MODEL_FILE) as f:
        return json.load(f)


def save_world_model(model):
    """Save updated world model."""
    with open(WORLD_MODEL_FILE, "w") as f:
        json.dump(model, f, indent=2)


def get_variants(kernel: str):
    """Get list of available variants for a kernel."""
    variant_dir = CHALLENGERS_DIR / kernel
    if not variant_dir.exists():
        return []
    return list(variant_dir.glob("*.py"))


def submit_kernel(kernel: str, variant: str = None):
    """
    Submit challenger(s) to MI355X via popcorn-cli.

    Args:
        kernel: "mla", "gemm", or "moe"
        variant: Specific variant file (or None for all)
    """
    print(f"\n=== Submitting {kernel.upper()} variants ===")

    if variant:
        variants = [Path(variant)]
    else:
        variants = get_variants(kernel)

    if not variants:
        print(f"No variants found for {kernel}")
        return

    for v in variants:
        print(f"\nSubmitting: {v.name}")

        # Build popcorn command
        leaderboard_map = {
            "mla": "amd-mixed-mla",
            "gemm": "amd-mxfp4-mm",
            "moe": "amd-moe-mxfp4",
        }
        leaderboard = leaderboard_map[kernel]

        cmd = [
            "popcorn",
            "submit",
            "--mode",
            "test",
            "--gpu",
            "MI355X",
            "--leaderboard",
            leaderboard,
            str(v),
        ]

        print(f"Command: {' '.join(cmd)}")

        # For now, just print — actual submission requires popcorn-cli setup
        # result = subprocess.run(cmd, capture_output=True, text=True)
        # if result.returncode != 0:
        #     print(f"FAILED: {result.stderr}")
        # else:
        #     print(f"Submitted: {result.stdout}")

        print(f"[DRY RUN] Would submit: {v}")


def update_world_model(kernel: str, results_file: str):
    """
    Update world model V-scores based on benchmark results.

    Args:
        kernel: Kernel type
        results_file: JSON file with benchmark results
    """
    print(f"\n=== Updating world model for {kernel.upper()} ===")

    # Load results
    results_path = Path(results_file)
    if not results_path.exists():
        print(f"Results file not found: {results_file}")
        return

    with open(results_path) as f:
        results = json.load(f)

    # Load world model
    model = load_world_model()

    # Update V-scores based on results
    for result in results.get("variants", []):
        variant_name = result["name"]
        speedup = result.get("speedup_vs_baseline", 1.0)
        correct = result.get("correct", True)

        # Find matching hypothesis
        for hyp in model["hypotheses"]:
            if hyp["kernel_type"] == kernel and variant_name in hyp.get("code_reference", ""):
                if correct and speedup > 1.0:
                    # Improvement: increase V-score
                    hyp["v_score"] = min(1.0, hyp["v_score"] + 0.1)
                    hyp["attempts"] += 1
                elif correct:
                    # Correct but no improvement
                    hyp["attempts"] += 1
                else:
                    # Failure: decrease V-score
                    hyp["v_score"] = max(0.0, hyp["v_score"] - 0.05)
                    hyp["attempts"] += 1
                    hyp["failure_reason"] = result.get("error", "Unknown")

                hyp["last_updated"] = datetime.now().isoformat()
                print(f"  {variant_name}: V={hyp['v_score']:.2f}, attempts={hyp['attempts']}")

    # Check stagnation
    for hyp in model["hypotheses"]:
        if hyp["kernel_type"] == kernel:
            stagnation_key = f"{kernel}_{hyp['id']}"
            if hyp["attempts"] >= model["world_model_state"]["stagnation_threshold"]:
                if hyp["v_score"] < 0.3:
                    print(f"  STAGNANT: {hyp['id']} (V={hyp['v_score']:.2f})")
                    hyp["status"] = "stale"

    save_world_model(model)
    print("\nWorld model updated.")


def generate_report():
    """Generate session report."""
    model = load_world_model()

    print("\n" + "=" * 60)
    print("ORCHESTRATION REPORT — Session 20260319")
    print("=" * 60)

    print(f"\nTotal hypotheses: {len(model['hypotheses'])}")
    print(f"Total iterations: {model['world_model_state']['total_iterations']}")

    for kernel in KERNELS:
        hyps = [h for h in model["hypotheses"] if h["kernel_type"] == kernel]
        if hyps:
            print(f"\n{kernel.upper()} Hypotheses ({len(hyps)}):")
            for h in hyps:
                status = h.get("status", "active")
                print(f"  [{status}] {h['id']}: V={h['v_score']:.2f}, attempts={h['attempts']}")
                print(f"           {h['description'][:60]}...")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Orchestration driver")
    subparsers = parser.add_subparsers(dest="command")

    # Submit command
    submit_parser = subparsers.add_parser("submit", help="Submit variants")
    submit_parser.add_argument("--kernel", required=True, choices=KERNELS)
    submit_parser.add_argument("--variant", help="Specific variant file")

    # Results command
    results_parser = subparsers.add_parser("results", help="Collect results")
    results_parser.add_argument("--kernel", required=True, choices=KERNELS)

    # Update world model command
    update_parser = subparsers.add_parser("update-world-model", help="Update V-scores")
    update_parser.add_argument("--kernel", required=True, choices=KERNELS)
    update_parser.add_argument("--result-file", required=True)

    # Report command
    subparsers.add_parser("report", help="Generate report")

    args = parser.parse_args()

    if args.command == "submit":
        submit_kernel(args.kernel, args.variant)
    elif args.command == "results":
        results_file = CHALLENGERS_DIR / args.kernel / "results.json"
        if results_file.exists():
            with open(results_file) as f:
                print(f.read())
        else:
            print(f"No results yet for {args.kernel}")
    elif args.command == "update-world-model":
        update_world_model(args.kernel, args.result_file)
    elif args.command == "report":
        generate_report()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
