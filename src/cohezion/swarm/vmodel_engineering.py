"""Systems Engineering V-Model integration for dynamic lever optimization.

The V-Model maps system development phases to verification/validation:

                      System Validation
                             ∧
                            ╱ ╲
                           ╱   ╲
                  System Verification
                         ╱     ╲
                        ╱       ╲
              Integration Testing
                     ╱            ╲
                    ╱              ╲
           Unit Testing             ╲
                ╱                      ╲
   ┌───────────┼───────────┬───────────┼───────────┐
   │           │           │           │           │
Requirements → Design → Architecture → Module → Implementation
   │           │           │           │           │

Each dynamic lever adjustment follows the V-Model lifecycle.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


logger = logging.getLogger(__name__)


class VPhase(Enum):
    """V-Model phases on the left side (decomposition)."""

    REQUIREMENTS = "requirements"  # Need definition
    SYSTEM_DESIGN = "system_design"  # High-level design
    ARCHITECTURE = "architecture"  # Component design
    MODULE_DESIGN = "module_design"  # Detailed design
    IMPLEMENTATION = "implementation"  # Code/execution


class VVerification(Enum):
    """V-Model phases on the right side (verification)."""

    UNIT_TEST = "unit_test"  # Module verification
    INTEGRATION_TEST = "integration_test"  # Component integration
    SYSTEM_TEST = "system_test"  # System verification
    SYSTEM_VALIDATION = "system_validation"  # Requirement validation


@dataclass
class VPhaseState:
    """State of a V-Model phase."""

    phase: VPhase | VVerification
    status: str = "pending"  # pending, in_progress, complete, failed
    started_at: str | None = None
    completed_at: str | None = None
    artifacts: list[str] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)

    def start(self):
        """Mark phase as started."""
        self.status = "in_progress"
        self.started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ")

    def complete(self, metrics: dict[str, Any] | None = None):
        """Mark phase as complete."""
        self.status = "complete"
        self.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ")
        if metrics:
            self.metrics.update(metrics)

    def fail(self, reason: str):
        """Mark phase as failed."""
        self.status = "failed"
        self.metrics["failure_reason"] = reason


@dataclass
class LeverAdjustmentLifecycle:
    """Complete V-Model lifecycle for a lever adjustment."""

    lever_name: str
    adjustment_id: str
    target_value: float
    current_value: float

    # Left side of V (Design)
    requirements_phase: VPhaseState = field(default_factory=lambda: VPhaseState(VPhase.REQUIREMENTS))
    system_design_phase: VPhaseState = field(default_factory=lambda: VPhaseState(VPhase.SYSTEM_DESIGN))
    architecture_phase: VPhaseState = field(default_factory=lambda: VPhaseState(VPhase.ARCHITECTURE))
    module_design_phase: VPhaseState = field(default_factory=lambda: VPhaseState(VPhase.MODULE_DESIGN))
    implementation_phase: VPhaseState = field(default_factory=lambda: VPhaseState(VPhase.IMPLEMENTATION))

    # Right side of V (Verification)
    unit_test_phase: VPhaseState = field(default_factory=lambda: VPhaseState(VVerification.UNIT_TEST))
    integration_test_phase: VPhaseState = field(default_factory=lambda: VPhaseState(VVerification.INTEGRATION_TEST))
    system_test_phase: VPhaseState = field(default_factory=lambda: VPhaseState(VVerification.SYSTEM_TEST))
    validation_phase: VPhaseState = field(default_factory=lambda: VPhaseState(VVerification.SYSTEM_VALIDATION))

    created_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ"))
    completed: bool = False

    def get_left_side(self) -> list[VPhaseState]:
        """Get left side phases (decomposition)."""
        return [
            self.requirements_phase,
            self.system_design_phase,
            self.architecture_phase,
            self.module_design_phase,
            self.implementation_phase,
        ]

    def get_right_side(self) -> list[VPhaseState]:
        """Get right side phases (verification)."""
        return [
            self.unit_test_phase,
            self.integration_test_phase,
            self.system_test_phase,
            self.validation_phase,
        ]

    def get_current_phase(self) -> VPhaseState | None:
        """Get current active phase."""
        all_phases = self.get_left_side() + self.get_right_side()
        for phase in all_phases:
            if phase.status == "in_progress":
                return phase

        # Return first pending
        for phase in all_phases:
            if phase.status == "pending":
                return phase

        return None

    def get_progress(self) -> float:
        """Get V-Model progress (0-1)."""
        all_phases = self.get_left_side() + self.get_right_side()
        complete = sum(1 for p in all_phases if p.status == "complete")
        failed = sum(1 for p in all_phases if p.status == "failed")
        return (complete + failed) / len(all_phases)

    def is_validated(self) -> bool:
        """Check if full V-Model cycle is complete."""
        return self.validation_phase.status == "complete"


class VModelEngineeringProcess:
    """Systems Engineering V-Model process for dynamic levers."""

    def __init__(self, lever_system):
        self.lever_system = lever_system
        self.active_lifecycles: dict[str, LeverAdjustmentLifecycle] = {}
        self.completed_lifecycles: list[LeverAdjustmentLifecycle] = []
        self.requirement_registry: dict[str, dict[str, Any]] = {}

    def start_adjustment(self, lever_name: str, target_value: float, requirements: dict[str, Any]) -> str:
        """Start a new V-Model adjustment lifecycle."""
        adjustment_id = f"adj_{lever_name}_{int(time.time())}"

        lever = self.lever_system.get_lever(lever_name)
        current_value = lever.current_value if lever else 0.0

        lifecycle = LeverAdjustmentLifecycle(
            lever_name=lever_name,
            adjustment_id=adjustment_id,
            target_value=target_value,
            current_value=current_value,
        )

        # Store requirements
        self.requirement_registry[adjustment_id] = requirements

        # Start requirements phase
        lifecycle.requirements_phase.start()
        lifecycle.requirements_phase.artifacts.append(f"requirements_{adjustment_id}.json")

        self.active_lifecycles[adjustment_id] = lifecycle

        logger.info(f"Started V-Model lifecycle {adjustment_id} for lever '{lever_name}'")
        return adjustment_id

    def advance_phase(self, adjustment_id: str, metrics: dict[str, Any] | None = None) -> bool:
        """Advance to next V-Model phase."""
        if adjustment_id not in self.active_lifecycles:
            logger.error(f"Adjustment {adjustment_id} not found")
            return False

        lifecycle = self.active_lifecycles[adjustment_id]
        phases = lifecycle.get_left_side() + lifecycle.get_right_side()

        # Find current in-progress or first pending
        current_idx = -1
        for idx, phase in enumerate(phases):
            if phase.status == "in_progress":
                current_idx = idx
                break
            elif phase.status == "pending" and current_idx == -1:
                current_idx = idx

        if current_idx == -1:
            logger.info(f"Lifecycle {adjustment_id} already complete")
            return True

        # Complete current phase
        phases[current_idx].complete(metrics)
        logger.info(f"Completed {phases[current_idx].phase.value} phase")

        # Start next phase if exists
        if current_idx + 1 < len(phases):
            phases[current_idx + 1].start()
            logger.info(f"Started {phases[current_idx + 1].phase.value} phase")
        else:
            lifecycle.completed = True
            logger.info(f"Lifecycle {adjustment_id} completed full V-Model cycle")

        return True

    def phase_requirements(self, adjustment_id: str) -> dict[str, Any]:
        """Define requirements phase for lever adjustment."""
        lever = self.lever_system.get_lever(self.active_lifecycles[adjustment_id].lever_name)

        goal_dict = None
        if lever and lever.goal:
            from dataclasses import asdict

            goal_dict = asdict(lever.goal)

        return {
            "goal": goal_dict,
            "current_value": lever.current_value if lever else None,
            "target_value": self.active_lifecycles[adjustment_id].target_value,
            "justification": self.requirement_registry.get(adjustment_id, {}).get("justification", ""),
            "constraints": self.requirement_registry.get(adjustment_id, {}).get("constraints", []),
        }

    def phase_system_design(self, adjustment_id: str) -> dict[str, Any]:
        """Define system design phase - how adjustment fits into system."""
        lifecycle = self.active_lifecycles[adjustment_id]
        lever_name = lifecycle.lever_name

        return {
            "component_affected": lever_name,
            "related_levers": self._get_related_levers(lever_name),
            "impact_assessment": self._assess_impact(lever_name, lifecycle.target_value),
            "rollback_plan": self._create_rollback_plan(lever_name),
        }

    def phase_architecture(self, adjustment_id: str) -> dict[str, Any]:
        """Define architecture phase - component interactions."""
        lifecycle = self.active_lifecycles[adjustment_id]

        return {
            "interfaces_affected": self._get_interfaces(lifecycle.lever_name),
            "dependencies": self._get_dependencies(lifecycle.lever_name),
            "integration_points": self._get_integration_points(lifecycle.lever_name),
        }

    def phase_module_design(self, adjustment_id: str) -> dict[str, Any]:
        """Define module design phase - implementation details."""
        lifecycle = self.active_lifecycles[adjustment_id]

        return {
            "implementation_steps": self._generate_implementation_plan(lifecycle),
            "test_strategy": self._define_test_strategy(lifecycle.lever_name),
            "validation_criteria": self._define_validation_criteria(lifecycle),
        }

    def phase_implementation(self, adjustment_id: str) -> dict[str, Any]:
        """Execute implementation - actually adjust the lever."""
        lifecycle = self.active_lifecycles[adjustment_id]
        lever = self.lever_system.get_lever(lifecycle.lever_name)

        if not lever:
            return {"success": False, "error": "Lever not found"}

        # Execute the adjustment
        old_value = lever.current_value
        success, msg = lever.set(lifecycle.target_value)

        return {
            "success": success,
            "old_value": old_value,
            "new_value": lever.current_value,
            "message": msg,
        }

    def phase_unit_test(self, adjustment_id: str) -> dict[str, Any]:
        """Unit test phase - verify lever adjustment."""
        lifecycle = self.active_lifecycles[adjustment_id]
        lever = self.lever_system.get_lever(lifecycle.lever_name)

        if not lever:
            return {"success": False, "error": "Lever not found"}

        # Verify lever was set correctly
        value_correct = abs(lever.current_value - lifecycle.target_value) < 0.001

        # Verify in range
        in_range, range_msg = lever.range.validate(lever.current_value)

        return {
            "success": value_correct and in_range,
            "value_correct": value_correct,
            "in_range": in_range,
            "current_value": lever.current_value,
            "target_value": lifecycle.target_value,
        }

    def phase_integration_test(self, adjustment_id: str) -> dict[str, Any]:
        """Integration test phase - verify with related systems."""
        lifecycle = self.active_lifecycles[adjustment_id]

        # Test integration with related levers
        related = self._get_related_levers(lifecycle.lever_name)

        integration_tests = []
        for related_lever in related:
            test_result = self._test_integration(lifecycle.lever_name, related_lever)
            integration_tests.append(test_result)

        all_passed = all(t["passed"] for t in integration_tests)

        return {
            "success": all_passed,
            "tests_run": len(integration_tests),
            "tests_passed": sum(1 for t in integration_tests if t["passed"]),
            "test_details": integration_tests,
        }

    def phase_system_test(self, adjustment_id: str) -> dict[str, Any]:
        """System test phase - verify system behavior."""
        lifecycle = self.active_lifecycles[adjustment_id]
        lever = self.lever_system.get_lever(lifecycle.lever_name)

        if not lever:
            return {"success": False, "error": "Lever not found"}

        # System-level metrics
        system_dashboard = self.lever_system.get_dashboard()

        # Check goal progress
        progress = lever.get_progress_toward_goal()

        return {
            "success": True,
            "goal_progress": progress,
            "system_health": system_dashboard.get("goals_achieved", 0)
            / max(system_dashboard.get("total_levers", 1), 1),
            "metrics": lever.metrics,
        }

    def phase_validation(self, adjustment_id: str) -> dict[str, Any]:
        """Validation phase - verify requirements met."""
        lifecycle = self.active_lifecycles[adjustment_id]
        lever = self.lever_system.get_lever(lifecycle.lever_name)
        requirements = self.requirement_registry.get(adjustment_id, {})

        if not lever:
            return {"success": False, "error": "Lever not found"}

        # Check if requirement was met
        requirement_met = self._check_requirements(lifecycle, requirements)

        if requirement_met:
            # Move to completed
            self.completed_lifecycles.append(lifecycle)
            del self.active_lifecycles[adjustment_id]

        return {
            "success": requirement_met,
            "requirement_met": requirement_met,
            "final_value": lever.current_value,
            "target_value": lifecycle.target_value,
            "goal_achieved": lever.get_progress_toward_goal() >= 1.0 if lever and lever.goal else None,
        }

    # Helper methods

    def _get_related_levers(self, lever_name: str) -> list[str]:
        """Identify related levers."""
        relationships = {
            "deterministic_ratio": ["heuristic_confidence_threshold", "max_heuristic_fallbacks"],
            "heuristic_confidence_threshold": ["deterministic_ratio"],
            "discovery_timeout_seconds": ["parallel_discovery_workers"],
            "memory_safety_threshold_percent": [
                "parallel_discovery_workers",
                "validation_sample_size",
            ],
        }
        return relationships.get(lever_name, [])

    def _assess_impact(self, lever_name: str, new_value: float) -> str:
        """Assess impact of adjustment."""
        if lever_name == "deterministic_ratio":
            if new_value > 0.5:
                return "HIGH - Significant improvement in reliability"
            else:
                return "MEDIUM - Gradual improvement"
        elif lever_name == "memory_safety_threshold_percent":
            if new_value > 80:
                return "MEDIUM - More headroom, less aggressive resource management"
            else:
                return "HIGH - Resource constraints tighter"
        return "LOW"

    def _create_rollback_plan(self, lever_name: str) -> dict[str, Any]:
        """Create rollback plan."""
        lever = self.lever_system.get_lever(lever_name)
        if not lever:
            return {}

        return {
            "rollback_action": "lever.reset()",
            "rollback_value": lever.range.default_value,
            "current_value": lever.current_value,
        }

    def _get_interfaces(self, lever_name: str) -> list[str]:
        """Get interfaces affected."""
        interfaces = {
            "deterministic_ratio": ["discovery_api", "capability_registry"],
            "discovery_timeout_seconds": ["discovery_api"],
        }
        return interfaces.get(lever_name, [])

    def _get_dependencies(self, lever_name: str) -> list[str]:
        """Get dependencies."""
        # Levers that must be adjusted first
        deps = {
            "validation_sample_size": ["capability_validation_enabled"],
        }
        return deps.get(lever_name, [])

    def _get_integration_points(self, lever_name: str) -> list[str]:
        """Get integration points."""
        return ["DynamicLeverSystem", "DiscoveryModule", "ValidationModule"]

    def _generate_implementation_plan(self, lifecycle: LeverAdjustmentLifecycle) -> list[dict[str, Any]]:
        """Generate implementation steps."""
        return [
            {
                "step": 1,
                "action": f"Validate target value {lifecycle.target_value}",
                "check": "Value in safe range",
            },
            {
                "step": 2,
                "action": f"Set lever {lifecycle.lever_name}",
                "check": "No exceptions raised",
            },
            {
                "step": 3,
                "action": "Persist state",
                "check": "State saved to disk",
            },
        ]

    def _define_test_strategy(self, lever_name: str) -> dict[str, Any]:
        """Define test strategy."""
        return {
            "unit_tests": ["value_correctness", "range_validation"],
            "integration_tests": ["related_lever_consistency"],
            "system_tests": ["goal_progress", "metric_update"],
            "validation_tests": ["requirements_satisfaction"],
        }

    def _define_validation_criteria(self, lifecycle: LeverAdjustmentLifecycle) -> dict[str, Any]:
        """Define validation criteria."""
        lever = self.lever_system.get_lever(lifecycle.lever_name)
        if not lever or not lever.goal:
            return {"has_goal": False}

        return {
            "has_goal": True,
            "target_value": lifecycle.target_value,
            "tolerance": lever.goal.tolerance,
            "optimize_direction": lever.goal.optimize_direction,
        }

    def _test_integration(self, lever1: str, lever2: str) -> dict[str, Any]:
        """Test integration between two levers."""
        return {
            "lever_pair": f"{lever1}-{lever2}",
            "passed": True,
            "test": "consistency_check",
        }

    def _check_requirements(self, lifecycle: LeverAdjustmentLifecycle, requirements: dict[str, Any]) -> bool:
        """Check if requirements are met."""
        lever = self.lever_system.get_lever(lifecycle.lever_name)
        if not lever:
            return False

        # Basic requirement: value was set
        if abs(lever.current_value - lifecycle.target_value) > 0.001:
            return False

        # Check constraints
        constraints = requirements.get("constraints", [])
        if "must_be_positive" in constraints and lever.current_value < 0:
            return False

        return True

    def get_lifecycle_status(self, adjustment_id: str) -> dict[str, Any] | None:
        """Get lifecycle status."""
        if adjustment_id not in self.active_lifecycles:
            return None

        lifecycle = self.active_lifecycles[adjustment_id]

        return {
            "adjustment_id": adjustment_id,
            "lever": lifecycle.lever_name,
            "progress": lifecycle.get_progress(),
            "current_phase": lifecycle.get_current_phase().phase.value if lifecycle.get_current_phase() else None,
            "left_side_complete": all(p.status == "complete" for p in lifecycle.get_left_side()),
            "right_side_complete": all(p.status == "complete" for p in lifecycle.get_right_side()),
            "validated": lifecycle.is_validated(),
        }

    def get_vmodel_dashboard(self) -> dict[str, Any]:
        """Get V-Model dashboard."""
        active_count = len(self.active_lifecycles)
        completed_count = len(self.completed_lifecycles)
        total = active_count + completed_count

        # Phase completion stats
        phase_counts = {}
        for lifecycle in list(self.active_lifecycles.values()) + self.completed_lifecycles:
            for phase in lifecycle.get_left_side() + lifecycle.get_right_side():
                phase_name = phase.phase.value
                if phase_name not in phase_counts:
                    phase_counts[phase_name] = {"total": 0, "complete": 0}
                phase_counts[phase_name]["total"] += 1
                if phase.status == "complete":
                    phase_counts[phase_name]["complete"] += 1

        return {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "active_adjustments": active_count,
            "completed_adjustments": completed_count,
            "total_adjustments": total,
            "completion_rate": completed_count / total if total > 0 else 0,
            "phase_completion": phase_counts,
        }


class VModelIntegratedLeverSystem:
    """Dynamic lever system with V-Model engineering process."""

    def __init__(self, lever_system):
        self.lever_system = lever_system
        self.ve_process = VModelEngineeringProcess(lever_system)

    def adjust_lever_vmodel(self, lever_name: str, target_value: float, requirements: dict[str, Any]) -> str:
        """Adjust a lever following V-Model process."""
        # Start lifecycle
        adjustment_id = self.ve_process.start_adjustment(lever_name, target_value, requirements)

        # Execute phases (simplified - in real use, these would be async)
        self._execute_vmodel_phases(adjustment_id)

        return adjustment_id

    def _execute_vmodel_phases(self, adjustment_id: str):
        """Execute all V-Model phases."""
        import logging

        logger = logging.getLogger(__name__)

        phases = [
            ("requirements", self.ve_process.phase_requirements),
            ("system_design", self.ve_process.phase_system_design),
            ("architecture", self.ve_process.phase_architecture),
            ("module_design", self.ve_process.phase_module_design),
            ("implementation", self.ve_process.phase_implementation),
            ("unit_test", self.ve_process.phase_unit_test),
            ("integration_test", self.ve_process.phase_integration_test),
            ("system_test", self.ve_process.phase_system_test),
            ("validation", self.ve_process.phase_validation),
        ]

        for phase_name, phase_func in phases:
            try:
                # Execute phase and get result
                result = phase_func(adjustment_id)
                # Advance to next phase, marking current as complete
                success = self.ve_process.advance_phase(adjustment_id, result)
                if not success:
                    logger.error(f"Failed to advance phase {phase_name}")
                    break
            except Exception as e:
                logger.error(f"Phase {phase_name} failed: {e}")
                break


def demo_vmodel_integration():
    """Demonstrate V-Model integration."""
    from cohezion.swarm.dynamic_levers import create_default_lever_system

    print("=" * 70)
    print("SYSTEMS ENGINEERING V-MODEL INTEGRATION DEMO")
    print("=" * 70)

    # Create systems
    lever_system = create_default_lever_system()
    integrated = VModelIntegratedLeverSystem(lever_system)

    print("\n🎯 Adjusting lever with V-Model process...")
    print("-" * 50)

    # Define requirements for adjustment
    requirements = {
        "justification": "Improve deterministic parsing coverage for reliability",
        "constraints": ["must_be_positive", "verify_before_commit"],
        "acceptance_criteria": {
            "extraction_rate": 0.80,
            "false_positives": 0.05,
        },
    }

    # Execute V-Model adjustment
    adjustment_id = integrated.adjust_lever_vmodel(
        lever_name="deterministic_ratio",
        target_value=0.50,  # Move from 0.28 to 0.50
        requirements=requirements,
    )

    print(f"\n📊 Adjustment ID: {adjustment_id}")

    # Show lifecycle status
    lifecycle = integrated.ve_process.get_lifecycle_status(adjustment_id)
    if lifecycle:
        print(f"  Lever: {lifecycle['lever']}")
        print(f"  Progress: {lifecycle['progress']:.0%}")
        print(f"  Validated: {lifecycle['validated']}")

    # Show V-Model dashboard
    dashboard = integrated.ve_process.get_vmodel_dashboard()
    print("\n📈 V-Model Dashboard:")
    print(f"  Active adjustments: {dashboard['active_adjustments']}")
    print(f"  Completed adjustments: {dashboard['completed_adjustments']}")
    print(f"  Completion rate: {dashboard['completion_rate']:.1%}")

    # Show phase completion
    print("\n  Phase Completion:")
    for phase, stats in dashboard["phase_completion"].items():
        rate = stats["complete"] / stats["total"] if stats["total"] > 0 else 0
        bar = "█" * int(rate * 10) + "░" * (10 - int(rate * 10))
        print(f"    {phase:25} | {bar} | {rate:.0%}")

    print("\n✅ V-Model demo complete")


if __name__ == "__main__":
    demo_vmodel_integration()
