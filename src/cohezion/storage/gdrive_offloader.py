"""Google Drive Storage Offloader and Headroom Manager.
=====================================================
Monitors filesystem headroom and securely offloads generated artifacts,
overnight logs, and heavy experiment traces to Google Drive (rclone remote)
to preserve local NVMe capacity and reduce physical disk entropy.
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import tarfile
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

logger = logging.getLogger("gdrive_offloader")

DEFAULT_REMOTE_BASE = "gdrive:cohezion-archive"
DEFAULT_WARNING_THRESHOLD_GB = 50.0  # Alert when < 50 GB free
DEFAULT_CRITICAL_THRESHOLD_GB = 20.0  # Force immediate offload when < 20 GB free


class StorageHealth(BaseModel):
    """Storage health metrics for monitored filesystem."""

    path: str
    total_gb: float
    used_gb: float
    available_gb: float
    use_percent: float
    status: Literal["healthy", "warning", "critical"]
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class OffloadJob(BaseModel):
    """Record of an offload execution to Google Drive."""

    job_id: str
    source_path: str
    remote_dest: str
    total_bytes: int = 0
    file_count: int = 0
    success: bool = False
    error_msg: str | None = None
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str | None = None


class GDriveStorageManager:
    """Manages local storage hygiene and coordinates secure Google Drive offloading."""

    def __init__(
        self,
        remote_base: str = DEFAULT_REMOTE_BASE,
        warning_gb: float = DEFAULT_WARNING_THRESHOLD_GB,
        critical_gb: float = DEFAULT_CRITICAL_THRESHOLD_GB,
    ) -> None:
        self.remote_base = remote_base.rstrip("/")
        self.warning_gb = warning_gb
        self.critical_gb = critical_gb

    def check_storage_health(self, target_path: str | Path = "/home") -> StorageHealth:
        """Inspect storage headroom on the given filesystem mount."""
        path_str = str(target_path)
        try:
            usage = shutil.disk_usage(path_str)
            total_gb = usage.total / (1024**3)
            used_gb = usage.used / (1024**3)
            avail_gb = usage.free / (1024**3)
            use_pct = (usage.used / usage.total) * 100.0 if usage.total > 0 else 0.0

            status: Literal["healthy", "warning", "critical"] = "healthy"
            if avail_gb < self.critical_gb:
                status = "critical"
            elif avail_gb < self.warning_gb:
                status = "warning"

            return StorageHealth(
                path=path_str,
                total_gb=round(total_gb, 2),
                used_gb=round(used_gb, 2),
                available_gb=round(avail_gb, 2),
                use_percent=round(use_pct, 1),
                status=status,
            )
        except Exception as e:
            logger.error("Failed to query disk usage for %s: %s", path_str, e)
            return StorageHealth(
                path=path_str,
                total_gb=0.0,
                used_gb=0.0,
                available_gb=0.0,
                use_percent=0.0,
                status="critical",
            )

    async def offload_path(
        self,
        local_path: Path,
        remote_subfolder: str = "overnight",
        move_files: bool = False,
    ) -> OffloadJob:
        """Safely copy or move a file/directory to Google Drive via rclone."""
        job_id = f"offload_{int(datetime.now(timezone.utc).timestamp())}"
        target_remote = f"{self.remote_base}/{remote_subfolder.strip('/')}"

        if not local_path.exists():
            return OffloadJob(
                job_id=job_id,
                source_path=str(local_path),
                remote_dest=target_remote,
                success=False,
                error_msg=f"Source path {local_path} does not exist",
            )

        # Count files & bytes
        total_bytes = 0
        file_count = 0
        if local_path.is_file():
            total_bytes = local_path.stat().st_size
            file_count = 1
        elif local_path.is_dir():
            for p in local_path.rglob("*"):
                if p.is_file():
                    total_bytes += p.stat().st_size
                    file_count += 1

        action_cmd = "move" if move_files else "copy"
        cmd = [
            "rclone",
            action_cmd,
            str(local_path),
            f"{target_remote}/{local_path.name}" if local_path.is_file() else target_remote,
            "--drive-chunk-size=32M",
            "--transfers=4",
        ]

        logger.info(
            "Initiating rclone %s from %s (%d files, %.2f MB) to %s",
            action_cmd,
            local_path,
            file_count,
            total_bytes / (1024**2),
            target_remote,
        )

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout_data, stderr_data = await asyncio.wait_for(proc.communicate(), timeout=300.0)

            if proc.returncode == 0:
                logger.info("Successfully offloaded %s to %s", local_path, target_remote)
                return OffloadJob(
                    job_id=job_id,
                    source_path=str(local_path),
                    remote_dest=target_remote,
                    total_bytes=total_bytes,
                    file_count=file_count,
                    success=True,
                    completed_at=datetime.now(timezone.utc).isoformat(),
                )
            else:
                err_text = stderr_data.decode("utf-8", errors="replace").strip()
                logger.error(
                    "Rclone %s failed (code %d): %s", action_cmd, proc.returncode, err_text
                )
                return OffloadJob(
                    job_id=job_id,
                    source_path=str(local_path),
                    remote_dest=target_remote,
                    total_bytes=total_bytes,
                    file_count=file_count,
                    success=False,
                    error_msg=f"rclone exit code {proc.returncode}: {err_text[:200]}",
                    completed_at=datetime.now(timezone.utc).isoformat(),
                )
        except Exception as e:
            logger.exception("Exception during rclone %s: %s", action_cmd, e)
            return OffloadJob(
                job_id=job_id,
                source_path=str(local_path),
                remote_dest=target_remote,
                total_bytes=total_bytes,
                file_count=file_count,
                success=False,
                error_msg=str(e),
                completed_at=datetime.now(timezone.utc).isoformat(),
            )

    async def compress_and_offload(
        self,
        source_dir: Path,
        archive_name: str,
        remote_subfolder: str = "archives",
        remove_source_after: bool = False,
    ) -> OffloadJob:
        """Compress directory into a .tar.gz tarball and offload to Google Drive."""
        job_id = f"compress_offload_{int(datetime.now(timezone.utc).timestamp())}"
        target_remote = f"{self.remote_base}/{remote_subfolder.strip('/')}"

        if not source_dir.exists() or not source_dir.is_dir():
            return OffloadJob(
                job_id=job_id,
                source_path=str(source_dir),
                remote_dest=target_remote,
                success=False,
                error_msg=f"Source directory {source_dir} not found",
            )

        with tempfile.TemporaryDirectory() as tmp_dir:
            archive_path = Path(tmp_dir) / f"{archive_name}.tar.gz"
            logger.info("Compressing %s -> %s", source_dir, archive_path)

            file_count = 0
            with tarfile.open(archive_path, "w:gz") as tar:
                for item in source_dir.iterdir():
                    tar.add(item, arcname=item.name)
                    file_count += 1

            total_bytes = archive_path.stat().st_size
            logger.info(
                "Archive created: %.2f MB across %d items", total_bytes / (1024**2), file_count
            )

            # Offload archive
            res = await self.offload_path(
                local_path=archive_path,
                remote_subfolder=remote_subfolder,
                move_files=False,
            )

            if res.success and remove_source_after:
                shutil.rmtree(source_dir)
                source_dir.mkdir(parents=True, exist_ok=True)
                logger.info("Cleaned local source directory %s post-offload", source_dir)

            res.source_path = str(source_dir)
            res.file_count = file_count
            return res
