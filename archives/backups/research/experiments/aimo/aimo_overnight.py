import datetime
import time

from swarm_driver import run_simulation


def log(msg):
    timestamp = datetime.datetime.now().isoformat()
    out = f"[{timestamp}] {msg}"
    print(out)
    with open("overnight_aimo.log", "a") as f:
        f.write(out + "\n")


def overnight_run(duration_hours=8):
    start_time = time.time()
    end_time = start_time + (duration_hours * 3600)

    iteration = 1
    best_accuracy = 0.0
    best_stability = 0.0

    log(f"Starting AIMO overnight refinement loop for {duration_hours} hours.")

    while time.time() < end_time:
        log(f"--- Iteration {iteration} ---")
        try:
            # Run the simulation
            accuracy, stability = run_simulation()
            log(f"Result -> Accuracy: {accuracy * 100:.2f}%, Stability: {stability:.3f}")

            if accuracy > best_accuracy or (
                accuracy == best_accuracy and stability > best_stability
            ):
                best_accuracy = accuracy
                best_stability = stability
                log(
                    f"*** NEW BEST: Acc: {best_accuracy * 100:.2f}%, Stab: {best_stability:.3f} ***"
                )

        except Exception as e:
            log(f"Error in iteration {iteration}: {e!s}")

        iteration += 1
        log("Cooling down for 1 minute to flush VRAM...")
        time.sleep(60)

    log("Overnight run completed.")


if __name__ == "__main__":
    overnight_run(duration_hours=8)
