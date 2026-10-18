"""Unit tests for Zero-Copy Shared Memory Data Product Buffer.

Verifies atomic write, zero-copy read, metadata roundtripping, and product lifecycle.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from cohezion.data_mesh.shm_mesh import (
    MAGIC,
    PROTOCOL_VERSION,
    SharedMemoryDataProductBuffer,
    ShmProductDescriptor,
)


@pytest.fixture
def tmp_shm_dir(tmp_path: Path) -> Path:
    shm_dir = tmp_path / "shm_mesh"
    shm_dir.mkdir(parents=True, exist_ok=True)
    return shm_dir


def test_shm_buffer_publish_and_read(tmp_shm_dir: Path) -> None:
    buffer = SharedMemoryDataProductBuffer(base_dir=tmp_shm_dir)

    test_product_id = "test-sensor-telemetry"
    test_payload = b"Sample 128-dim embedding or raw spectrometry peaks\x00\xff" * 10
    test_meta = {"sample_rate": 44100, "dims": 128, "precision": "fp32"}

    desc = buffer.publish(test_product_id, test_payload, metadata=test_meta)

    assert isinstance(desc, ShmProductDescriptor)
    assert desc.product_id == test_product_id
    assert desc.payload_size == len(test_payload)
    assert desc.metadata == test_meta
    assert Path(desc.shm_path).exists()

    # Zero-copy read
    read_meta, read_payload = buffer.read(test_product_id)
    assert read_meta == test_meta
    assert bytes(read_payload) == test_payload


def test_shm_buffer_list_and_delete(tmp_shm_dir: Path) -> None:
    buffer = SharedMemoryDataProductBuffer(base_dir=tmp_shm_dir)

    buffer.publish("product_a", b"alpha", metadata={"k": 1})
    buffer.publish("product_b", b"beta", metadata={"k": 2})

    products = buffer.list_products()
    assert "product_a" in products
    assert "product_b" in products

    deleted = buffer.delete("product_a")
    assert deleted is True

    products_after = buffer.list_products()
    assert "product_a" not in products_after
    assert "product_b" in products_after


def test_shm_buffer_nonexistent_read(tmp_shm_dir: Path) -> None:
    buffer = SharedMemoryDataProductBuffer(base_dir=tmp_shm_dir)
    with pytest.raises(FileNotFoundError):
        buffer.read("non_existent_product")
