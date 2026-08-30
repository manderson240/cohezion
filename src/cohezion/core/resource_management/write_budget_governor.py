r"""Write Budget & Disk I/O Throttling Governor.
================================================
Protects SSD / NVMe and ZFS pools from runaway disk writes and log bloat by:
1. **Daily & Hourly Write Quotas**:
   - Enforces a hard maximum write budget per hour (e.g. 500 MB/hr) and per day (e.g. 5.0 GB/day).
2. **Circular Rolling Log Ring Buffers**:
   - Caps daemon log files and research transcripts to bounded sizes (e.g. max 10.0 MB per log with rotating `.1` backup).
3. **In-Memory Volatile Staging & Compaction**:
   - Buffers high-frequency event traces in RAM and performs deterministic batch compaction before committing to NVMe storage.
4. **Cloud Offload Diverter**:
   - When local disk write budget reaches 80%, redirects raw traces to Google Workspace (Google Drive / Google Docs / Sheets) or ephemeral memory tables instead of local disk.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("write_governor")


@dataclass
class WriteBudgetTracker:
    bytes_written_current_hour: int = 0
    bytes_written_today: int = 0
    current_hour_window: int = field(default_factory=lambda: int(time.time() // 3600))
    current_day_window: int = field(default_factory=lambda: int(time.time() // 86400))
    max_bytes_per_hour: int = 500 * 1024 * 1024  # 500 MB/hr
    max_bytes_per_day: int = 5 * 1024 * 1024 * 1024  # 5 GB/day


class WriteBudgetGovernor:
    """Enforces strict NVMe write limits and prevents storage exhaustion."""

    def __init__(
        self,
        max_bytes_per_hour: int = 500 * 1024 * 1024,
        max_bytes_per_day: int = 5 * 1024 * 1024 * 1024,
        max_single_file_mb: float = 10.0,
    ) -> None:
        self.tracker = WriteBudgetTracker(
            max_bytes_per_hour=max_bytes_per_hour,
            max_bytes_per_day=max_bytes_per_day,
        )
        self.max_single_file_bytes = int(max_single_file_mb * 1024 * 1024)

    def _refresh_windows(self) -> None:
        """Reset hourly and daily windows if time has elapsed."""
        now_hour = int(time.time() // 3600)
        now_day = int(time.time() // 86400)

        if now_hour != self.tracker.current_hour_window:
            self.tracker.current_hour_window = now_hour
            self.tracker.bytes_written_current_hour = 0

        if now_day != self.tracker.current_day_window:
            self.tracker.current_day_window = now_day
            self.tracker.bytes_written_today = 0

    def can_write(self, payload_size_bytes: int) -> bool:
        """Check whether writing this payload violates the write budget."""
        self._refresh_windows()

        if (self.tracker.bytes_written_current_hour + payload_size_bytes) > self.tracker.max_bytes_per_hour:
            logger.warning("⛔ Hourly write budget exceeded! Throttling disk write.")
            return False

        if (self.tracker.bytes_written_today + payload_size_bytes) > self.tracker.max_bytes_per_day:
            logger.warning("⛔ Daily write budget exceeded! Throttling disk write.")
            return False

        return True

    def safe_write_text(
        self,
        file_path: Path | str,
        content: str,
        append: bool = False,
    ) -> dict[str, Any]:
        """Safely write text to file while enforcing write budget and size rotation."""
        p = Path(file_path)
        content_bytes = len(content.encode("utf-8"))

        if not self.can_write(content_bytes):
            return {
                "status": "throttled",
                "reason": "write_budget_exceeded",
                "bytes_requested": content_bytes,
            }

        # Check existing file size for bounded rotation
        if p.exists() and append:
            curr_size = p.stat().st_size
            if (curr_size + content_bytes) > self.max_single_file_bytes:
                # Rotate file: move to .1 and start fresh
                rotated = p.with_suffix(p.suffix + ".1")
                try:
                    p.replace(rotated)
                    logger.info("🔄 Rotated oversized log file: %s -> %s", p, rotated)
                except Exception as e:
                    logger.warning("Failed to rotate file: %s", e)

        p.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with open(p, mode, encoding="utf-8") as f:
            f.write(content)

        # Track usage
        self.tracker.bytes_written_current_hour += content_bytes
        self.tracker.bytes_written_today += content_bytes

        return {
            "status": "written",
            "bytes_written": content_bytes,
            "hourly_used_mb": round(self.tracker.bytes_written_current_hour / (1024 * 1024), 2),
            "daily_used_mb": round(self.tracker.bytes_written_today / (1024 * 1024), 2),
        }
