"""
ASCENDED COHEZION - Autonomous Universe Simulation Launcher
Triple-Track Mission Controller

Usage:
    uv run python launch_universe_mission.py --track rapid
    uv run python launch_universe_mission.py --track balanced
    uv run python launch_universe_mission.py --track deep
    uv run python launch_universe_mission.py --all

Email: manderson240@gmail.com
"""

import asyncio
import argparse
import logging
import sys
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            "/home/mike-anderson/dev/cohezion/logs/universe_mission.log"
        ),
    ],
)

logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(
        description="ASCENDED COHEZION - Autonomous Universe Simulation"
    )
    parser.add_argument(
        "--track",
        choices=["rapid", "balanced", "deep", "all"],
        help="Which track to launch",
    )
    parser.add_argument(
        "--email", default="manderson240@gmail.com", help="Email for notifications"
    )
    parser.add_argument(
        "--status", action="store_true", help="Show current mission status"
    )
    parser.add_argument(
        "--test", action="store_true", help="Run short test (1 hour per track)"
    )

    args = parser.parse_args()

    logger.info("🌌 ASCENDED COHEZION - Universe Simulation Launcher")
    logger.info(f"   Time: {datetime.now().isoformat()}")
    logger.info(f"   Email: {args.email}")

    try:
        import sys
        import os

        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

        from cohezion.swarm.autonomous_universe_mission import (
            AutonomousUniverseMission,
            TrackType,
            get_mission_orchestrator,
        )

        orchestrator = get_mission_orchestrator(args.email)

        if args.status:
            # Show current status
            status = orchestrator.get_all_missions()
            print("\n" + "=" * 60)
            print("ASCENDED COHEZION - Mission Status")
            print("=" * 60)

            if status["active"]:
                print(f"\n🟢 ACTIVE MISSIONS ({len(status['active'])}):")
                for mission in status["active"]:
                    print(f"  • {mission['mission_id']}")
                    print(f"    Track: {mission['track_type']}")
                    print(f"    Status: {mission['status']}")
                    print(f"    Progress: {mission['progress']}")
                    print()
            else:
                print("\n⚪ No active missions")

            if status["history"]:
                print(f"\n📜 RECENT HISTORY ({len(status['history'])} missions):")
                for mission in status["history"][-5:]:  # Last 5
                    print(
                        f"  • {mission['mission_id']}: {mission['status']} ({mission.get('duration_hours', 'N/A')}h)"
                    )

            print("\n" + "=" * 60)

        elif args.track:
            # Launch specific track(s)
            if args.track == "all":
                logger.info("Launching ALL tracks...")
                missions = await orchestrator.start_all_tracks()
                print("\n✅ All tracks launched:")
                for track, mission_id in missions:
                    print(f"  {track}: {mission_id}")

            else:
                track_map = {
                    "rapid": TrackType.RAPID,
                    "balanced": TrackType.BALANCED,
                    "deep": TrackType.DEEP,
                }

                track_type = track_map[args.track]

                if args.test:
                    # Override duration for testing
                    logger.info(f"🧪 TEST MODE: Launching {args.track} track (1 hour)")
                    # Note: In test mode, we'd override the config - implementation pending

                mission_id = await orchestrator.start_track(track_type)

                print(f"\n✅ Mission launched:")
                print(f"  ID: {mission_id}")
                print(f"  Track: {args.track}")
                print(f"  Email: {args.email}")
                print(f"\nDashboard will be available at:")
                print(f"  http://localhost:8000/{mission_id}_live.html")

                # If not test mode, wait for completion
                if not args.test:
                    print("\n⏳ Mission running in background...")
                    print("   You will receive email notifications at milestones.")
                    print("   Use --status to check progress.")

        else:
            parser.print_help()

    except ImportError as e:
        logger.error(f"Import error: {e}")
        print("\n❌ Error: Could not import required modules.")
        print("   Make sure you're in the correct Python environment.")
        print("   Try: uv run python launch_universe_mission.py")

    except Exception as e:
        logger.exception("Unexpected error")
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
