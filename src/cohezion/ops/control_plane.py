"""Cohezion Unified Operations Control Plane.

Provides continuous, automated orchestration and monitoring across:
1. Hardware: AMD Strix Halo 128GB UMA, NPU/iGPU/CPU silicon lanes, GTT aperture, PSI memory pressure.
2. Software: Lemonade OmniRouter, Ollama Cloud, SurrealDB, systemd daemons, Obsidian Vault, Git index hygiene.
3. Projects: Active Kaggle competition pipelines, Agentic Kanban work-queue, Sovereign Autopoiesis daemon.
"""

from __future__ import annotations

import base64
import contextlib
import json
import logging
import os
import shutil
import subprocess
import urllib.request
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cohezion.reliability.oom_guard import MemoryState, OOMGuard


logger = logging.getLogger("cohezion.ops.control_plane")

# Config constants
SURREAL_URL = os.getenv("SURREAL_URL", "http://localhost:8001/sql")
SURREAL_NS = os.getenv("SURREAL_NS", "cohezion")
SURREAL_DB = os.getenv("SURREAL_DB", "main")
SURREAL_AUTH = base64.b64encode(b"root:root").decode()

LEMONADE_BASE_URL = os.getenv("LEMONADE_BASE_URL", "http://127.0.0.1:13305")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")

OBSIDIAN_VAULT_DIR = Path(
    os.getenv("OBSIDIAN_VAULT_DIR", str(Path.home() / "vaults" / "cohezion-vault"))
)
WORK_QUEUE_PATH = Path(
    os.getenv("WORK_QUEUE_PATH", str(Path.home() / ".cohezion" / "work-queue.json"))
)
AUTOPOIESIS_LOG_PATH = Path("/tmp/cohezion_overnight_autopoiesis.log")


# =====================================================================
# Telemetry Data Models
# =====================================================================


@dataclass(frozen=True, slots=True)
class HardwareTelemetry:
    """Telemetry for AMD Strix Halo tri-silicon architecture."""

    available_ram_gb: float
    total_ram_gb: float
    dynamic_floor_gb: float
    gtt_used_gb: float
    gtt_total_gb: float
    swap_used_gb: float
    psi_memory_avg10: float
    is_memory_safe: bool
    cpu_cores_logical: int
    cpu_cores_physical: int
    load_avg_1m: float
    load_avg_5m: float
    status: str  # HEALTHY, DEGRADED, CRITICAL

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SoftwareTelemetry:
    """Telemetry for runtime models, systemd services, and storage engines."""

    lemonade_online: bool
    lemonade_models_loaded: list[str]
    ollama_online: bool
    ollama_models_loaded: list[str]
    surrealdb_online: bool
    systemd_services: dict[str, str]  # service_name -> status (active, failed, inactive)
    git_index_file_count: int
    git_index_healthy: bool
    obsidian_vault_accessible: bool
    status: str  # HEALTHY, DEGRADED, CRITICAL

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class ProjectTelemetry:
    """Telemetry for Kaggle tracks, Kanban tasks, and Autopoiesis loops."""

    active_kaggle_tracks: list[dict[str, Any]]
    kanban_summary: dict[str, int]  # status -> count
    autopoiesis_cycle: int
    autopoiesis_target_cycles: int
    autopoiesis_last_reward: float
    autopoiesis_last_delta_s: float
    autopoiesis_converged: bool
    status: str  # HEALTHY, DEGRADED, CRITICAL

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class DoctorDiagnostic:
    """Outcome of a health check rule."""

    subsystem: str
    rule_name: str
    passed: bool
    severity: str  # INFO, WARNING, ERROR
    message: str
    action_item: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class OperationsSnapshot:
    """Unified operational snapshot combining Hardware, Software, and Projects."""

    timestamp: str
    overall_status: str  # HEALTHY, DEGRADED, CRITICAL
    hardware: HardwareTelemetry
    software: SoftwareTelemetry
    projects: ProjectTelemetry
    diagnostics: list[DoctorDiagnostic] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# =====================================================================
# 1. Hardware Orchestrator
# =====================================================================


class HardwareOrchestrator:
    """Inspects and manages Strix Halo tri-silicon compute and memory resources."""

    @staticmethod
    def get_telemetry() -> HardwareTelemetry:
        """Inspect system memory, GTT aperture, and CPU compute load."""
        mem: MemoryState = OOMGuard.get_memory_state()

        # CPU core topology
        logical_cores = os.cpu_count() or 1
        physical_cores = logical_cores // 2 if logical_cores > 1 else 1
        try:
            load1, load5, _ = os.getloadavg()
        except (AttributeError, OSError):
            load1, load5 = 0.0, 0.0

        # Assess hardware health status
        status = "HEALTHY"
        if not mem.is_safe:
            status = "CRITICAL"
        elif mem.available_gb < 24.0 or mem.gtt_used_gb > 42.0 or mem.psi_some_10 > 5.0:
            status = "DEGRADED"

        return HardwareTelemetry(
            available_ram_gb=mem.available_gb,
            total_ram_gb=mem.total_gb,
            dynamic_floor_gb=mem.dynamic_floor_gb,
            gtt_used_gb=mem.gtt_used_gb,
            gtt_total_gb=mem.gtt_total_gb,
            swap_used_gb=mem.swap_used_gb,
            psi_memory_avg10=mem.psi_some_10,
            is_memory_safe=mem.is_safe,
            cpu_cores_logical=logical_cores,
            cpu_cores_physical=physical_cores,
            load_avg_1m=round(load1, 2),
            load_avg_5m=round(load5, 2),
            status=status,
        )

    @staticmethod
    def heal_hardware() -> dict[str, Any]:
        """Perform non-destructive hardware memory and cache reclamation."""
        actions: list[str] = []
        # Check current state
        mem = OOMGuard.get_memory_state()
        if mem.available_gb < 20.0 or mem.gtt_used_gb > 45.0:
            actions.append(
                f"Memory tight (Avail: {mem.available_gb}G, GTT: {mem.gtt_used_gb}G). Calling sync."
            )
            try:
                subprocess.run(["sync"], check=False, timeout=5)
            except Exception as e:
                actions.append(f"sync failed: {e}")
        else:
            actions.append("Memory state within safe margins. No invasive action needed.")

        return {"actions": actions, "timestamp": datetime.now(UTC).isoformat()}


# =====================================================================
# 2. Software Orchestrator
# =====================================================================


class SoftwareOrchestrator:
    """Manages inference runtimes, systemd daemons, and storage engines."""

    @staticmethod
    def _check_http_endpoint(url: str, timeout: float = 5.0) -> tuple[bool, str]:
        """Check if an HTTP endpoint is reachable."""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "CohezionControlPlane"})  # noqa: S310
            with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
                return resp.status in (200, 204), resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            return False, str(e)

    @classmethod
    def get_telemetry(cls) -> SoftwareTelemetry:
        """Inspect Lemonade, Ollama, SurrealDB, systemd services, and storage."""
        # 1. Lemonade OmniRouter
        lemonade_ok, lemonade_resp = cls._check_http_endpoint(f"{LEMONADE_BASE_URL}/v1/models")
        lemonade_models: list[str] = []
        if lemonade_ok:
            try:
                data = json.loads(lemonade_resp)
                lemonade_models = [m.get("id", "") for m in data.get("data", [])]
            except Exception:
                pass

        # 2. Ollama Cloud
        ollama_ok, ollama_resp = cls._check_http_endpoint(f"{OLLAMA_BASE_URL}/api/tags")
        ollama_models: list[str] = []
        if ollama_ok:
            try:
                data = json.loads(ollama_resp)
                ollama_models = [m.get("name", "") for m in data.get("models", [])]
            except Exception:
                pass

        # 3. SurrealDB
        surreal_ok, _ = cls._check_http_endpoint(f"{SURREAL_URL.replace('/sql', '')}/version")

        # 4. Systemd services inspection
        target_services = [
            "cohezion-actioner.service",
            "cohezion-daemon-orchestrator.service",
            "cohezion-daily-researcher.timer",
            "lemonade.service",
        ]
        services_status: dict[str, str] = {}
        for s in target_services:
            try:
                res = subprocess.run(
                    ["systemctl", "--user", "is-active", s],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                services_status[s] = res.stdout.strip() or "inactive"
            except Exception:
                services_status[s] = "unknown"

        # 5. Git index check (Learning 416 & global rules: max file limit)
        git_count = 0
        git_limit = int(os.environ.get("COHEZION_GIT_INDEX_LIMIT", "15000"))
        git_healthy = True
        try:
            res = subprocess.run(["git", "ls-files"], capture_output=True, text=True, timeout=5)
            git_count = len(res.stdout.splitlines())
            git_healthy = git_count <= git_limit
        except Exception:
            git_healthy = True

        # 6. Obsidian Vault check
        vault_accessible = OBSIDIAN_VAULT_DIR.is_dir()

        # Health status evaluation
        status = "HEALTHY"
        if not lemonade_ok or not surreal_ok:
            status = "CRITICAL"
        elif not git_healthy or not vault_accessible:
            status = "DEGRADED"

        return SoftwareTelemetry(
            lemonade_online=lemonade_ok,
            lemonade_models_loaded=lemonade_models,
            ollama_online=ollama_ok,
            ollama_models_loaded=ollama_models,
            surrealdb_online=surreal_ok,
            systemd_services=services_status,
            git_index_file_count=git_count,
            git_index_healthy=git_healthy,
            obsidian_vault_accessible=vault_accessible,
            status=status,
        )


# =====================================================================
# 3. Project Orchestrator
# =====================================================================


class ProjectOrchestrator:
    """Manages active Kaggle competitions, Kanban work-queue, and Autopoiesis loops."""

    @staticmethod
    def get_kaggle_tracks() -> list[dict[str, Any]]:
        """Retrieve recent status for active Kaggle competitions."""
        active_comps = [
            "rsna-knee-abnormality-detection",
            "arc-prize-2026-arc-agi-2",
            "arc-prize-2026-arc-agi-3",
        ]
        tracks: list[dict[str, Any]] = []

        if not shutil.which("kaggle"):
            return [{"competition": c, "status": "Kaggle CLI not installed"} for c in active_comps]

        for comp in active_comps:
            try:
                res = subprocess.run(
                    ["kaggle", "competitions", "submissions", "-c", comp],
                    capture_output=True,
                    text=True,
                    timeout=8,
                )
                lines = [line.strip() for line in res.stdout.splitlines() if line.strip()]
                if len(lines) >= 3:
                    # Parse top submission header & row
                    top_row = lines[2].split()
                    ref = top_row[0] if top_row else "N/A"
                    status = "UNKNOWN"
                    score = "N/A"
                    for token in top_row:
                        if "SubmissionStatus." in token:
                            status = token.replace("SubmissionStatus.", "")
                        elif token.replace(".", "").isdigit() and len(token) >= 4:
                            score = token
                    tracks.append(
                        {
                            "competition": comp,
                            "latest_ref": ref,
                            "status": status,
                            "public_score": score,
                        }
                    )
                else:
                    tracks.append(
                        {
                            "competition": comp,
                            "latest_ref": "None",
                            "status": "NO_SUBMISSIONS",
                            "public_score": "N/A",
                        }
                    )
            except Exception as exc:
                tracks.append(
                    {
                        "competition": comp,
                        "latest_ref": "N/A",
                        "status": f"ERROR: {exc}",
                        "public_score": "N/A",
                    }
                )

        return tracks

    @staticmethod
    def get_kanban_summary() -> dict[str, int]:
        """Parse work-queue JSON and summarize task statuses."""
        if not WORK_QUEUE_PATH.exists():
            return {}

        summary: dict[str, int] = {
            "pending": 0,
            "approved": 0,
            "in_progress": 0,
            "completed": 0,
            "rejected_by_guardrail": 0,
        }
        try:
            with open(WORK_QUEUE_PATH, encoding="utf-8") as f:
                data = json.load(f)
            items = data.get("items", []) if isinstance(data, dict) else []
            for it in items:
                st = it.get("status", "pending")
                summary[st] = summary.get(st, 0) + 1
        except Exception as e:
            logger.warning(f"Failed to read work-queue.json: {e}")

        return summary

    @staticmethod
    def get_autopoiesis_status() -> dict[str, Any]:
        """Inspect autonomous overnight autopoiesis daemon log."""
        import glob

        latest_cycle = 0
        reward = 0.0
        delta_s = 0.0
        converged = False

        candidate_paths = [AUTOPOIESIS_LOG_PATH]
        task_logs = [
            Path(p)
            for p in glob.glob(
                f"{Path.home()}/.gemini/antigravity-cli/brain/*/.system_generated/tasks/*.log"
            )
        ]
        # Sort task logs by mtime desc
        task_logs.sort(key=lambda x: x.stat().st_mtime if x.exists() else 0, reverse=True)
        candidate_paths.extend(task_logs)

        for p in candidate_paths:
            if not p.exists() or p.stat().st_size == 0:
                continue
            with contextlib.suppress(Exception), open(p, encoding="utf-8") as f:
                for line in f:
                    if "[Cycle " in line and "/240]" in line:
                        with contextlib.suppress(Exception):
                            latest_cycle = max(
                                latest_cycle, int(line.split("[Cycle ")[1].split("/")[0])
                            )
                    elif "Cycle " in line and "Executed: Converged=" in line:
                        converged = "Converged=True" in line
                        if "Reward=" in line:
                            with contextlib.suppress(Exception):
                                reward = float(line.split("Reward=")[1].split(",")[0])
                        if "Delta S=" in line:
                            with contextlib.suppress(Exception):
                                delta_s = float(line.split("Delta S=")[1].split()[0])
            if latest_cycle > 0:
                break

        return {
            "cycle": latest_cycle,
            "target_cycles": 240,
            "reward": reward,
            "delta_s": delta_s,
            "converged": converged,
        }

    @classmethod
    def get_telemetry(cls) -> ProjectTelemetry:
        """Aggregate telemetry for projects."""
        tracks = cls.get_kaggle_tracks()
        kanban = cls.get_kanban_summary()
        autopoiesis = cls.get_autopoiesis_status()

        status = "HEALTHY"
        # Check if any active Kaggle track has failed
        for tr in tracks:
            if tr.get("status") in ("FAILED", "ERROR"):
                status = "DEGRADED"

        return ProjectTelemetry(
            active_kaggle_tracks=tracks,
            kanban_summary=kanban,
            autopoiesis_cycle=autopoiesis["cycle"],
            autopoiesis_target_cycles=autopoiesis["target_cycles"],
            autopoiesis_last_reward=autopoiesis["reward"],
            autopoiesis_last_delta_s=autopoiesis["delta_s"],
            autopoiesis_converged=autopoiesis["converged"],
            status=status,
        )


# =====================================================================
# 4. Master Control Plane
# =====================================================================


class CohezionControlPlane:
    """Master orchestrator integrating Hardware, Software, and Project Management."""

    def __init__(self) -> None:
        self.hardware = HardwareOrchestrator()
        self.software = SoftwareOrchestrator()
        self.projects = ProjectOrchestrator()

    def run_diagnostics(
        self,
        hw: HardwareTelemetry,
        sw: SoftwareTelemetry,
        proj: ProjectTelemetry,
    ) -> list[DoctorDiagnostic]:
        """Run system invariants and doctor assertions."""
        diagnostics: list[DoctorDiagnostic] = []

        # Rule 1: Memory Headroom (Hardware)
        if hw.available_ram_gb >= hw.dynamic_floor_gb:
            diagnostics.append(
                DoctorDiagnostic(
                    subsystem="hardware",
                    rule_name="memory_headroom_floor",
                    passed=True,
                    severity="INFO",
                    message=f"Available RAM ({hw.available_ram_gb:.1f} GiB) exceeds dynamic floor ({hw.dynamic_floor_gb:.1f} GiB)",
                )
            )
        else:
            diagnostics.append(
                DoctorDiagnostic(
                    subsystem="hardware",
                    rule_name="memory_headroom_floor",
                    passed=False,
                    severity="ERROR",
                    message=f"Available RAM ({hw.available_ram_gb:.1f} GiB) breached dynamic floor ({hw.dynamic_floor_gb:.1f} GiB)",
                    action_item="Reclaim memory or restart idle heavy inference engines",
                )
            )

        # Rule 2: GTT Aperture Capping (Hardware)
        if hw.gtt_used_gb <= 50.0:
            diagnostics.append(
                DoctorDiagnostic(
                    subsystem="hardware",
                    rule_name="gtt_aperture_cap",
                    passed=True,
                    severity="INFO",
                    message=f"GTT aperture used ({hw.gtt_used_gb:.1f} GiB) within safe 50.0 GiB ceiling",
                )
            )
        else:
            diagnostics.append(
                DoctorDiagnostic(
                    subsystem="hardware",
                    rule_name="gtt_aperture_cap",
                    passed=False,
                    severity="WARNING",
                    message=f"GTT aperture ({hw.gtt_used_gb:.1f} GiB) exceeds safe 50.0 GiB ceiling",
                    action_item="Unload secondary GGUF models from Lemonade/iGPU",
                )
            )

        # Rule 3: Kernel PSI Memory Pressure (Hardware)
        if hw.psi_memory_avg10 <= 20.0:
            diagnostics.append(
                DoctorDiagnostic(
                    subsystem="hardware",
                    rule_name="psi_memory_pressure",
                    passed=True,
                    severity="INFO",
                    message=f"Memory PSI ({hw.psi_memory_avg10:.1f}) indicates zero swap thrashing",
                )
            )
        else:
            diagnostics.append(
                DoctorDiagnostic(
                    subsystem="hardware",
                    rule_name="psi_memory_pressure",
                    passed=False,
                    severity="ERROR",
                    message=f"Memory PSI ({hw.psi_memory_avg10:.1f}) exceeds safe limit (20.0)",
                    action_item="Throttle parallel simulation worker threads",
                )
            )

        # Rule 4: Lemonade OmniRouter Availability (Software)
        if sw.lemonade_online:
            diagnostics.append(
                DoctorDiagnostic(
                    subsystem="software",
                    rule_name="lemonade_omnirouter_online",
                    passed=True,
                    severity="INFO",
                    message=f"Lemonade OmniRouter online ({len(sw.lemonade_models_loaded)} models in catalog)",
                )
            )
        else:
            diagnostics.append(
                DoctorDiagnostic(
                    subsystem="software",
                    rule_name="lemonade_omnirouter_online",
                    passed=False,
                    severity="ERROR",
                    message="Lemonade OmniRouter on port 13305 is offline or unreachable",
                    action_item="Run 'lemonade serve' or check systemctl --user status lemonade",
                )
            )

        # Rule 5: SurrealDB Database Availability (Software)
        if sw.surrealdb_online:
            diagnostics.append(
                DoctorDiagnostic(
                    subsystem="software",
                    rule_name="surrealdb_online",
                    passed=True,
                    severity="INFO",
                    message="SurrealDB state engine is responsive on port 8001",
                )
            )
        else:
            diagnostics.append(
                DoctorDiagnostic(
                    subsystem="software",
                    rule_name="surrealdb_online",
                    passed=False,
                    severity="ERROR",
                    message="SurrealDB on port 8001 is offline or unreachable",
                    action_item="Restart SurrealDB daemon via systemctl start surrealdb",
                )
            )

        # Rule 6: Git Index File Limit (Software)
        git_limit = int(os.environ.get("COHEZION_GIT_INDEX_LIMIT", "15000"))
        if sw.git_index_healthy:
            diagnostics.append(
                DoctorDiagnostic(
                    subsystem="software",
                    rule_name="git_index_size_limit",
                    passed=True,
                    severity="INFO",
                    message=f"Git tracked index ({sw.git_index_file_count} files) under {git_limit} file limit",
                )
            )
        else:
            diagnostics.append(
                DoctorDiagnostic(
                    subsystem="software",
                    rule_name="git_index_size_limit",
                    passed=False,
                    severity="WARNING",
                    message=f"Git tracked index ({sw.git_index_file_count} files) breaches {git_limit} limit",
                    action_item="Untrack node_modules, cache, or large vendor binaries",
                )
            )

        # Rule 7: Autopoiesis Daemon Progress (Projects)
        if proj.autopoiesis_cycle > 0 and proj.autopoiesis_last_delta_s <= 0.0:
            diagnostics.append(
                DoctorDiagnostic(
                    subsystem="projects",
                    rule_name="autopoiesis_negentropy_progress",
                    passed=True,
                    severity="INFO",
                    message=f"Autopoiesis Cycle {proj.autopoiesis_cycle}/{proj.autopoiesis_target_cycles} active with negative entropy (ΔS={proj.autopoiesis_last_delta_s:.4f})",
                )
            )
        else:
            diagnostics.append(
                DoctorDiagnostic(
                    subsystem="projects",
                    rule_name="autopoiesis_negentropy_progress",
                    passed=False,
                    severity="WARNING",
                    message="Autopoiesis daemon is either inactive or experiencing non-negative entropy",
                    action_item="Check scripts/ops/autonomous_overnight_autopoiesis_daemon.py",
                )
            )

        return diagnostics

    def snapshot(self) -> OperationsSnapshot:
        """Create a complete, synchronized operations snapshot."""
        hw = self.hardware.get_telemetry()
        sw = self.software.get_telemetry()
        proj = self.projects.get_telemetry()

        diagnostics = self.run_diagnostics(hw, sw, proj)

        # Compute overall status
        critical_count = sum(1 for d in diagnostics if not d.passed and d.severity == "ERROR")
        warning_count = sum(1 for d in diagnostics if not d.passed and d.severity == "WARNING")

        if critical_count > 0:
            overall = "CRITICAL"
        elif warning_count > 0:
            overall = "DEGRADED"
        else:
            overall = "HEALTHY"

        return OperationsSnapshot(
            timestamp=datetime.now(UTC).isoformat(),
            overall_status=overall,
            hardware=hw,
            software=sw,
            projects=proj,
            diagnostics=diagnostics,
        )

    def persist_snapshot(self, snapshot: OperationsSnapshot) -> dict[str, bool]:
        """Persist snapshot to SurrealDB and Obsidian Vault fail-open."""
        results = {"surreal": False, "vault": False}

        # 1. SurrealDB persistence
        try:
            surql = f"CREATE system_telemetry CONTENT {json.dumps(snapshot.to_dict())};"
            req = urllib.request.Request(  # noqa: S310
                SURREAL_URL,
                data=surql.encode("utf-8"),
                headers={
                    "surreal-ns": SURREAL_NS,
                    "surreal-db": SURREAL_DB,
                    "Content-Type": "text/plain",
                    "Authorization": f"Basic {SURREAL_AUTH}",
                },
            )
            with urllib.request.urlopen(req, timeout=3) as resp:  # noqa: S310
                results["surreal"] = resp.status in (200, 204)
        except Exception as e:
            logger.warning(f"Failed to persist operations snapshot to SurrealDB: {e}")

        # 2. Obsidian Vault persistence
        try:
            ops_dir = OBSIDIAN_VAULT_DIR / "ops"
            ops_dir.mkdir(parents=True, exist_ok=True)
            daily_file = ops_dir / "latest_control_plane.md"

            content = (
                f"# Cohezion Operations Snapshot\n\n"
                f"- **Timestamp**: `{snapshot.timestamp}`\n"
                f"- **Overall Status**: `{snapshot.overall_status}`\n\n"
                f"## Hardware\n"
                f"- **RAM**: Available `{snapshot.hardware.available_ram_gb:.1f} GiB` / Floor `{snapshot.hardware.dynamic_floor_gb:.1f} GiB`\n"
                f"- **GTT Aperture**: `{snapshot.hardware.gtt_used_gb:.1f} GiB` / `{snapshot.hardware.gtt_total_gb:.1f} GiB`\n"
                f"- **PSI Memory Pressure**: `{snapshot.hardware.psi_memory_avg10:.1f}`\n"
                f"- **CPU**: `{snapshot.hardware.cpu_cores_physical}` physical / `{snapshot.hardware.cpu_cores_logical}` logical cores, Load: `{snapshot.hardware.load_avg_1m}`\n\n"
                f"## Software\n"
                f"- **Lemonade (port 13305)**: `{'Online' if snapshot.software.lemonade_online else 'Offline'}` ({len(snapshot.software.lemonade_models_loaded)} models)\n"
                f"- **Ollama (port 11434)**: `{'Online' if snapshot.software.ollama_online else 'Offline'}` ({len(snapshot.software.ollama_models_loaded)} models)\n"
                f"- **SurrealDB (port 8001)**: `{'Online' if snapshot.software.surrealdb_online else 'Offline'}`\n"
                f"- **Git Index**: `{snapshot.software.git_index_file_count} files` (`{'Healthy' if snapshot.software.git_index_healthy else 'Bloated'}`)\n\n"
                f"## Projects\n"
                f"- **Autopoiesis Cycle**: `{snapshot.projects.autopoiesis_cycle}/{snapshot.projects.autopoiesis_target_cycles}` (ΔS = `{snapshot.projects.autopoiesis_last_delta_s:.4f}`)\n"
                f"- **Kanban Items**: {json.dumps(snapshot.projects.kanban_summary)}\n"
                f"- **Kaggle Active Tracks**: {len(snapshot.projects.active_kaggle_tracks)} tracks monitored\n"
            )
            daily_file.write_text(content, encoding="utf-8")
            results["vault"] = True
        except Exception as e:
            logger.warning(f"Failed to persist operations snapshot to Obsidian Vault: {e}")

        return results


# =====================================================================
# CLI Entrypoints
# =====================================================================


def render_cli_dashboard(snapshot: OperationsSnapshot) -> None:
    """Print an ASCII dashboard summarizing operations."""
    status_icon = (
        "🟢"
        if snapshot.overall_status == "HEALTHY"
        else ("🟡" if snapshot.overall_status == "DEGRADED" else "🔴")
    )

    print("\n" + "=" * 80)
    print(f"🌌 COHEZION OPERATIONS CONTROL PLANE {status_icon} [{snapshot.overall_status}]")
    print(f"Time: {snapshot.timestamp}")
    print("=" * 80)

    # Hardware Section
    hw = snapshot.hardware
    hw_icon = "✅" if hw.status == "HEALTHY" else ("⚠️" if hw.status == "DEGRADED" else "❌")
    print(f"\n{hw_icon} HARDWARE (AMD Strix Halo 128GB UMA)")
    print(
        f"  • Available RAM:    {hw.available_ram_gb:>6.1f} GiB  [Floor: {hw.dynamic_floor_gb:.1f} GiB]"
    )
    print(f"  • GTT Aperture:     {hw.gtt_used_gb:>6.1f} GiB  [Ceiling: 50.0 GiB]")
    print(f"  • Memory PSI:       {hw.psi_memory_avg10:>6.1f}%    [Max Safe: 20.0%]")
    print(
        f"  • CPU Load (1m/5m): {hw.load_avg_1m:.2f} / {hw.load_avg_5m:.2f}  [{hw.cpu_cores_physical} cores / {hw.cpu_cores_logical} threads]"
    )

    # Software Section
    sw = snapshot.software
    sw_icon = "✅" if sw.status == "HEALTHY" else ("⚠️" if sw.status == "DEGRADED" else "❌")
    print(f"\n{sw_icon} SOFTWARE (Inference, Services & Storage)")
    print(
        f"  • Lemonade (13305): {'🟢 ONLINE' if sw.lemonade_online else '🔴 OFFLINE'}  [{len(sw.lemonade_models_loaded)} models]"
    )
    print(
        f"  • Ollama (11434):   {'🟢 ONLINE' if sw.ollama_online else '🔴 OFFLINE'}  [{len(sw.ollama_models_loaded)} models]"
    )
    print(f"  • SurrealDB (8001): {'🟢 ONLINE' if sw.surrealdb_online else '🔴 OFFLINE'}")
    print(
        f"  • Git Index:        {sw.git_index_file_count} files  [{'🟢 OK' if sw.git_index_healthy else '🔴 BLOATED'}]"
    )
    print(
        f"  • Obsidian Vault:   {'🟢 ACCESSIBLE' if sw.obsidian_vault_accessible else '🔴 MISSING'}"
    )

    # Projects Section
    proj = snapshot.projects
    proj_icon = "✅" if proj.status == "HEALTHY" else ("⚠️" if proj.status == "DEGRADED" else "❌")
    print(f"\n{proj_icon} PROJECTS (Kaggle, Kanban, Autopoiesis)")
    print(
        f"  • Autopoiesis:      Cycle {proj.autopoiesis_cycle}/{proj.autopoiesis_target_cycles}  [ΔS = {proj.autopoiesis_last_delta_s:.4f} | Converged: {proj.autopoiesis_converged}]"
    )
    print(f"  • Kanban Tasks:     {proj.kanban_summary}")
    print("  • Kaggle Active Tracks:")
    for tr in proj.active_kaggle_tracks:
        print(
            f"      - {tr['competition'][:32]:<32} | Ref: {tr.get('latest_ref', 'N/A')} | Status: {tr.get('status', 'N/A')} | Score: {tr.get('public_score', 'N/A')}"
        )

    # Diagnostics Summary
    failures = [d for d in snapshot.diagnostics if not d.passed]
    if failures:
        print("\n⚠️ DIAGNOSTIC ALERTS:")
        for f in failures:
            print(f"  • [{f.severity}] {f.subsystem.upper()}: {f.message}")
            if f.action_item:
                print(f"    ↳ Remedy: {f.action_item}")
    else:
        print("\n✅ ALL INVARIANT DIAGNOSTIC RULES PASSED")
    print("=" * 80 + "\n")


def main() -> None:
    """CLI execution entrypoint."""
    import sys

    control_plane = CohezionControlPlane()
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "heal":
        print("Running hardware and memory self-healing...")
        res = control_plane.hardware.heal_hardware()
        print(json.dumps(res, indent=2))
        return

    snapshot = control_plane.snapshot()
    persisted = control_plane.persist_snapshot(snapshot)

    if cmd == "json":
        print(json.dumps(snapshot.to_dict(), indent=2))
    elif cmd == "doctor":
        render_cli_dashboard(snapshot)
        failures = [d for d in snapshot.diagnostics if not d.passed and d.severity == "ERROR"]
        if failures:
            sys.exit(1)
    else:
        render_cli_dashboard(snapshot)
        print(
            f"Snapshot persisted to SurrealDB: {persisted['surreal']} | Obsidian Vault: {persisted['vault']}"
        )


if __name__ == "__main__":
    main()
