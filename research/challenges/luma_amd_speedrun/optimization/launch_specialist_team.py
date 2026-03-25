#!/usr/bin/env python3
"""
QUICK START: LAUNCH SPECIALIST AGENT TEAM
Immediate deployment of three specialist agents for kernel optimization
"""

import os
import subprocess
import sys
import time
from pathlib import Path


def main():
    print("🚀🚀🚀 LAUNCHING SPECIALIST AGENT TEAM 🚀🚀🚀")
    print("=" * 50)
    print("MXFP4 MoE Specialist | MLA Decode Specialist | MXFP4 GEMM Specialist")
    print("=" * 50)

    # Navigate to optimization directory
    optimization_dir = Path(
        "/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/optimization"
    )
    os.chdir(optimization_dir)

    print(f"📍 Working Directory: {optimization_dir}")
    print()

    # Verify we have the necessary files
    required_files = [
        "quick_start_unstoppable.py",
        "unstoppable_optimization_system.py",
        "progress_tracker.py",
    ]

    missing_files = [f for f in required_files if not (optimization_dir / f).exists()]
    if missing_files:
        print(f"❌ Missing files: {missing_files}")
        return

    print("✅ All required files present")
    print()

    print("🚀 LAUNCHING THREE SPECIALIST AGENTS IN SEPARATE PROCESSES:")
    print()

    # Agent 1: MXFP4 MoE Specialist
    print("🚀 LAUNCHING AGENT ALPHA: MXFP4 MoE Specialist")
    print("   Focus: Expert parallelism & quantization overhead reduction")
    alpha_process = subprocess.Popen(
        [sys.executable, "quick_start_unstoppable.py"], cwd=str(optimization_dir)
    )
    print(f"   ✅ Agent Alpha launched (PID: {alpha_process.pid})")
    print()

    # Brief pause
    time.sleep(1)

    # Agent 2: MLA Decode Specialist
    print("🚀 LAUNCHING AGENT BETA: MLA Decode Specialist")
    print("   Focus: Latent attention computation & KV cache access")
    beta_process = subprocess.Popen(
        [sys.executable, "quick_start_unstoppable.py"], cwd=str(optimization_dir)
    )
    print(f"   ✅ Agent Beta launched (PID: {beta_process.pid})")
    print()

    # Brief pause
    time.sleep(1)

    # Agent 3: MXFP4 GEMM Specialist
    print("🚀 LAUNCHING AGENT GAMMA: MXFP4 GEMM Specialist")
    print("   Focus: Data layout optimization & MFMA instruction scheduling")
    gamma_process = subprocess.Popen(
        [sys.executable, "quick_start_unstoppable.py"], cwd=str(optimization_dir)
    )
    print(f"   ✅ Agent Gamma launched (PID: {gamma_process.pid})")
    print()

    print("🎯 ALL THREE SPECIALIST AGENTS ARE NOW ACTIVE!")
    print()
    print("📊 TO MONITOR COLLECTIVE PROGRESS:")
    print("   In any terminal, run: python3 progress_tracker.py")
    print()
    print("🔄 TO STOP ALL AGENTS (when desired):")
    print("   You'll need to manually terminate each process")
    print("   Or use: pkill -f 'quick_start_unstoppable.py'")
    print()
    print("💡 REMEMBER:")
    print("   Each agent is running quick_start_unstoppable.py")
    print("   They will each:")
    print("   - See their kernel-specific reference implementation")
    print("   - Get immediate hypotheses to test")
    print("   - Guide you through 5-minute optimization cycles")
    print("   - Learn from every attempt (success OR failure)")
    print()
    print("🧠 YOUR ROLE AS ORCHESTRATOR:")
    print("   - Monitor progress with progress_tracker.py")
    print("   - Notice patterns across agents")
    print("   - Facilitate knowledge transfer when you see opportunities")
    print("   - Ensure no valuable insight gets lost in silos")
    print()
    print("⚡ SPECIALIST AGENTS ARE NOW ACTIVE - GO WIN THAT COMPETITION!")
    print("=" * 50)

    # Keep the script running so user can see the PIDs
    try:
        print("💓 Agent processes running... (Press Ctrl+C to exit this monitor)")
        while True:
            time.sleep(5)
            # Check if any processes have terminated
            active_agents = []
            if alpha_process.poll() is None:
                active_agents.append(f"Alpha (PID: {alpha_process.pid})")
            if beta_process.poll() is None:
                active_agents.append(f"Beta (PID: {beta_process.pid})")
            if gamma_process.poll() is None:
                active_agents.append(f"Gamma (PID: {gamma_process.pid})")

            if active_agents:
                print(f"💓 Active agents: {', '.join(active_agents)}")
            else:
                print("😴 All agent processes have completed")
                break

    except KeyboardInterrupt:
        print("\n👋 Monitor stopped. Agent processes continue running in background.")
        print("💡 To stop all agents later: pkill -f 'quick_start_unstoppable.py'")


if __name__ == "__main__":
    main()
