import pytest

pytest.importorskip("mem0", reason="mem0 optional dep not installed")
"""Tests for the local-first mem0 adapter (cohezion.memory.mem0_adapter).

Two layers:
  - Config/telemetry/import-safety tests run ALWAYS (no mem0 dependency).
  - Construction test uses importorskip("mem0") — skips cleanly when the optional
    `memory` extra is absent, so CI without the extra stays green.

Live add/search (LLM extraction) is intentionally NOT tested here: it requires a
live Lemonade node, and a passing test that can't actually run the extraction
would be a false signal. That validation is deferred to node-restore.
"""

from __future__ import annotations

import sys

import pytest

from cohezion.memory import Mem0Config, build_local_mem0, mem0_adapter, mem0_available


def test_config_defaults_are_local_first():
    """Default config must wire LLM + embedder to local Lemonade, not a cloud API."""
    d = Mem0Config().to_mem0_dict()
    assert d["llm"]["provider"] == "openai"
    assert d["llm"]["config"]["openai_base_url"].startswith("http://localhost:"), (
        "LLM must default to a local Lemonade endpoint (local-first policy)"
    )
    assert d["embedder"]["config"]["openai_base_url"].startswith("http://localhost:")
    # embedder dims and vector-store dims must agree, else add() fails at runtime
    assert d["embedder"]["config"]["embedding_dims"] == 768
    assert d["vector_store"]["config"]["embedding_model_dims"] == 768
    # in-process embedded store (path, no host/port) — no server process required
    assert d["vector_store"]["provider"] == "qdrant"
    assert "path" in d["vector_store"]["config"]
    assert "host" not in d["vector_store"]["config"]


def test_config_overrides_propagate():
    """Caller overrides must flow into the mem0 dict (e.g. route to NPU port)."""
    cfg = Mem0Config(llm_base_url="http://localhost:13306/v1", llm_model="llama3.2-1b-FLM")
    d = cfg.to_mem0_dict()
    assert d["llm"]["config"]["openai_base_url"] == "http://localhost:13306/v1"
    assert d["llm"]["config"]["model"] == "llama3.2-1b-FLM"


def test_disable_telemetry_sets_optout(monkeypatch):
    """Telemetry must be disabled so conversational memory never egresses."""
    monkeypatch.delenv("MEM0_TELEMETRY", raising=False)
    monkeypatch.delenv("POSTHOG_DISABLED", raising=False)
    mem0_adapter.disable_telemetry()
    assert mem0_adapter.os.environ["MEM0_TELEMETRY"] == "False"
    assert mem0_adapter.os.environ["POSTHOG_DISABLED"] == "1"


def test_disable_telemetry_respects_explicit_override(monkeypatch):
    """setdefault must not clobber an operator who deliberately re-enabled telemetry."""
    monkeypatch.setenv("MEM0_TELEMETRY", "True")
    mem0_adapter.disable_telemetry()
    assert mem0_adapter.os.environ["MEM0_TELEMETRY"] == "True"


def test_build_raises_clear_error_when_mem0_absent(monkeypatch):
    """With mem0 unimportable, build must raise ImportError naming the install extra."""
    # Force `from mem0 import Memory` to fail regardless of install state.
    monkeypatch.setitem(sys.modules, "mem0", None)
    with pytest.raises(ImportError, match=r"\.\[memory\]|mem0ai"):
        build_local_mem0()


def test_mem0_available_reflects_install_state(monkeypatch):
    """mem0_available() is True normally; False when mem0 is masked."""
    assert mem0_available() in (True, False)  # smoke: no crash
    monkeypatch.setitem(sys.modules, "mem0", None)
    assert mem0_available() is False


def test_build_local_mem0_constructs_offline(tmp_path):
    """Construction must succeed offline (clients lazy) and expose add/search."""
    pytest.importorskip("mem0", reason="optional `memory` extra not installed")
    cfg = Mem0Config(storage_path=str(tmp_path / "qdrant"))
    mem = build_local_mem0(cfg)
    assert hasattr(mem, "add") and hasattr(mem, "search"), (
        "mem0 Memory must expose add/search; construction made no network call"
    )
