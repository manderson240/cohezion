import asyncio
import logging
import random
from datetime import datetime, timedelta
from pathlib import Path

from cohezion.gaia.interface import get_planetary_interface
from cohezion.mcp.email_notifier import EmailNotifier, NotificationConfig
from cohezion.swarm.agents.gaia_agent import GaiaAgent
from cohezion.swarm.agents.seti_agent import SETIAgent


# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("universe_sim.log"), logging.StreamHandler()],
)
logger = logging.getLogger("UniverseDriver")


class UniverseDriver:
    """
    The Engine of Time for the Overnight Simulation (Gateway 31).
    Runs until 06:00 AM Local Time.
    """

    def __init__(self):
        self.notifier = EmailNotifier(config=NotificationConfig.from_env())
        self.interface = get_planetary_interface()

        # Swarm Roster
        self.gaia = GaiaAgent()
        self.seti = SETIAgent()
        self.agents = [self.gaia, self.seti]

        # Simulation State
        self.chronicle: list[str] = []
        self.start_time = datetime.now()
        # Set End Time to 6:00 AM tomorrow (or today if currently before 6am)
        now = datetime.now()
        target = now.replace(hour=6, minute=0, second=0, microsecond=0)
        if target <= now:
            target += timedelta(days=1)
        self.end_time = target

        logger.info(f"🌌 Universe Simulation Initialized. Ends at: {self.end_time}")

    async def run_simulation(self):
        """Main Event Loop."""
        logger.info("🚀 BIG BANG: Simulation Started.")
        self._log_event("BIG BANG: Universe instantiated.")

        # Send Start Email
        await self.notifier.send_report(
            "Universe Simulation Started",
            f"The Infinite Game has begun.\nEnd Time: {self.end_time}\nMode: Sovereign/Gaia",
        )

        last_hour = datetime.now().hour

        while datetime.now() < self.end_time:
            current_epoch = self._determine_epoch()

            # 1. Swarm Activity (Simulation Step)
            await self._run_step(current_epoch)

            # 2. Hourly Chronicle
            now = datetime.now()
            if now.hour != last_hour:
                await self._generate_hourly_report()
                last_hour = now.hour

            # Sleep to pace the simulation (prevent getting banned/overheating real hardware)
            await asyncio.sleep(10)  # 10 seconds per "tick"

        # 3. Final Dawn Report
        await self._generate_final_report()

    def _determine_epoch(self) -> str:
        """Map time progress to Evolutionary Epochs."""
        total_duration = (self.end_time - self.start_time).total_seconds()
        elapsed = (datetime.now() - self.start_time).total_seconds()
        progress = elapsed / total_duration

        if progress < 0.10:
            return "Planck Era (Quantum Chaos)"
        if progress < 0.30:
            return "Inflationary Era (Expansion)"
        if progress < 0.60:
            return "Biogenesis (Life Emergence)"
        if progress < 0.90:
            return "Noosphere (Civilization)"
        return "Omega Point (Transcendence)"

    async def _run_step(self, epoch: str):
        """Execute one 'tick' of the universe."""

        # Gaia regulates
        vital_signs = self.interface.get_cosmic_constants()
        gaia_thought = f"Epoch: {epoch}. Status: {vital_signs}"

        # Occasionally Gaia speaks/acts
        if random.random() < 0.1:  # 10% chance per tick
            res = await self.gaia.process(gaia_thought)
            self._log_event(f"Gaia Action: {res[:100]}...")

        # SETI Listens
        if random.random() < 0.05:  # 5% chance
            res = await self.seti.process("Scanning the cosmic background...")
            if "TECHNOSIGNATURE" in res:
                self._log_event("🚨 SETI ALERT: First Contact Candidate!")
                await self.notifier.send_report("SETI ALERT", res)

    async def _generate_hourly_report(self):
        """Send telemetry update."""
        stats = self.interface.get_cosmic_constants()
        epoch = self._determine_epoch()

        subject = f"Hourly Chronicle: {datetime.now().strftime('%H:%00')} ({epoch})"
        body = f"""
        ### 🌌 Universe Status Report
        **Epoch**: {epoch}
        **Time**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

        ### 📊 Vital Signs
        - **Entropy**: {stats["UniversalEntropy"]:.4f}
        - **Vacuum Energy**: {stats["VacuumEnergy"]:.2f}
        - **Temperature**: {stats["CosmicTemperature"]:.1f}

        ### 📜 Recent Events
        {self._get_recent_logs(5)}
        """

        await self.notifier.send_report(subject, body)
        logger.info(f"Hourly Report Sent: {subject}")

    async def _generate_final_report(self):
        """Generate the Anthropic Portfolio Deliverable."""
        logger.info("🌅 FINAL DAWN: Generating Universe Portfolio.")

        chronicle_text = "\n".join(self.chronicle)

        subject = "FINAL DAWN: Universe Portfolio (Anthropic Application)"
        body = f"""
        # The Infinite Game: Simulation Concluded

        **Duration**: {self.start_time} to {self.end_time}
        **Total Epochs**: 5

        ## 🧬 Evolutionary Summary
        The simulation successfully traversed from the Planck Era to the Omega Point.
        Strategies deployed:
        1. **Sovereignty**: Maintained local-only execution using `LocalRegistry`.
        2. **Gaia**: Regulated system homeostasis via `PlanetaryInterface`.
        3. **Discovery**: `SETIAgent` scanned for exogenic signals (Arecibo Protocol).

        ## 📜 Full Chronicle
        (Attached below is the abridged history of this universe)

        {self._get_recent_logs(20)}

        ---
        *Generated by Cohezion Swarm (Gateway 31)*
        """

        await self.notifier.send_report(subject, body)

        # Also save to artifact
        Path("chronicle_of_the_infinite.md").write_text(
            f"# Chronicle of the Infinite\n\n{chronicle_text}"
        )

    def _log_event(self, event: str):
        ts = datetime.now().strftime("%H:%M:%S")
        entry = f"[{ts}] {event}"
        self.chronicle.append(entry)
        logger.info(entry)

    def _get_recent_logs(self, n: int) -> str:
        return "\n".join(self.chronicle[-n:])


if __name__ == "__main__":
    driver = UniverseDriver()
    try:
        asyncio.run(driver.run_simulation())
    except KeyboardInterrupt:
        logger.info("Simulation halted by user.")
