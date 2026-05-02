import os
import signal
import subprocess
import time


def run_process(cmd):
    # Accept command as a list to avoid shell injection
    if isinstance(cmd, str):
        cmd = cmd.split()
    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=os.environ.get("COHEZION_ROOT", "."),
        text=True,
        preexec_fn=os.setsid,
    )


def test_singularity():
    print("🌌 Initiating Singularity Check...")
    print("   Starting Subsystems...")

    # 1. Start Nexus (Logic)
    nexus = run_process("uv run python3 scripts/drivers/nexus_research.py")

    # 2. Start Cortex (Vision)
    cortex = run_process("uv run python3 src/cohezion/system/visual_cortex.py")

    # 3. Start Dreamer (Subconscious)
    dreamer = run_process("uv run python3 src/cohezion/system/dreamer.py")

    # 4. Start Simulation (Reality) - Mocked via Unit Test agent logic or actual agent?
    # Running the full `universal_simulation.py` driver connects everything.
    sim = run_process("uv run python3 scripts/drivers/universal_simulation.py")

    processes = [nexus, cortex, dreamer, sim]
    names = ["Nexus", "Cortex", "Dreamer", "Sim"]

    try:
        print("⏳ Running for 30 seconds...")
        for _i in range(30):
            time.sleep(1)
            # Check for early failures
            for p, name in zip(processes, names, strict=False):
                if p.poll() is not None:
                    print(f"❌ {name} died early! Exit Code: {p.returncode}")
                    # stdout, stderr = p.communicate()
                    # print(stderr)
                    return
            print(".", end="", flush=True)

        print("\n✅ System Stable for 30s.")

    except KeyboardInterrupt:
        print("\n⚠️ Interrupted.")
    finally:
        print("🛑 Shutting down Singularity...")
        for p in processes:
            if p.poll() is None:
                os.killpg(os.getpgid(p.pid), signal.SIGTERM)
        print("✅ Shutdown complete.")


if __name__ == "__main__":
    test_singularity()
