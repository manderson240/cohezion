import os

import psutil

from cohezion.governance.guardian import Guardian


class LocalResourceManagerGuard(Guardian):
    """Guard to prevent OOM errors by enforcing resource limits on local processes."""

    def __init__(self):
        super().__init__("local-resource-manager-guard")
        self.max_memory_percent = 85.0
        self.max_process_memory_gb = 8.0

    def check_system_memory(self):
        """Check overall system memory usage."""
        try:
            mem = psutil.virtual_memory()
            if mem.percent > self.max_memory_percent:
                self.log_violation(
                    f"System memory usage critical: {mem.percent}% (> {self.max_memory_percent}%)",
                    location="system",
                )
        except Exception as e:
            self.logger.error(f"Failed to check system memory: {e}")

    def check_node_options(self, auto_heal: bool):
        """Ensure NODE_OPTIONS is set to prevent V8 OOM."""
        node_options = os.getenv("NODE_OPTIONS", "")
        if "max-old-space-size" not in node_options:
            msg = "NODE_OPTIONS lacks --max-old-space-size to prevent V8 OOM."
            if auto_heal:
                env_path = self.project_root / ".env"
                if env_path.exists():
                    content = env_path.read_text()
                    if "NODE_OPTIONS=" not in content:
                        with open(env_path, "a") as f:
                            f.write(
                                '\n# Auto-healed by LocalResourceManagerGuard\nNODE_OPTIONS="--max-old-space-size=8192"\n'
                            )
                        self.log_violation(
                            msg + " (Auto-healed by appending to .env)", location=".env"
                        )
                        return
            self.log_violation(msg, location="environment")

    def check_zombie_processes(self, auto_heal: bool):
        """Check for memory-hogging processes and process explosions."""
        overture_count = 0
        for proc in psutil.process_iter(["pid", "name", "cmdline", "memory_info"]):
            try:
                cmdline = proc.info.get("cmdline") or []
                name = proc.info.get("name") or ""
                mem_info = proc.info.get("memory_info")

                mem_gb = mem_info.rss / (1024**3) if mem_info else 0.0

                cmd_str = " ".join(cmdline) if cmdline else ""
                if "overture-proxy" in cmd_str or "overture-mcp" in cmd_str:
                    overture_count += 1

                if mem_gb > self.max_process_memory_gb:
                    msg = f"Process {proc.info['pid']} ({name}) exceeding memory limit: {mem_gb:.2f}GB > {self.max_process_memory_gb}GB"
                    # Do not kill essential dev tools or the browser automatically unless specified
                    safe_to_kill = not any(
                        x in name.lower() or x in cmd_str.lower()
                        for x in ["chrome", "claude", "gemini", "zed", "firefox"]
                    )
                    if auto_heal and safe_to_kill:
                        proc.terminate()
                        self.log_violation(
                            msg + " (Auto-healed by termination)",
                            location=f"pid:{proc.info['pid']}",
                        )
                    else:
                        self.log_violation(msg, location=f"pid:{proc.info['pid']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        if overture_count > 10:
            msg = f"Detected {overture_count} overture processes (possible explosion)."
            if auto_heal:
                for proc in psutil.process_iter(["pid", "cmdline"]):
                    try:
                        cmdline = proc.info.get("cmdline") or []
                        cmd_str = " ".join(cmdline) if cmdline else ""
                        if "overture-proxy" in cmd_str or "overture-mcp" in cmd_str:
                            proc.terminate()
                    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                        continue
                self.log_violation(
                    msg + " (Auto-healed by terminating all overture processes)", location="system"
                )
            else:
                self.log_violation(msg, location="system")

    def run(self, auto_heal: bool = False) -> bool:
        self.check_system_memory()
        self.check_node_options(auto_heal)
        self.check_zombie_processes(auto_heal)
        return len(self.violations) == 0


if __name__ == "__main__":
    guard = LocalResourceManagerGuard()
    success = guard.run(auto_heal=True)
    guard.report()
    if not success:
        import sys

        sys.exit(1)
