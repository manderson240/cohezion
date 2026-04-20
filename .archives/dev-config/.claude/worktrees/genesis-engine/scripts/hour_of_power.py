import asyncio
import logging
import random
from datetime import datetime, timedelta

from cohezion.gaia.interface import get_planetary_interface
from cohezion.mcp.email_notifier import EmailNotifier, NotificationConfig
from cohezion.mcp.findings_dispatcher import FindingsDispatcher
from cohezion.swarm.agents.gaia_agent import GaiaAgent
from cohezion.swarm.agents.seti_agent import SETIAgent


# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("hour_of_power.log"), logging.StreamHandler()],
)
logger = logging.getLogger("HourOfPower")


class HourOfPowerDriver:
    """
    Experimental 60-minute Autonomous Run.
    Gateway 32: Redundancy Suppression & External Delivery.
    """

    def __init__(self):
        self.notifier = EmailNotifier(config=NotificationConfig.from_env())
        self.dispatcher = FindingsDispatcher()
        self.interface = get_planetary_interface()

        # Swarm Roster
        self.gaia = GaiaAgent()
        self.seti = SETIAgent()

        # Simulation State
        self.chronicle: list[str] = []
        self.start_time = datetime.now()
        self.end_time = self.start_time + timedelta(hours=1)

        logger.info(f"✨ Hour of Power Initialized. Termination at: {self.end_time}")

    async def run(self):
        """Main Loop."""
        logger.info("🚀 HOUR OF POWER: Autonomous Ignition.")
        start_msg = f"Autonomous simulation started. Ending at: {self.end_time}"
        await self.dispatcher.dispatch("Ignition", start_msg)
        await self.notifier.send_report("🚀 Hour of Power: Ignition", start_msg)

        last_epoch = None
        while datetime.now() < self.end_time:
            progress = (datetime.now() - self.start_time).total_seconds() / 3600
            epoch = self._get_mini_epoch(progress)

            if epoch != last_epoch:
                await self.notifier.send_report(
                    f"🌌 New Epoch: {epoch}",
                    f"Simulation has evolved to the {epoch} phase.",
                )
                last_epoch = epoch

            # 1. Swarm Step
            await self._run_step(epoch)

            # Pacing
            await asyncio.sleep(30)  # 2 ticks per minute

        # Finalization
        logger.info("🏁 HOUR OF POWER: Simulation Concluded.")
        await self.dispatcher.dispatch("Conclusion", "1-hour autonomous run complete. Review results/pulse.")
        await self.notifier.send_report(
            "🏁 Hour of Power: Concluded",
            "The 1-hour high-fidelity run has completed successfully.",
        )

    def _get_mini_epoch(self, progress: float) -> str:
        if progress < 0.2:
            return "Initial Alignment"
        if progress < 0.5:
            return "High-Fidelity Expansion"
        if progress < 0.8:
            return "Coherent Convergence"
        return "Systemic Emergence"

    async def _run_step(self, epoch: str):
        vital_signs = self.interface.get_cosmic_constants()

        # Gaia Action
        if random.random() < 0.2:
            res = await self.gaia.process(
                f"Epoch: {epoch}. Maintain homeostasis for: {vital_signs}"
            )
            self._log_event(f"Gaia: {res[:50]}...")
            if "CRITICAL" in res.upper():
                await self.dispatcher.dispatch("Gaia Alert", res[:200], color=0xFF6B6B)

        # SETI Action
        if random.random() < 0.1:
            res = await self.seti.process("Scanning for exogenic signals in the 1-hour window...")
            self._log_event(f"SETI: {res[:50]}...")
            if "SIGNAL" in res.upper():
                await self.dispatcher.dispatch("SETI Signal", res[:200], color=0x4ECDC4)

    def _log_event(self, event: str):
        ts = datetime.now().strftime("%H:%M:%S")
        entry = f"[{ts}] {event}"
        self.chronicle.append(entry)
        logger.info(entry)


if __name__ == "__main__":
    driver = HourOfPowerDriver()
    try:
        asyncio.run(driver.run())
    except KeyboardInterrupt:
        logger.info("Hour of Power manually halted.")
