import os

import toml


def test_ruff_config_exists():
    """Verify that pyproject.toml exists and contains ruff configuration."""
    assert os.path.exists("pyproject.toml")

    with open("pyproject.toml") as f:
        config = toml.load(f)

    assert "tool" in config
    assert "ruff" in config["tool"]
    assert config["tool"]["ruff"]["line-length"] == 88
