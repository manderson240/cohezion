"""Shared test fixtures for vault_linker tests."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def make_md(tmp_path):
    """Factory fixture to create markdown files in a temp vault."""
    def _make(name: str, tags: list[str], links: list[str] = None, content: str = "") -> Path:
        tags_yaml = json.dumps(tags)
        links_str = "\n".join(f"[[{lnk}]]" for lnk in (links or []))
        body = f"---\ntitle: {name}\ntags: {tags_yaml}\n---\n\n{content}\n\n{links_str}\n"
        p = tmp_path / f"{name}.md"
        p.write_text(body, encoding="utf-8")
        return p
    return _make
