import hashlib
import logging
import asyncio
import time
from cohezion.core.time_keeper import get_time_keeper

logger = logging.getLogger(__name__)

class RedundancyManager:
    """
    Manages task redundancy and tiered suppression for agents.
    """
    def __init__(self, agent_name: str, window_size: int = 100):
        self.agent_name = agent_name
        self.window_size = window_size
        self.history: list[str] = [] # Rolling window of SHA-256 hashes
        self.last_suppression_time: float = 0
        self.suppression_level: int = 0 # 0: None, 1: Warning, 2: Perturbation, 3: Hard Sleep

    def _get_hash(self, task_str: str) -> str:
        return hashlib.sha256(task_str.encode()).hexdigest()

    def check(self, task_str: str) -> tuple[int, str | None]:
        """
        Check for redundancy and return (suppression_level, modified_task).

        Levels:
        0 - Proceed normally
        1 - Warning (Log only)
        2 - Perturbation (Modify prompt)
        3 - Hard Sleep (Stop / Delay)
        """
        task_hash = self._get_hash(task_str)
        self.history.append(task_hash)
        if len(self.history) > self.window_size:
            self.history.pop(0)

        count = self.history.count(task_hash)

        if count >= 50:
            return 3, None # Hard Sleep
        elif count >= 10:
            # Perturb the task to break the loop
            perturbed = f"{task_str} (Redundancy recovery mode: analyze from a novel perspective)"
            return 2, perturbed
        elif count >= 3:
            return 1, task_str

        return 0, task_str

    async def apply_suppression(self, level: int, task_str: str):
        """Log event and handle suppression delays."""
        tk = get_time_keeper()

        if level == 1:
            logger.warning(f"🔄 Redundancy Warning [{self.agent_name}]: Task repeated.")
            await tk.log_event(
                agent_name=self.agent_name,
                event_type="REDUNDANCY_LEVEL_1",
                details={"task": task_str[:50]}
            )
        elif level == 2:
            logger.info(f"✨ Perturbing task for {self.agent_name} to break redundancy loop.")
            await tk.log_event(
                agent_name=self.agent_name,
                event_type="REDUNDANCY_LEVEL_2",
                details={"action": "perturbation"}
            )
        elif level == 3:
            delay = 300 # 5 minutes sleep
            logger.error(f"🛑 HARD SLEEP triggered for {self.agent_name}. Suspending for {delay}s.")
            await tk.log_event(
                agent_name=self.agent_name,
                event_type="REDUNDANCY_LEVEL_3",
                details={"delay": delay}
            )
            await asyncio.sleep(delay)
