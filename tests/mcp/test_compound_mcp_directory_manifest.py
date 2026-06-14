"""Item 879: compound-mcp directory manifest for Claude connector directory."""

from __future__ import annotations
import json
from pathlib import Path

MANIFEST_PATH = (
    Path(__file__).parent.parent.parent
    / "src"
    / "cohezion"
    / "mcp"
    / "compound_mcp_directory_manifest.json"
)


def _load() -> dict:
    assert MANIFEST_PATH.exists(), f"Manifest not found: {MANIFEST_PATH}"
    with open(MANIFEST_PATH) as f:
        return json.load(f)


def test_manifest_file_exists_and_parses() -> None:
    data = _load()
    assert isinstance(data, dict)


def test_required_top_level_keys() -> None:
    data = _load()
    for key in ("name", "description", "tools", "category", "auth_type"):
        assert key in data, f"Missing required key: {key}"


def test_tools_list_has_at_least_87_entries() -> None:
    data = _load()
    assert len(data["tools"]) >= 87, f"Expected >=87 tools, got {len(data['tools'])}"


def test_category_is_valid() -> None:
    data = _load()
    valid = {"productivity", "developer", "data", "ai", "engineering"}
    assert data["category"] in valid, f"Invalid category: {data['category']}"


def test_auth_type_is_valid() -> None:
    data = _load()
    valid = {"none", "oauth2", "api_key"}
    assert data["auth_type"] in valid, f"Invalid auth_type: {data['auth_type']}"


def test_tools_are_strings() -> None:
    data = _load()
    assert all(isinstance(t, str) for t in data["tools"])


def test_name_is_nonempty_string() -> None:
    data = _load()
    assert isinstance(data["name"], str) and len(data["name"]) > 0


def test_description_is_nonempty_string() -> None:
    data = _load()
    assert isinstance(data["description"], str) and len(data["description"]) > 0


def test_no_duplicate_tool_names() -> None:
    data = _load()
    tools = data["tools"]
    assert len(tools) == len(set(tools)), "Duplicate tool names in manifest"


def test_manifest_includes_compound_start_session() -> None:
    """Sanity check: a known compound tool appears in the manifest."""
    data = _load()
    assert "compound_start_session" in data["tools"]
