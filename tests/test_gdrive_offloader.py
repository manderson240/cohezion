"""Unit tests for GDriveOffloader.
=================================
Verifies folder discovery, file save, fallback mechanisms, zero crashing,
compact cache disk budget management, and pure low-memory (<5MB RAM) streaming operations.
"""

import json
import logging
import sys
import tracemalloc
from pathlib import Path
from unittest.mock import MagicMock

# Ensure worktree src has priority over external editable installs
_WORKTREE_SRC = str((Path(__file__).resolve().parent.parent / "src").resolve())
if _WORKTREE_SRC not in sys.path or sys.path[0] != _WORKTREE_SRC:
    sys.path.insert(0, _WORKTREE_SRC)
for mod_name in list(sys.modules.keys()):
    if mod_name == "cohezion" or mod_name.startswith("cohezion."):
        mod = sys.modules[mod_name]
        mod_file = getattr(mod, "__file__", "") or ""
        if not mod_file.startswith(_WORKTREE_SRC):
            del sys.modules[mod_name]

import pytest

from cohezion.storage.gdrive_offloader import (
    DEFAULT_FOLDER_ID,
    DEFAULT_FOLDER_NAME,
    FolderInfo,
    GDriveOffloader,
    OffloadResult,
)


def test_default_constants_and_initialization(tmp_path: Path):
    """Verify default folder name, folder ID, and initialization attributes."""
    assert DEFAULT_FOLDER_NAME == "Cohezion_Kaggle_Checkpoints"
    assert DEFAULT_FOLDER_ID == "1YRg6l3MwI2JMVBmqX7u4TDiw5OHbE3yC"

    offloader = GDriveOffloader(local_cache_dir=tmp_path / "offload")
    assert offloader.folder_name == "Cohezion_Kaggle_Checkpoints"
    assert offloader.folder_id == "1YRg6l3MwI2JMVBmqX7u4TDiw5OHbE3yC"
    assert offloader.local_cache_dir == tmp_path / "offload"
    assert offloader.local_cache_dir.exists()
    assert not offloader.is_online


def test_folder_discovery_existing_folder_online(tmp_path: Path):
    """Verify discovery of existing folder via mock client find_folder."""
    mock_client = MagicMock()
    mock_client.find_folder.return_value = {
        "id": "remote_existing_folder_99",
        "name": DEFAULT_FOLDER_NAME,
    }

    offloader = GDriveOffloader(client=mock_client, local_cache_dir=tmp_path / "cache")
    folder = offloader.find_or_create_folder()

    assert isinstance(folder, FolderInfo)
    assert folder.id == "remote_existing_folder_99"
    assert folder["id"] == "remote_existing_folder_99"
    assert folder.status == "found"
    mock_client.find_folder.assert_called_once_with(DEFAULT_FOLDER_NAME, parent_id=None)
    mock_client.create_folder.assert_not_called()


def test_folder_creation_new_folder_online(tmp_path: Path):
    """Verify creation of destination folder when not found on Google Drive."""
    mock_client = MagicMock()
    mock_client.find_folder.return_value = None
    mock_client.create_folder.return_value = {
        "id": "remote_created_folder_101",
        "name": "Custom_Checkpoints",
    }

    offloader = GDriveOffloader(client=mock_client, local_cache_dir=tmp_path / "cache")
    folder = offloader.find_or_create_folder(folder_name="Custom_Checkpoints", parent_id="root_123")

    assert folder.id == "remote_created_folder_101"
    assert folder.status == "created"
    mock_client.find_folder.assert_called_once_with("Custom_Checkpoints", parent_id="root_123")
    mock_client.create_folder.assert_called_once_with("Custom_Checkpoints", parent_id="root_123")


def test_folder_discovery_offline_fallback(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    """Verify offline mode falls back to local cache directory with warning log."""
    cache_dir = tmp_path / "offline_cache"
    offloader = GDriveOffloader(client=None, local_cache_dir=cache_dir)

    with caplog.at_level(logging.WARNING):
        folder = offloader.find_or_create_folder()

    assert folder.id == DEFAULT_FOLDER_ID
    assert folder.name == DEFAULT_FOLDER_NAME
    assert folder.status == "cached"
    assert folder.path is not None
    assert Path(folder.path).exists()
    assert (cache_dir / DEFAULT_FOLDER_NAME).is_dir()
    assert any("offline or unauthenticated" in rec.message for rec in caplog.records)


def test_file_save_and_upload_online(tmp_path: Path):
    """Verify structured summaries (JSON and Markdown) upload to Google Drive via mock client."""
    mock_client = MagicMock()
    mock_client.upload_file.return_value = {"id": "gdrive_file_json_01", "name": "eval_summary.json"}

    offloader = GDriveOffloader(client=mock_client, local_cache_dir=tmp_path / "cache")

    # 1. JSON summary
    summary_data = {
        "model": "qwen2.5-coder-7b",
        "evaluation": {"accuracy": 0.942, "latency_ms": 12.5},
        "completed": True,
    }
    res_json = offloader.offload_json(summary_data, "eval_summary.json")

    assert isinstance(res_json, OffloadResult)
    assert res_json.success is True
    assert res_json.destination == "gdrive"
    assert res_json.file_id == "gdrive_file_json_01"
    assert res_json["destination"] == "gdrive"
    assert res_json.bytes_written > 0
    assert mock_client.upload_file.called

    # 2. Markdown summary
    mock_client.upload_file.return_value = {"id": "gdrive_file_md_02", "name": "benchmark_report.md"}
    md_content = "# Evaluation Trajectory Report\n\n- Epoch 10: Converged\n- Loss: 0.012\n"
    res_md = offloader.offload_markdown(md_content, "benchmark_report.md")

    assert res_md.success is True
    assert res_md.destination == "gdrive"
    assert res_md.file_id == "gdrive_file_md_02"


def test_fallback_mechanisms_offline(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    """Verify offline operations save to compact local cache without crashing and log warnings."""
    cache_dir = tmp_path / "cache_fallback"
    offloader = GDriveOffloader(client=None, local_cache_dir=cache_dir)

    with caplog.at_level(logging.WARNING):
        # 1. JSON offload
        payload = {"experiment_id": "exp_v42", "best_score": 0.887}
        res_json = offloader.offload_json(payload, "exp_v42_summary.json")

        assert res_json.success is True
        assert res_json.destination == "local_cache"
        assert res_json.file_id is None
        local_json_path = Path(res_json.file_path)
        assert local_json_path.exists()

        # Verify saved content
        saved_data = json.loads(local_json_path.read_text(encoding="utf-8"))
        assert saved_data == payload

        # 2. Markdown offload
        md_text = "### Experiment Notes\n* Gradient clip applied\n* LR warmup 100 steps\n"
        res_md = offloader.offload_markdown(md_text, "notes.md")

        assert res_md.success is True
        assert res_md.destination == "local_cache"
        local_md_path = Path(res_md.file_path)
        assert local_md_path.exists()
        assert local_md_path.read_text(encoding="utf-8") == md_text

    # Verify warning logs emitted
    warnings = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(warnings) >= 2
    assert any("offline or unauthenticated" in w for w in warnings)


def test_fallback_on_client_exception(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    """Verify resilience: remote upload errors trigger local cache fallback with zero crashing."""
    mock_client = MagicMock()
    mock_client.upload_file.side_effect = ConnectionResetError("Remote host disconnected")

    cache_dir = tmp_path / "resilience_cache"
    offloader = GDriveOffloader(client=mock_client, local_cache_dir=cache_dir)

    with caplog.at_level(logging.WARNING):
        res = offloader.offload_summary({"checkpoint": "chk_epoch_5.pt"}, "chk_summary.json")

    # Must NOT crash, must succeed via fallback
    assert res.success is True
    assert res.destination == "local_cache"
    assert res.error is not None
    assert "Remote host disconnected" in res.error
    assert Path(res.file_path).exists()
    assert any("Google Drive upload failed" in rec.message for rec in caplog.records)


def test_pure_low_memory_operation(tmp_path: Path):
    """Verify that offloading large payloads stays strictly below 5MB RAM via chunked streaming."""
    offloader = GDriveOffloader(local_cache_dir=tmp_path / "low_mem_cache")

    # 10 MB payload streamed via generator in 64 KB chunks
    total_chunks = 160
    chunk_size = 64 * 1024
    expected_total_bytes = total_chunks * chunk_size

    def stream_large_payload():
        chunk = b"Z" * chunk_size
        for _ in range(total_chunks):
            yield chunk

    tracemalloc.start()
    tracemalloc.reset_peak()
    try:
        result = offloader.offload_summary(stream_large_payload(), "large_payload_10mb.bin")
        current, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    peak_mb = peak / (1024 * 1024)

    assert result.success is True
    assert result.destination == "local_cache"
    assert result.bytes_written == expected_total_bytes

    saved_file = Path(result.file_path)
    assert saved_file.exists()
    assert saved_file.stat().st_size == expected_total_bytes

    # Strict low-memory assertion: strictly under 5.0 MB peak memory
    assert peak_mb < 5.0, f"Memory peak was {peak_mb:.2f} MB, must be strictly under 5.0 MB"


def test_compact_cache_disk_pruning(tmp_path: Path):
    """Verify cache pruning prevents unbounded disk consumption by enforcing budget."""
    cache_dir = tmp_path / "compact_cache"
    # Set a tiny 10 KB budget and max 4 files
    offloader = GDriveOffloader(
        local_cache_dir=cache_dir,
        max_cache_size_bytes=10 * 1024,
        max_cached_files=4,
        auto_prune=True,
    )

    # Write 6 files of 3 KB each = 18 KB (> 10 KB budget)
    for i in range(6):
        data = f"data_block_{i:04d}_" + ("x" * 3000)
        offloader.offload_summary(data, f"block_{i}.txt")

    stats = offloader.get_cache_stats()
    # Cache must stay within limits
    assert stats["file_count"] <= 4
    assert stats["total_bytes"] <= 10 * 1024


def test_offload_file_and_archive_directory(tmp_path: Path):
    """Verify offloading existing checkpoint files and directory archiving."""
    cache_dir = tmp_path / "checkpoint_cache"
    offloader = GDriveOffloader(local_cache_dir=cache_dir)

    # 1. Existing file
    source_file = tmp_path / "model_weights.bin"
    source_file.write_bytes(b"MODEL_WEIGHT_BYTES_12345")
    res_file = offloader.offload_file(source_file)

    assert res_file.success is True
    assert res_file.bytes_written == len(b"MODEL_WEIGHT_BYTES_12345")
    assert (cache_dir / "model_weights.bin").exists()

    # 2. Directory archive
    source_dir = tmp_path / "run_artifacts"
    source_dir.mkdir()
    (source_dir / "step_1.log").write_text("step 1 log content")
    (source_dir / "step_2.log").write_text("step 2 log content")

    res_archive = offloader.archive_directory(source_dir, "run_bundle")
    assert res_archive.success is True
    assert (cache_dir / "run_bundle.tar.gz").exists()
    assert (cache_dir / "run_bundle.tar.gz").stat().st_size > 0


def test_offload_nonexistent_file_raises(tmp_path: Path):
    """Verify FileNotFoundError when attempting to offload a nonexistent local file."""
    offloader = GDriveOffloader(local_cache_dir=tmp_path / "cache")
    with pytest.raises(FileNotFoundError):
        offloader.offload_file(tmp_path / "does_not_exist_file.pt")
