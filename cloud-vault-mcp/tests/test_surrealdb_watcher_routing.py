import pytest
from pathlib import Path
from types import SimpleNamespace

from mcp_server.surrealdb_sync import VaultFileHandler


class _StubSync:
    def __init__(self):
        self.paper_calls = []
        self.concept_calls = []

    def sync_paper(self, path):
        self.paper_calls.append(path)

    def sync_concept(self, path):
        self.concept_calls.append(path)


@pytest.fixture
def stub_sync():
    return _StubSync()


@pytest.fixture
def handler(stub_sync):
    return VaultFileHandler(stub_sync)


def test_cortex_md_calls_sync_paper(handler, stub_sync):
    event = SimpleNamespace(is_directory=False, src_path="/some/path/cortex/file.md")
    handler.on_modified(event)
    assert stub_sync.paper_calls == [Path("/some/path/cortex/file.md")]
    assert stub_sync.concept_calls == []


def test_cerebellum_md_calls_sync_concept(handler, stub_sync):
    event = SimpleNamespace(is_directory=False, src_path="/some/path/cerebellum/file.md")
    handler.on_modified(event)
    assert stub_sync.concept_calls == [Path("/some/path/cerebellum/file.md")]
    assert stub_sync.paper_calls == []


def test_decisions_md_calls_sync_concept_regression(handler, stub_sync):
    event = SimpleNamespace(is_directory=False, src_path="/some/path/decisions/file.md")
    handler.on_modified(event)
    assert stub_sync.concept_calls == [Path("/some/path/decisions/file.md")]
    assert stub_sync.paper_calls == []


def test_patterns_md_calls_sync_concept(handler, stub_sync):
    event = SimpleNamespace(is_directory=False, src_path="/some/path/patterns/file.md")
    handler.on_modified(event)
    assert stub_sync.concept_calls == [Path("/some/path/patterns/file.md")]
    assert stub_sync.paper_calls == []


def test_legacy_papers_md_calls_sync_paper(handler, stub_sync):
    event = SimpleNamespace(is_directory=False, src_path="/some/path/papers/file.md")
    handler.on_modified(event)
    assert stub_sync.paper_calls == [Path("/some/path/papers/file.md")]
    assert stub_sync.concept_calls == []


def test_legacy_concepts_md_calls_sync_concept(handler, stub_sync):
    event = SimpleNamespace(is_directory=False, src_path="/some/path/concepts/file.md")
    handler.on_modified(event)
    assert stub_sync.concept_calls == [Path("/some/path/concepts/file.md")]
    assert stub_sync.paper_calls == []


def test_directory_events_ignored(handler, stub_sync):
    event = SimpleNamespace(is_directory=True, src_path="/some/path/cortex/")
    handler.on_modified(event)
    assert stub_sync.paper_calls == []
    assert stub_sync.concept_calls == []


def test_non_md_files_ignored(handler, stub_sync):
    event = SimpleNamespace(is_directory=False, src_path="/some/path/cortex/file.txt")
    handler.on_modified(event)
    assert stub_sync.paper_calls == []
    assert stub_sync.concept_calls == []


def test_on_created_routes_like_on_modified(handler, stub_sync):
    event = SimpleNamespace(is_directory=False, src_path="/some/path/decisions/file.md")
    handler.on_created(event)
    assert stub_sync.concept_calls == [Path("/some/path/decisions/file.md")]
    assert stub_sync.paper_calls == []
