"""Tests for cohezion.concurrency package."""

from __future__ import annotations

import asyncio
import json
import logging
import threading
from pathlib import Path

import pytest

from cohezion.concurrency.file_lock import LockedFileOperation
from cohezion.concurrency.ollama_gate import OllamaGate, get_gate, reset_gate
from cohezion.concurrency.safe_singleton import safe_singleton


# ---------------------------------------------------------------------------
# OllamaGate tests
# ---------------------------------------------------------------------------


class TestOllamaGate:
    """Tests for the async semaphore gate."""

    @pytest.mark.asyncio
    async def test_gate_limits_concurrency(self) -> None:
        """Gate should block the 5th concurrent caller when limit is 4."""
        gate = OllamaGate(max_concurrent=4)
        active = 0
        max_active = 0

        async def worker() -> None:
            nonlocal active, max_active
            async with gate:
                active += 1
                max_active = max(max_active, active)
                await asyncio.sleep(0.05)
                active -= 1

        await asyncio.gather(*[worker() for _ in range(8)])
        assert max_active <= 4

    @pytest.mark.asyncio
    async def test_gate_available_property(self) -> None:
        """available should reflect semaphore state."""
        gate = OllamaGate(max_concurrent=3)
        assert gate.available == 3
        async with gate:
            assert gate.available == 2
        assert gate.available == 3

    @pytest.mark.asyncio
    async def test_gate_releases_on_exception(self) -> None:
        """Gate should release slot even when body raises."""
        gate = OllamaGate(max_concurrent=2)
        with pytest.raises(ValueError, match="boom"):
            async with gate:
                raise ValueError("boom")
        assert gate.available == 2

    @pytest.mark.asyncio
    async def test_gate_custom_limit(self) -> None:
        """Gate should honour a non-default concurrency limit."""
        gate = OllamaGate(max_concurrent=1)
        active = 0
        max_active = 0

        async def worker() -> None:
            nonlocal active, max_active
            async with gate:
                active += 1
                max_active = max(max_active, active)
                await asyncio.sleep(0.02)
                active -= 1

        await asyncio.gather(*[worker() for _ in range(4)])
        assert max_active == 1

    @pytest.mark.asyncio
    async def test_gate_logs_acquire_release(self, caplog: pytest.LogCaptureFixture) -> None:
        """Gate should log acquire and release at DEBUG level."""
        gate = OllamaGate(max_concurrent=2)
        with caplog.at_level(logging.DEBUG, logger="cohezion.concurrency.ollama_gate"):
            async with gate:
                pass
        messages = [r.message for r in caplog.records]
        assert any("acquiring" in m for m in messages)
        assert any("released" in m for m in messages)


class TestGetGate:
    """Tests for the get_gate singleton factory."""

    def setup_method(self) -> None:
        reset_gate()

    def teardown_method(self) -> None:
        reset_gate()

    def test_get_gate_returns_singleton(self) -> None:
        """get_gate() should return the same instance on repeated calls."""
        g1 = get_gate()
        g2 = get_gate()
        assert g1 is g2

    def test_get_gate_thread_safe(self) -> None:
        """get_gate() should return the same instance from multiple threads."""
        results: list[OllamaGate] = []

        def fetch() -> None:
            results.append(get_gate())

        threads = [threading.Thread(target=fetch) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len({id(g) for g in results}) == 1

    def test_reset_gate(self) -> None:
        """reset_gate() should clear the singleton."""
        g1 = get_gate()
        reset_gate()
        g2 = get_gate()
        assert g1 is not g2


# ---------------------------------------------------------------------------
# LockedFileOperation tests
# ---------------------------------------------------------------------------


class TestLockedFileOperation:
    """Tests for the file-lock context manager."""

    def test_read_write_json(self, tmp_path: Path) -> None:
        """Should round-trip JSON data through lock."""
        fp = tmp_path / "data.json"
        data = {"count": 42, "items": [1, 2, 3]}
        with LockedFileOperation(fp) as locked:
            locked.write_json(data)
        with LockedFileOperation(fp) as locked:
            result = locked.read_json()
        assert result == data

    def test_read_json_default(self, tmp_path: Path) -> None:
        """Should return default when file doesn't exist."""
        fp = tmp_path / "missing.json"
        with LockedFileOperation(fp) as locked:
            result = locked.read_json(default={"empty": True})
        assert result == {"empty": True}

    def test_read_write_text(self, tmp_path: Path) -> None:
        """Should round-trip text through lock."""
        fp = tmp_path / "note.md"
        with LockedFileOperation(fp) as locked:
            locked.write_text("hello world")
        with LockedFileOperation(fp) as locked:
            result = locked.read_text()
        assert result == "hello world"

    def test_read_text_default(self, tmp_path: Path) -> None:
        """Should return default for missing text file."""
        fp = tmp_path / "missing.txt"
        with LockedFileOperation(fp) as locked:
            result = locked.read_text(default="fallback")
        assert result == "fallback"

    def test_creates_lock_sidecar(self, tmp_path: Path) -> None:
        """Should create a .lock sidecar file."""
        fp = tmp_path / "config.json"
        lock_path = Path(f"{fp}.lock")
        with LockedFileOperation(fp) as locked:
            locked.write_json({"a": 1})
            assert lock_path.exists()

    def test_concurrent_writers(self, tmp_path: Path) -> None:
        """Multiple threads writing should not corrupt data."""
        fp = tmp_path / "counter.json"
        fp.write_text(json.dumps({"count": 0}))

        def increment() -> None:
            for _ in range(20):
                with LockedFileOperation(fp) as locked:
                    data = locked.read_json(default={"count": 0})
                    data["count"] += 1
                    locked.write_json(data)

        threads = [threading.Thread(target=increment) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        with LockedFileOperation(fp) as locked:
            final = locked.read_json()
        assert final["count"] == 100

    def test_read_json_empty_file(self, tmp_path: Path) -> None:
        """Should return default for empty file."""
        fp = tmp_path / "empty.json"
        fp.write_text("")
        with LockedFileOperation(fp) as locked:
            result = locked.read_json(default={"zero": True})
        assert result == {"zero": True}


# ---------------------------------------------------------------------------
# safe_singleton tests
# ---------------------------------------------------------------------------


class TestSafeSingleton:
    """Tests for the safe_singleton decorator."""

    def test_returns_same_instance(self) -> None:
        """Decorated function should return the same object."""

        @safe_singleton
        def make_thing() -> dict:
            return {"created": True}

        a = make_thing()
        b = make_thing()
        assert a is b

    def test_reset_clears_instance(self) -> None:
        """reset() should clear the cached instance."""

        @safe_singleton
        def make_thing() -> dict:
            return {"created": True}

        a = make_thing()
        make_thing.reset()
        b = make_thing()
        assert a is not b

    def test_thread_safe(self) -> None:
        """Concurrent threads should all get the same instance."""
        call_count = 0

        @safe_singleton
        def make_thing() -> dict:
            nonlocal call_count
            call_count += 1
            return {"id": call_count}

        results: list[dict] = []

        def fetch() -> None:
            results.append(make_thing())

        threads = [threading.Thread(target=fetch) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should be the same instance
        assert len({id(r) for r in results}) == 1
        make_thing.reset()

    def test_preserves_function_name(self) -> None:
        """Decorator should preserve __name__ and __doc__."""

        @safe_singleton
        def my_factory() -> str:
            """My docstring."""
            return "instance"

        assert my_factory.__name__ == "my_factory"
        assert my_factory.__doc__ == "My docstring."
        my_factory.reset()

    def test_passes_args_on_first_call(self) -> None:
        """Args should be forwarded to the factory on first creation."""

        @safe_singleton
        def make_thing(value: int = 0) -> dict:
            return {"value": value}

        result = make_thing(value=42)
        assert result["value"] == 42
        # Second call ignores args (returns cached)
        same = make_thing(value=99)
        assert same["value"] == 42
        make_thing.reset()
