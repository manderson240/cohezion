#!/usr/bin/env python3
"""Demo script for dynamic and adaptive multi-agent orchestration.

This script demonstrates:
1. Dynamic agent registry (hot-reload, runtime registration)
2. Adaptive routing (self-learning, performance-based)
3. Multi-agent execution with fallback
4. Performance tracking and analytics
"""

import asyncio
import sys
from pathlib import Path

# Add cohezion to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cohezion.swarm import (
    DynamicAgentRegistry,
    AdaptiveRouter,
    MultiAgentOrchestrator,
    ExecutionResult,
    CODE_SPECIALIST,
    REASONING_SPECIALIST,
    NOVEL_SPECIALIST,
)


async def demo_specialists():
    """Demonstrate validated specialists."""
    print("\n" + "=" * 70)
    print("🎯 VALIDATED SPECIALISTS")
    print("=" * 70)
    
    specialists = [
        CODE_SPECIALIST,
        REASONING_SPECIALIST,
        NOVEL_SPECIALIST,
    ]
    
    for s in specialists:
        print(f"\n📌 {s.name}")
        print(f"   Model: {s.model}")
        print(f"   Backend: {s.backend.name}")
        print(f"   TPS: {s.performance_stats.get('tps', 'N/A')}")
        print(f"   Context: {s.performance_stats.get('context_window', 'N/A'):,}")
        print(f"   Capabilities: {', '.join(s.capabilities[:3])}")


async def demo_dynamic_registry():
    """Demonstrate dynamic agent registry."""
    print("\n" + "=" * 70)
    print("🔧 DYNAMIC AGENT REGISTRY")
    print("=" * 70)
    
    # Create registry
    registry = DynamicAgentRegistry()
    
    # List built-in agents
    print("\n📋 Built-in Agents:")
    agents = registry.list_agents(active_only=True)
    for agent in agents:
        print(f"   • {agent.name} - {', '.join(agent.capabilities[:2])}")
    
    # Get agent instance
    print("\n🔍 Getting Agent Instance:")
    instance = registry.get_agent_instance("CodeSpecialist")
    if instance:
        print(f"   ✓ Got {instance.name}")
        print(f"   ✓ Model: {instance.model}")
    
    # Check if agents have specific capabilities
    print("\n🎯 Agents with Code Capability:")
    code_agents = registry.get_agents_by_capability("code_generation")
    for agent in code_agents:
        print(f"   • {agent.name}")


async def demo_adaptive_routing():
    """Demonstrate adaptive routing."""
    print("\n" + "=" * 70)
    print("🧠 ADAPTIVE ROUTING")
    print("=" * 70)
    
    # Create registry and router
    registry = DynamicAgentRegistry()
    router = AdaptiveRouter(registry)
    
    test_tasks = [
        ("Write a Python function to calculate fibonacci", "Code task"),
        ("Explain the tradeoffs between microservices and monoliths", "Reasoning task"),
        ("Summarize this 50-page document...", "Long context"),
        ("Experiment with a novel approach to caching", "Novel research"),
    ]
    
    for task, task_type in test_tasks:
        print(f"\n📝 {task_type}:")
        print(f"   Input: {task[:50]}...")
        
        decision = await router.route(task)
        
        print(f"   → Routed to: {decision.agent_name}")
        print(f"   → Confidence: {decision.confidence:.2f}")
        print(f"   → Reasoning: {decision.reasoning[:70]}...")
        print(f"   → Expected: {decision.expected_latency_ms:.0f}ms, quality={decision.expected_quality:.2f}")
        
        if decision.alternative_agents:
            print(f"   → Alternatives: {', '.join(decision.alternative_agents)}")


async def demo_orchestration():
    """Demonstrate multi-agent orchestration."""
    print("\n" + "=" * 70)
    print("🚀 MULTI-AGENT ORCHESTRATION")
    print("=" * 70)
    
    # Initialize orchestrator
    print("\n⚙️  Initializing Orchestrator...")
    orchestrator = MultiAgentOrchestrator(enable_learning=False)
    await orchestrator.start()
    
    # Execute tasks
    tasks = [
        "Write a Python function to reverse a string",
        "Explain quantum computing simply",
        "Compare REST vs GraphQL APIs",
    ]
    
    print("\n📤 Executing Tasks:")
    for task in tasks:
        print(f"\n   Task: {task}")
        
        result = await orchestrator.execute(task)
        
        print(f"   → Agent: {result.agent_name}")
        print(f"   → Backend: {result.backend}")
        print(f"   → Confidence: {result.routing_confidence:.2f}")
        print(f"   → Latency: {result.latency_ms:.1f}ms")
        print(f"   → Quality: {result.quality_score:.2f}")
        print(f"   → Success: {'✅' if result.success else '❌'}")
    
    # Show stats
    print("\n📊 Orchestration Stats:")
    orchestrator.print_report()
    
    # Shutdown
    await orchestrator.stop()


async def demo_batch_execution():
    """Demonstrate batch execution."""
    print("\n" + "=" * 70)
    print("⚡ BATCH EXECUTION")
    print("=" * 70)
    
    orchestrator = MultiAgentOrchestrator(enable_learning=False)
    await orchestrator.start()
    
    # Create batch of tasks
    tasks = [
        f"Task {i}: Calculate {n} * {n}"
        for i, n in enumerate(range(1, 6))
    ]
    
    print(f"\n📦 Executing {len(tasks)} tasks concurrently...")
    
    start = asyncio.get_event_loop().time()
    results = await orchestrator.execute_batch(tasks, max_concurrent=3)
    elapsed = asyncio.get_event_loop().time() - start
    
    print(f"\n   ✓ Completed {len(results)} tasks in {elapsed:.2f}s")
    print(f"   ✓ Average latency: {sum(r.latency_ms for r in results)/len(results):.1f}ms")
    print(f"   ✓ Success rate: {sum(1 for r in results if r.success)/len(results):.0%}")
    
    await orchestrator.stop()


async def demo_learning():
    """Demonstrate adaptive learning."""
    print("\n" + "=" * 70)
    print("📈 ADAPTIVE LEARNING")
    print("=" * 70)
    
    registry = DynamicAgentRegistry()
    router = AdaptiveRouter(registry)
    
    print("\n🧪 Simulating Learning Loop:")
    
    # Simulate multiple executions
    for i in range(5):
        task = "Test code generation"
        decision = await router.route(task)
        
        # Simulate outcome
        success = True
        latency = 100 + i * 10  # Getting faster
        quality = 0.8 + i * 0.03  # Getting better
        
        await router.feedback(decision, {
            "success": success,
            "latency_ms": latency,
            "quality_score": quality,
            "features": decision.features,
        })
        
        print(f"   Step {i+1}: confidence={decision.confidence:.2f}, "
              f"latency={latency}ms, quality={quality:.2f}")
    
    # Show routing stats
    stats = router.get_routing_stats()
    if stats:
        print(f"\n   📊 Learning Progress:")
        print(f"      - Total routings: {stats.get('total_routings', 0)}")
        print(f"      - Success rate: {stats.get('success_rate', 0):.1%}")
        print(f"      - Avg confidence: {stats.get('avg_confidence', 0):.2f}")


async def main():
    """Run complete demo."""
    print("\n" + "🎪" * 35)
    print("   COHEZION MULTI-AGENT ORCHESTRATION DEMO")
    print("   Dynamic • Adaptive • Hardware-Optimized")
    print("🎪" * 35)
    
    try:
        await demo_specialists()
        await demo_dynamic_registry()
        await demo_adaptive_routing()
        await demo_orchestration()
        await demo_batch_execution()
        await demo_learning()
        
        print("\n" + "=" * 70)
        print("✅ DEMO COMPLETE")
        print("=" * 70)
        print("\nKey Features Demonstrated:")
        print("  • ✅ Validated Specialists (Gemma-4-E2B, qwen3:4b, Jan-v1-4B)")
        print("  • ✅ Dynamic Agent Registry (hot-reload ready)")
        print("  • ✅ Adaptive Routing (self-learning)")
        print("  • ✅ Multi-Agent Orchestration (fallback chains)")
        print("  • ✅ Performance Analytics")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
