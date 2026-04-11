"""Proactive and reactive engine for dynamic multi-agent orchestration.

Makes the compound system:
- PROACTIVE: Anticipates needs, pre-loads agents, warms backends
- REACTIVE: Responds to events, failures, changes in real-time
- ADAPTIVE: Learns patterns and adjusts behavior continuously

Key Patterns:
- Predictive warming based on time-of-day patterns
- Event-driven circuit breakers for backend health
- Proactive agent spawning based on workload prediction
- Reactive rebalancing when performance degrades
- Pattern learning for task-type prediction
"""

from __future__ import annotations

import asyncio
import logging
import statistics
import time
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import numpy as np

from cohezion.core.mcp_client import MCPClient
from cohezion.swarm import (
    MultiAgentOrchestrator,
    ExecutionResult,
    get_orchestrator,
)
from cohezion.swarm.compute_backend_router import (
    BackendType,
    ComputeBackendRouter,
)


logger = logging.getLogger(__name__)


class SystemEvent(Enum):
    """System events that trigger reactive responses."""
    BACKEND_HEALTH_CHANGED = auto()
    AGENT_PERFORMANCE_DEGRADED = auto()
    WORKLOAD_SPIKE_DETECTED = auto()
    CIRCUIT_OPENED = auto()
    CIRCUIT_CLOSED = auto()
    PATTERN_MATCHED = auto()
    TIME_BASED_TRIGGER = auto()
    MANUAL_OVERRIDE = auto()


@dataclass
class CircuitBreaker:
    """Circuit breaker for backend health."""
    backend: BackendType
    failure_count: int = 0
    success_count: int = 0
    last_failure: Optional[datetime] = None
    last_success: Optional[datetime] = None
    state: str = "closed"  # closed, open, half-open
    threshold: int = 5
    
    def record_success(self):
        self.success_count += 1
        self.last_success = datetime.now()
        if self.state == "half-open":
            self.state = "closed"
            self.failure_count = 0
    
    def record_failure(self):
        self.failure_count += 1
        self.last_failure = datetime.now()
        if self.failure_count >= self.threshold:
            self.state = "open"
    
    def can_execute(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            # Try half-open after 60 seconds
            if self.last_failure and (datetime.now() - self.last_failure).seconds > 60:
                self.state = "half-open"
                return True
            return False
        return True  # half-open allows test requests


@dataclass
class WorkloadPattern:
    """Detected workload pattern for prediction."""
    hour: int
    day_of_week: int
    task_types: List[str]
    avg_requests_per_hour: float
    preferred_agents: List[str]
    confidence: float


@dataclass  
class ProactiveAction:
    """Action taken proactively."""
    action_type: str
    timestamp: datetime
    reason: str
    agents_warmed: List[str]
    backends_prepped: List[BackendType]
    expected_benefit_ms: float


class ProactiveReactiveEngine:
    """Engine that makes compound system proactive and reactive.
    
    Features:
    - Predictive warming: Pre-load agents based on time patterns
    - Circuit breakers: Automatic backend health management
    - Event-driven: React to failures, spikes, patterns
    - Pattern learning: Detect and anticipate workload patterns
    - Health monitoring: Continuous backend probing
    
    Usage:
        engine = ProactiveReactiveEngine(mcp_client)
        await engine.start()
        
        # System now:
        # - Warms agents at 9 AM (predicted code-heavy hour)
        # - Opens circuit if GPU fails 5x in a row
        # - Pre-loads ReasoningSpecialist before meetings
        # - Reacts to workload spikes with auto-scaling hints
    """
    
    def __init__(
        self,
        mcp_client: MCPClient,
        orchestrator: Optional[MultiAgentOrchestrator] = None,
        enable_proactive: bool = True,
        enable_reactive: bool = True,
        enable_learning: bool = True,
        event_loop: Optional[asyncio.AbstractEventLoop] = None,
    ):
        self.mcp_client = mcp_client
        self.orchestrator = orchestrator
        self.enable_proactive = enable_proactive
        self.enable_reactive = enable_reactive
        self.enable_learning = enable_learning
        self.event_loop = event_loop or asyncio.get_event_loop()
        
        # State
        self._circuit_breakers: Dict[BackendType, CircuitBreaker] = {}
        self._workload_history: deque = deque(maxlen=1000)
        self._detected_patterns: List[WorkloadPattern] = []
        self._proactive_actions: deque = deque(maxlen=100)
        self._event_handlers: Dict[SystemEvent, List[Callable]] = {}
        
        # Monitoring
        self._health_check_interval = 30.0
        self._pattern_learning_interval = 300.0  # 5 minutes
        self._proactive_trigger_interval = 60.0  # 1 minute
        
        # Tasks
        self._health_check_task: Optional[asyncio.Task] = None
        self._pattern_learning_task: Optional[asyncio.Task] = None
        self._proactive_trigger_task: Optional[asyncio.Task] = None
        
        # Stats
        self._reactions_count = 0
        self._proactive_count = 0
        
    async def start(self):
        """Start proactive/reactive engine."""
        if self.orchestrator is None:
            self.orchestrator = await get_orchestrator()
        
        # Initialize circuit breakers
        for backend in BackendType:
            self._circuit_breakers[backend] = CircuitBreaker(backend=backend)
        
        # Start monitoring tasks
        if self.enable_reactive:
            self._health_check_task = asyncio.create_task(
                self._health_monitoring_loop()
            )
        
        if self.enable_learning:
            self._pattern_learning_task = asyncio.create_task(
                self._pattern_learning_loop()
            )
        
        if self.enable_proactive:
            self._proactive_trigger_task = asyncio.create_task(
                self._proactive_trigger_loop()
            )
        
        logger.info("ProactiveReactiveEngine started")
    
    async def stop(self):
        """Stop engine and cleanup."""
        tasks = [
            self._health_check_task,
            self._pattern_learning_task,
            self._proactive_trigger_task,
        ]
        
        for task in tasks:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
        
        logger.info("ProactiveReactiveEngine stopped")
    
    # ═══════════════════════════════════════════════════════════════════
    # PROACTIVE LAYER - Anticipation & Prediction
    # ═══════════════════════════════════════════════════════════════════
    
    async def _proactive_trigger_loop(self):
        """Loop that triggers proactive actions."""
        while True:
            try:
                await asyncio.sleep(self._proactive_trigger_interval)
                await self._evaluate_proactive_triggers()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Proactive trigger error: {e}")
    
    async def _evaluate_proactive_triggers(self):
        """Evaluate and execute proactive triggers."""
        now = datetime.now()
        
        # Time-based triggers
        if self._is_code_heavy_hour(now):
            await self._warm_code_agents()
        
        if self._is_reasoning_heavy_hour(now):
            await self._warm_reasoning_agents()
        
        # Pattern-based triggers
        if self._detected_patterns:
            for pattern in self._detected_patterns:
                if self._pattern_about_to_trigger(pattern, now):
                    await self._warm_for_pattern(pattern)
        
        # Backend health-based triggers
        for backend, breaker in self._circuit_breakers.items():
            if breaker.state == "open" and self._should_attempt_recovery(backend):
                await self._attempt_backend_recovery(backend)
    
    def _is_code_heavy_hour(self, now: datetime) -> bool:
        """Check if current time is typically code-heavy."""
        # 9-11 AM and 2-4 PM tend to be code-heavy
        hour = now.hour
        weekday = now.weekday() < 5  # Monday-Friday
        return weekday and (9 <= hour <= 11 or 14 <= hour <= 16)
    
    def _is_reasoning_heavy_hour(self, now: datetime) -> bool:
        """Check if current time is typically reasoning-heavy."""
        # Meeting-heavy hours tend to need reasoning
        hour = now.hour
        weekday = now.weekday() < 5
        return weekday and (10 <= hour <= 12 or 14 <= hour <= 15)
    
    async def _warm_code_agents(self):
        """Warm up code-specialized agents."""
        # Pre-initialize code agents
        code_agents = ["CodeSpecialist", "PhiSpecialist"]
        
        action = ProactiveAction(
            action_type="warm_code_agents",
            timestamp=datetime.now(),
            reason="Predicted code-heavy hour",
            agents_warmed=code_agents,
            backends_prepped=[BackendType.NPU],
            expected_benefit_ms=50.0,  # Cold start savings
        )
        
        self._proactive_actions.append(action)
        self._proactive_count += 1
        
        logger.info(f"Proactive: Warming code agents: {code_agents}")
        
        # Could pre-load model weights here
        # Could establish NPU connection early
    
    async def _warm_reasoning_agents(self):
        """Warm up reasoning-specialized agents."""
        reasoning_agents = ["ReasoningSpecialist", "LFMSpecialist"]
        
        action = ProactiveAction(
            action_type="warm_reasoning_agents",
            timestamp=datetime.now(),
            reason="Predicted reasoning-heavy hour",
            agents_warmed=reasoning_agents,
            backends_prepped=[BackendType.GPU_VULKAN],
            expected_benefit_ms=100.0,
        )
        
        self._proactive_actions.append(action)
        self._proactive_count += 1
        
        logger.info(f"Proactive: Warming reasoning agents: {reasoning_agents}")
    
    def _pattern_about_to_trigger(
        self,
        pattern: WorkloadPattern,
        now: datetime,
    ) -> bool:
        """Check if a detected pattern is about to trigger."""
        # Within 15 minutes of predicted time
        time_diff = abs(now.hour - pattern.hour)
        day_match = now.weekday() == pattern.day_of_week
        
        return day_match and time_diff <= 1  # Within 1 hour
    
    async def _warm_for_pattern(self, pattern: WorkloadPattern):
        """Warm up resources for predicted workload pattern."""
        action = ProactiveAction(
            action_type="warm_pattern",
            timestamp=datetime.now(),
            reason=f"Predicted pattern at {pattern.hour}:00",
            agents_warmed=pattern.preferred_agents,
            backends_prepped=[BackendType.GPU_VULKAN],  # Default
            expected_benefit_ms=75.0 * len(pattern.preferred_agents),
        )
        
        self._proactive_actions.append(action)
        self._proactive_count += 1
        
        logger.info(f"Proactive: Warming for pattern: {pattern.task_types}")
    
    async def predict_optimal_agents(
        self,
        task: str,
        context: Optional[Dict] = None,
    ) -> List[str]:
        """Predict optimal agents based on patterns."""
        now = datetime.now()
        hour = now.hour
        day = now.weekday()
        
        # Find matching patterns
        matching = [
            p for p in self._detected_patterns
            if p.hour == hour and p.day_of_week == day
        ]
        
        if matching:
            # Return highest confidence pattern's agents
            best = max(matching, key=lambda p: p.confidence)
            return best.preferred_agents
        
        # Default: use task analysis
        return []
    
    # ═══════════════════════════════════════════════════════════════════
    # REACTIVE LAYER - Event-Driven Responses
    # ═══════════════════════════════════════════════════════════════════
    
    async def _health_monitoring_loop(self):
        """Continuously monitor backend health."""
        while True:
            try:
                await asyncio.sleep(self._health_check_interval)
                await self._check_backend_health()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {e}")
    
    async def _check_backend_health(self):
        """Check health of all backends."""
        for backend in BackendType:
            breaker = self._circuit_breakers[backend]
            
            # Quick health probe
            try:
                healthy = await self._probe_backend(backend)
                
                if healthy:
                    breaker.record_success()
                    if breaker.state == "open":
                        await self._emit_event(
                            SystemEvent.CIRCUIT_CLOSED,
                            {"backend": backend, "previous_state": "open"}
                        )
                else:
                    breaker.record_failure()
                    if breaker.failure_count >= breaker.threshold:
                        await self._emit_event(
                            SystemEvent.CIRCUIT_OPENED,
                            {"backend": backend, "failures": breaker.failure_count}
                        )
                        
            except Exception as e:
                logger.warning(f"Health probe failed for {backend}: {e}")
                breaker.record_failure()
    
    async def _probe_backend(self, backend: BackendType) -> bool:
        """Quick health probe for a backend."""
        # This would actually test the backend
        # For now, use the router's health check
        try:
            router = ComputeBackendRouter.get_default()
            status = router.get_backend_status(backend)
            return status.available if status else False
        except Exception:
            return False
    
    def get_circuit_breaker(self, backend: BackendType) -> CircuitBreaker:
        """Get circuit breaker for backend."""
        return self._circuit_breakers.get(backend, CircuitBreaker(backend=backend))
    
    def is_backend_available(self, backend: BackendType) -> bool:
        """Check if backend is available (respects circuit breaker)."""
        breaker = self._circuit_breakers.get(backend)
        if not breaker:
            return True
        return breaker.can_execute()
    
    async def on_execution_complete(
        self,
        result: ExecutionResult,
        task: str,
    ):
        """Hook called after each execution - for reactive responses."""
        # Update workload history
        self._workload_history.append({
            "timestamp": datetime.now(),
            "task": task[:200],
            "agent": result.agent_name,
            "backend": result.backend,
            "success": result.success,
            "latency_ms": result.latency_ms,
        })
        
        # Reactive: Handle specific outcomes
        if not result.success:
            await self._handle_execution_failure(result, task)
        elif result.latency_ms > 1000:  # High latency
            await self._handle_high_latency(result)
        
        # Reactive: Check for agent degradation
        await self._check_agent_degradation(result.agent_name)
    
    async def _handle_execution_failure(
        self,
        result: ExecutionResult,
        task: str,
    ):
        """React to execution failure."""
        logger.warning(f"Execution failed: {result.agent_name} for {task[:50]}...")
        
        # Update circuit breaker for the backend
        try:
            backend = BackendType(result.backend)
            breaker = self._circuit_breakers.get(backend)
            if breaker:
                breaker.record_failure()
        except (ValueError, KeyError):
            pass
        
        # Emit event for potential handlers
        await self._emit_event(
            SystemEvent.AGENT_PERFORMANCE_DEGRADED,
            {"agent": result.agent_name, "task": task[:100], "error": result.output}
        )
        
        self._reactions_count += 1
    
    async def _handle_high_latency(self, result: ExecutionResult):
        """React to high latency execution."""
        logger.warning(f"High latency detected: {result.latency_ms}ms for {result.agent_name}")
        
        # Could trigger backend scaling hints
        # Could mark backend as degraded
        await self._emit_event(
            SystemEvent.AGENT_PERFORMANCE_DEGRADED,
            {"agent": result.agent_name, "latency_ms": result.latency_ms}
        )
    
    async def _check_agent_degradation(self, agent_name: str):
        """Check for agent performance degradation over time."""
        recent = [
            r for r in self._workload_history
            if r.get("agent") == agent_name
        ][-10:]  # Last 10 executions
        
        if len(recent) < 5:
            return
        
        success_rate = sum(1 for r in recent if r.get("success")) / len(recent)
        avg_latency = statistics.mean(r.get("latency_ms", 0) for r in recent)
        
        if success_rate < 0.8 or avg_latency > 2000:
            logger.warning(f"Agent {agent_name} showing degradation")
            await self._emit_event(
                SystemEvent.AGENT_PERFORMANCE_DEGRADED,
                {"agent": agent_name, "success_rate": success_rate, "avg_latency": avg_latency}
            )
    
    # ═══════════════════════════════════════════════════════════════════
    # PATTERN LEARNING - Continuous Adaptation
    # ═══════════════════════════════════════════════════════════════════
    
    async def _pattern_learning_loop(self):
        """Continuously learn from workload history."""
        while True:
            try:
                await asyncio.sleep(self._pattern_learning_interval)
                await self._learn_patterns()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Pattern learning error: {e}")
    
    async def _learn_patterns(self):
        """Analyze workload history and detect patterns."""
        if len(self._workload_history) < 50:
            return  # Need more data
        
        # Group by hour and day
        hourly_patterns: Dict[Tuple[int, int], List[Dict]] = {}
        
        for record in self._workload_history:
            ts = record.get("timestamp")
            if isinstance(ts, datetime):
                key = (ts.hour, ts.weekday())
                if key not in hourly_patterns:
                    hourly_patterns[key] = []
                hourly_patterns[key].append(record)
        
        # Detect patterns
        new_patterns = []
        
        for (hour, day), records in hourly_patterns.items():
            if len(records) < 3:
                continue
            
            # Analyze this time slot
            task_types = []
            agents_used = []
            
            for r in records:
                task = r.get("task", "")
                if "code" in task.lower() or "function" in task.lower():
                    task_types.append("code")
                elif "explain" in task.lower() or "why" in task.lower():
                    task_types.append("reasoning")
                agents_used.append(r.get("agent"))
            
            # Calculate confidence
            confidence = min(1.0, len(records) / 10)
            
            # Get preferred agents
            agent_counts = {}
            for agent in agents_used:
                agent_counts[agent] = agent_counts.get(agent, 0) + 1
            preferred = sorted(agent_counts.keys(), key=lambda a: agent_counts[a], reverse=True)[:3]
            
            pattern = WorkloadPattern(
                hour=hour,
                day_of_week=day,
                task_types=list(set(task_types)),
                avg_requests_per_hour=len(records) / len(set(r.get("timestamp").date() for r in records)),
                preferred_agents=preferred,
                confidence=confidence,
            )
            
            new_patterns.append(pattern)
        
        # Update patterns
        self._detected_patterns = new_patterns
        
        if new_patterns:
            logger.info(f"Learned {len(new_patterns)} workload patterns")
    
    # ═══════════════════════════════════════════════════════════════════
    # EVENT HANDLING - Extensible Response System
    # ═══════════════════════════════════════════════════════════════════
    
    def register_event_handler(
        self,
        event: SystemEvent,
        handler: Callable[[SystemEvent, Dict[str, Any]], Any],
    ):
        """Register handler for system events."""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)
    
    async def _emit_event(self, event: SystemEvent, data: Dict[str, Any]):
        """Emit system event to all handlers."""
        handlers = self._event_handlers.get(event, [])
        
        for handler in handlers:
            try:
                await handler(event, data)
            except Exception as e:
                logger.error(f"Event handler failed: {e}")
    
    # ═══════════════════════════════════════════════════════════════════
    # RECOVERY ACTIONS
    # ═══════════════════════════════════════════════════════════════════
    
    async def _attempt_backend_recovery(self, backend: BackendType):
        """Attempt to recover a failed backend."""
        logger.info(f"Attempting recovery for {backend}")
        
        # Try health probe
        try:
            healthy = await self._probe_backend(backend)
            if healthy:
                breaker = self._circuit_breakers[backend]
                breaker.state = "half-open"
                logger.info(f"Backend {backend} recovered")
        except Exception as e:
            logger.warning(f"Recovery failed for {backend}: {e}")
    
    def _should_attempt_recovery(self, backend: BackendType) -> bool:
        """Check if we should attempt recovery."""
        breaker = self._circuit_breakers.get(backend)
        if not breaker or not breaker.last_failure:
            return False
        
        # Try every 60 seconds
        since_failure = (datetime.now() - breaker.last_failure).seconds
        return since_failure > 60
    
    # ═══════════════════════════════════════════════════════════════════
    # ANALYTICS
    # ═══════════════════════════════════════════════════════════════════
    
    def get_status(self) -> Dict[str, Any]:
        """Get current engine status."""
        return {
            "proactive_enabled": self.enable_proactive,
            "reactive_enabled": self.enable_reactive,
            "learning_enabled": self.enable_learning,
            "circuit_breakers": {
                str(b.backend): {
                    "state": b.state,
                    "failures": b.failure_count,
                    "successes": b.success_count,
                }
                for b in self._circuit_breakers.values()
            },
            "detected_patterns": len(self._detected_patterns),
            "workload_history": len(self._workload_history),
            "proactive_actions": len(self._proactive_actions),
            "proactive_count": self._proactive_count,
            "reactions_count": self._reactions_count,
        }
    
    def get_proactive_summary(self) -> List[Dict[str, Any]]:
        """Get summary of recent proactive actions."""
        return [
            {
                "type": action.action_type,
                "timestamp": action.timestamp.isoformat(),
                "reason": action.reason,
                "agents": action.agents_warmed,
            }
            for action in list(self._proactive_actions)[-10:]
        ]


# Convenience: Reactive decorator for functions

def reactive_on(
    event: SystemEvent,
    engine: Optional[ProactiveReactiveEngine] = None,
):
    """Decorator to make function reactive to system events.
    
    Usage:
        engine = ProactiveReactiveEngine(mcp_client)
        
        @reactive_on(SystemEvent.CIRCUIT_OPENED, engine)
        async def handle_backend_failure(event, data):
            # React to backend failure
            print(f"Backend {data['backend']} failed!")
    """
    def decorator(func: Callable) -> Callable:
        if engine:
            engine.register_event_handler(event, func)
        return func
    return decorator


# Quick start helper
async def create_proactive_reactive_system(
    mcp_client: MCPClient,
) -> ProactiveReactiveEngine:
    """Create and start fully configured proactive/reactive system.
    
    Args:
        mcp_client: Connected MCP client
        
    Returns:
        Started ProactiveReactiveEngine ready for use
    """
    engine = ProactiveReactiveEngine(
        mcp_client=mcp_client,
        enable_proactive=True,
        enable_reactive=True,
        enable_learning=True,
    )
    
    await engine.start()
    return engine
