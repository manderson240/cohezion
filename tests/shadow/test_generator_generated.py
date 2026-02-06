from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from cohezion.meta.generator import MetaGenerator, _snake_case, _to_json


@pytest.fixture
def meta_generator():
    return MetaGenerator()


@patch("cohezion.meta.generator.jinja2.Environment.get_template")
@patch("cohezion.meta.generator.open", new_callable=MagicMock)
def test_generate_agent(mock_open, mock_get_template, meta_generator):
    spec_path = Path("specs/research_agent.yaml")
    output_dir = Path("src/cohezion/agents/")
    dry_run = False

    # Mocking the template render and save operations
    mock_template = MagicMock()
    mock_get_template.return_value = mock_template
    mock_template.render.return_value = "Generated code"
    mock_open.return_value.__enter__.return_value.write.return_value = None

    result = meta_generator.generate_agent(spec_path, output_dir, dry_run)

    assert result["success"] is True
    assert result["files_generated"] == ["src/cohezion/agents/research_agent.py"]
    mock_template.render.assert_called_once_with(
        agent={"class_name": "ResearchAgent", "filename": "research_agent"}
    )
    mock_open.assert_called_once_with("src/cohezion/agents/research_agent.py", "w")
    mock_open.return_value.__enter__.return_value.write.assert_called_once_with(
        "Generated code"
    )


@patch("cohezion.meta.generator.jinja2.Environment.get_template")
def test_generate_agent_exception(mock_get_template, meta_generator):
    spec_path = Path("specs/research_agent.yaml")
    output_dir = Path("src/cohezion/agents/")
    dry_run = False

    # Mocking the template render and save operations
    mock_template = MagicMock()
    mock_get_template.return_value = mock_template
    mock_template.render.side_effect = Exception("Test error")

    result = meta_generator.generate_agent(spec_path, output_dir, dry_run)

    assert result["success"] is False
    assert result["errors"][0] == "Test error"
    mock_template.render.assert_called_once_with(
        agent={"class_name": "ResearchAgent", "filename": "research_agent"}
    )


def test_snake_case():
    assert _snake_case("CamelCase") == "camel_case"
    assert _snake_case("already_snake_case") == "already_snake_case"


def test_to_json():
    assert _to_json(None) == "None"
    assert _to_json("test_string") == '"test_string"'
    assert _to_json({"key": "value"}) == '{"key": "value"}'
