import asyncio
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from cohezion.storage.gdrive_offloader import (
    GDriveStorageManager,
    StorageHealth,
    OffloadJob,
)


def test_storage_health_inspection():
    mgr = GDriveStorageManager(warning_gb=50.0, critical_gb=20.0)
    health = mgr.check_storage_health("/home")
    assert isinstance(health, StorageHealth)
    assert health.total_gb > 0
    assert health.available_gb > 0
    assert health.status in ("healthy", "warning", "critical")


@pytest.mark.asyncio
async def test_offload_path_nonexistent():
    mgr = GDriveStorageManager()
    job = await mgr.offload_path(Path("/nonexistent/file/path/12345"))
    assert not job.success
    assert "does not exist" in (job.error_msg or "")


@pytest.mark.asyncio
async def test_offload_path_mock_success(tmp_path):
    test_file = tmp_path / "sample.txt"
    test_file.write_text("Hello Cohezion Cloud Storage!")

    mgr = GDriveStorageManager()

    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate.return_value = (b"Transferred 1 file", b"")

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
        job = await mgr.offload_path(test_file, remote_subfolder="test_folder")
        assert job.success
        assert job.file_count == 1
        assert job.total_bytes > 0
        assert mock_exec.called


@pytest.mark.asyncio
async def test_compress_and_offload_mock_success(tmp_path):
    sub_dir = tmp_path / "data_to_archive"
    sub_dir.mkdir()
    (sub_dir / "item1.log").write_text("log line 1")
    (sub_dir / "item2.log").write_text("log line 2")

    mgr = GDriveStorageManager()

    mock_proc = AsyncMock()
    mock_proc.returncode = 0
    mock_proc.communicate.return_value = (b"Transferred archive", b"")

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        job = await mgr.compress_and_offload(
            source_dir=sub_dir,
            archive_name="test_bundle",
            remote_subfolder="test_archives",
            remove_source_after=False,
        )
        assert job.success
        assert job.file_count == 2
