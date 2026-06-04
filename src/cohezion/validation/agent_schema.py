# mixed-case attribute matches schema field name
"""Pydantic validation schema for .claude/agents/*.md agent definition files.

Provides the single source of truth for validating agent file frontmatter,
ensuring all agent definitions conform to the expected structure.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError


_GIT = shutil.which("git") or "/usr/bin/git"


class AgentFileValidationError(Exception):
    """Raised when one or more agent files fail validation.

    Parameters
    ----------
    path : Path | None
        Path to the failing file (None when multiple files fail).
    errors : list[str]
        Human-readable error descriptions.
    """

    def __init__(self, path: Path | None, errors: list[str]) -> None:
        self.path = path
        self.errors = errors
        msg = "; ".join(errors)
        if path:
            msg = f"{path}: {msg}"
        super().__init__(msg)


class AgentFileSchema(BaseModel):
    """Schema for agent file YAML frontmatter.

    Validates that agent definitions have the required fields and correct types.
    Uses ``extra="forbid"`` to catch typos in field names.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    name: str = Field(
        ...,
        pattern=r"^[a-z][a-z0-9-]*$",
        description="Lowercase kebab-case agent identifier.",
    )
    description: str = Field(
        ...,
        min_length=10,
        description="Human-readable description of the agent's purpose.",
    )
    tools: list[str] | None = Field(
        default=None,
        description="Tool names the agent is allowed to use.",
    )
    disallowedTools: list[str] | None = Field(
        default=None,
        description="Tool names the agent is forbidden from using.",
    )
    model: str | None = Field(
        default=None,
        description="Model name to use for this agent (e.g. 'sonnet').",
    )


def extract_frontmatter(text: str) -> dict:
    """Extract YAML frontmatter from text delimited by ``---`` lines.

    Parameters
    ----------
    text : str
        Full file content.

    Returns
    -------
    dict
        Parsed frontmatter, or empty dict if none found.
    """
    lines = text.split("\n")

    # Must start with ---
    if not lines or lines[0].strip() != "---":
        return {}

    # Find closing ---
    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return {}

    yaml_block = "\n".join(lines[1:end_idx])
    if not yaml_block.strip():
        return {}

    parsed = yaml.safe_load(yaml_block)
    if not isinstance(parsed, dict):
        return {}

    return parsed


def validate_agent_file(path: Path | str) -> AgentFileSchema:
    """Read and validate a single agent definition file.

    Parameters
    ----------
    path : Path | str
        Path to the ``.md`` agent file.

    Returns
    -------
    AgentFileSchema
        Validated schema instance.

    Raises
    ------
    AgentFileValidationError
        If the file cannot be read or fails validation.
    """
    path = Path(path)

    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AgentFileValidationError(path, [f"Cannot read file: {exc}"]) from exc

    frontmatter = extract_frontmatter(text)
    if not frontmatter:
        raise AgentFileValidationError(path, ["No valid YAML frontmatter found."])

    try:
        return AgentFileSchema(**frontmatter)
    except ValidationError as exc:
        errors = [e["msg"] for e in exc.errors()]
        raise AgentFileValidationError(path, errors) from exc


def validate_all_agent_files(
    directory: Path | str | None = None,
) -> list[AgentFileSchema]:
    """Validate all agent ``.md`` files in a directory.

    Parameters
    ----------
    directory : Path | str | None
        Directory to scan. Defaults to ``.claude/agents/`` relative to the
        git repository root.

    Returns
    -------
    list[AgentFileSchema]
        List of validated agent schemas.

    Raises
    ------
    AgentFileValidationError
        If any agent file fails validation (all errors combined).
    """
    if directory is None:
        result = subprocess.run(
            [_GIT, "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            raise AgentFileValidationError(
                None, ["Cannot determine git root: " + result.stderr.strip()]
            )
        directory = Path(result.stdout.strip()) / ".claude" / "agents"

    directory = Path(directory)
    if not directory.is_dir():
        raise AgentFileValidationError(None, [f"Directory not found: {directory}"])

    md_files = sorted(directory.glob("*.md"))
    if not md_files:
        raise AgentFileValidationError(None, [f"No .md files found in {directory}"])

    validated: list[AgentFileSchema] = []
    all_errors: list[str] = []

    for md_file in md_files:
        try:
            validated.append(validate_agent_file(md_file))
        except AgentFileValidationError as exc:
            all_errors.extend(f"{md_file.name}: {e}" for e in exc.errors)

    if all_errors:
        raise AgentFileValidationError(None, all_errors)

    return validated


def generate_agent_frontmatter(
    name: str,
    description: str,
    tools: list[str] | None = None,
    disallowed_tools: list[str] | None = None,
    model: str | None = None,
) -> str:
    """Generate validated YAML frontmatter for an agent file.

    Parameters
    ----------
    name : str
        Agent name (lowercase kebab-case).
    description : str
        Agent description (min 10 chars).
    tools : list[str] | None
        Allowed tools.
    disallowed_tools : list[str] | None
        Disallowed tools.
    model : str | None
        Model name.

    Returns
    -------
    str
        YAML frontmatter string wrapped in ``---`` delimiters.

    Raises
    ------
    AgentFileValidationError
        If the generated frontmatter fails validation.
    """
    data: dict = {"name": name, "description": description}
    if tools is not None:
        data["tools"] = tools
    if disallowed_tools is not None:
        data["disallowedTools"] = disallowed_tools
    if model is not None:
        data["model"] = model

    try:
        AgentFileSchema(**data)
    except ValidationError as exc:
        errors = [e["msg"] for e in exc.errors()]
        raise AgentFileValidationError(None, errors) from exc

    yaml_str = yaml.dump(data, default_flow_style=False, sort_keys=False)
    return f"---\n{yaml_str}---\n"
