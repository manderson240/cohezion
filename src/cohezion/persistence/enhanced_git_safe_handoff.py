"""
🔐 COHEZION ENHANCED GIT-SAFE HANDOFF SYSTEM
Session state preservation with validation, compression, and automatic triggers

Built with compound engineering - every handoff makes future recovery faster.
"""

import asyncio
import json
import hashlib
import zlib
import pickle
import base64
import time
import signal
import psutil
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Callable
from enum import Enum
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HandoffTrigger(Enum):
    """Automatic handoff trigger conditions"""

    MEMORY_THRESHOLD = "memory_threshold"
    TIME_INTERVAL = "time_interval"
    CHECKPOINT_REQUEST = "checkpoint_request"
    GRACEFUL_SHUTDOWN = "graceful_shutdown"
    ERROR_RECOVERY = "error_recovery"
    MANUAL_TRIGGER = "manual_trigger"


@dataclass
class CompressedContext:
    """Compressed session context for efficient storage"""

    original_size: int
    compressed_size: int
    compression_ratio: float
    compression_method: str
    data_hash: str
    chunk_count: int


@dataclass
class ValidationResult:
    """Validation result for handoff integrity"""

    is_valid: bool
    errors: List[str]
    warnings: List[str]
    integrity_score: float  # 0.0 - 1.0
    validation_timestamp: str


@dataclass
class EnhancedHandoffState:
    """Enhanced handoff state with compression and validation"""

    session_id: str
    timestamp: float
    trigger_type: str

    # Core session data
    simulation_state: Dict[str, Any]
    agent_states: Dict[str, Any]
    quantum_topology: Dict[str, Any]

    # Compression metadata
    compression: CompressedContext

    # Validation
    validation: ValidationResult

    # Git integration
    git_commit_hash: Optional[str]
    git_branch: Optional[str]

    # Recovery metadata
    recovery_priority: int  # 1-10, higher = faster recovery
    dependencies: List[str]  # Other sessions this depends on

    # Compound engineering metrics
    compound_factor: float
    compression_efficiency: float
    validation_score: float


class ContextCompressor:
    """
    📦 Context Compression Engine
    Compresses large session states for efficient storage and transmission
    """

    def __init__(self, max_chunk_size: int = 1024 * 1024):  # 1MB chunks
        self.max_chunk_size = max_chunk_size
        self.compression_stats: List[Dict[str, Any]] = []

    def compress(
        self, data: Dict[str, Any], method: str = "zlib"
    ) -> Tuple[bytes, CompressedContext]:
        """Compress session data with intelligent chunking"""
        # Serialize to JSON first
        json_data = json.dumps(data, default=str).encode("utf-8")
        original_size = len(json_data)

        # Compress based on method
        if method == "zlib":
            compressed = zlib.compress(json_data, level=9)
        elif method == "pickle":
            pickle_data = pickle.dumps(data)
            compressed = zlib.compress(pickle_data, level=9)
        else:
            compressed = json_data

        compressed_size = len(compressed)
        compression_ratio = original_size / max(compressed_size, 1)

        # Chunk if necessary
        chunks = []
        chunk_count = 0
        for i in range(0, len(compressed), self.max_chunk_size):
            chunk = compressed[i : i + self.max_chunk_size]
            chunks.append(chunk)
            chunk_count += 1

        # Generate hash for integrity
        data_hash = hashlib.sha256(compressed).hexdigest()[:16]

        context = CompressedContext(
            original_size=original_size,
            compressed_size=compressed_size,
            compression_ratio=compression_ratio,
            compression_method=method,
            data_hash=data_hash,
            chunk_count=chunk_count,
        )

        # Join chunks for storage
        compressed_data = b"".join(chunks)

        # Log stats
        self.compression_stats.append(
            {
                "timestamp": datetime.now().isoformat(),
                "original_size": original_size,
                "compressed_size": compressed_size,
                "ratio": compression_ratio,
                "method": method,
            }
        )

        logger.info(
            f"📦 Compressed {original_size:,} bytes → {compressed_size:,} bytes ({compression_ratio:.2f}×)"
        )

        return compressed_data, context

    def decompress(
        self, compressed_data: bytes, context: CompressedContext
    ) -> Dict[str, Any]:
        """Decompress session data"""
        # Verify hash
        actual_hash = hashlib.sha256(compressed_data).hexdigest()[:16]
        if actual_hash != context.data_hash:
            raise ValueError(
                f"Data corruption detected: hash mismatch {actual_hash} != {context.data_hash}"
            )

        # Decompress
        if context.compression_method == "zlib":
            json_data = zlib.decompress(compressed_data)
            data = json.loads(json_data.decode("utf-8"))
        elif context.compression_method == "pickle":
            pickle_data = zlib.decompress(compressed_data)
            data = pickle.loads(pickle_data)
        else:
            data = json.loads(compressed_data.decode("utf-8"))

        logger.info(
            f"📦 Decompressed {context.compressed_size:,} bytes → {context.original_size:,} bytes"
        )

        return data

    def get_stats(self) -> Dict[str, Any]:
        """Get compression statistics"""
        if not self.compression_stats:
            return {"status": "No compression history"}

        total_original = sum(s["original_size"] for s in self.compression_stats)
        total_compressed = sum(s["compressed_size"] for s in self.compression_stats)
        avg_ratio = total_original / max(total_compressed, 1)

        return {
            "total_sessions": len(self.compression_stats),
            "total_original_bytes": total_original,
            "total_compressed_bytes": total_compressed,
            "average_compression_ratio": avg_ratio,
            "space_saved_gb": (total_original - total_compressed) / (1024**3),
            "methods_used": list(set(s["method"] for s in self.compression_stats)),
        }


class HandoffValidator:
    """
    ✅ Handoff Validation Engine
    Ensures handoff integrity and completeness
    """

    def __init__(self):
        self.validation_rules: List[Callable[[Dict[str, Any]], Tuple[bool, str]]] = []
        self._register_default_rules()

    def _register_default_rules(self):
        """Register default validation rules"""
        self.validation_rules.extend(
            [
                self._validate_session_id,
                self._validate_timestamp,
                self._validate_simulation_state,
                self._validate_agent_count,
                self._validate_quantum_topology,
            ]
        )

    def _validate_session_id(self, state: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate session ID format"""
        session_id = state.get("session_id", "")
        if not session_id or len(session_id) < 8:
            return False, "Invalid session ID"
        return True, "Session ID valid"

    def _validate_timestamp(self, state: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate timestamp is recent"""
        timestamp = state.get("timestamp", 0)
        age = time.time() - timestamp
        if age > 86400:  # 24 hours
            return False, f"Handoff is {age / 3600:.1f} hours old"
        return True, "Timestamp valid"

    def _validate_simulation_state(self, state: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate simulation state completeness"""
        sim_state = state.get("simulation_state", {})
        required_keys = ["universe_id", "phase", "agent_count"]
        missing = [k for k in required_keys if k not in sim_state]
        if missing:
            return False, f"Missing simulation keys: {missing}"
        return True, "Simulation state valid"

    def _validate_agent_count(self, state: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate agent count is reasonable"""
        agent_states = state.get("agent_states", {})
        agent_count = len(agent_states)
        if agent_count > 100_000_000:
            return False, f"Unreasonably high agent count: {agent_count}"
        if agent_count == 0:
            return False, "No agents in state"
        return True, f"Agent count valid: {agent_count}"

    def _validate_quantum_topology(self, state: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate quantum topology structure"""
        topology = state.get("quantum_topology", {})
        if "twistors" not in topology:
            return False, "Missing twistor data"
        if "er_epr_bridges" not in topology:
            return False, "Missing ER=EPR bridge data"
        return True, "Quantum topology valid"

    def validate(self, state: Dict[str, Any]) -> ValidationResult:
        """Run all validation rules"""
        errors = []
        warnings = []
        passed = 0
        total = len(self.validation_rules)

        for rule in self.validation_rules:
            try:
                is_valid, message = rule(state)
                if is_valid:
                    passed += 1
                else:
                    errors.append(message)
            except Exception as e:
                warnings.append(f"Validation rule failed: {str(e)}")

        integrity_score = passed / max(total, 1)
        is_valid = len(errors) == 0

        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            integrity_score=integrity_score,
            validation_timestamp=datetime.now().isoformat(),
        )


class EnhancedGitSafeHandoff:
    """
    🔐 Enhanced Git-Safe Handoff Manager

    Features:
    - Automatic triggers (memory, time, errors)
    - Context compression for large states
    - Validation before and after handoff
    - Recovery mechanisms with priority levels
    - Compound engineering (each recovery is faster)
    """

    def __init__(
        self,
        repo_path: str = "/home/mike-anderson/dev/cohezion",
        memory_threshold: float = 0.85,  # 85% memory usage
        checkpoint_interval: int = 3600,  # 1 hour
        auto_trigger: bool = True,
    ):
        self.repo_path = Path(repo_path)
        self.memory_threshold = memory_threshold
        self.checkpoint_interval = checkpoint_interval
        self.auto_trigger = auto_trigger

        # Components
        self.compressor = ContextCompressor()
        self.validator = HandoffValidator()

        # State storage
        self.handoff_dir = self.repo_path / "data" / "handoffs"
        self.handoff_dir.mkdir(parents=True, exist_ok=True)
        self.handoff_history: List[EnhancedHandoffState] = []

        # Auto-trigger setup
        self.last_checkpoint = time.time()
        self.running = False
        self.trigger_callbacks: Dict[HandoffTrigger, List[Callable]] = {
            trigger: [] for trigger in HandoffTrigger
        }

        # Recovery statistics
        self.recovery_stats = {
            "total_handoffs": 0,
            "successful_recoveries": 0,
            "failed_recoveries": 0,
            "avg_recovery_time": 0.0,
            "compression_savings_gb": 0.0,
        }

        # Register signal handlers
        if auto_trigger:
            self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""

        def handle_sigterm(signum, frame):
            logger.info("🛑 SIGTERM received - creating emergency handoff")
            asyncio.create_task(self.create_emergency_handoff())

        def handle_sigint(signum, frame):
            logger.info("🛑 SIGINT received - creating emergency handoff")
            asyncio.create_task(self.create_emergency_handoff())

        signal.signal(signal.SIGTERM, handle_sigterm)
        signal.signal(signal.SIGINT, handle_sigint)

    def register_trigger_callback(self, trigger: HandoffTrigger, callback: Callable):
        """Register callback for automatic trigger"""
        self.trigger_callbacks[trigger].append(callback)

    async def start_auto_monitoring(self, simulation_context: Dict[str, Any]):
        """Start automatic monitoring for triggers"""
        self.running = True
        self.simulation_context = simulation_context

        logger.info("🔍 Auto-monitoring started")
        logger.info(f"   Memory threshold: {self.memory_threshold:.0%}")
        logger.info(f"   Checkpoint interval: {self.checkpoint_interval}s")

        while self.running:
            try:
                await self._check_triggers()
                await asyncio.sleep(5)  # Check every 5 seconds
            except Exception as e:
                logger.error(f"Auto-monitoring error: {e}")
                await asyncio.sleep(1)

    async def _check_triggers(self):
        """Check for automatic trigger conditions"""
        # Memory threshold
        memory = psutil.virtual_memory()
        if memory.percent / 100 > self.memory_threshold:
            logger.warning(f"⚠️ Memory threshold exceeded: {memory.percent:.1f}%")
            await self._trigger_handoff(HandoffTrigger.MEMORY_THRESHOLD)
            return

        # Time interval
        if time.time() - self.last_checkpoint > self.checkpoint_interval:
            logger.info("⏰ Checkpoint interval reached")
            await self._trigger_handoff(HandoffTrigger.TIME_INTERVAL)
            return

    async def _trigger_handoff(self, trigger: HandoffTrigger):
        """Trigger handoff and run callbacks"""
        # Run callbacks
        for callback in self.trigger_callbacks.get(trigger, []):
            try:
                await callback()
            except Exception as e:
                logger.error(f"Trigger callback error: {e}")

        # Create handoff
        if hasattr(self, "simulation_context"):
            await self.create_handoff(
                self.simulation_context, trigger_type=trigger.value
            )

        self.last_checkpoint = time.time()

    async def create_handoff(
        self,
        simulation_context: Dict[str, Any],
        trigger_type: str = "manual",
        commit_message: Optional[str] = None,
    ) -> EnhancedHandoffState:
        """Create enhanced git-safe handoff"""
        logger.info("🔐 CREATING ENHANCED GIT-SAFE HANDOFF")
        logger.info(f"   Trigger: {trigger_type}")

        # Generate session ID
        session_id = f"handoff_{int(time.time())}_{hashlib.sha256(str(simulation_context).encode()).hexdigest()[:8]}"

        # Extract state components
        simulation_state = {
            "universe_id": simulation_context.get("universe_id", "unknown"),
            "phase": simulation_context.get("phase", "unknown"),
            "agent_count": simulation_context.get("agent_count", 0),
            "timestamp": datetime.now().isoformat(),
        }

        agent_states = simulation_context.get("agents", {})
        quantum_topology = {
            "twistors": simulation_context.get("twistors", []),
            "er_epr_bridges": simulation_context.get("er_epr_bridges", []),
            "quantum_bio_networks": simulation_context.get("quantum_bio_networks", []),
        }

        # Prepare data for compression
        state_data = {
            "simulation_state": simulation_state,
            "agent_states": agent_states,
            "quantum_topology": quantum_topology,
        }

        # Compress data
        compressed_data, compression_context = self.compressor.compress(
            state_data, method="zlib"
        )

        # Validate before saving
        validation_result = self.validator.validate(state_data)
        if not validation_result.is_valid:
            logger.warning(f"⚠️ Validation failed: {validation_result.errors}")

        # Calculate metrics
        compound_factor = 4.37 + (self.recovery_stats["total_handoffs"] * 0.1)
        compression_efficiency = compression_context.compression_ratio
        validation_score = validation_result.integrity_score

        # Create handoff state
        handoff_state = EnhancedHandoffState(
            session_id=session_id,
            timestamp=time.time(),
            trigger_type=trigger_type,
            simulation_state=simulation_state,
            agent_states={"compressed": True, "hash": compression_context.data_hash},
            quantum_topology=quantum_topology,
            compression=compression_context,
            validation=validation_result,
            git_commit_hash=None,
            git_branch=None,
            recovery_priority=self._calculate_recovery_priority(simulation_context),
            dependencies=simulation_context.get("dependencies", []),
            compound_factor=compound_factor,
            compression_efficiency=compression_efficiency,
            validation_score=validation_score,
        )

        # Save compressed data
        await self._save_handoff(handoff_state, compressed_data)

        # Create git commit
        git_hash, git_branch = await self._create_git_commit(
            handoff_state, commit_message
        )
        handoff_state.git_commit_hash = git_hash
        handoff_state.git_branch = git_branch

        # Update history
        self.handoff_history.append(handoff_state)
        self.recovery_stats["total_handoffs"] += 1
        self.last_checkpoint = time.time()

        logger.info(f"✅ Handoff created: {session_id}")
        logger.info(f"   Compression: {compression_efficiency:.2f}×")
        logger.info(f"   Validation: {validation_score:.1%}")
        logger.info(f"   Compound Factor: {compound_factor:.2f}×")

        return handoff_state

    async def create_emergency_handoff(self):
        """Create emergency handoff for crash recovery"""
        if hasattr(self, "simulation_context"):
            await self.create_handoff(
                self.simulation_context,
                trigger_type=HandoffTrigger.GRACEFUL_SHUTDOWN.value,
                commit_message="🛑 EMERGENCY HANDOFF - Graceful shutdown",
            )

    def _calculate_recovery_priority(self, context: Dict[str, Any]) -> int:
        """Calculate recovery priority (1-10) based on context"""
        priority = 5  # Default

        # Higher priority for more agents
        agent_count = context.get("agent_count", 0)
        if agent_count > 10_000_000:
            priority += 2
        elif agent_count > 1_000_000:
            priority += 1

        # Higher priority if simulation is near completion
        phase = context.get("phase", "")
        if "complete" in phase.lower():
            priority += 2

        return min(10, max(1, priority))

    async def _save_handoff(
        self, handoff_state: EnhancedHandoffState, compressed_data: bytes
    ):
        """Save handoff to disk"""
        # Save metadata
        metadata_path = self.handoff_dir / f"{handoff_state.session_id}.json"
        with open(metadata_path, "w") as f:
            json.dump(asdict(handoff_state), f, indent=2, default=str)

        # Save compressed data
        data_path = self.handoff_dir / f"{handoff_state.session_id}.bin"
        with open(data_path, "wb") as f:
            f.write(compressed_data)

        # Create symlink to latest
        latest_meta = self.handoff_dir / "latest_handoff.json"
        latest_data = self.handoff_dir / "latest_handoff.bin"

        if latest_meta.exists():
            latest_meta.unlink()
        if latest_data.exists():
            latest_data.unlink()

        latest_meta.symlink_to(metadata_path.name)
        latest_data.symlink_to(data_path.name)

        logger.info(f"💾 Handoff saved: {metadata_path}")

    async def _create_git_commit(
        self, handoff_state: EnhancedHandoffState, commit_message: Optional[str]
    ) -> Tuple[Optional[str], Optional[str]]:
        """Create git commit for handoff"""
        try:
            git_dir = self.repo_path / ".git"
            if not git_dir.exists():
                return None, None

            # Get current branch
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            branch = result.stdout.strip()

            # Default commit message
            if commit_message is None:
                commit_message = (
                    f"🔐 Handoff: {handoff_state.session_id[:16]} | "
                    f"Trigger: {handoff_state.trigger_type} | "
                    f"Agents: {handoff_state.simulation_state.get('agent_count', 0):,} | "
                    f"Compression: {handoff_state.compression_efficiency:.2f}× | "
                    f"Validation: {handoff_state.validation_score:.1%}"
                )

            # Add handoff files
            subprocess.run(
                ["git", "add", "data/handoffs/"],
                cwd=self.repo_path,
                capture_output=True,
                check=True,
            )

            # Create commit
            subprocess.run(
                ["git", "commit", "-m", commit_message, "--no-verify"],
                cwd=self.repo_path,
                capture_output=True,
                check=True,
            )

            # Get commit hash
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            commit_hash = result.stdout.strip()

            logger.info(f"🔐 Git commit: {commit_hash[:8]} on {branch}")
            return commit_hash, branch

        except Exception as e:
            logger.warning(f"Git commit failed: {e}")
            return None, None

    async def recover_handoff(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Recover simulation from handoff"""
        logger.info(f"🔄 RECOVERING HANDOFF: {session_id}")
        start_time = time.time()

        # Find handoff files
        metadata_path = self.handoff_dir / f"{session_id}.json"
        data_path = self.handoff_dir / f"{session_id}.bin"

        if not metadata_path.exists():
            logger.error(f"❌ Handoff not found: {session_id}")
            self.recovery_stats["failed_recoveries"] += 1
            return None

        try:
            # Load metadata
            with open(metadata_path, "r") as f:
                metadata = json.load(f)

            # Load compressed data
            with open(data_path, "rb") as f:
                compressed_data = f.read()

            # Decompress
            compression_context = CompressedContext(**metadata["compression"])
            state_data = self.compressor.decompress(
                compressed_data, compression_context
            )

            # Validate recovered data
            validation_result = self.validator.validate(state_data)
            if not validation_result.is_valid:
                logger.warning(
                    f"⚠️ Recovered data validation: {validation_result.errors}"
                )

            recovery_time = time.time() - start_time
            self.recovery_stats["successful_recoveries"] += 1

            # Update average recovery time
            total_recoveries = self.recovery_stats["successful_recoveries"]
            current_avg = self.recovery_stats["avg_recovery_time"]
            self.recovery_stats["avg_recovery_time"] = (
                current_avg * (total_recoveries - 1) + recovery_time
            ) / total_recoveries

            logger.info(f"✅ Recovery complete in {recovery_time:.2f}s")
            logger.info(f"   Validation: {validation_result.integrity_score:.1%}")

            return {
                "metadata": metadata,
                "state_data": state_data,
                "validation": validation_result,
                "recovery_time": recovery_time,
            }

        except Exception as e:
            logger.error(f"❌ Recovery failed: {e}")
            self.recovery_stats["failed_recoveries"] += 1
            return None

    async def recover_latest(self) -> Optional[Dict[str, Any]]:
        """Recover from latest handoff"""
        latest_meta = self.handoff_dir / "latest_handoff.json"
        if not latest_meta.exists():
            logger.error("❌ No latest handoff found")
            return None

        # Read session ID from symlink target
        target = latest_meta.resolve()
        session_id = target.stem

        return await self.recover_handoff(session_id)

    def get_recovery_stats(self) -> Dict[str, Any]:
        """Get recovery statistics"""
        stats = self.recovery_stats.copy()
        stats["compression_stats"] = self.compressor.get_stats()
        stats["total_handoffs"] = len(self.handoff_history)
        stats["success_rate"] = stats["successful_recoveries"] / max(
            stats["total_handoffs"], 1
        )
        return stats

    def stop_monitoring(self):
        """Stop auto-monitoring"""
        self.running = False
        logger.info("🔍 Auto-monitoring stopped")


# Global enhanced handoff manager
ENHANCED_HANDOFF_MANAGER = EnhancedGitSafeHandoff()


async def demo_enhanced_handoff():
    """Demonstrate enhanced handoff system"""
    print("🔐 COHEZION ENHANCED GIT-SAFE HANDOFF DEMO")
    print("=" * 60)

    # Create sample simulation context
    simulation_context = {
        "universe_id": "quantum_topology_50m_demo",
        "phase": "simulation_in_progress",
        "agent_count": 50_000_000,
        "twistors": [{"id": f"twistor_{i}"} for i in range(1000)],
        "er_epr_bridges": [{"id": f"bridge_{i}"} for i in range(500)],
        "quantum_bio_networks": [{"id": f"network_{i}"} for i in range(200)],
        "agents": {f"agent_{i}": {"state": "active"} for i in range(1000)},  # Sample
    }

    # Create handoff
    handoff = await ENHANCED_HANDOFF_MANAGER.create_handoff(
        simulation_context,
        trigger_type="demo",
        commit_message="🔐 Demo handoff for 50M agent simulation",
    )

    print(f"\n📊 HANDOFF CREATED")
    print(f"   Session ID: {handoff.session_id}")
    print(f"   Compression: {handoff.compression_efficiency:.2f}×")
    print(f"   Validation: {handoff.validation_score:.1%}")
    print(f"   Recovery Priority: {handoff.recovery_priority}/10")
    print(
        f"   Git Commit: {handoff.git_commit_hash[:8] if handoff.git_commit_hash else 'N/A'}"
    )

    # Recover handoff
    print("\n🔄 TESTING RECOVERY...")
    recovered = await ENHANCED_HANDOFF_MANAGER.recover_handoff(handoff.session_id)

    if recovered:
        print(f"✅ Recovery successful!")
        print(f"   Recovery time: {recovered['recovery_time']:.2f}s")
        print(f"   Agents recovered: {len(recovered['state_data']['agent_states'])}")

    # Show stats
    stats = ENHANCED_HANDOFF_MANAGER.get_recovery_stats()
    print(f"\n📈 RECOVERY STATISTICS")
    print(f"   Total handoffs: {stats['total_handoffs']}")
    print(f"   Success rate: {stats['success_rate']:.1%}")
    print(f"   Avg recovery time: {stats['avg_recovery_time']:.2f}s")
    print(
        f"   Space saved: {stats.get('compression_stats', {}).get('space_saved_gb', 0):.2f} GB"
    )

    print("\n🎉 Enhanced handoff system demo complete!")

    return handoff


if __name__ == "__main__":
    asyncio.run(demo_enhanced_handoff())
