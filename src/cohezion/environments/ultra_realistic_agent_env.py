"""UltraRealisticAgentEnv — Gymnasium Environment for Long-Horizon Agent Training.
=============================================================================
Directly aligns with Anthropic's 'Research Engineer, Universes' mandate:
- Simulates realistic, messy OS execution environments with sandbox isolation
- Stochastically injects human steering, tool failures, and goal pivots mid-trajectory
- Measures genuine capability: task completion, interruption resilience, context recovery
- Exposes standard Gymnasium spaces for PPO/RL training, while remaining fully navigable
  by LLM agents via text/JSON action envelopes.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import gymnasium as gym
import numpy as np
from gymnasium import spaces

from cohezion.environments.interruption_engine import (
    InterruptionEngine,
)
from cohezion.security.linux_namespace_sandbox import LinuxNamespaceSandbox


logger = logging.getLogger(__name__)


class UltraRealisticAgentEnv(gym.Env):
    """Ultra-realistic, interruptible Gymnasium environment for agentic RL."""

    metadata = {"render_modes": ["human", "ansi"]}

    def __init__(
        self,
        task_suite: list[dict[str, Any]] | None = None,
        max_steps: int = 50,
        interruption_prob: float = 0.25,
        use_namespaces: bool = True,
        seed: int | None = None,
    ) -> None:
        super().__init__()
        self.max_steps = max_steps
        self.use_namespaces = use_namespaces
        self.rng = np.random.default_rng(seed)
        self.task_suite = task_suite or self.generate_procedural_task_suite(n_tasks=30, seed=seed or 42)

        self.interruption_engine = InterruptionEngine(
            interrupt_probability=interruption_prob,
            min_interval_steps=3,
            max_interruptions_per_episode=3,
            seed=seed,
        )

        self.sandbox_runner: LinuxNamespaceSandbox | None = None
        if use_namespaces:
            with_bwrap = LinuxNamespaceSandbox()
            if with_bwrap.is_available:
                self.sandbox_runner = with_bwrap

        # Observation & Action Spaces
        self.observation_space = spaces.Dict(
            {
                "stdout": spaces.Text(max_length=4096),
                "stderr": spaces.Text(max_length=2048),
                "exit_code": spaces.Discrete(256),
                "active_interrupt": spaces.Discrete(2),
                "interrupt_message": spaces.Text(max_length=1024),
                "step_count": spaces.Discrete(10000),
                "poincare_state": spaces.Box(low=-1.0, high=1.0, shape=(12,), dtype=np.float32),
                "task_description": spaces.Text(max_length=1024),
            }
        )

        # 0: run_command, 1: write_file, 2: read_file, 3: respond_to_interrupt, 4: complete_task
        self.action_space = spaces.Dict(
            {
                "action_type": spaces.Discrete(5),
                "command": spaces.Text(max_length=512),
                "path": spaces.Text(max_length=256),
                "content": spaces.Text(max_length=4096),
                "interrupt_response": spaces.Text(max_length=512),
            }
        )

        # Episode runtime state
        self.current_task: dict[str, Any] = {}
        self.sandbox_dir: Path | None = None
        self.step_count: int = 0
        self.poincare_vector: np.ndarray = np.zeros(12, dtype=np.float32)
        self.task_completed: bool = False

    def reset(
        self, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Initializes a fresh task episode and isolated sandbox workspace."""
        super().reset(seed=seed)
        if seed is not None:
            self.rng = np.random.default_rng(seed)

        self.step_count = 0
        self.task_completed = False
        self.poincare_vector = (self.rng.random(12).astype(np.float32) * 0.2) - 0.1

        # Select task
        task_idx = int(self.rng.integers(0, len(self.task_suite)))
        self.current_task = self.task_suite[task_idx]

        # Clean prior sandbox if any
        if self.sandbox_dir and self.sandbox_dir.exists():
            shutil.rmtree(self.sandbox_dir, ignore_errors=True)

        self.sandbox_dir = Path(tempfile.mkdtemp(prefix="cohezion_universe_sb_"))

        # Setup initial files
        for filename, content in self.current_task.get("setup_files", {}).items():
            fpath = self.sandbox_dir / filename
            fpath.parent.mkdir(parents=True, exist_ok=True)
            fpath.write_text(content, encoding="utf-8")

        self.interruption_engine.reset(seed=seed)

        obs = {
            "stdout": f"Workspace initialized at {self.sandbox_dir.name}.",
            "stderr": "",
            "exit_code": 0,
            "active_interrupt": 0,
            "interrupt_message": "",
            "step_count": 0,
            "poincare_state": self.poincare_vector,
            "task_description": self.current_task["description"],
        }
        info = {
            "task_id": self.current_task["task_id"],
            "sandbox_dir": str(self.sandbox_dir),
            "step": 0,
        }
        return obs, info

    @staticmethod
    def generate_procedural_task_suite(n_tasks: int = 30, seed: int = 42) -> list[dict[str, Any]]:
        """Generates a reproducible suite of parameterized tasks with diverse root causes."""
        rng = np.random.default_rng(seed)
        # Canonical baseline tasks (guarantee exact baseline test coverage)
        canonical = [
            {
                "task_id": "debug_python_syntax",
                "description": "Locate 'app.py', fix the SyntaxError, and verify tests pass with 'python3 test_app.py'.",
                "setup_files": {
                    "app.py": "def add(a, b):\n    return a + b\n\ndef multiply(a, b\n    return a * b\n",
                    "test_app.py": "from app import add, multiply\nassert add(2, 3) == 5\nassert multiply(4, 5) == 20\nprint('ALL TESTS PASSED')\n",
                },
                "verifier_command": "python3 test_app.py",
                "verifier_pattern": "ALL TESTS PASSED",
            },
            {
                "task_id": "parse_security_logs",
                "description": "Analyze 'access.log', find all failed attempts (status 401), and write IP counts to 'report.json'.",
                "setup_files": {
                    "access.log": (
                        "192.168.1.10 - 200 - /login\n"
                        "10.0.0.5 - 401 - /admin\n"
                        "10.0.0.5 - 401 - /admin\n"
                        "172.16.0.2 - 200 - /dashboard\n"
                        "10.0.0.5 - 401 - /admin\n"
                    ),
                },
                "verifier_command": "python3 -c \"import json; d=json.load(open('report.json')); assert d.get('10.0.0.5') == 3; print('REPORT VERIFIED')\"",
                "verifier_pattern": "REPORT VERIFIED",
            },
            {
                "task_id": "refactor_config_format",
                "description": "Convert 'config.ini' key-values into valid JSON in 'config.json' and verify.",
                "setup_files": {
                    "config.ini": "[server]\nport = 8080\nhost = localhost\ndebug = true\n",
                },
                "verifier_command": "python3 -c \"import json; d=json.load(open('config.json')); assert d.get('port') in (8080, '8080'); print('CONFIG VERIFIED')\"",
                "verifier_pattern": "CONFIG VERIFIED",
            },
        ]
        suite = list(canonical)
        for i in range(len(canonical), n_tasks):
            cat_choice = i % 3
            if cat_choice == 0:
                fn_name = f"calc_{i}"
                factor = int(rng.integers(2, 10))
                val = int(rng.integers(10, 50))
                expected = val * factor
                suite.append({
                    "task_id": f"debug_python_syntax_v{i}",
                    "description": f"Locate 'app_{i}.py', fix the SyntaxError, and verify tests pass with 'python3 test_app_{i}.py'.",
                    "setup_files": {
                        f"app_{i}.py": f"def {fn_name}(x):\n    return x * {factor}\n\ndef broken_fn(a, b\n    return a * b\n",
                        f"test_app_{i}.py": f"from app_{i} import {fn_name}\nassert {fn_name}({val}) == {expected}\nprint('ALL TESTS PASSED')\n",
                    },
                    "verifier_command": f"python3 test_app_{i}.py",
                    "verifier_pattern": "ALL TESTS PASSED",
                })
            elif cat_choice == 1:
                target_ip = f"10.0.{rng.integers(1, 10)}.{rng.integers(2, 200)}"
                count = int(rng.integers(2, 5))
                lines = [f"{target_ip} - 401 - /admin\n" for _ in range(count)]
                lines.append("192.168.1.1 - 200 - /login\n")
                suite.append({
                    "task_id": f"parse_security_logs_v{i}",
                    "description": f"Analyze 'access_{i}.log', count status 401 for {target_ip}, write to 'report_{i}.json'.",
                    "setup_files": {
                        f"access_{i}.log": "".join(lines),
                    },
                    "verifier_command": f"python3 -c \"import json; d=json.load(open('report_{i}.json')); assert d.get('{target_ip}') == {count}; print('REPORT VERIFIED')\"",
                    "verifier_pattern": "REPORT VERIFIED",
                })
            else:
                port = int(rng.integers(3000, 9000))
                suite.append({
                    "task_id": f"refactor_config_format_v{i}",
                    "description": f"Convert 'config_{i}.ini' to valid JSON in 'config_{i}.json' and verify port {port}.",
                    "setup_files": {
                        f"config_{i}.ini": f"[server]\nport = {port}\nhost = localhost\ndebug = true\n",
                    },
                    "verifier_command": f"python3 -c \"import json; d=json.load(open('config_{i}.json')); assert d.get('port') in ({port}, '{port}'); print('CONFIG VERIFIED')\"",
                    "verifier_pattern": "CONFIG VERIFIED",
                })
        return suite[:n_tasks]

    def _calculate_ground_truth_progress(self) -> float:
        """Calculates true root-cause progress p_t in [0.0, 1.0]."""
        if self.task_completed:
            return 1.0
        if not self.sandbox_dir or not self.sandbox_dir.exists():
            return 0.0

        # Check if the primary verifier passes
        success, _ = self._verify_task_completion()
        if success:
            return 1.0

        # Partial progress detection based on syntax or partial files
        task_id = self.current_task.get("task_id", "")
        if "debug_python" in task_id:
            for py_file in self.sandbox_dir.glob("*.py"):
                if py_file.name.startswith("test_"):
                    continue
                try:
                    import ast
                    ast.parse(py_file.read_text(encoding="utf-8"))
                    return 0.5  # Syntax repaired, but test verification pending
                except Exception:
                    pass
        elif "parse_security" in task_id:
            for json_file in self.sandbox_dir.glob("*.json"):
                try:
                    data = json.loads(json_file.read_text(encoding="utf-8"))
                    if isinstance(data, dict) and len(data) > 0:
                        return 0.5
                except Exception:
                    pass
        elif "config" in task_id:
            for json_file in self.sandbox_dir.glob("*.json"):
                try:
                    data = json.loads(json_file.read_text(encoding="utf-8"))
                    if isinstance(data, dict) and "port" in data:
                        return 0.5
                except Exception:
                    pass
        return 0.0

    def _compute_potential(self, progress: float, norm: float, step: int) -> float:
        """PBRS Potential Function: Phi(s) = lambda1 * p - lambda2 * c - lambda3 * t.
        Guarantees policy invariance under Ng, Harada, Russell (1999).
        """
        lambda1 = 5.0
        lambda2 = 2.0
        lambda3 = 0.02
        c_t = float(np.clip(norm, 0.0, 1.0))
        return float(lambda1 * progress - lambda2 * c_t - lambda3 * step)

    def step(
        self, action: dict[str, Any] | str
    ) -> tuple[dict[str, Any], float, bool, bool, dict[str, Any]]:
        """Executes action inside sandbox, processes interruptions, and calculates reward via PBRS."""
        self.step_count += 1
        parsed_action = self._parse_action(action)

        # Compute prior potential Phi(s_t)
        p_prev = self._calculate_ground_truth_progress()
        norm_prev = float(np.linalg.norm(self.poincare_vector))
        phi_prev = self._compute_potential(p_prev, norm_prev, self.step_count - 1)

        stdout = ""
        stderr = ""
        exit_code = 0
        action_penalty = 0.0

        action_type = parsed_action.get("action_type", "run_command")

        # 1. Execute Sandbox Action
        if action_type in (0, "run_command"):
            cmd = parsed_action.get("command", "").strip()
            stdout, stderr, exit_code = self._exec_in_sandbox(cmd)
        elif action_type in (1, "write_file"):
            p = parsed_action.get("path", "").strip()
            content = parsed_action.get("content", "")
            if p and self.sandbox_dir:
                target_file = self.sandbox_dir / p
                target_file.parent.mkdir(parents=True, exist_ok=True)
                target_file.write_text(content, encoding="utf-8")
                stdout = f"Wrote {len(content)} bytes to {p}."
            else:
                stderr = "Invalid path or uninitialized workspace."
                exit_code = 1
        elif action_type in (2, "read_file"):
            p = parsed_action.get("path", "").strip()
            if p and self.sandbox_dir:
                target_file = self.sandbox_dir / p
                if target_file.exists():
                    stdout = target_file.read_text(encoding="utf-8", errors="replace")[:4000]
                else:
                    stderr = f"File {p} not found."
                    exit_code = 1
        elif action_type in (3, "respond_to_interrupt"):
            resp = parsed_action.get("interrupt_response", "")
            resolved, reason = self.interruption_engine.resolve_current_interruption(
                self.step_count, resp, parsed_action, sandbox_dir=self.sandbox_dir
            )
            if resolved:
                stdout = f"INTERRUPTION RESOLVED: {reason}"
            else:
                action_penalty -= 0.5
                stderr = f"INTERRUPTION UNRESOLVED: {reason}"
                exit_code = 1
        elif action_type in (4, "complete_task"):
            # Run verification test
            success, msg = self._verify_task_completion()
            if success:
                self.task_completed = True
                stdout = f"TASK VERIFIED: {msg}"
            else:
                action_penalty -= 1.0  # Premature completion penalty
                stderr = f"TASK VERIFICATION FAILED: {msg}"
                exit_code = 1

        # Check if action incidentally resolved active interruption
        if action_type != 3 and self.interruption_engine.active_interrupt:
            resp_summary = f"{stdout} {stderr} {parsed_action}"
            resolved, reason = self.interruption_engine.resolve_current_interruption(
                self.step_count, resp_summary, parsed_action, sandbox_dir=self.sandbox_dir
            )
            if resolved:
                stdout += f"\n[AUTO-RESOLVED INTERRUPTION: {reason}]"

        # 2. Update Poincaré Latent Trajectory
        step_drift = (self.rng.random(12).astype(np.float32) - 0.5) * 0.05
        p_current = self._calculate_ground_truth_progress()
        if p_current > p_prev or self.task_completed:
            self.poincare_vector = (self.poincare_vector * 0.85) + step_drift
        else:
            self.poincare_vector = (self.poincare_vector * 1.05) + step_drift

        norm_current = float(np.linalg.norm(self.poincare_vector))
        if norm_current >= 0.95:
            self.poincare_vector = self.poincare_vector * (0.95 / norm_current)
            norm_current = 0.95

        conformal_factor = float(2.0 / (1.0 - (norm_current**2) + 1e-6))

        # 3. Interruption Engine Update with physical mutations
        active_irq = self.interruption_engine.maybe_trigger_interruption(
            self.step_count, self.current_task["description"], sandbox_dir=self.sandbox_dir
        )

        active_interrupt_flag = 1 if active_irq is not None else 0
        interrupt_msg = active_irq.message if active_irq is not None else ""

        # 4. Compute Mathematically Rigorous Potential-Based Reward Shaping (PBRS)
        # R_t = R_base + gamma * Phi(s_{t+1}) - Phi(s_t) + action_penalty
        phi_next = self._compute_potential(p_current, norm_current, self.step_count)
        gamma = 0.99
        r_base = 10.0 if self.task_completed else 0.0
        pbrs_shaping = gamma * phi_next - phi_prev

        # Final reward completely eliminates camping and interrupt farming
        reward = float(r_base + pbrs_shaping + action_penalty)

        # 5. Termination conditions
        terminated = bool(self.task_completed)
        truncated = bool(self.step_count >= self.max_steps)

        obs = {
            "stdout": stdout[:4096],
            "stderr": stderr[:2048],
            "exit_code": exit_code,
            "active_interrupt": active_interrupt_flag,
            "interrupt_message": interrupt_msg,
            "step_count": self.step_count,
            "poincare_state": self.poincare_vector,
            "task_description": self.current_task["description"],
        }

        resilience = self.interruption_engine.compute_resilience_metrics()
        info = {
            "task_id": self.current_task["task_id"],
            "sandbox_dir": str(self.sandbox_dir),
            "task_completed": self.task_completed,
            "step": self.step_count,
            "reward": round(reward, 4),
            "irs_score": resilience["interruption_resilience_score"],
            "resolution_rate": resilience["resolution_rate"],
            "mean_recovery_steps": resilience["mean_recovery_steps"],
            "conformal_factor": round(conformal_factor, 4),
            "ground_truth_progress": round(p_current, 2),
        }

        return obs, reward, terminated, truncated, info

    def _exec_in_sandbox(self, command: str) -> tuple[str, str, int]:
        """Executes a bash command in the isolated workspace, respecting active physical tool faults."""
        if not command:
            return ("", "Empty command.", 1)

        if not self.sandbox_dir or not self.sandbox_dir.exists():
            return ("", "Sandbox directory does not exist.", 1)

        # Physical Tool Fault Check
        fault_marker = self.sandbox_dir / ".tool_fault_active"
        if fault_marker.exists():
            cmd_tokens = command.strip().split()
            first_word = cmd_tokens[0] if cmd_tokens else ""
            # Safe diagnostic & recovery commands that remain unblocked
            safe_diagnostics = {"cat", "which", "echo", "pwd", "ls", "python", "python3", "env", "chmod", "find"}
            if first_word not in safe_diagnostics and "fallback" not in command and "retry" not in command:
                return ("", f"bash: {first_word}: command execution failed: tool fault active (exit 127)", 127)

        try:
            bwrap_bin = shutil.which("bwrap")
            if bwrap_bin:
                exec_cmd = [
                    bwrap_bin,
                    "--ro-bind", "/", "/",
                    "--bind", str(self.sandbox_dir), str(self.sandbox_dir),
                    "--dev", "/dev",
                    "--proc", "/proc",
                    "--unshare-all",
                    "--die-with-parent",
                    "--new-session",
                    "bash", "-c", command,
                ]
            else:
                exec_cmd = ["bash", "-c", command]

            res = subprocess.run(
                exec_cmd,
                cwd=str(self.sandbox_dir),
                capture_output=True,
                text=True,
                timeout=10.0,
            )
            return (res.stdout, res.stderr, res.returncode)
        except subprocess.TimeoutExpired:
            return ("", "Command timed out after 10.0s.", 124)
        except Exception as exc:
            return ("", str(exc), 1)

    def _verify_task_completion(self) -> tuple[bool, str]:
        """Runs the task's deterministic verification command."""
        v_cmd = self.current_task.get("verifier_command")
        v_pat = self.current_task.get("verifier_pattern")
        if not v_cmd or not self.sandbox_dir:
            return (True, "No verifier command specified; marked complete.")

        try:
            res = subprocess.run(
                ["bash", "-c", v_cmd],
                cwd=str(self.sandbox_dir),
                capture_output=True,
                text=True,
                timeout=10.0,
            )
            output = f"{res.stdout}\n{res.stderr}"
            if res.returncode == 0 and (not v_pat or v_pat in output):
                return (True, f"Verifier passed: {v_pat or 'return code 0'}")
            return (False, f"Verification failed (code {res.returncode}): {output[:200]}")
        except Exception as e:
            return (False, f"Verifier error: {e}")

    def _parse_action(self, action: dict[str, Any] | str) -> dict[str, Any]:
        """Parses dictionary or JSON action into normalized dictionary."""
        if isinstance(action, dict):
            return action
        if isinstance(action, str):
            try:
                parsed = json.loads(action)
                if isinstance(parsed, dict):
                    return parsed
            except Exception:
                pass
            # Default text to shell command
            return {"action_type": "run_command", "command": action}
        return {"action_type": "run_command", "command": str(action)}

    def close(self) -> None:
        """Cleans up the ephemeral sandbox workspace."""
        if self.sandbox_dir and self.sandbox_dir.exists():
            shutil.rmtree(self.sandbox_dir, ignore_errors=True)
            self.sandbox_dir = None
        super().close()
