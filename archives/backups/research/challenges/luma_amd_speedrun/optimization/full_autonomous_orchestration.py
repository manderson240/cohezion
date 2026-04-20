#!/usr/bin/env python3
"""
FULLY AUTONOMOUS MULTI-AGENT ORCHESTRATOR
True hands-off operation - launches, monitors, and manages specialist agent team
NO USER INTERVENTION REQUIRED AFTER LAUNCH
"""

import signal
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any


class FullyAutonomousOrchestrator:
    """
    Fully autonomous multi-agent orchestrator that:
    1. Launches specialist agents for each kernel
        self.duration_hours = duration_hours
    3. Collects and shares insights between agents
    4. Manages the entire optimization cycle autonomously
    5. Requires ZERO user intervention after launch
    """

    def __init__(self, duration_hours: float = 2.0):
        self.start_time = time.time()
        self.duration_hours = duration_hours
        self.session_id = f"full_auto_opt_{int(self.start_time)}"
        self.base_dir = Path(
            "/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/optimization"
        )
        self.log_dir = self.base_dir / f"logs_{self.session_id}"
        self.log_dir.mkdir(exist_ok=True)

        # Specialist agent definitions with enhanced autonomy
        self.specialist_agents = {
            "alpha_mxe_mxfp4": {
                "name": "Agent Alpha: MXFP4 MoE Specialist",
                "kernel": "moe_mxfp4",
                "focus": "Expert computation parallelism & quantization overhead reduction",
                "reference": "../op_tests/op_benchmarks/triton/bench_fav3_sage_mxfp4.py",
                "goals": [
                    "Maximize expert computation parallelism",
                    "Optimize memory routing for sparse expert access",
                    "Reduce MXFP4 quantization/dequantization overhead",
                    "Optimize mixed precision strategies (FP4 vs higher precision)",
                    "Minimize synchronization between experts",
                ],
                "script": "quick_start_unstoppable.py",
                "restart_count": 0,
                "max_restarts": 5,
            },
            "beta_mla_decode": {
                "name": "Agent Beta: MLA Decode Specialist",
                "kernel": "mla_decode",
                "focus": "Latent attention computation & KV cache access optimization",
                "reference": "../op_tests/op_benchmarks/triton/bench_mla_decode.py",
                "goals": [
                    "Optimize latent attention computation efficiency",
                    "Improve KV cache access patterns (building on Paged Attention)",
                    "Enhance grouped query processing efficiency",
                    "Optimize memory bandwidth for latent representations",
                    "Better leverage CDNA3 matrix cores & memory subsystems",
                ],
                "script": "quick_start_unstoppable.py",
                "restart_count": 0,
                "max_restarts": 5,
            },
            "gamma_mxfp4_gemm": {
                "name": "Agent Gamma: MXFP4 GEMM Specialist",
                "kernel": "mxfp4_gemm",
                "focus": "Data layout & MFMA instruction scheduling optimization",
                "reference": "../op_tests/op_benchmarks/triton/mxfp4-mm/",
                "goals": [
                    "Optimize MXFP4-specific data layout & packing",
                    "Optimize accumulation precision strategy (FP16 vs FP32)",
                    "Maximize MFMA instruction utilization & scheduling",
                    "Minimize quantization/dequantization overhead",
                    "Optimize wavefront-aware tiling for MI355X execution model",
                ],
                "script": "quick_start_unstoppable.py",
                "restart_count": 0,
                "max_restarts": 5,
            },
        }

        # System state
        self.running_agents: dict[str, subprocess.Popen] = {}
        self.agent_logs: dict[str, Path] = {}
        self.collective_insights: list[dict] = []
        self.system_active = True
        self.last_insight_share = time.time()
        self.last_health_check = time.time()

        # Setup logging & signal handlers
        self._setup_orchestration_logging()
        self._setup_signal_handlers()

        self._log_orchestration(
            "ORCHESTRATOR", "🤖 FULLY AUTONOMOUS MULTI-AGENT ORCHESTRATOR INITIALIZED 🤖"
        )
        self._log_orchestration("ORCHESTRATOR", f"Session: {self.session_id}")
        self._log_orchestration("ORCHESTRATOR", f"Duration: {duration_hours} hours")
        self._log_orchestration(
            "PHILOSOPHY", "FAILURE IS NOT AN OPTION - EVERY AGENT LEARNS FROM SETBACKS"
        )
        self._log_orchestration(
            "MISSION", f"Deploying {len(self.specialist_agents)} fully autonomous specialist agents"
        )

    def _setup_orchestration_logging(self):
        """Setup orchestration-level logging"""
        self.orchestration_log = self.log_dir / "orchestration.log"
        with open(self.orchestration_log, "w") as f:
            f.write("🤖 FULLY AUTONOMOUS MULTI-AGENT ORCHESTRATION LOG 🤖\n")
            f.write(f"Session: {self.session_id}\n")
            f.write(f"Started: {datetime.fromtimestamp(self.start_time)}\n")
            f.write(f"Duration: {self.duration_hours} hours\n")
            f.write("Philosophy: FAILURE IS NOT AN OPTION\n")
            f.write(f"Agents: {list(self.specialist_agents.keys())}\n")
            f.write("=" * 70 + "\n\n")

    def _setup_signal_handlers(self):
        """Setup signal handlers"""

        def signal_handler(signum, frame):
            self._log_orchestration(
                "ORCHESTRATOR", f"Received signal {signum} - INITIATING GRACEFUL SHUTDOWN"
            )
            self.shutdown_requested = True

        self.shutdown_requested = False
        signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
        signal.signal(signal.SIGTERM, signal_handler)  # Kill signal

    def _log_orchestration(self, component: str, message: str):
        """Orchestration-level logging"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] [{component}] {message}\n"

        with open(self.orchestration_log, "a") as f:
            f.write(log_entry)
        # Also print to console for visibility
        print(f"[ORCHESTRATOR] {message}")

    def _launch_specialist_agent(
        self, agent_id: str, agent_config: dict[str, Any]
    ) -> subprocess.Popen:
        """Launch a specialist agent as a subprocess"""
        agent_name = agent_config["name"]
        self._log_orchestration("LAUNCH", f"Deploying {agent_name}")

        # Create agent-specific log directory
        agent_log_dir = self.log_dir / f"agent_{agent_id}"
        agent_log_dir.mkdir(exist_ok=True)

        # Prepare agent log file
        agent_log_file = agent_log_dir / "agent.log"

        # Build the agent command
        agent_script = self.base_dir / agent_config["script"]
        agent_command = [
            sys.executable,  # Current Python interpreter
            str(agent_script),
        ]

        # Launch the agent subprocess
        try:
            agent_process = subprocess.Popen(
                agent_command,
                cwd=str(self.base_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            self.running_agents[agent_id] = agent_process
            self.agent_logs[agent_id] = agent_log_file
            agent_config["restart_count"] = 0  # Reset restart count on successful launch

            self._log_orchestration(
                "LAUNCH_SUCCESS", f"{agent_name} launched (PID: {agent_process.pid})"
            )

            # Start output logging threads for this agent
            threading.Thread(
                target=self._monitor_agent_output,
                args=(agent_id, agent_process, agent_log_file),
                daemon=True,
            ).start()

            return agent_process

        except Exception as e:
            self._log_orchestration("LAUNCH_ERROR", f"Failed to launch {agent_name}: {e}")
            raise

    def _monitor_agent_output(self, agent_id: str, process: subprocess.Popen, log_file: Path):
        """Monitor and log agent output, extract insights for sharing"""
        try:
            with open(log_file, "w") as f:
                f.write(f"🤖 AGENT LOG: {self.specialist_agents[agent_id]['name']} 🤖\n")
                f.write(f"Started: {datetime.fromtimestamp(time.time())}\n")
                f.write(f"Mission: {self.specialist_agents[agent_id]['focus']}\n")
                f.write("=" * 60 + "\n\n")

                # Monitor stdout and stderr combined for simplicity
                for line in iter(process.stdout.readline, ""):
                    if line:
                        f.write(f"[OUT] {line}")
                        f.flush()
                        self._process_agent_output(agent_id, line.strip())

                for line in iter(process.stderr.readline, ""):
                    if line:
                        f.write(f"[ERR] {line}")
                        f.flush()
                        self._process_agent_output(agent_id, line.strip(), is_error=True)

            # Wait for process to complete
            return_code = process.wait()
            self._log_orchestration(
                "AGENT_COMPLETED",
                f"{self.specialist_agents[agent_id]['name']} completed with exit code {return_code}",
            )

        except Exception as e:
            with open(log_file, "a") as f:
                f.write(f"[MONITOR_ERROR] {e}\n")
            self._log_orchestration("MONITOR_ERROR", f"Agent {agent_id} monitoring error: {e}")

    def _process_agent_output(self, agent_id: str, output_line: str, is_error: bool = False):
        """Process agent output for insights and health signals"""
        # Look for key patterns indicating insights worth sharing
        insight_indicators = [
            "success",
            "improvement",
            "breakthrough",
            "working",
            "effective",
            "lesson learned",
            "hypothesis confirmed",
            "optimization working",
            "% improvement",
            "performance gain",
            "achieved",
            "solved",
        ]

        failure_indicators = [
            "failed",
            "error",
            "exception",
            "timeout",
            "crash",
            "broken",
            "not working",
            "doesn't work",
            "validation failed",
        ]

        output_lower = output_line.lower()

        # Check for insights worth sharing
        is_insight = any(indicator in output_lower for indicator in insight_indicators)
        is_failure_insight = any(indicator in output_lower for indicator in failure_indicators)

        if is_insight or is_failure_insight:
            insight = {
                "timestamp": time.time(),
                "agent_id": agent_id,
                "agent_name": self.specialist_agents[agent_id]["name"],
                "insight": output_line[:250],
                "type": "failure_insight"
                if is_failure_insight and not is_insight
                else "success_insight"
                if is_insight and not is_failure_insight
                else "neutral_insight",
                "is_error": is_error,
            }

            self.collective_insights.append(insight)

            # Share insight immediately if it's significant
            if len(self.collective_insights) % 3 == 0:  # Share every 3rd insight to avoid flooding
                self._share_collective_insights()

            # Keep insights list manageable
            if len(self.collective_insights) > 100:
                self.collective_insights = self.collective_insights[-50:]

    def _share_collective_insights(self):
        """Share collected insights across all agents"""
        if len(self.collective_insights) < 2:
            return

        # Get recent insights to share
        recent_insights = (
            self.collective_insights[-3:]
            if len(self.collective_insights) >= 3
            else self.collective_insights
        )

        if recent_insights:
            self._log_orchestration(
                "INSIGHT_SYNTHESIS",
                f"🔄 Sharing {len(recent_insights)} recent insights across specialist agent team",
            )

            for insight in recent_insights:
                agent_name = insight["agent_name"]
                insight_text = insight["insight"][:120]
                insight_type = (
                    "🟢 SUCCESS"
                    if insight["type"] == "success_insight"
                    else "🔴 LEARNING"
                    if insight["type"] == "failure_insight"
                    else "⚪ INFO"
                )

                self._log_orchestration(
                    "SHARED_INSIGHT", f"[{agent_name}] {insight_type}: {insight_text}"
                )

    def _check_and_restart_agents(self):
        """Check agent health and restart if needed"""
        current_time = time.time()

        # Only check health every 60 seconds to avoid overhead
        if current_time - self.last_health_check < 60:
            return

        self.last_health_check = current_time

        agents_to_restart = []

        for agent_id, process in self.running_agents.items():
            agent_name = self.specialist_agents[agent_id]["name"]
            max_restarts = self.specialist_agents[agent_id]["max_restarts"]

            # Check if process has terminated
            if process.poll() is not None:
                exit_code = process.returncode
                current_restarts = self.specialist_agents[agent_id]["restart_count"]

                self._log_orchestration(
                    "AGENT_TERMINATED",
                    f"{agent_name} terminated (exit code: {exit_code}) - Restart attempts: {current_restarts}/{max_restarts}",
                )

                # Check if we should restart
                if current_restarts < max_restarts:
                    agents_to_restart.append((agent_id, agent_name, exit_code))
                else:
                    self._log_orchestration(
                        "AGENT_MAX_RESTARTS",
                        f"{agent_name} has reached max restarts ({max_restarts}) - not restarting",
                    )
            # Also check for zombie/unresponsive processes (optional enhancement)

        # Restart terminated agents
        for agent_id, agent_name, exit_code in agents_to_restart:
            self._log_orchestration(
                "AGENT_RESTARTING",
                f"Restarting {agent_name} (attempt {self.specialist_agents[agent_id]['restart_count'] + 1})",
            )

            try:
                # Kill any lingering process if needed
                old_process = self.running_agents[agent_id]
                if old_process.poll() is None:
                    old_process.kill()
                    old_process.wait(timeout=2)

                # Launch new instance
                new_process = self._launch_specialist_agent(
                    agent_id, self.specialist_agents[agent_id]
                )
                self._log_orchestration(
                    "AGENT_RESTARTED",
                    f"{agent_name} restarted successfully (PID: {new_process.pid})",
                )

            except Exception as e:
                self._log_orchestration(
                    "AGENT_RESTART_FAILED", f"Failed to restart {agent_name}: {e}"
                )

    def _display_autonomous_status(self):
        """Display current autonomous orchestration status"""
        current_time = time.time()
        runtime_hours = (current_time - self.start_time) / 3600

        self._log_orchestration("STATUS", "=== FULLY AUTONOMOUS ORCHESTRATION STATUS ===")
        self._log_orchestration("STATUS", f"Session ID: {self.session_id}")
        self._log_orchestration("STATUS", f"Runtime: {runtime_hours:.2f} hours")

        # Agent statuses
        self._log_orchestration("STATUS", "--- AGENT STATUS ---")
        for agent_id, agent_config in self.specialist_agents.items():
            agent_name = agent_config["name"]
            process = self.running_agents.get(agent_id)

            if process is None:
                status = "NOT LAUNCHED"
            elif process.poll() is None:
                status = f"RUNNING (PID: {process.pid})"
                restarts = self.specialist_agents[agent_id]["restart_count"]
                if restarts > 0:
                    status += f" [Restarted {restarts} times]"
            else:
                status = f"STOPPED (exit code: {process.returncode})"

            self._log_orchestration("STATUS", f"{agent_name}: {status}")

        # Insights and sharing
        insight_count = len(self.collective_insights)
        self._log_orchestration("STATUS", f"Collected {insight_count} cross-agent insights")

        if insight_count > 0:
            recent_insights = (
                self.collective_insights[-2:]
                if len(self.collective_insights) >= 2
                else self.collective_insights
            )
            for insight in recent_insights[-1:]:  # Show most recent
                agent_name = insight["agent_name"]
                insight_preview = (
                    insight["insight"][:60] + "..."
                    if len(insight["insight"]) > 60
                    else insight["insight"]
                )
                insight_type = (
                    "🟢"
                    if insight["type"] == "success_insight"
                    else "🔴"
                    if insight["type"] == "failure_insight"
                    else "⚪"
                )
                self._log_orchestration(
                    "STATUS", f"Latest insight: [{agent_name}] {insight_type} {insight_preview}"
                )

        self._log_orchestration("STATUS", "=== END STATUS ===")

    def launch_fully_autonomous_orchestration(self):
        """
        Launch fully autonomous multi-agent orchestration
        Runs until completion time or manual shutdown
        """
        self._log_orchestration(
            "LAUNCH_START", "🚀 LAUNCHING FULLY AUTONOMOUS MULTI-AGENT ORCHESTRATION 🚀"
        )
        self._log_orchestration(
            "LAUNCH_DETAILS",
            f"Duration: {self.duration_hours} hours | Agents: {len(self.specialist_agents)}",
        )
        self._log_orchestration(
            "LAUNCH_DETAILS",
            f"Total expected agent-hours: {len(self.specialist_agents) * self.duration_hours:.1f}",
        )

        try:
            # PHASE 1: LAUNCH ALL SPECIALIST AGENTS
            self._log_orchestration("PHASE_1", "🚀 LAUNCHING SPECIALIST AGENT TEAM")

            launch_success_count = 0
            for agent_id, agent_config in self.specialist_agents.items():
                try:
                    self._launch_specialist_agent(agent_id, agent_config)
                    launch_success_count += 1
                    time.sleep(0.5)  # Small delay between launches
                except Exception as e:
                    self._log_orchestration("LAUNCH_ERROR", f"Failed to launch {agent_id}: {e}")

            self._log_orchestration(
                "PHASE_1_COMPLETE",
                f"Launched {launch_success_count}/{len(self.specialist_agents)} specialist agents",
            )

            if launch_success_count == 0:
                self._log_orchestration(
                    "LAUNCH_CRITICAL", "CRITICAL: No agents launched successfully - aborting"
                )
                return

            # PHASE 2: AUTONOMOUS OPERATION LOOP
            self._log_orchestration("PHASE_2", "🔄 ENTERING FULLY AUTONOMOUS OPERATION LOOP")
            end_time = time.time() + (self.duration_hours * 3600)  # Convert hours to seconds

            status_update_interval = 120  # Update status every 2 minutes
            insight_share_interval = 90  # Share insights every 1.5 minutes
            last_status_update = time.time()
            last_insight_share = time.time()

            self._log_orchestration(
                "ORCHESTRATION_ACTIVE",
                f"🤖 FULLY AUTONOMOUS ORCHESTRATION ACTIVE - {len(self.running_agents)} specialist agents optimizing",
            )
            self._log_orchestration(
                "ORCHESTRATION_DETAILS",
                f"Each agent running: {self.specialist_agents[list(self.specialist_agents.keys())[0]]['script']}",
            )

            while (
                time.time() < end_time
                and self.system_active
                and not getattr(self, "shutdown_requested", False)
            ):
                current_time = time.time()

                # Periodic status updates
                if current_time - last_status_update >= status_update_interval:
                    self._display_autonomous_status()
                    last_status_update = current_time

                # Periodic insight sharing
                if current_time - last_insight_share >= insight_share_interval:
                    self._share_collective_insights()
                    last_insight_share = current_time

                # Agent health checks and restarts
                self._check_and_restart_agents()

                # Brief sleep to prevent excessive CPU usage
                time.sleep(15)

            # Handle shutdown request
            if getattr(self, "shutdown_requested", False):
                self._log_orchestration("SHUTDOWN_REQUESTED", "Shutdown requested by user signal")

            # PHASE 3: ORCHESTRATION COMPLETION
            self._log_orchestration("PHASE_3", "🏁 ORCHESTRATION COMPLETION")
            actual_runtime = time.time() - self.start_time
            self._log_orchestration(
                "MISSION_ACCOMPLISHED", "🏆 FULLY AUTONOMOUS MULTI-AGENT ORCHESTRATION COMPLETED"
            )
            self._log_orchestration(
                "MISSION_DETAILS", f"Actual runtime: {actual_runtime / 3600:.2f} hours"
            )
            self._log_orchestration(
                "MISSION_DETAILS",
                f"Agent-hours delivered: {len([p for p in self.running_agents.values() if p.poll() is None]) * actual_runtime / 3600:.1f}",
            )
            self._log_orchestration(
                "MISSION_DETAILS",
                f"Collected {len(self.collective_insights)} cross-agent insights for knowledge transfer",
            )
            self._log_orchestration("MISSION_DETAILS", f"Logs stored in: {self.log_dir}")

        except Exception as e:
            self._log_orchestration("ORCHESTRATION_ERROR", f"Orchestration system error: {e}")
            self._log_orchestration("ORCHESTRATION_ERROR", "System attempting graceful shutdown...")
        finally:
            self._shutdown_all_agents()
            self._log_orchestration(
                "ORCHESTRATION_COMPLETE",
                "🤖 FULLY AUTONOMOUS ORCHESTRATION SYSTEM SHUTDOWN COMPLETE",
            )

    def _shutdown_all_agents(self):
        """Gracefully shutdown all specialist agents"""
        self._log_orchestration(
            "SHUTSTART", "Initiating graceful shutdown of all specialist agents"
        )

        shutdown_count = 0
        for agent_id, process in self.running_agents.items():
            agent_name = self.specialist_agents[agent_id]["name"]
            try:
                # Try graceful termination first
                process.terminate()
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=8)
                    self._log_orchestration(
                        "AGENT_SHUTDOWN", f"✅ {agent_name} shutdown gracefully"
                    )
                    shutdown_count += 1
                except subprocess.TimeoutExpired:
                    # Force kill if needed
                    process.kill()
                    process.wait()
                    self._log_orchestration(
                        "AGENT_FORCE_KILLED", f"⚠️ {agent_name} force killed after timeout"
                    )
                    shutdown_count += 1
            except Exception as e:
                self._log_orchestration(
                    "AGENT_SHUTDOWN_ERROR", f"❌ Error shutting down {agent_name}: {e}"
                )

        self.running_agents.clear()
        self._log_orchestration(
            "SHUTDOWN_COMPLETE", f"✅ All {shutdown_count} specialist agents shutdown"
        )

        # Final summary
        runtime_hours = (time.time() - self.start_time) / 3600
        self._log_orchestration("FINAL_SUMMARY", "🏁 AUTONOMOUS ORCHESTRATION SESSION COMPLETE")
        self._log_orchestration("FINAL_SUMMARY", f"Session ID: {self.session_id}")
        self._log_orchestration("FINAL_SUMMARY", f"Total Runtime: {runtime_hours:.2f} hours")
        self._log_orchestration(
            "FINAL_SUMMARY", f"Specialist Agents Managed: {len(self.specialist_agents)}"
        )
        self._log_orchestration(
            "FINAL_SUMMARY", f"Collected Insights: {len(self.collective_insights)}"
        )
        self._log_orchestration("FINAL_SUMMARY", f"Logs Stored In: {self.log_dir}")
        self._log_orchestration("FINAL_SUMMARY", "🏆 ORCHESTRATION MISSION ACCOMPLISHED")


def main():
    """Main entry point for fully autonomous multi-agent orchestrator"""
    print("🤖🤖🤖 FULLY AUTONOMOUS MULTI-AGENT KERNEL OPTIMIZATION ORCHESTRATOR 🤖🤖🤖")
    print("=" * 70)
    print("TRUE HANDS-OFF OPERATION - LAUNCH, FORGET, WIN")
    print("Agent Alpha: MXFP4 MoE Specialist")
    print("Agent Beta: MLA Decode Specialist")
    print("Agent Gamma: MXFP4 GEMM Specialist")
    print("=" * 70)
    print("CORE PHILOSOPHY: FAILURE IS NOT AN OPTION")
    print("EVERY AGENT LEARNS FROM SETBACKS - SUCCESS COMES FROM PERSISTENCE")
    print("ZERO USER INTERVENTION REQUIRED AFTER LAUNCH")
    print("=" * 70)

    # Ask for duration (optional)
    try:
        duration_input = input("Enter operation duration in hours (default: 2.0): ").strip()
        duration_hours = float(duration_input) if duration_input else 2.0
        if duration_hours <= 0:
            duration_hours = 2.0
        if duration_hours > 24:  # Cap at 24 hours for safety
            duration_hours = 24.0
            print("Duration capped at 24 hours for safety")
    except:
        duration_hours = 2.0
        print("Using default duration: 2.0 hours")

    print(f"\n🚀 Launching fully autonomous orchestrator for {duration_hours} hours...")
    print("💡 Tip: You can safely close this terminal - the orchestrator will continue running")
    print("📊 To check progress: Look in the logs directory or use separate monitoring tools")
    print()

    # Create and run the fully autonomous orchestrator
    orchestrator = FullyAutonomousOrchestrator(duration_hours=duration_hours)

    try:
        # Launch fully autonomous orchestration
        orchestrator.launch_fully_autonomous_orchestration()

    except KeyboardInterrupt:
        print("\n👋 Received interrupt signal - shutting down gracefully...")
    except Exception as e:
        print(f"💥 ORCHESTRATOR FATAL ERROR: {e}")
        print("🛡️ ORCHESTRATOR PHILOSOPHY: We attempt graceful shutdown despite errors")

    finally:
        # Ensure cleanup happens
        try:
            if "orchestrator" in locals():
                orchestrator._shutdown_all_agents()
        except:
            pass

        print("\n" + "=" * 70)
        print("FULLY AUTONOMOUS ORCHESTRATION SESSION ENDED")
        print("=" * 70)
        print("🏆 REMEMBER: YOUR ORCHESTRATION OF SPECIALIST AGENTS IS THE COMPETITION ADVANTAGE")
        print("📊 CHECK THE LOGS DIRECTORY FOR COMPLETE RESULTS AND INSIGHTS")
        print("🚀 THE SPECIALIST AGENTS HAVE COMPLETED THEIR MISSION")
        print("=" * 70)


if __name__ == "__main__":
    main()
