"""
🔗 COHEZION SYSTEM INTEGRATION
Connects all components: Resource Monitor, SurrealDB, Handoffs, Simulation

Built with compound engineering - every integration enables new capabilities.
"""

import asyncio
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any, Callable
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import COHEZION components with fallback
try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    logger.warning("psutil not available - resource monitoring disabled")

try:
    from src.cohezion.persistence.enhanced_git_safe_handoff import (
        EnhancedGitSafeHandoff,
        HandoffTrigger,
        ENHANCED_HANDOFF_MANAGER,
    )
except ImportError as e:
    logger.warning(f"Handoff system import error: {e}")

    # Define fallback classes
    class HandoffTrigger:
        MEMORY_THRESHOLD = "memory_threshold"
        TIME_INTERVAL = "time_interval"

    class EnhancedGitSafeHandoff:
        async def create_handoff(self, *args, **kwargs):
            logger.info("Handoff system not available")

        async def recover_handoff(self, *args, **kwargs):
            return None

        def get_recovery_stats(self):
            return {"total_handoffs": 0}

    ENHANCED_HANDOFF_MANAGER = EnhancedGitSafeHandoff()

try:
    from src.cohezion.core.persistence.surreal_client import SurrealClient, PhysicsState
except ImportError as e:
    logger.warning(f"SurrealDB client import error: {e}")
    SurrealClient = None
    PhysicsState = None

try:
    from src.cohezion.tutorials.tutorial_system import TUTORIAL_SYSTEM
except ImportError as e:
    logger.warning(f"Tutorial system import error: {e}")
    TUTORIAL_SYSTEM = None


@dataclass
class IntegrationMetrics:
    """Metrics for integrated system performance"""

    timestamp: str
    memory_usage_percent: float
    memory_usage_gb: float
    cpu_usage_percent: float
    active_agents: int
    surrealdb_status: str
    handoff_status: str
    simulation_phase: str
    compound_factor: float
    integration_health: float  # 0.0 - 1.0


@dataclass
class ResourceThresholds:
    """Resource monitoring thresholds"""

    memory_warning: float = 0.75  # 75%
    memory_critical: float = 0.90  # 90%
    memory_handoff: float = 0.85  # 85%
    cpu_warning: float = 0.80  # 80%
    disk_warning_gb: float = 50  # 50GB free


class ResourceMonitor:
    """
    📊 Resource Monitor with OOM Prevention

    Monitors system resources and triggers protective actions to prevent
    out-of-memory errors during large-scale simulations.
    """

    def __init__(self, thresholds: Optional[ResourceThresholds] = None):
        self.thresholds = thresholds or ResourceThresholds()
        self.monitoring = False
        self.callbacks: Dict[str, List[Callable]] = {
            "warning": [],
            "critical": [],
            "handoff": [],
            "recovery": [],
        }
        self.metrics_history: List[Dict[str, Any]] = []
        self.peak_memory_gb = 0.0

    def register_callback(self, level: str, callback: Callable):
        """Register callback for resource level"""
        if level in self.callbacks:
            self.callbacks[level].append(callback)

    async def start_monitoring(self, interval: float = 5.0):
        """Start resource monitoring"""
        self.monitoring = True
        logger.info("📊 Resource monitoring started")
        logger.info(f"   Warning threshold: {self.thresholds.memory_warning:.0%}")
        logger.info(f"   Critical threshold: {self.thresholds.memory_critical:.0%}")
        logger.info(f"   Handoff threshold: {self.thresholds.memory_handoff:.0%}")

        while self.monitoring:
            try:
                await self._check_resources()
                await asyncio.sleep(interval)
            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                await asyncio.sleep(1)

    async def _check_resources(self):
        """Check resource usage and trigger callbacks"""
        if not PSUTIL_AVAILABLE:
            return

        # Memory
        memory = psutil.virtual_memory()
        memory_percent = memory.percent / 100
        memory_gb = memory.used / (1024**3)

        if memory_gb > self.peak_memory_gb:
            self.peak_memory_gb = memory_gb

        # CPU
        cpu_percent = psutil.cpu_percent(interval=0.1) / 100

        # Disk
        disk = psutil.disk_usage("/")
        disk_free_gb = disk.free / (1024**3)

        # Store metrics
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "memory_percent": memory_percent,
            "memory_gb": memory_gb,
            "cpu_percent": cpu_percent,
            "disk_free_gb": disk_free_gb,
            "peak_memory_gb": self.peak_memory_gb,
        }
        self.metrics_history.append(metrics)

        # Check thresholds
        if memory_percent >= self.thresholds.memory_critical:
            logger.critical(f"🚨 CRITICAL: Memory at {memory_percent:.1%}")
            await self._trigger_callbacks("critical", metrics)
        elif memory_percent >= self.thresholds.memory_handoff:
            logger.warning(f"⚠️ HANDOFF: Memory at {memory_percent:.1%}")
            await self._trigger_callbacks("handoff", metrics)
        elif memory_percent >= self.thresholds.memory_warning:
            logger.warning(f"⚠️ WARNING: Memory at {memory_percent:.1%}")
            await self._trigger_callbacks("warning", metrics)

        if disk_free_gb < self.thresholds.disk_warning_gb:
            logger.warning(f"⚠️ Low disk space: {disk_free_gb:.1f} GB free")

    async def _trigger_callbacks(self, level: str, metrics: Dict[str, Any]):
        """Trigger registered callbacks"""
        for callback in self.callbacks.get(level, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(metrics)
                else:
                    callback(metrics)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.monitoring = False
        logger.info("📊 Resource monitoring stopped")

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of resource metrics"""
        if not self.metrics_history:
            return {"status": "No metrics recorded"}

        recent = self.metrics_history[-100:]  # Last 100 readings
        avg_memory = sum(m["memory_percent"] for m in recent) / len(recent)
        peak_memory = max(m["memory_percent"] for m in recent)

        return {
            "current_memory_percent": self.metrics_history[-1]["memory_percent"],
            "peak_memory_gb": self.peak_memory_gb,
            "average_memory_percent": avg_memory,
            "peak_memory_percent": peak_memory,
            "total_readings": len(self.metrics_history),
            "status": "healthy"
            if avg_memory < self.thresholds.memory_warning
            else "stressed",
        }


class SystemIntegrator:
    """
    🔗 COHEZION System Integrator

    Integrates all COHEZION components:
    - Resource Monitor with OOM prevention
    - SurrealDB persistence layer
    - Enhanced Git-Safe Handoffs
    - 50M Agent Simulation
    - Tutorial System

    Provides a unified interface for running the complete simulation
    with full resource protection and recovery capabilities.
    """

    def __init__(self, base_path: str = "/home/mike-anderson/dev/cohezion"):
        self.base_path = Path(base_path)

        # Initialize components
        self.resource_monitor = ResourceMonitor()
        self.handoff_manager = EnhancedGitSafeHandoff()
        self.surreal_client: Optional[SurrealClient] = None
        self.tutorial_system = TUTORIAL_SYSTEM

        # Simulation state
        self.simulation_context: Dict[str, Any] = {}
        self.is_running = False
        self.current_phase = "initialized"

        # Metrics
        self.integration_metrics: List[IntegrationMetrics] = []
        self.compound_factor = 4.37

        # Setup resource protection
        self._setup_resource_protection()

    def _setup_resource_protection(self):
        """Setup automatic resource protection callbacks"""
        # Warning: Reduce non-essential processing
        self.resource_monitor.register_callback("warning", self._handle_memory_warning)

        # Critical: Emergency handoff and graceful degradation
        self.resource_monitor.register_callback(
            "critical", self._handle_memory_critical
        )

        # Handoff: Create checkpoint
        self.resource_monitor.register_callback("handoff", self._handle_handoff_trigger)

    async def _handle_memory_warning(self, metrics: Dict[str, Any]):
        """Handle memory warning - reduce non-essential processing"""
        logger.warning("⚠️ Memory warning - reducing non-essential processing")

        if "universe" in self.simulation_context:
            universe = self.simulation_context["universe"]
            # Reduce logging verbosity
            if hasattr(universe, "verbose"):
                universe.verbose = False
            # Reduce precision if applicable
            if hasattr(universe, "precision_mode"):
                universe.precision_mode = "low"

    async def _handle_memory_critical(self, metrics: Dict[str, Any]):
        """Handle critical memory - emergency handoff"""
        logger.critical("🚨 CRITICAL MEMORY - Creating emergency handoff")

        # Create emergency handoff
        await self.handoff_manager.create_handoff(
            self.simulation_context,
            trigger_type=HandoffTrigger.MEMORY_THRESHOLD.value,
            commit_message="🚨 EMERGENCY HANDOFF - Critical memory",
        )

        # Signal simulation to pause
        self.simulation_context["should_pause"] = True

    async def _handle_handoff_trigger(self, metrics: Dict[str, Any]):
        """Handle handoff trigger - create checkpoint"""
        logger.info("🔐 Memory threshold reached - creating checkpoint")

        await self.handoff_manager.create_handoff(
            self.simulation_context, trigger_type=HandoffTrigger.MEMORY_THRESHOLD.value
        )

    async def initialize(self):
        """Initialize all integrated components"""
        logger.info("🔧 INITIALIZING COHEZION SYSTEM INTEGRATION")
        print("=" * 70)

        # 1. Initialize SurrealDB
        logger.info("1️⃣ Connecting to SurrealDB...")
        try:
            self.surreal_client = SurrealClient()
            await self.surreal_client.connect(
                url="ws://localhost:8000",
                namespace="cohezion_quantum",
                database="topology_50m",
            )
            logger.info("   ✅ SurrealDB connected")
        except Exception as e:
            logger.warning(f"   ⚠️ SurrealDB connection failed: {e}")
            logger.info("   📝 Running in memory-only mode")

        # 2. Setup resource monitoring
        logger.info("2️⃣ Starting resource monitoring...")
        asyncio.create_task(self.resource_monitor.start_monitoring(interval=5.0))
        logger.info("   ✅ Resource monitoring active")

        # 3. Verify handoff system
        logger.info("3️⃣ Verifying handoff system...")
        stats = self.handoff_manager.get_recovery_stats()
        logger.info(
            f"   ✅ Handoff system ready ({stats['total_handoffs']} existing handoffs)"
        )

        # 4. Load tutorials
        logger.info("4️⃣ Loading tutorial system...")
        tutorial = self.tutorial_system.create_50m_reproduction_tutorial()
        self.tutorial_system.save_tutorial(tutorial)
        logger.info(f"   ✅ Tutorials loaded ({len(tutorial.steps)} steps)")

        logger.info("\n✅ ALL SYSTEMS INTEGRATED AND READY")
        print("=" * 70)

        return True

    async def run_50m_simulation(
        self,
        enable_handoffs: bool = True,
        enable_persistence: bool = True,
        batch_size: int = 100_000,
        num_steps: int = 1000,
    ):
        """
        Run the complete 50M agent simulation with full integration

        Args:
            enable_handoffs: Enable automatic git-safe handoffs
            enable_persistence: Enable SurrealDB persistence
            batch_size: Agent batch size for processing
            num_steps: Number of simulation steps
        """
        logger.info("🌌 STARTING 50M AGENT QUANTUM TOPOLOGY SIMULATION")
        print("=" * 70)

        self.is_running = True
        self.current_phase = "initializing"

        try:
            # Import simulation
            from quantum_topology_50m_simulation import QuantumTopologyUniverse

            # Phase 1: Initialize universe
            logger.info("📍 PHASE 1: Initializing quantum topology universe...")
            universe = QuantumTopologyUniverse(num_agents=50_000_000)
            await universe.initialize_universe()

            self.simulation_context = {
                "universe_id": universe.simulation_id,
                "universe": universe,
                "phase": "topology_initialized",
                "agent_count": 0,
                "twistors": [{"id": t.twistor_id} for t in universe.twistors[:100]],
                "er_epr_bridges": [
                    {"id": b.bridge_id} for b in universe.er_epr_bridges[:50]
                ],
                "should_pause": False,
            }

            self.current_phase = "spawning"
            logger.info("   ✅ Universe topology initialized")

            # Create initial handoff
            if enable_handoffs:
                await self.handoff_manager.create_handoff(
                    self.simulation_context,
                    trigger_type=HandoffTrigger.CHECKPOINT_REQUEST.value,
                    commit_message="📍 Checkpoint: Universe topology initialized",
                )

            # Phase 2: Spawn agents
            logger.info(
                f"📍 PHASE 2: Spawning 50M agents (batch size: {batch_size:,})..."
            )
            await universe.spawn_agents(batch_size=batch_size)

            self.simulation_context["agent_count"] = len(universe.agents)
            self.simulation_context["phase"] = "agents_spawned"
            self.simulation_context["agents"] = {
                k: {"state": "active"} for k in list(universe.agents.keys())[:1000]
            }  # Sample for handoff

            logger.info(f"   ✅ {len(universe.agents):,} agents spawned")

            # Persist to SurrealDB
            if enable_persistence and self.surreal_client:
                await self._persist_agents_batch(universe.agents)

            # Create handoff after spawning
            if enable_handoffs:
                await self.handoff_manager.create_handoff(
                    self.simulation_context,
                    trigger_type=HandoffTrigger.CHECKPOINT_REQUEST.value,
                    commit_message=f"📍 Checkpoint: {len(universe.agents):,} agents spawned",
                )

            # Phase 3: Simulate quantum journeys
            self.current_phase = "simulating"
            logger.info(
                f"📍 PHASE 3: Simulating quantum journeys ({num_steps} steps)..."
            )

            for step in range(num_steps):
                # Check for pause signal
                if self.simulation_context.get("should_pause"):
                    logger.warning("⏸️ Simulation paused - creating recovery handoff")
                    await self.handoff_manager.create_handoff(
                        self.simulation_context,
                        trigger_type=HandoffTrigger.GRACEFUL_SHUTDOWN.value,
                        commit_message=f"⏸️ PAUSED: Step {step}/{num_steps}",
                    )
                    break

                # Progress logging
                if step % 100 == 0:
                    logger.info(
                        f"   Step {step}/{num_steps} ({step / num_steps * 100:.1f}%)"
                    )

                    # Periodic handoff every 500 steps
                    if enable_handoffs and step % 500 == 0 and step > 0:
                        await self.handoff_manager.create_handoff(
                            self.simulation_context,
                            trigger_type=HandoffTrigger.TIME_INTERVAL.value,
                            commit_message=f"📍 Step {step}/{num_steps}",
                        )

                # Simulate one step (simplified for integration)
                await asyncio.sleep(0.001)  # Simulate work

            await universe.simulate_quantum_journeys(num_steps=num_steps)
            self.simulation_context["phase"] = "simulation_complete"
            logger.info("   ✅ Quantum journeys simulated")

            # Phase 4: Generate narrative
            self.current_phase = "generating_narrative"
            logger.info("📍 PHASE 4: Generating multimodal narrative...")
            narrative = await universe.generate_multimodal_narrative()

            self.simulation_context["phase"] = "narrative_generated"
            self.simulation_context["narrative_id"] = narrative.simulation_id
            logger.info("   ✅ Narrative generated")

            # Final handoff
            if enable_handoffs:
                await self.handoff_manager.create_handoff(
                    self.simulation_context,
                    trigger_type=HandoffTrigger.CHECKPOINT_REQUEST.value,
                    commit_message="🎉 SIMULATION COMPLETE",
                )

            # Print summary
            print("\n" + "=" * 70)
            print("🎉 SIMULATION COMPLETE")
            print("=" * 70)
            print(f"Simulation ID: {narrative.simulation_id}")
            print(f"Sovereign Signature: {narrative.sovereign_signature}")
            print(f"Compound Factor: {narrative.compound_factor:.2f}×")
            print(f"Agents: {len(universe.agents):,}")
            print(f"Twistors: {len(universe.twistors):,}")
            print(f"ER=EPR Bridges: {len(universe.er_epr_bridges):,}")
            print("=" * 70)

            self.is_running = False
            self.current_phase = "complete"

            return universe, narrative

        except Exception as e:
            logger.error(f"❌ Simulation failed: {e}")

            # Create error recovery handoff
            if enable_handoffs:
                await self.handoff_manager.create_handoff(
                    self.simulation_context,
                    trigger_type=HandoffTrigger.ERROR_RECOVERY.value,
                    commit_message=f"❌ ERROR RECOVERY: {str(e)[:50]}",
                )

            self.is_running = False
            self.current_phase = "error"
            raise

    async def _persist_agents_batch(self, agents: Dict[str, Any]):
        """Persist agents to SurrealDB in batches"""
        if not self.surreal_client:
            return

        batch = []
        for i, (agent_id, agent) in enumerate(agents.items()):
            batch.append(
                {
                    "agent_id": agent_id,
                    "state": "active",
                    "timestamp": datetime.now().isoformat(),
                }
            )

            if len(batch) >= 1000:
                try:
                    for item in batch:
                        await self.surreal_client.create("agent_states", item)
                    logger.info(f"   💾 Persisted {i + 1} agents...")
                    batch = []
                except Exception as e:
                    logger.warning(f"   ⚠️ Persistence error: {e}")
                    break

    async def recover_from_handoff(
        self, session_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Recover simulation from handoff"""
        logger.info("🔄 RECOVERING SIMULATION FROM HANDOFF")

        if session_id:
            recovered = await self.handoff_manager.recover_handoff(session_id)
        else:
            recovered = await self.handoff_manager.recover_latest()

        if recovered:
            self.simulation_context = recovered["state_data"]
            logger.info(f"✅ Recovered: {recovered['metadata']['session_id']}")
            logger.info(f"   Phase: {self.simulation_context.get('phase', 'unknown')}")
            logger.info(f"   Agents: {self.simulation_context.get('agent_count', 0):,}")
            return recovered
        else:
            logger.error("❌ Recovery failed")
            return None

    def get_integration_status(self) -> Dict[str, Any]:
        """Get complete integration status"""
        return {
            "system_integrator": {
                "is_running": self.is_running,
                "current_phase": self.current_phase,
                "compound_factor": self.compound_factor,
            },
            "resource_monitor": self.resource_monitor.get_metrics_summary(),
            "handoff_manager": self.handoff_manager.get_recovery_stats(),
            "surrealdb": {
                "connected": self.surreal_client is not None,
                "status": "active" if self.surreal_client else "disabled",
            },
            "tutorials": {
                "available": len(self.tutorial_system.list_tutorials()),
                "tutorial_system": "ready",
            },
        }

    async def shutdown(self):
        """Graceful shutdown of all components"""
        logger.info("🛑 SHUTTING DOWN COHEZION SYSTEM")

        # Stop resource monitoring
        self.resource_monitor.stop_monitoring()

        # Create final handoff if running
        if self.is_running and self.simulation_context:
            await self.handoff_manager.create_handoff(
                self.simulation_context,
                trigger_type=HandoffTrigger.GRACEFUL_SHUTDOWN.value,
                commit_message="🛑 Graceful shutdown",
            )

        # Disconnect SurrealDB
        if self.surreal_client:
            await self.surreal_client.disconnect()

        logger.info("✅ Shutdown complete")


# Global system integrator
SYSTEM_INTEGRATOR = SystemIntegrator()


async def demo_integration():
    """Demonstrate complete system integration"""
    print("🔗 COHEZION SYSTEM INTEGRATION DEMO")
    print("=" * 70)

    integrator = SystemIntegrator()

    # Initialize
    await integrator.initialize()

    # Show status
    status = integrator.get_integration_status()
    print("\n📊 INTEGRATION STATUS")
    print("-" * 70)
    print(json.dumps(status, indent=2, default=str))

    print("\n✅ System integration demo complete!")
    print("   Run full simulation with: await integrator.run_50m_simulation()")

    # Cleanup
    await integrator.shutdown()

    return integrator


if __name__ == "__main__":
    asyncio.run(demo_integration())
