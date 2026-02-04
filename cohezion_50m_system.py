#!/usr/bin/env python3
"""
🌌 COHEZION 50M AGENT QUANTUM TOPOLOGY - COMPLETE SYSTEM

This is the main entry point for running the complete COHEZION system with:
- 50M Agent Quantum Topology Simulation
- Comprehensive Tutorial System
- Enhanced Git-Safe Handoffs
- Resource Monitoring with OOM Prevention
- SurrealDB Persistence
- Full System Integration

Usage:
    python3 cohezion_50m_system.py [command]

Commands:
    tutorial      - Access reproduction tutorials
    simulate      - Run 50M agent simulation with full protection
    recover       - Recover from last handoff
    status        - Show system status
    demo          - Run demonstration
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Ensure src is in path
sys.path.insert(0, "/home/mike-anderson/dev/cohezion/src")

from cohezion.integration.system_integrator import SystemIntegrator, SYSTEM_INTEGRATOR
from cohezion.tutorials.tutorial_system import TUTORIAL_SYSTEM
from cohezion.persistence.enhanced_git_safe_handoff import ENHANCED_HANDOFF_MANAGER


def print_banner():
    """Print COHEZION banner"""
    print("""
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║     🌌 COHEZION - 50M Agent Quantum Topology Simulation 🌌           ║
║                                                                      ║
║     Penrose Twistors • ER=EPR Bridges • Quantum Biology              ║
║     Compound Engineering • SurrealDB • Git-Safe Handoffs             ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
    """)


async def run_tutorial():
    """Run tutorial system"""
    print("📚 COHEZION TUTORIAL SYSTEM")
    print("=" * 70)

    # Generate tutorials
    tutorial = TUTORIAL_SYSTEM.create_50m_reproduction_tutorial()
    TUTORIAL_SYSTEM.save_tutorial(tutorial)

    print(f"✅ Tutorial: {tutorial.title}")
    print(f"   Steps: {len(tutorial.steps)}")
    print(f"   Difficulty: {tutorial.difficulty}")
    print(f"   Est. Time: {tutorial.estimated_time}")

    print("\n📋 Available Steps:")
    for step in tutorial.steps:
        print(
            f"   {step.step_number}. {step.title} ({step.difficulty}, {step.time_estimate})"
        )

    print("\n📄 Lessons Learned:")
    for i, lesson in enumerate(tutorial.lessons_learned, 1):
        print(f"   {i}. {lesson}")

    # Generate lessons learned doc
    doc = TUTORIAL_SYSTEM.generate_lessons_learned_doc(tutorial.tutorial_id)
    doc_path = Path(
        "/home/mike-anderson/dev/cohezion/tutorials/50M_REPRODUCTION_GUIDE.md"
    )
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    with open(doc_path, "w") as f:
        f.write(doc)
    print(f"\n💾 Full guide saved: {doc_path}")


async def run_simulation():
    """Run 50M agent simulation with full integration"""
    print("🌌 RUNNING 50M AGENT SIMULATION")
    print("=" * 70)

    integrator = SystemIntegrator()

    try:
        # Initialize
        await integrator.initialize()

        # Run simulation with all protections
        print("\n🚀 Starting simulation with:")
        print("   ✅ Resource monitoring (OOM protection)")
        print("   ✅ Automatic handoffs every 500 steps")
        print("   ✅ SurrealDB persistence")
        print("   ✅ Graceful degradation on resource pressure")
        print()

        universe, narrative = await integrator.run_50m_simulation(
            enable_handoffs=True,
            enable_persistence=True,
            batch_size=100_000,
            num_steps=1000,
        )

        return universe, narrative

    except Exception as e:
        print(f"\n❌ Simulation error: {e}")
        print("🔄 Attempting recovery from last handoff...")

        recovered = await integrator.recover_from_handoff()
        if recovered:
            print("✅ Recovery successful - can resume from checkpoint")
        else:
            print("❌ Recovery failed - check handoff files")

        raise
    finally:
        await integrator.shutdown()


async def show_status():
    """Show complete system status"""
    print("📊 COHEZION SYSTEM STATUS")
    print("=" * 70)

    integrator = SystemIntegrator()

    # Quick init to get status
    status = integrator.get_integration_status()

    print("\n🔧 Integration Status:")
    print(f"   Running: {status['system_integrator']['is_running']}")
    print(f"   Phase: {status['system_integrator']['current_phase']}")
    print(f"   Compound Factor: {status['system_integrator']['compound_factor']}×")

    print("\n📊 Resource Monitor:")
    rm = status["resource_monitor"]
    for key, value in rm.items():
        print(f"   {key}: {value}")

    print("\n🔐 Handoff Manager:")
    hm = status["handoff_manager"]
    print(f"   Total Handoffs: {hm['total_handoffs']}")
    print(f"   Success Rate: {hm['success_rate']:.1%}")
    print(f"   Avg Recovery: {hm['avg_recovery_time']:.2f}s")

    print("\n💾 SurrealDB:")
    print(f"   Connected: {status['surrealdb']['connected']}")
    print(f"   Status: {status['surrealdb']['status']}")

    print("\n📚 Tutorials:")
    print(f"   Available: {status['tutorials']['available']}")
    print(f"   System: {status['tutorials']['tutorial_system']}")


async def run_recovery():
    """Recover from last handoff"""
    print("🔄 RECOVERING FROM LAST HANDOFF")
    print("=" * 70)

    integrator = SystemIntegrator()
    recovered = await integrator.recover_from_handoff()

    if recovered:
        print("\n✅ RECOVERY SUCCESSFUL")
        print(f"   Session: {recovered['metadata']['session_id']}")
        print(f"   Recovery Time: {recovered['recovery_time']:.2f}s")
        print(f"   Validation Score: {recovered['validation'].integrity_score:.1%}")
        print(f"   Phase: {recovered['state_data'].get('phase', 'unknown')}")
        print(f"   Agents: {recovered['state_data'].get('agent_count', 0):,}")

        print("\n🚀 Ready to resume simulation")
    else:
        print("\n❌ RECOVERY FAILED")
        print("   No handoff files found or data corrupted")


async def run_demo():
    """Run demonstration of all components"""
    print("🎭 COHEZION SYSTEM DEMONSTRATION")
    print("=" * 70)

    # 1. Tutorial System
    print("\n1️⃣ TUTORIAL SYSTEM")
    print("-" * 70)
    await run_tutorial()

    # 2. Handoff System
    print("\n2️⃣ ENHANCED HANDOFF SYSTEM")
    print("-" * 70)
    from cohezion.persistence.enhanced_git_safe_handoff import demo_enhanced_handoff

    await demo_enhanced_handoff()

    # 3. System Integration (without full simulation)
    print("\n3️⃣ SYSTEM INTEGRATION")
    print("-" * 70)
    integrator = SystemIntegrator()
    await integrator.initialize()

    status = integrator.get_integration_status()
    print(f"✅ Integration Status: {status['system_integrator']['current_phase']}")
    print(f"   Resource Monitor: {status['resource_monitor']['status']}")
    print(f"   SurrealDB: {status['surrealdb']['status']}")
    print(f"   Tutorials: {status['tutorials']['available']} available")

    await integrator.shutdown()

    print("\n" + "=" * 70)
    print("🎉 DEMONSTRATION COMPLETE")
    print("=" * 70)
    print("\nTo run full 50M simulation:")
    print("   python3 cohezion_50m_system.py simulate")


async def main():
    """Main entry point"""
    print_banner()

    if len(sys.argv) < 2:
        command = "demo"
    else:
        command = sys.argv[1]

    commands = {
        "tutorial": run_tutorial,
        "tutorials": run_tutorial,
        "simulate": run_simulation,
        "sim": run_simulation,
        "recover": run_recovery,
        "status": show_status,
        "demo": run_demo,
    }

    if command in commands:
        try:
            await commands[command]()
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)
    else:
        print(f"Unknown command: {command}")
        print(f"\nAvailable commands: {', '.join(commands.keys())}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
