import xml.etree.ElementTree as ET
from pathlib import Path

import yaml


def verify_yaml(file_path):
    """Verify YAML file is syntactically correct."""
    try:
        with open(file_path) as f:
            yaml.safe_load(f)
        return True, None
    except yaml.YAMLError as e:
        return False, str(e)


def verify_xml(file_path):
    """Verify XML file is syntactically correct."""
    try:
        ET.parse(file_path)
        return True, None
    except ET.ParseError as e:
        return False, str(e)


def test_bmad_yaml_files():
    """Test all YAML workflow and config files."""
    bmad_root = Path(__file__).parent.parent / "bmad"
    yaml_files = list(bmad_root.rglob("*.yaml")) + list(bmad_root.rglob("*.yml"))

    errors = []
    for yaml_file in yaml_files:
        is_valid, error = verify_yaml(yaml_file)
        if not is_valid:
            errors.append(f"{yaml_file}: {error}")

    assert not errors, "YAML validation errors:\n" + "\n".join(errors)


def test_bmad_xml_files():
    """Test all XML task definition files."""
    bmad_root = Path(__file__).parent.parent / "bmad"
    xml_files = list(bmad_root.rglob("*.xml"))

    errors = []
    for xml_file in xml_files:
        is_valid, error = verify_xml(xml_file)
        if not is_valid:
            errors.append(f"{xml_file}: {error}")

    assert not errors, "XML validation errors:\n" + "\n".join(errors)


def test_sprint_status_yaml():
    """Test sprint status YAML file."""
    sprint_status = Path(__file__).parent.parent / "sprint-status.yaml"
    if sprint_status.exists():
        is_valid, error = verify_yaml(sprint_status)
        assert is_valid, f"sprint-status.yaml validation error: {error}"
