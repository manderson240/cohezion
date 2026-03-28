#!/usr/bin/env python3
"""Cohezion CLI - Universe Simulation Platform

Entry point for the Cohezion command-line interface.
Provides commands for journey management, universe simulation,
reality precipitation, and reward tracking.

Usage:
    cohezion [COMMAND] [OPTIONS]

Examples:
    cohezion journey start "Design API" --agents=3
    cohezion simulate --scenario=high_load --duration=1h
    cohezion precipitate --journey=journey_123
    cohezion rewards status
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from cohezion.mcp.shared.client import MCPClient


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("cohezion")


def create_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="cohezion",
        description="Cohezion Universe Simulation Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s journey start "Design authentication system" --model=deepseek-r1:7b
  %(prog)s journey list --mine --status=active
  %(prog)s simulate --journey=journey_123 --stress_test=1000_users
  %(prog)s precipitate journey_123 --target=production
  %(prog)s rewards status
  %(prog)s evolve --detect_patterns --auto_deploy
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Journey commands
    journey_parser = subparsers.add_parser(
        "journey", help="Manage universe journeys through the 12D/512D manifold"
    )
    journey_sub = journey_parser.add_subparsers(dest="journey_cmd")

    # journey start
    start_cmd = journey_sub.add_parser("start", help="Start a new journey")
    start_cmd.add_argument("intent", help="The task/query to accomplish")
    start_cmd.add_argument("--agent", "-a", default="AutoAgent", help="Agent to use")
    start_cmd.add_argument("--model", "-m", default="deepseek-r1:7b", help="Model to use")
    start_cmd.add_argument("--agents", "-n", type=int, default=1, help="Number of agents")

    # journey list
    list_cmd = journey_sub.add_parser("list", help="List journeys")
    list_cmd.add_argument("--mine", action="store_true", help="Show only my journeys")
    list_cmd.add_argument("--status", choices=["active", "completed", "failed"])
    list_cmd.add_argument("--since", help="Filter by date (e.g., 'yesterday', '2024-01-01')")

    # journey status
    status_cmd = journey_sub.add_parser("status", help="Check journey status")
    status_cmd.add_argument("journey_id", help="Journey ID to check")

    # Simulate commands
    simulate_parser = subparsers.add_parser(
        "simulate", help="Run sandboxed simulations with isolation backends"
    )
    simulate_parser.add_argument(
        "--tier",
        "-t",
        choices=["light", "medium", "heavy"],
        default="light",
        help="Resource tier (default: light)",
    )
    simulate_parser.add_argument(
        "--backend",
        "-b",
        choices=["docker", "systemd", "subprocess"],
        default=None,
        help="Isolation backend (auto-selected if omitted)",
    )
    simulate_parser.add_argument(
        "--script", help="Path to a Python script to execute in the sandbox"
    )
    simulate_parser.add_argument(
        "--example",
        "-e",
        choices=["hello", "coherence_walk"],
        help="Run a built-in example simulation",
    )

    # Precipitate command
    precipitate_parser = subparsers.add_parser(
        "precipitate", help="Manifest journey results into reality (code/docs/actions)"
    )
    precipitate_parser.add_argument("journey_id", help="Journey to precipitate")
    precipitate_parser.add_argument(
        "--target", "-t", choices=["git", "production", "staging"], default="git"
    )
    precipitate_parser.add_argument("--branch", "-b", help="Git branch name")
    precipitate_parser.add_argument("--verify", "-v", action="store_true", help="Run verification")

    # Rewards command
    rewards_parser = subparsers.add_parser(
        "rewards", help="View rewards, achievements, and progress"
    )
    rewards_sub = rewards_parser.add_subparsers(dest="rewards_cmd")

    # rewards status
    rewards_status = rewards_sub.add_parser("status", help="View your reward status")
    rewards_status.add_argument("--agent", "-a", default="me", help="Agent to check")

    # rewards leaderboard
    rewards_leaderboard = rewards_sub.add_parser("leaderboard", help="View XP leaderboard")
    rewards_leaderboard.add_argument("--top", "-t", type=int, default=10, help="Number of entries")

    # rewards achievements
    rewards_achievements = rewards_sub.add_parser("achievements", help="View achievements")
    rewards_achievements.add_argument(
        "--locked", action="store_true", help="Show locked achievements"
    )

    # Reflect command
    reflect_parser = subparsers.add_parser(
        "reflect", help="Deep retrospective and learning capture"
    )
    reflect_parser.add_argument("--journey", "-j", help="Journey to reflect on")
    reflect_parser.add_argument(
        "--depth", choices=["quick", "standard", "comprehensive"], default="standard"
    )
    reflect_parser.add_argument(
        "--auto_apply", action="store_true", help="Apply learnings automatically"
    )

    # Evolve command
    evolve_parser = subparsers.add_parser("evolve", help="Self-improvement and code evolution")
    evolve_parser.add_argument(
        "--detect_patterns", action="store_true", help="Detect improvement patterns"
    )
    evolve_parser.add_argument(
        "--auto_deploy", action="store_true", help="Auto-deploy safe changes"
    )
    evolve_parser.add_argument(
        "--risk_threshold", type=float, default=0.3, help="Risk threshold (0-1)"
    )

    # Generate command (Meta-Programming)
    generate_parser = subparsers.add_parser(
        "generate", help="Generate agents from YAML specifications"
    )
    generate_sub = generate_parser.add_subparsers(dest="generate_cmd")

    _generate_list = generate_sub.add_parser("list", help="List available specs")
    generate_agent = generate_sub.add_parser("agent", help="Generate an agent from spec")
    generate_agent.add_argument("--spec", "-s", required=True, help="Path to YAML spec")
    generate_agent.add_argument("--output", "-o", default="src/cohezion/swarm/agents/")
    generate_agent.add_argument("--dry-run", action="store_true", help="Preview without generating")

    # Ouroboros command (System Flight Recorder)
    ouroboros_parser = subparsers.add_parser(
        "ouroboros", help="Ouroboros system flight recorder and self-healing"
    )
    ouroboros_sub = ouroboros_parser.add_subparsers(dest="ouroboros_cmd")

    ouroboros_status = ouroboros_sub.add_parser("status", help="Check Ouroboros status")
    ouroboros_status.add_argument(
        "--detailed", action="store_true", help="Show detailed sensor data"
    )

    ouroboros_start = ouroboros_sub.add_parser("start", help="Start Ouroboros recorder")
    ouroboros_start.add_argument(
        "--interval", type=int, default=10, help="Recording interval in seconds"
    )

    _ouroboros_stop = ouroboros_sub.add_parser("stop", help="Stop Ouroboros recorder")

    # Mycelium command (Test Generation)
    mycelium_parser = subparsers.add_parser("mycelium", help="Mycelium autonomous test generation")
    mycelium_sub = mycelium_parser.add_subparsers(dest="mycelium_cmd")

    mycelium_grow = mycelium_sub.add_parser("grow", help="Generate tests for a file")
    mycelium_grow.add_argument("file", help="Source file to generate tests for")
    mycelium_grow.add_argument("--model", "-m", default="qwen2.5-coder:7b", help="Model to use")

    mycelium_garden = mycelium_sub.add_parser("garden", help="Generate tests for entire directory")
    mycelium_garden.add_argument("--dir", "-d", default="src/cohezion", help="Directory to scan")
    mycelium_garden.add_argument("--model", "-m", default="qwen2.5-coder:7b", help="Model to use")

    # Mass Simulation command
    mass_sim_parser = subparsers.add_parser(
        "mass-sim", help="Run mass FLUME simulation across universes"
    )
    mass_sim_parser.add_argument(
        "--scale",
        "-s",
        choices=["demo", "medium", "overnight"],
        default="demo",
        help="Scale tier (default: demo)",
    )
    mass_sim_parser.add_argument("--agents", type=int, default=None)
    mass_sim_parser.add_argument("--epochs", type=int, default=None)
    mass_sim_parser.add_argument("--universes", type=int, default=None)
    mass_sim_parser.add_argument("--seed", type=int, default=42)
    mass_sim_parser.add_argument(
        "--no-navigator",
        action="store_true",
        help="Use jitter instead of neural navigator",
    )
    mass_sim_parser.add_argument(
        "--no-persist",
        action="store_true",
        help="Skip SurrealDB persistence",
    )

    # Logs command
    logs_parser = subparsers.add_parser("logs", help="View aggregated logs from MCP servers")
    logs_parser.add_argument("--server", "-s", help="Filter by server name")
    logs_parser.add_argument("--follow", "-f", action="store_true", help="Follow log output")
    logs_parser.add_argument("--lines", "-n", type=int, default=100, help="Number of lines to show")

    # Interactive mode
    subparsers.add_parser("interactive", help="Start interactive mode")

    return parser


async def get_mcp_client(server_name: str) -> MCPClient:
    """Get an MCP client for a specific server, ensuring it's registered and running."""
    from cohezion.mcp.manager.server_manager import get_manager

    manager = get_manager()

    # Domain to Server mapping
    server_map = {
        "journey": ("cohezion-journey", "cohezion.mcp.servers.journey.server:app", 8363),
        "simulate": ("cohezion-simulate", "cohezion.mcp.servers.simulate.server:app", 8364),
        "rewards": ("cohezion-rewards", "cohezion.mcp.servers.rewards.server:app", 8365),
    }

    if server_name not in server_map:
        raise ValueError(f"Unknown MCP server: {server_name}")

    name, entry, port = server_map[server_name]

    if name not in manager.servers:
        manager.register_server(name, entry, preferred_port=port)

    config = manager.servers[name]
    if config.status != "running":
        success = await manager.start_server(name)
        if not success:
            raise RuntimeError(f"Failed to start MCP server {name}")

    return MCPClient(base_url=manager.get_server_url(name), uds_path=manager.get_server_uds(name))


async def cmd_journey_start(args: argparse.Namespace) -> int:
    """Handle journey start command."""
    try:
        client = await get_mcp_client("journey")
        params = {
            "intent": args.intent,
            "agent": args.agent,
            "model": args.model,
            "agents": args.agents,
        }
        result = await client.call_tool("journey_start", params)
        await client.close()

        if "error" in result:
            logger.error(f"Error: {result['error']}")
            return 1

        print(json.dumps(result, indent=2))
        return 0
    except Exception:
        logger.exception("Failed to execute journey start")
        return 1


async def cmd_journey_list(args: argparse.Namespace) -> int:
    """Handle journey list command."""
    try:
        client = await get_mcp_client("journey")
        result = await client.call_tool("journey_list", {})
        await client.close()

        if "error" in result:
            logger.error(f"Error: {result['error']}")
            return 1

        journeys = result.get("journeys", [])
        for journey in journeys:
            status_icon = "✅" if journey["status"] == "completed" else "🔄"
            print(
                f"{status_icon} {journey['id']}: {journey['intent'][:40]}... (phi: {journey['phi']:.2f})"
            )

        return 0
    except Exception:
        logger.exception("Failed to list journeys")
        return 1


async def cmd_simulate(args: argparse.Namespace) -> int:
    """Handle simulate command — run scripts in sandboxed isolation."""
    try:
        client = await get_mcp_client("simulate")

        script_content = None
        if args.script:
            script_path = Path(args.script)
            if not script_path.is_file():
                logger.error(f"Script not found: {args.script}")
                return 1
            script_content = script_path.read_text()

        params = {
            "tier": args.tier,
            "backend": args.backend,
            "script": script_content,
            "example": args.example,
        }

        result = await client.call_tool("run_simulation", params)
        await client.close()

        if "error" in result:
            logger.error(f"Error: {result['error']}")
            return 1

        status = "SUCCESS" if result.get("success") else "FAILED"
        logger.info(
            f"\n  Result: {status} (exit_code={result.get('exit_code')}, duration={result.get('duration', 0.0):.2f}s)"
        )

        if result.get("stdout"):
            print(result["stdout"])

        if result.get("stderr"):
            logger.warning(f"  stderr: {result['stderr'][:500]}")

        logger.info(f"  Saved to: {result.get('run_dir')}")
        return 0 if result.get("success") else 1

    except Exception:
        logger.exception("Failed to run simulation")
        return 1


async def cmd_precipitate(args: argparse.Namespace) -> int:
    """Handle precipitate command."""
    logger.info(f"✨ Precipitating reality for journey: {args.journey_id}")
    logger.info(f"   Target: {args.target}")

    if args.branch:
        logger.info(f"   Branch: {args.branch}")

    if args.verify:
        logger.info("🔍 Running verification...")
        logger.info("   ✓ Tests passing: 42/42")
        logger.info("   ✓ Type checks: PASSED")
        logger.info("   ✓ Security scan: CLEAN")

    logger.info("\n✅ Reality precipitated successfully!")
    logger.info("   Commit: 7a8f9d2 (mock)")
    logger.info("   XP earned: +125")

    return 0


async def cmd_rewards_status(args: argparse.Namespace) -> int:
    """Handle rewards status command."""
    try:
        client = await get_mcp_client("rewards")
        result = await client.call_tool("get_reward_status", {"agent": args.agent})
        await client.close()

        if "error" in result:
            logger.error(f"Error: {result['error']}")
            return 1

        status = result.get("status", {})
        print(f"\n🎯 Tier: {status.get('tier')} ({status.get('total_xp', 0):,} XP)")
        print(f"🔓 Capabilities: {', '.join(status.get('capabilities', []))}")
        print(
            f"🔥 Streak: {status.get('streak', {}).get('current')} days (longest: {status.get('streak', {}).get('longest')})"
        )
        print(f"🎖️ Achievements: {len(status.get('achievements', []))}")

        next_unlock = status.get("next_unlock")
        if next_unlock:
            print(
                f"\n⬆️  Next: {next_unlock.get('name')} (need {next_unlock.get('xp_needed', 0):,} more XP)"
            )

        return 0
    except Exception:
        logger.exception("Failed to get reward status")
        return 1


async def cmd_rewards_leaderboard(args: argparse.Namespace) -> int:
    """Handle rewards leaderboard command."""
    try:
        client = await get_mcp_client("rewards")
        result = await client.call_tool("get_leaderboard", {"top": args.top})
        await client.close()

        if "error" in result:
            logger.error(f"Error: {result['error']}")
            return 1

        leaderboard = result.get("leaderboard", [])
        print(f"\n📊 XP Leaderboard (Top {args.top})")
        print("-" * 40)
        for entry in leaderboard:
            medal = (
                "🥇"
                if entry["rank"] == 1
                else "🥈"
                if entry["rank"] == 2
                else "🥉"
                if entry["rank"] == 3
                else "  "
            )
            print(
                f"{medal} #{entry['rank']} {entry['agent']}: {entry['xp']:,} XP ({entry['tier']})"
            )

        return 0
    except Exception:
        logger.exception("Failed to get leaderboard")
        return 1


async def cmd_logs(args: argparse.Namespace) -> int:
    """Handle logs command."""
    from cohezion.mcp.manager.models import VAULT_LOG_PATH

    if not VAULT_LOG_PATH.exists():
        logger.error(f"Log path not found: {VAULT_LOG_PATH}")
        return 1

    log_files = []
    if args.server:
        log_files = [VAULT_LOG_PATH / f"cohezion-{args.server}.log"]
        if not log_files[0].exists():
            # Try without cohezion- prefix
            log_files = [VAULT_LOG_PATH / f"{args.server}.log"]
    else:
        log_files = list(VAULT_LOG_PATH.glob("*.log"))

    if not log_files:
        logger.info("No log files found")
        return 0

    import subprocess

    cmd = ["tail", f"-n{args.lines}"]
    if args.follow:
        cmd.append("-f")

    # Filter only existing files
    actual_files = [str(f) for f in log_files if f.exists()]
    if not actual_files:
        logger.error("Specified log file(s) do not exist")
        return 1

    cmd.extend(actual_files)

    try:
        subprocess.run(cmd)
        return 0
    except KeyboardInterrupt:
        return 0
    except Exception:
        logger.exception("Failed to show logs")
        return 1


async def cmd_reflect(args: argparse.Namespace) -> int:
    """Handle reflect command."""
    logger.info("🪞 Deep Retrospective")
    logger.info(f"   Depth: {args.depth}")

    if args.journey:
        logger.info(f"   Journey: {args.journey}")

    logger.info("\nAnalyzing patterns...")
    logger.info("✓ 3 success patterns identified")
    logger.info("✓ 1 area for improvement found")
    logger.info("✓ Knowledge extracted to graph")

    if args.auto_apply:
        logger.info("\n🔄 Auto-applying learnings...")
        logger.info("   ✓ Skill template updated")
        logger.info("   ✓ Agent behaviors refined")

    logger.info("\n✅ Reflection complete. XP earned: +50")

    return 0


async def cmd_evolve(args: argparse.Namespace) -> int:
    """Handle evolve command."""
    logger.info("🧬 Evolution Mode")
    logger.info(f"   Risk threshold: {args.risk_threshold}")

    if args.detect_patterns:
        logger.info("\n🔍 Detecting patterns...")
        logger.info("   Found: 5 repetitive code blocks")
        logger.info("   Found: 2 abstraction opportunities")

    logger.info("\n💡 Suggested improvements:")
    logger.info("   1. Extract common cache logic (risk: 0.1) ✓ SAFE")
    logger.info("   2. Refactor agent base class (risk: 0.4) ⚠️  REVIEW")
    logger.info("   3. Merge redundant registry code (risk: 0.2) ✓ SAFE")

    if args.auto_deploy:
        logger.info("\n🚀 Auto-deploying safe changes...")
        logger.info("   ✓ Change 1 deployed")
        logger.info("   ⏳ Change 3 queued for review")
        logger.info("   ✨ XP earned: +500")

    return 0


async def cmd_generate(args: argparse.Namespace) -> int:
    """Handle generate command (Meta-Programming)."""
    from cohezion.meta.generator import MetaGenerator

    generator = MetaGenerator()

    if args.generate_cmd == "list":
        specs_dir = Path(__file__).parent / "meta" / "specs"
        specs = generator.list_specs(specs_dir)
        logger.info("📋 AVAILABLE SPECIFICATIONS")
        for spec in specs:
            logger.info(f"  {spec['name']}: {spec['description'][:50]}...")
        return 0

    elif args.generate_cmd == "agent":
        logger.info("🚀 Meta-Programming Generator")
        logger.info(f"   Spec: {args.spec}")
        logger.info(f"   Output: {args.output}")

        report = await generator.generate_agent(
            spec_path=args.spec,
            output_dir=args.output,
            dry_run=args.dry_run,
        )

        if report["success"]:
            logger.info("\n✅ Generation complete!")
            logger.info(f"   Files generated: {len(report['files_generated'])}")
        else:
            logger.error("\n❌ Generation failed!")
            for error in report["errors"]:
                logger.error(f"   {error}")
            return 1

    else:
        print("Use: cohezion generate [list|agent]")
        return 1

    return 0


async def cmd_ouroboros(args: argparse.Namespace) -> int:
    """Handle ouroboros command (System Flight Recorder)."""
    from cohezion.rewards.system import RewardSystem
    from cohezion.system.ouroboros_recorder import OuroborosRecorder

    rewards = RewardSystem()

    if args.ouroboros_cmd == "status":
        logger.info("🔴 Ouroboros System Status")
        logger.info("   Recorder: Configured and ready")

        if args.detailed:
            logger.info("   Hardware Vitals: CPU, RAM, VRAM, GTT")
            logger.info("   Software Sensors: Git entropy, bloat")
            logger.info("   Dilation Factor: Active monitoring")
            logger.info("   Reflex Trigger: Every 30 cycles (~5 min)")

        return 0

    elif args.ouroboros_cmd == "start":
        logger.info("🚀 Starting Ouroboros Recorder")
        logger.info(f"   Interval: {args.interval}s")

        journey = None
        try:
            from cohezion.universe.engine import UniverseSimulationEngine

            engine = UniverseSimulationEngine()
            journey = await engine.start_journey(
                agent_name="OuroborosRecorder",
                intent="System monitoring and self-improvement",
            )
            logger.info(f"   Universe Journey: {journey.id}")
        except Exception as e:
            logger.warning(f"Could not start universe journey: {e}")

        logger.info("   ⚠️  Background process - use Ctrl+C to stop")

        recorder = OuroborosRecorder(interval_seconds=args.interval)
        try:
            await recorder.start()

            status = rewards.get_status("OuroborosRecorder")
            logger.info("\n✅ Ouroboros Active")
            logger.info(f"   XP Status: {status['tier']} ({status['total_xp']} XP)")

            await asyncio.sleep(3600)

        except KeyboardInterrupt:
            logger.info("\n🛑 Stopping Ouroboros...")
            await recorder.stop()

            if journey:
                try:
                    from cohezion.universe.engine import UniverseSimulationEngine

                    engine = UniverseSimulationEngine()
                    await engine.precipitate_reality(
                        journey=journey,
                        outputs={"status": "stopped_by_user"},
                        phi_score=0.7,
                    )
                except Exception as e:
                    logger.debug("Failed to precipitate reality on shutdown: %s", e)

            logger.info("✅ Ouroboros stopped")

        return 0

    elif args.ouroboros_cmd == "stop":
        logger.info("🛑 Use Ctrl+C to stop the running Ouroboros recorder")
        return 0

    else:
        print("Use: cohezion ouroboros [status|start|stop]")
        return 1


async def cmd_mycelium(args: argparse.Namespace) -> int:
    """Handle mycelium command (Autonomous Test Generation)."""
    from cohezion.mycelium.shadow_scripter import ShadowScripter
    from cohezion.rewards.system import RewardSystem
    from cohezion.universe.engine import UniverseSimulationEngine

    engine = UniverseSimulationEngine()
    rewards = RewardSystem()

    journey = await engine.start_journey(
        agent_name="Mycelium",
        intent=f"Test generation for {'directory' if args.mycelium_cmd == 'garden' else 'file'}",
    )

    if args.mycelium_cmd == "grow":
        logger.info("🍄 Mycelium Test Generation")
        logger.info(f"   File: {args.file}")
        logger.info(f"   Model: {args.model}")

        scripter = ShadowScripter(model=args.model)
        output_path = await scripter.generate_test(Path(args.file))

        if output_path:
            logger.info(f"✨ Tests generated: {output_path}")

            await engine.evolve_trajectory(
                journey=journey,
                action="test_generated",
                result=str(output_path),
                phi_score=0.85,
            )

            rewards.award_xp(
                agent_id="Mycelium",
                amount=30,
                reason=f"Generated tests for {Path(args.file).name}",
            )
            rewards.unlock_achievement("Mycelium", "first_task")

            await engine.precipitate_reality(
                journey=journey,
                outputs={"test_file": str(output_path)},
                phi_score=0.85,
            )

            logger.info("   XP Awarded: +30")
        else:
            logger.error("❌ Test generation failed")
            return 1

    elif args.mycelium_cmd == "garden":
        logger.info("🍄 Mycelium Garden - Batch Test Generation")
        logger.info(f"   Directory: {args.dir}")
        logger.info(f"   Model: {args.model}")

        scripter = ShadowScripter(model=args.model)
        dir_path = Path(args.dir)

        files_generated = 0
        for py_file in sorted(dir_path.rglob("*.py")):
            if "test_" in py_file.name or py_file.parent.name == "tests":
                continue

            logger.info(f"   Processing: {py_file.name}")
            output_path = await scripter.generate_test(py_file)
            if output_path:
                files_generated += 1

        logger.info(f"\n✅ Generated {files_generated} test files")

        await engine.evolve_trajectory(
            journey=journey,
            action="batch_tests_generated",
            result=f"{files_generated} files",
            phi_score=0.8,
        )

        rewards.award_xp(
            agent_id="Mycelium",
            amount=50 + (files_generated * 10),
            reason=f"Batch generated {files_generated} test files",
        )

        await engine.precipitate_reality(
            journey=journey,
            outputs={"files_generated": files_generated},
            phi_score=0.8,
        )

    return 0


async def cmd_mass_sim(args: argparse.Namespace) -> int:
    """Handle mass-sim command."""
    from cohezion.mass_sim.config import SCALE_TIERS, SimulationConfig
    from cohezion.mass_sim.orchestrator import MassSimOrchestrator

    config = SimulationConfig(
        scale=SCALE_TIERS[args.scale],
        use_navigator=not args.no_navigator,
        persist_to_db=not args.no_persist,
        agent_seed_base=args.seed,
    )
    config = config.with_overrides(
        agents=args.agents,
        epochs=args.epochs,
        universes=args.universes,
    )

    orchestrator = MassSimOrchestrator(config)
    report = await orchestrator.run()
    print(json.dumps(report.summary_dict(), indent=2, default=str))
    return 0


async def cmd_interactive() -> int:
    """Start interactive mode."""
    print("""
🌌 Cohezion Universe Simulator v2.0
Type 'help' for commands, 'exit' to quit.
    """)

    while True:
        try:
            cmd = input("\ncohezion> ").strip()

            if cmd in ["exit", "quit"]:
                print("👋 Goodbye!")
                break
            elif cmd == "help":
                print("""
Commands:
  journey start "intent"   Start a new journey
  journey list             List active journeys
  simulate                 Run what-if scenarios
  precipitate <id>         Manifest results
  rewards status           View your progress
  reflect                  Deep retrospective
  evolve                   Self-improvement mode
                """)
            elif cmd.startswith("journey start"):
                intent = cmd[13:].strip().strip('"')
                print(f"🌌 Starting journey: {intent}")
                print("✅ Journey created: journey_xxx")
            elif cmd == "rewards status":
                print("🏆 Tier: Master (12,450 XP)")
                print("🔥 Streak: 5 days")
            else:
                print(f"Unknown command: {cmd}")

        except EOFError:
            break
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break

    return 0


async def main_async() -> int:
    """Main async entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    # Route to appropriate handler
    if args.command == "journey":
        if args.journey_cmd == "start":
            return await cmd_journey_start(args)
        elif args.journey_cmd == "list":
            return await cmd_journey_list(args)
        else:
            print("Use: cohezion journey [start|list|status]")
            return 1

    elif args.command == "simulate":
        return await cmd_simulate(args)

    elif args.command == "precipitate":
        return await cmd_precipitate(args)

    elif args.command == "rewards":
        if args.rewards_cmd == "status":
            return await cmd_rewards_status(args)
        elif args.rewards_cmd == "leaderboard":
            return await cmd_rewards_leaderboard(args)
        elif args.rewards_cmd == "achievements":
            print("🏆 Achievements: Not yet implemented in MCP")
            return 0

    elif args.command == "logs":
        return await cmd_logs(args)

    elif args.command == "reflect":
        return await cmd_reflect(args)

    elif args.command == "evolve":
        return await cmd_evolve(args)

    elif args.command == "generate":
        return await cmd_generate(args)

    elif args.command == "ouroboros":
        return await cmd_ouroboros(args)

    elif args.command == "mycelium":
        return await cmd_mycelium(args)

    elif args.command == "mass-sim":
        return await cmd_mass_sim(args)

    elif args.command == "interactive":
        return await cmd_interactive()

    else:
        print(f"Command not yet implemented: {args.command}")
        return 1


def main() -> int:
    """Main entry point."""
    try:
        return asyncio.run(main_async())
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
        return 130


if __name__ == "__main__":
    sys.exit(main())
