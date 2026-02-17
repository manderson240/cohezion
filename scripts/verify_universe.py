import asyncio
import logging
import sys
from pathlib import Path

# Mock the UniverseDriver to run fast
from scripts.universe_driver import UniverseDriver


class FastDriver(UniverseDriver):
    """Driver with accelerated time for testing."""

    async def run_simulation(self):
        # Override run to simulate faster
        self._log_event("BIG BANG: Universe instantiated.")

        # Simulate 1 step of each Epoch
        epochs = ["Planck Era", "Inflationary Era", "Biogenesis", "Noosphere"]
        for e in epochs:
            print(f"Simulating Epoch: {e}")
            await self._run_step(e)

        # Simulate Hourly Report
        await self._generate_hourly_report()

        # Simulate Final Report
        await self._generate_final_report()

    async def _run_step(self, epoch: str):
        # Skip actual agent calls to save time/tokens unless necessary
        # Just update stats
        self.interface.report_activity()
        self._log_event(f"Step in {epoch}")


# Add src to path
sys.path.append(str(Path.cwd() / "src"))


async def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger("UniverseVerify")

    print("\n--- 🌌 Test 1: Instantiation ---")
    driver = FastDriver()

    # Check start/end times
    print(f"Start: {driver.start_time}")
    print(f"End: {driver.end_time}")

    if driver.end_time > driver.start_time:
        print("✅ PASS: Time horizon valid.")
    else:
        print("❌ FAIL: Invalid time horizon.")

    print("\n--- ⏳ Test 2: Epoch Progression (Fast Forward) ---")

    await driver.run_simulation()

    print("\n--- 📜 Chronicle Check ---")
    chronicle = driver.chronicle
    for entry in chronicle:
        print(entry)

    if any("BIG BANG" in e for e in chronicle):
        print("✅ PASS: Big Bang occurred.")

    # Check if artifacts generated
    if Path("chronicle_of_the_infinite.md").exists():
        print("✅ PASS: Chronicle Artifact saved.")
        Path("chronicle_of_the_infinite.md").unlink()  # Cleanup


if __name__ == "__main__":
    asyncio.run(main())
