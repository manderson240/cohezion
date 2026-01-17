"""
Agent Journey Tracker - Record agent thought trajectories in 12D physics space.

Tracks:
- Agent activations (analyst, critic, synthesizer)
- Thought vectors at each step
- Physics state evolution
- Critique/resolution events
"""

import time
import json
from dataclasses import dataclass, asdict, field
from datetime import datetime, UTC
from pathlib import Path
from typing import Any
from enum import Enum


class AgentType(Enum):
    ANALYST = "analyst"
    CRITIC = "critic"
    SYNTHESIZER = "synthesizer"


@dataclass
class JourneyStep:
    """A single step in an agent's journey."""
    timestamp: str
    agent_type: str
    agent_name: str
    perspective: str | None
    input_summary: str
    output_summary: str
    physics_state: dict[str, float]
    duration_ms: float
    confidence: float
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass 
class AgentJourney:
    """Complete journey of a debate/query through the agent swarm."""
    journey_id: str
    query: str
    started_at: str
    steps: list[JourneyStep] = field(default_factory=list)
    final_response: str | None = None
    total_duration_ms: float = 0.0
    final_confidence: float = 0.0
    
    def add_step(self, step: JourneyStep) -> None:
        self.steps.append(step)
        self.total_duration_ms += step.duration_ms
    
    def to_dict(self) -> dict:
        return {
            "journey_id": self.journey_id,
            "query": self.query,
            "started_at": self.started_at,
            "steps": [s.to_dict() for s in self.steps],
            "final_response": self.final_response,
            "total_duration_ms": self.total_duration_ms,
            "final_confidence": self.final_confidence,
            "step_count": len(self.steps),
        }


class JourneyTracker:
    """
    Tracks agent journeys through the swarm.
    
    Records:
    - Step-by-step agent activations
    - Physics state at each step
    - Saves to universe_nodes for visualization
    """
    
    def __init__(self, output_dir: Path | None = None):
        self.output_dir = output_dir or Path("src/cohezion/knowledge_graph/universe_nodes/journeys")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._current_journey: AgentJourney | None = None
        self._journeys: list[AgentJourney] = []
    
    def start_journey(self, query: str) -> str:
        """Start tracking a new journey."""
        journey_id = f"journey_{int(time.time() * 1000)}"
        self._current_journey = AgentJourney(
            journey_id=journey_id,
            query=query,
            started_at=datetime.now(UTC).isoformat(),
        )
        return journey_id
    
    def record_step(
        self,
        agent_type: AgentType,
        agent_name: str,
        perspective: str | None,
        input_text: str,
        output_text: str,
        physics_state: dict[str, float],
        duration_ms: float,
        confidence: float = 0.0,
    ) -> None:
        """Record a step in the current journey."""
        if not self._current_journey:
            return
        
        step = JourneyStep(
            timestamp=datetime.now(UTC).isoformat(),
            agent_type=agent_type.value,
            agent_name=agent_name,
            perspective=perspective,
            input_summary=input_text[:200] + "..." if len(input_text) > 200 else input_text,
            output_summary=output_text[:200] + "..." if len(output_text) > 200 else output_text,
            physics_state=physics_state,
            duration_ms=duration_ms,
            confidence=confidence,
        )
        self._current_journey.add_step(step)
    
    def end_journey(self, final_response: str, final_confidence: float) -> AgentJourney:
        """Complete the current journey and save it."""
        if not self._current_journey:
            raise ValueError("No active journey")
        
        self._current_journey.final_response = final_response
        self._current_journey.final_confidence = final_confidence
        
        # Save to file
        journey_file = self.output_dir / f"{self._current_journey.journey_id}.json"
        with open(journey_file, "w") as f:
            json.dump(self._current_journey.to_dict(), f, indent=2)
        
        self._journeys.append(self._current_journey)
        completed = self._current_journey
        self._current_journey = None
        return completed
    
    def get_recent_journeys(self, limit: int = 10) -> list[dict]:
        """Get recent journeys for visualization."""
        journey_files = sorted(self.output_dir.glob("*.json"), reverse=True)[:limit]
        journeys = []
        for f in journey_files:
            try:
                journeys.append(json.loads(f.read_text()))
            except:
                pass
        return journeys
    
    def get_journey_trajectory(self, journey_id: str) -> list[dict]:
        """Get physics trajectory for a specific journey."""
        journey_file = self.output_dir / f"{journey_id}.json"
        if not journey_file.exists():
            return []
        
        journey = json.loads(journey_file.read_text())
        return [
            {
                "step": i,
                "agent": step["agent_name"],
                "physics": step["physics_state"],
            }
            for i, step in enumerate(journey.get("steps", []))
        ]


# Singleton
_tracker: JourneyTracker | None = None


def get_journey_tracker() -> JourneyTracker:
    global _tracker
    if _tracker is None:
        _tracker = JourneyTracker()
    return _tracker
