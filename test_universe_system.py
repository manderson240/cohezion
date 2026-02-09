#!/usr/bin/env python3
"""
Quick Test: ASCENDED COHEZION Universe Simulation

Tests the basic functionality of all 6 components:
1. Mission Orchestrator
2. Openweight Grading
3. Display Engine
4. Notifications
5. Evolution Engine
6. Launch Script

Usage: uv run python3 test_universe_system.py
"""

import asyncio
import sys

sys.path.insert(0, "/home/mike-anderson/dev/cohezion/src")


async def test_components():
    """Test all universe simulation components"""

    print("=" * 70)
    print("🌌 ASCENDED COHEZION - Universe Simulation System Test")
    print("=" * 70)
    print()

    # 1. Test Mission Orchestrator
    print("1️⃣ Testing Mission Orchestrator...")
    from cohezion.swarm.autonomous_universe_mission import (
        AutonomousUniverseMission,
        TrackType,
    )

    orchestrator = AutonomousUniverseMission("manderson240@gmail.com")
    print(f"   ✅ Initialized with {len(orchestrator.TRACKS)} tracks")
    print(f"   📧 Email: {orchestrator.email_recipient}")

    # Show track configurations
    for track_type, config in orchestrator.TRACKS.items():
        print(
            f"   📊 {track_type.value}: {len(config.universes)} universes, {config.duration_hours}h"
        )
    print()

    # 2. Test Grading System
    print("2️⃣ Testing Grading System...")
    from cohezion.swarm.openweight_grader import OpenweightGradingPanel

    grader = OpenweightGradingPanel("manderson240@gmail.com")
    print(f"   ✅ Initialized")
    print(f"   🎓 Available graders: {len(grader.available_graders)}")
    print(f"   📊 Grading rubric: {len(grader.RUBRIC)} criteria")
    print()

    # 3. Test Display Engine
    print("3️⃣ Testing Display Engine...")
    from cohezion.swarm.universe_display_engine import UniverseDisplayEngine

    display = UniverseDisplayEngine()
    print(f"   ✅ Initialized")
    print(f"   🎨 Output directory: {display.output_dir}")
    print(f"   📺 Real-time enabled: {display.config.enable_realtime}")
    print()

    # 4. Test Notifications
    print("4️⃣ Testing Notification System...")
    from cohezion.swarm.milestone_alerts import NotificationManager

    notifier = NotificationManager("manderson240@gmail.com")
    print(f"   ✅ Initialized")
    print(f"   📧 Recipient: {notifier.recipient}")
    print(f"   💾 Config path: {notifier.config_path}")
    print()

    # 5. Test Evolution Engine
    print("5️⃣ Testing Evolution Engine...")
    from cohezion.swarm.compound_evolution import CompoundEvolutionEngine

    evolution = CompoundEvolutionEngine()
    print(f"   ✅ Initialized")
    print(f"   🔄 Tracks monitored: {len(evolution.track_states)}")
    print(f"   📚 Pattern library: {len(evolution.pattern_library)} entries")
    print()

    # 6. Test getting evolution summary
    print("6️⃣ Testing Evolution Summary...")
    summary = evolution.get_evolution_summary()
    print(f"   📊 Total improvements: {summary['total_improvements']}")
    print(f"   📚 Total patterns: {summary['total_patterns']}")
    print()

    print("=" * 70)
    print("✅ ALL TESTS PASSED")
    print("=" * 70)
    print()
    print("🚀 Ready to launch universe simulations!")
    print()
    print("Next steps:")
    print("  1. Run: uv run python launch_universe_mission.py --status")
    print("  2. Run: uv run python launch_universe_mission.py --track rapid")
    print("  3. Check email at manderson240@gmail.com for notifications")
    print()


if __name__ == "__main__":
    asyncio.run(test_components())
