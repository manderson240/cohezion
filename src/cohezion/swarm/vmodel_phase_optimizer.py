"""Phase duration optimizer for V-Model lifecycle.

Implements Phase 3: Track phase durations, identify bottlenecks,
suggest optimizations, measure before/after.
"""

import json
import logging
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from collections import defaultdict
import time

from cohezion.swarm.vmodel_engineering import VPhase, VVerification


logger = logging.getLogger(__name__)


@dataclass
class PhaseMetrics:
    """Metrics for a V-Model phase."""
    phase_name: str
    durations_ms: List[float] = field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0
    artifacts_created: int = 0
    
    def add_duration(self, duration_ms: float, success: bool = True):
        """Record a phase execution."""
        self.durations_ms.append(duration_ms)
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for this phase."""
        if not self.durations_ms:
            return {"count": 0}
        
        return {
            "count": len(self.durations_ms),
            "mean_ms": statistics.mean(self.durations_ms),
            "median_ms": statistics.median(self.durations_ms),
            "min_ms": min(self.durations_ms),
            "max_ms": max(self.durations_ms),
            "stdev_ms": statistics.stdev(self.durations_ms) if len(self.durations_ms) > 1 else 0,
            "success_rate": self.success_count / (self.success_count + self.failure_count)
            if (self.success_count + self.failure_count) > 0 else 0,
            "total_duration_ms": sum(self.durations_ms),
        }


@dataclass
class BottleneckAnalysis:
    """Analysis of bottlenecks in V-Model lifecycle."""
    slowest_phase: str
    slowest_duration_ms: float
    percentage_of_total: float
    rank: int
    suggestion: str
    expected_improvement_ms: float


class PhaseOptimizer:
    """Optimizer for V-Model phase durations."""
    
    # Optimization suggestions by phase type
    OPTIMIZATION_SUGGESTIONS = {
        "requirements": "Cache common requirement patterns",
        "system_design": "Template rollback plans",
        "architecture": "Pre-compute interface mappings",
        "module_design": "Auto-generate test strategies",
        "implementation": "Parallelize independent steps",
        "unit_test": "Cache previous test results",
        "integration_test": "Mock external dependencies",
        "system_test": "Cache system state snapshots",
        "validation": "Automate acceptance criteria checks",
    }
    
    def __init__(self, data_path: Optional[Path] = None):
        self.data_path = data_path or Path("~/.config/cohezion/vmodel_metrics.jsonl").expanduser()
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.phase_metrics: Dict[str, PhaseMetrics] = {}
        self.lifecycle_history: List[Dict[str, Any]] = []
        
        self._load_historical_data()
    
    def record_phase_execution(
        self,
        phase_name: str,
        duration_ms: float,
        success: bool = True,
        lifecycle_id: Optional[str] = None
    ):
        """Record a phase execution."""
        if phase_name not in self.phase_metrics:
            self.phase_metrics[phase_name] = PhaseMetrics(phase_name=phase_name)
        
        self.phase_metrics[phase_name].add_duration(duration_ms, success)
        
        # Record to lifecycle history
        if lifecycle_id:
            self.lifecycle_history.append({
                "lifecycle_id": lifecycle_id,
                "phase": phase_name,
                "duration_ms": duration_ms,
                "success": success,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            })
    
    def analyze_bottlenecks(self, lifecycle_id: Optional[str] = None) -> List[BottleneckAnalysis]:
        """Identify bottlenecks in phase execution."""
        # Get phases to analyze
        if lifecycle_id:
            phases = [
                h for h in self.lifecycle_history
                if h["lifecycle_id"] == lifecycle_id
            ]
            phase_durations = defaultdict(list)
            for p in phases:
                phase_durations[p["phase"]].append(p["duration_ms"])
        else:
            phase_durations = {
                name: metrics.durations_ms
                for name, metrics in self.phase_metrics.items()
            }
        
        if not phase_durations:
            return []
        
        # Calculate total duration per phase (mean)
        phase_totals = {
            name: statistics.mean(durations) if durations else 0
            for name, durations in phase_durations.items()
        }
        
        # Sort by duration (slowest first)
        sorted_phases = sorted(
            phase_totals.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        total_duration = sum(phase_totals.values())
        
        bottlenecks = []
        for rank, (phase_name, duration) in enumerate(sorted_phases, 1):
            percentage = (duration / total_duration * 100) if total_duration > 0 else 0
            
            # Get suggestion
            suggestion = self.OPTIMIZATION_SUGGESTIONS.get(
                phase_name,
                "Profile for hotspots"
            )
            
            # Estimate improvement (typically 30% for first optimization)
            expected_improvement = duration * 0.3
            
            bottlenecks.append(BottleneckAnalysis(
                slowest_phase=phase_name,
                slowest_duration_ms=duration,
                percentage_of_total=percentage,
                rank=rank,
                suggestion=suggestion,
                expected_improvement_ms=expected_improvement
            ))
        
        return bottlenecks
    
    def get_optimization_plan(self) -> Dict[str, Any]:
        """Generate optimization plan based on bottleneck analysis."""
        bottlenecks = self.analyze_bottlenecks()
        
        if not bottlenecks:
            return {"status": "insufficient_data"}
        
        top_bottleneck = bottlenecks[0]
        
        return {
            "status": "optimization_recommended",
            "priority": "high" if top_bottleneck.percentage_of_total > 25 else "medium",
            "target_phase": top_bottleneck.slowest_phase,
            "current_duration_ms": top_bottleneck.slowest_duration_ms,
            "percentage_of_total": f"{top_bottleneck.percentage_of_total:.1f}%",
            "suggestion": top_bottleneck.suggestion,
            "expected_improvement_ms": top_bottleneck.expected_improvement_ms,
            "expected_improvement_percent": "30%",
            "all_bottlenecks": [
                {
                    "phase": b.slowest_phase,
                    "duration_ms": b.slowest_duration_ms,
                    "percentage": f"{b.percentage_of_total:.1f}%",
                    "suggestion": b.suggestion
                }
                for b in bottlenecks[:3]  # Top 3
            ]
        }
    
    def compare_before_after(
        self,
        phase_name: str,
        optimization_applied: str,
        window_size: int = 10
    ) -> Dict[str, Any]:
        """Compare phase performance before and after optimization."""
        metrics = self.phase_metrics.get(phase_name)
        if not metrics or len(metrics.durations_ms) < window_size * 2:
            return {"status": "insufficient_data"}
        
        # Split into before/after
        mid = len(metrics.durations_ms) // 2
        before = metrics.durations_ms[:mid]
        after = metrics.durations_ms[mid:]
        
        before_mean = statistics.mean(before)
        after_mean = statistics.mean(after)
        
        improvement_ms = before_mean - after_mean
        improvement_percent = (improvement_ms / before_mean * 100) if before_mean > 0 else 0
        
        return {
            "phase": phase_name,
            "optimization": optimization_applied,
            "before_mean_ms": before_mean,
            "after_mean_ms": after_mean,
            "improvement_ms": improvement_ms,
            "improvement_percent": f"{improvement_percent:.1f}%",
            "status": "improved" if improvement_ms > 0 else "regressed",
            "sample_size_before": len(before),
            "sample_size_after": len(after),
        }
    
    def get_dashboard(self) -> Dict[str, Any]:
        """Get optimization dashboard."""
        bottlenecks = self.analyze_bottlenecks()
        
        # Phase stats
        phase_stats = {
            name: metrics.get_stats()
            for name, metrics in self.phase_metrics.items()
        }
        
        # Total lifecycles tracked
        lifecycle_count = len(set(
            h["lifecycle_id"] for h in self.lifecycle_history
            if h.get("lifecycle_id")
        ))
        
        return {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "lifecycles_tracked": lifecycle_count,
            "total_phase_executions": len(self.lifecycle_history),
            "phases_monitored": len(self.phase_metrics),
            "top_bottleneck": {
                "phase": bottlenecks[0].slowest_phase if bottlenecks else None,
                "duration_ms": bottlenecks[0].slowest_duration_ms if bottlenecks else None,
                "suggestion": bottlenecks[0].suggestion if bottlenecks else None,
            },
            "phase_stats": phase_stats,
            "optimization_recommended": len(bottlenecks) > 0 and bottlenecks[0].percentage_of_total > 20
        }
    
    def print_dashboard(self):
        """Print visual dashboard."""
        dashboard = self.get_dashboard()
        
        print("\n" + "="*70)
        print("V-MODEL PHASE OPTIMIZATION DASHBOARD")
        print("="*70)
        print(f"Timestamp: {dashboard['timestamp']}")
        print(f"Lifecycles Tracked: {dashboard['lifecycles_tracked']}")
        print(f"Phase Executions: {dashboard['total_phase_executions']}")
        print("-"*70)
        
        # Phase stats
        print("\nPHASE PERFORMANCE:")
        print("-"*70)
        for phase, stats in sorted(dashboard['phase_stats'].items()):
            if stats['count'] > 0:
                bar = self._duration_bar(stats['mean_ms'])
                print(f"  {phase:20} | {stats['mean_ms']:8.1f}ms | [{bar}] | n={stats['count']}")
        
        # Bottleneck
        if dashboard['optimization_recommended']:
            print("\n⚠️  OPTIMIZATION RECOMMENDED:")
            print("-"*70)
            bottleneck = dashboard['top_bottleneck']
            print(f"  Phase: {bottleneck['phase']}")
            print(f"  Current: {bottleneck['duration_ms']:.1f}ms")
            print(f"  Suggestion: {bottleneck['suggestion']}")
        
        print("="*70)
    
    def _duration_bar(self, duration_ms: float, max_ms: float = 500, width: int = 20) -> str:
        """Generate ASCII bar for duration."""
        filled = int(min(width, width * duration_ms / max_ms))
        return "█" * filled + "░" * (width - filled)
    
    def _load_historical_data(self):
        """Load historical metrics from disk."""
        if not self.data_path.exists():
            return
        
        try:
            with open(self.data_path, 'r') as f:
                for line in f:
                    data = json.loads(line)
                    if data.get("type") == "phase_execution":
                        self.record_phase_execution(
                            phase_name=data["phase"],
                            duration_ms=data["duration_ms"],
                            success=data.get("success", True),
                            lifecycle_id=data.get("lifecycle_id")
                        )
        except Exception as e:
            logger.warning(f"Failed to load historical data: {e}")
    
    def save(self):
        """Save metrics to disk."""
        records = []
        for history in self.lifecycle_history:
            records.append({
                **history,
                "type": "phase_execution"
            })
        
        with open(self.data_path, 'w') as f:
            for record in records:
                f.write(json.dumps(record) + "\n")
        
        logger.info(f"Saved {len(records)} phase execution records")


class InstrumentedVModelEngineering:
    """V-Model engineering with automatic phase instrumentation."""
    
    def __init__(self, base_engineering):
        self.base = base_engineering
        self.optimizer = PhaseOptimizer()
    
    def execute_phase_with_instrumentation(
        self,
        phase_name: str,
        phase_func,
        *args,
        **kwargs
    ) -> Tuple[Any, float, bool]:
        """Execute a phase with timing instrumentation."""
        start_time = time.perf_counter()
        
        try:
            result = phase_func(*args, **kwargs)
            success = result.get("success", True) if isinstance(result, dict) else True
        except Exception as e:
            logger.error(f"Phase {phase_name} failed: {e}")
            result = None
            success = False
        
        end_time = time.perf_counter()
        duration_ms = (end_time - start_time) * 1000
        
        # Record metrics
        self.optimizer.record_phase_execution(
            phase_name=phase_name,
            duration_ms=duration_ms,
            success=success
        )
        
        return result, duration_ms, success


def demo_phase_optimizer():
    """Demonstrate phase optimizer."""
    print("="*70)
    print("PHASE 3: V-MODEL PHASE OPTIMIZER")
    print("="*70)
    
    optimizer = PhaseOptimizer()
    
    # Simulate some phase execution data
    print("\n📝 Simulating V-Model phase executions...")
    
    # Simulate 10 lifecycles with varying durations
    for i in range(10):
        lifecycle_id = f"lifecycle_{i}"
        
        # Requirements (fast)
        optimizer.record_phase_execution("requirements", 50 + i * 5, True, lifecycle_id)
        
        # System Design (medium)
        optimizer.record_phase_execution("system_design", 120 + i * 10, True, lifecycle_id)
        
        # Architecture (medium)
        optimizer.record_phase_execution("architecture", 80 + i * 8, True, lifecycle_id)
        
        # Module Design (slow - bottleneck candidate)
        optimizer.record_phase_execution("module_design", 300 + i * 20, True, lifecycle_id)
        
        # Implementation (slowest - bottleneck)
        optimizer.record_phase_execution("implementation", 500 + i * 30, True, lifecycle_id)
        
        # Unit Test (fast)
        optimizer.record_phase_execution("unit_test", 100 + i * 5, True, lifecycle_id)
        
        # Integration Test (medium)
        optimizer.record_phase_execution("integration_test", 150 + i * 10, True, lifecycle_id)
        
        # System Test (medium)
        optimizer.record_phase_execution("system_test", 120 + i * 8, True, lifecycle_id)
        
        # Validation (fast)
        optimizer.record_phase_execution("validation", 80 + i * 5, True, lifecycle_id)
    
    print(f"  Recorded: {len(optimizer.lifecycle_history)} phase executions")
    print(f"  Lifecycles: 10")
    
    # Show dashboard
    optimizer.print_dashboard()
    
    # Analyze bottlenecks
    print("\n🔍 Bottleneck Analysis:")
    print("-"*70)
    bottlenecks = optimizer.analyze_bottlenecks()
    
    for i, b in enumerate(bottlenecks[:3], 1):
        print(f"  {i}. {b.slowest_phase}")
        print(f"      Duration: {b.slowest_duration_ms:.1f}ms")
        print(f"      Share: {b.percentage_of_total:.1f}%")
        print(f"      Suggestion: {b.suggestion}")
    
    # Get optimization plan
    print("\n📋 Optimization Plan:")
    print("-"*70)
    plan = optimizer.get_optimization_plan()
    
    if plan["status"] == "optimization_recommended":
        print(f"  Priority: {plan['priority'].upper()}")
        print(f"  Target: {plan['target_phase']}")
        print(f"  Current: {plan['current_duration_ms']:.1f}ms")
        print(f"  Share: {plan['percentage_of_total']}")
        print(f"  Suggestion: {plan['suggestion']}")
        print(f"  Expected: {plan['expected_improvement_percent']} faster")
    
    print("\n" + "="*70)
    print("✅ PHASE 3 DEMONSTRATED: Phase Optimization Working")
    print("="*70)
    print("\n🎯 Dogfooding Result:")
    print("   - Phase durations automatically tracked")
    print("   - Bottlenecks identified (implementation, module_design)")
    print("   - Optimization suggestions generated")
    print("   - Before/after comparison framework ready")
    print("\n🎯 Next: Apply optimization, measure improvement")


if __name__ == "__main__":
    demo_phase_optimizer()
