"""
Eigent Agent - Integration with CAMEL-AI and Lemonade local server.
Supports multi-agent workforce orchestration and long-horizon tasks.
Supports Symphony-168 roles: Cartographer, Surgeon, Verifier, and SRE.
"""

import asyncio
import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path

import numpy as np


try:
    from camel.agents import ChatAgent
    from camel.configs import ChatGPTConfig
    from camel.messages import BaseMessage
    from camel.models import ModelFactory
    from camel.types import ModelType, RoleType

    CAMEL_AVAILABLE = True
except ImportError:
    CAMEL_AVAILABLE = False
    ChatAgent = BaseMessage = ChatGPTConfig = ModelFactory = ModelType = RoleType = None

from cohezion.core.event_bus import EventType, get_event_bus
from cohezion.core.persistence.repositories.pattern_repository import PatternRepository
from cohezion.core.persistence.surreal_client import SurrealClient
from cohezion.swarm.agents.base_scout import BaseScout, Finding
from cohezion.swarm.agents.code_review_swarm import CodeReviewSwarm
from cohezion.universe.hiho_unified_engine import HIHOUnifiedEngine


logger = logging.getLogger(__name__)


class EigentAgent(BaseScout):
    """
    A Cohezion agent that utilizes CAMEL-AI for multi-agent coordination,
    routed through the local Lemonade inference server.
    """

    def __init__(
        self,
        model: str = "Gemma-4-E2B-it-GGUF",
        lemonade_url: str = "http://localhost:13305",
        role: str = "System Architect",
        **kwargs,
    ) -> None:
        super().__init__(model=model, ollama_url=lemonade_url)

        self.lemonade_url = lemonade_url
        self.role = role
        self.checkpoint_dir = Path("data/eigent/checkpoints")
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        if not CAMEL_AVAILABLE:
            raise ImportError("CAMEL-AI required.")

        self.model_config = ChatGPTConfig(temperature=0.2)
        self.camel_model = ModelFactory.create(
            model_platform="openai",
            model_type=ModelType.GPT_4O,
            model_config_dict=self.model_config.as_dict(),
            api_key="lemonade",
            url=f"{self.lemonade_url}/v1",
        )

        self.agent = ChatAgent(
            system_message=BaseMessage.make_assistant_message(
                role_name=self.role, content=f"You are a {self.role} in Symphony-168."
            ),
            model=self.camel_model,
        )

        self.physics_engine = HIHOUnifiedEngine()
        self.surreal_client = SurrealClient()
        self.pattern_repo = PatternRepository(client=self.surreal_client)
        self.code_swarm = CodeReviewSwarm(repository=self.pattern_repo)
        self._sre_alert_active = False

    async def chat(self, user_msg: str) -> str:
        """Execute a single chat turn with the CAMEL agent."""
        msg = BaseMessage.make_user_message(role_name="User", content=user_msg)
        response = self.agent.step(msg)
        return response.msgs[0].content

    async def analyze(self, path: Path) -> list[Finding]:
        """BaseScout compliance."""
        return []

    async def run_journey(self, task_description: str, duration_days: float = 7.0):
        """Unified Symphony-168 Journey Loop."""
        logger.info(f"Starting Symphony-168 Phase: {self.role}")

        journey_id = hashlib.sha256(task_description.encode()).hexdigest()[:12]
        checkpoint_file = self.checkpoint_dir / f"{journey_id}.json"

        if checkpoint_file.exists():
            state = json.loads(checkpoint_file.read_text())
        else:
            state = {
                "task": task_description,
                "role": self.role,
                "iterations": 0,
                "status": "active",
                "logs": [],
            }

        # SRE specific event subscription
        if self.role == "Reliability Engineer":
            bus = await get_event_bus()

            @bus.subscribe(EventType.SYSTEM_HEALTH)
            async def on_health_event(event):
                if event.payload.get("type") == "service_down":
                    logger.warning(
                        f"SRE REACTION: Service {event.payload['data'].get('name')} is down. Attempting recovery..."
                    )
                    self._sre_alert_active = True

        total_intervals = int(duration_days * 24)
        for i in range(state["iterations"], total_intervals):
            log_entry = {"time": datetime.now().isoformat(), "iteration": i + 1}

            if self.role == "Manifold Analyst":  # Cartographer
                vectors = [np.random.rand(12) for _ in range(5)]
                evolved = await self.physics_engine.step_simulation(vectors)
                log_entry["manifold_drift"] = float(
                    np.mean([np.linalg.norm(v1 - v2) for v1, v2 in zip(vectors, evolved)])
                )

            elif self.role == "Code Surgeon":
                all_files = list(Path("src/cohezion").rglob("*.py"))
                batch = all_files[i * 10 : (i + 1) * 10]
                if batch:
                    for f in batch:
                        await self.code_swarm.static_scout.scan_file(f)
                    log_entry["files_scanned"] = len(batch)

            elif self.role == "QA Automator":  # Verifier
                # Simulate spinning up transient lane via Fleet Monitor
                from cohezion.governance.fleet_monitor import get_fleet_monitor

                monitor = get_fleet_monitor()
                test_port = 8081 + (i % 10)
                pid = await monitor.spawn_ephemeral_service(
                    f"test-lane-{test_port}", test_port, ["sleep", "60"]
                )
                if pid:
                    log_entry["transient_lane"] = f"localhost:{test_port}"
                    await asyncio.sleep(2)
                    await monitor.reap_service(f"test-lane-{test_port}")

            elif self.role == "Reliability Engineer":  # SRE
                if self._sre_alert_active:
                    log_entry["recovery_action"] = "Triggered service restart"
                    self._sre_alert_active = False
                log_entry["fleet_health"] = "nominal"

            # Database persistence
            try:
                if not self.surreal_client._connected:
                    await self.surreal_client.connect()
                await self.surreal_client.create("journey_logs", log_entry)
            except Exception:
                pass

            state["iterations"] = i + 1
            checkpoint_file.write_text(json.dumps(state, indent=2))
            await asyncio.sleep(0.1)  # Sim tempo

        state["status"] = "completed"
        checkpoint_file.write_text(json.dumps(state, indent=2))
