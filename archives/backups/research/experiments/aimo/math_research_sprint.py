import argparse
import json
import time
from datetime import datetime, timedelta

from math_research_harness import MathResearchHarness


def log_sprint(msg):
    timestamp = datetime.now().isoformat()
    print(f"[{timestamp}] {msg}")
    with open("sprint_monitor.log", "a") as f:
        f.write(f"[{timestamp}] {msg}\n")


def get_seconds_until(target_time_str):
    now = datetime.now()
    try:
        target_h, target_m = map(int, target_time_str.split(":"))
        target_time = now.replace(hour=target_h, minute=target_m, second=0, microsecond=0)
        if target_time < now:
            target_time += timedelta(days=1)
        return (target_time - now).total_seconds()
    except ValueError:
        log_sprint(f"Invalid time format: {target_time_str}. Defaulting to 1 hour.")
        return 3600


class AdaptiveResearchSprint:
    def __init__(self, target_seconds):
        self.harness = MathResearchHarness()
        self.end_time = time.time() + target_seconds
        self.iteration = 1
        self.best_acc = 0.0
        self.stagnation_count = 0
        self.current_focus = "Edge Case Verification"

        self.focus_areas = [
            "Edge Case Verification",
            "SymPy Symbolic Extraction",
            "Multi-Agent Cross-Review",
            "Prompt Simplification",
            "Monte Carlo Sense-Checking",
        ]

    def pivot_strategy(self):
        try:
            focus_idx = (self.focus_areas.index(self.current_focus) + 1) % len(self.focus_areas)
        except ValueError:
            focus_idx = 0
        self.current_focus = self.focus_areas[focus_idx]
        log_sprint(f"!!! STAGNATION DETECTED. Pivoting focus to: {self.current_focus} !!!")
        self.stagnation_count = 0

    def run(self):
        log_sprint(
            f"Starting Adaptive Research Sprint until {datetime.fromtimestamp(self.end_time).strftime('%H:%M:%S')}"
        )

        # Initial Baseline
        acc, stab = self.harness.run_experiment("Adaptive Baseline")
        self.best_acc = acc
        self.harness.log_result("Adaptive Baseline", acc, stab, True)
        self.harness.backup_config("sprint_best")

        while time.time() < self.end_time:
            try:
                log_sprint(
                    f"--- Sprint Iteration {self.iteration} (Focus: {self.current_focus}) ---"
                )

                with open("specialist_prompts.json") as f:
                    current_prompts = json.load(f)

                # Use the new LLM-driven proposal logic from the harness
                mutated_prompts, mutation_desc = self.harness.propose_mutation(current_prompts)
                log_sprint(f"Lead Agent Proposed: {mutation_desc}")

                with open("specialist_prompts.json", "w") as f:
                    json.dump(mutated_prompts, f, indent=2)

                # Run Experiment
                new_acc, new_stab = self.harness.run_experiment(mutation_desc)
                is_best = new_acc > self.best_acc
                self.harness.log_result(mutation_desc, new_acc, new_stab, is_best)

                if is_best:
                    log_sprint(f"SUCCESS: New Best found ({new_acc * 100:.2f}%)")
                    self.best_acc = new_acc
                    self.harness.backup_config("sprint_best")
                    self.stagnation_count = 0
                else:
                    log_sprint("FAILURE: No improvement.")
                    self.harness.restore_config("sprint_best")
                    self.stagnation_count += 1

                if self.stagnation_count >= 3:
                    self.pivot_strategy()

            except Exception as e:
                log_sprint(f"ERROR in Sprint Iteration {self.iteration}: {e!s}")
                log_sprint("Attempting to recover by reverting to sprint_best...")
                try:
                    self.harness.restore_config("sprint_best")
                except Exception as restore_e:
                    log_sprint(f"Failed to restore sprint_best: {restore_e!s}")

            finally:
                self.iteration += 1
                remaining = (self.end_time - time.time()) / 60
                log_sprint(f"Time Remaining: {remaining:.1f} minutes.")
                time.sleep(10)

        log_sprint("Sprint target time reached. Finalizing results.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--until", help="Target end time (HH:MM)")
    parser.add_argument("--hours", type=float, default=1.0)
    args = parser.parse_args()

    seconds = get_seconds_until(args.until) if args.until else args.hours * 3600
    sprint = AdaptiveResearchSprint(seconds)
    sprint.run()
