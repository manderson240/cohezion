from __future__ import annotations

import json
import re

from autocontext.scenarios.artifact_editing import (
    Artifact,
    ArtifactEditingInterface,
    ArtifactEditingResult,
    ArtifactValidationResult,
)


class ArtifactEditingPythonArtifactEditing(ArtifactEditingInterface):
    name = 'artifact_editing_python'
    _validation_rules = ['src/cohezion/core/registry.py must not contain "except (ImportError, Exception)"', 'src/cohezion/core/registry.py must not contain "except (Exception, ImportError)"', 'src/cohezion/core/registry.py must contain "except ImportError:"', 'src/cohezion/core/registry.py must not contain "except (ValueError, KeyError, Exception)"', 'src/cohezion/core/registry.py must contain "except (ValueError, KeyError):"', 'src/cohezion/core/loader.py must not contain "except (AttributeError, Exception, TypeError)"', 'src/cohezion/core/loader.py must contain "except (AttributeError, TypeError):"', 'src/cohezion/core/loader.py must not contain "except (OSError, Exception)"', 'src/cohezion/core/loader.py must contain "except OSError:"', 'src/cohezion/core/registry.py must contain "except (RuntimeError, ConnectionError):"', 'src/cohezion/core/loader.py must contain "except (PermissionError, FileNotFoundError):"']

    def describe_task(self) -> str:
        return 'In each Python file under src/cohezion/core/, find every except clause whose tuple contains Exception alongside one or more specific exception types (e.g. `except (ImportError, Exception):` or `except (ValueError, KeyError, Exception):`). Remove Exception from those tuples. If removing Exception leaves only one type, collapse the tuple to a bare `except SpecificError:`. Do not change any other code, comments, or unrelated except clauses.'

    def get_rubric(self) -> str:
        return 'Evaluate: (1) every stealth-bare-except tuple has Exception removed, (2) single-remaining-type tuples are collapsed to bare form, (3) except clauses that already lack Exception are untouched, (4) no unrelated lines are modified, (5) files remain syntactically valid Python.'

    def initial_artifacts(self, seed: int | None = None) -> list[Artifact]:
        return [
            Artifact(path='src/cohezion/core/registry.py', content='"""Skill registry — loads and caches PRIME skill definitions."""\nfrom __future__ import annotations\n\nimport json\nimport logging\nfrom pathlib import Path\nfrom typing import Any\n\nlogger = logging.getLogger(__name__)\n\n_REGISTRY_CACHE: dict[str, Any] = {}\n\n\ndef load_skill(name: str, skills_dir: Path) -> dict[str, Any] | None:\n    """Return parsed skill JSON, or None if the skill cannot be loaded."""\n    if name in _REGISTRY_CACHE:\n        return _REGISTRY_CACHE[name]\n\n    candidate = skills_dir / f"{name}.json"\n    try:\n        raw = candidate.read_text(encoding="utf-8")\n    except (ImportError, Exception):\n        # file missing or unreadable\n        logger.warning("skill file not found: %s", candidate)\n        return None\n\n    try:\n        data = json.loads(raw)\n    except (ValueError, KeyError, Exception):\n        logger.error("malformed skill JSON: %s", candidate)\n        return None\n\n    _REGISTRY_CACHE[name] = data\n    return data\n\n\ndef connect_registry(host: str, port: int) -> bool:\n    """Ping the remote registry endpoint."""\n    import socket\n\n    try:\n        with socket.create_connection((host, port), timeout=2):\n            return True\n    except (RuntimeError, ConnectionError):\n        # genuine sibling types — no Exception in this tuple, must stay untouched\n        return False\n\n\ndef _parse_manifest(raw: str) -> dict[str, Any]:\n    """Parse a registry manifest string."""\n    try:\n        return json.loads(raw)\n    except json.JSONDecodeError:\n        # single specific type — must stay untouched\n        raise\n', content_type='python', metadata={}),
            Artifact(path='src/cohezion/core/loader.py', content='"""Dynamic module loader for Cohezion compound skills."""\nfrom __future__ import annotations\n\nimport importlib\nimport logging\nfrom pathlib import Path\nfrom types import ModuleType\n\nlogger = logging.getLogger(__name__)\n\n\ndef load_module(dotted_path: str) -> ModuleType | None:\n    """Import a dotted module path, returning None on failure."""\n    try:\n        return importlib.import_module(dotted_path)\n    except (AttributeError, Exception, TypeError):\n        logger.warning("could not import %s", dotted_path)\n        return None\n\n\ndef read_source(path: Path) -> str | None:\n    """Read a source file, returning None when the path is inaccessible."""\n    try:\n        return path.read_text(encoding="utf-8")\n    except (OSError, Exception):\n        logger.warning("unreadable source: %s", path)\n        return None\n\n\ndef ensure_writable(path: Path) -> bool:\n    """Return True only when *path* can be opened for writing."""\n    try:\n        path.touch(exist_ok=True)\n        return True\n    except (PermissionError, FileNotFoundError):\n        # both are genuine siblings — this tuple must not be changed\n        return False\n\n\ndef get_attr(module: ModuleType, name: str) -> object | None:\n    """Safely retrieve an attribute from a module."""\n    try:\n        return getattr(module, name)\n    except AttributeError:\n        # single type, no tuple — must stay untouched\n        return None\n', content_type='python', metadata={})
        ]

    def get_edit_prompt(self, artifacts: list[Artifact]) -> str:
        rendered = json.dumps([artifact.to_dict() for artifact in artifacts], indent=2)
        rules = "\n".join(f"- {rule}" for rule in self._validation_rules)
        return (
            f"{self.describe_task()}\n\n"
            f"Artifacts:\n{rendered}\n\n"
            f"Validation rules:\n{rules}\n\n"
            'Return JSON with shape {"artifacts": [{"path": "...", "content": "...", "content_type": "..."}]} '
            "containing the full edited artifact set."
        )

    def _rules_for_path(self, path: str) -> list[str]:
        relevant: list[str] = []
        for rule in self._validation_rules:
            if " must " in rule:
                prefix, _ = rule.split(" must ", 1)
                if "/" in prefix and prefix.strip() != path:
                    continue
            relevant.append(rule)
        return relevant

    def _extract_snippets(self, rule: str) -> list[str]:
        return [match[0] or match[1] for match in re.findall(r'"([^"]+)"|\'([^\']+)\'', rule)]

    def validate_artifact(self, artifact: Artifact) -> ArtifactValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        if not artifact.content.strip():
            errors.append(f"{artifact.path} must not be empty")
        for rule in self._rules_for_path(artifact.path):
            snippets = self._extract_snippets(rule)
            if not snippets:
                continue
            if "must not contain" in rule:
                for snippet in snippets:
                    if snippet in artifact.content:
                        errors.append(f"{artifact.path} violates rule: {rule}")
            else:
                for snippet in snippets:
                    if snippet not in artifact.content:
                        errors.append(f"{artifact.path} violates rule: {rule}")
        return ArtifactValidationResult(valid=not errors, errors=errors, warnings=warnings)

    def evaluate_edits(self, original: list[Artifact], edited: list[Artifact]) -> ArtifactEditingResult:
        diffs = self.compute_diffs(original, edited)
        validations = [self.validate_artifact(artifact) for artifact in edited]
        valid_count = sum(1 for result in validations if result.valid)
        error_count = sum(len(result.errors) for result in validations)
        correctness = valid_count / max(len(edited), 1)
        change_score = 1.0 if diffs else 0.0
        baseline = max(len(original), 1)
        precision = 1.0 if len(diffs) <= baseline else max(0.2, 1.0 - ((len(diffs) - baseline) / baseline) * 0.2)
        score = round((correctness * 0.7) + (change_score * 0.15) + (precision * 0.15), 4)
        return ArtifactEditingResult(
            score=score,
            reasoning=f"Validated {valid_count} of {len(edited)} artifacts with {len(diffs)} tracked edits.",
            dimension_scores={
                "correctness": round(correctness, 4),
                "change_completeness": round(change_score, 4),
                "precision": round(precision, 4),
            },
            diffs=diffs,
            validation=ArtifactValidationResult(
                valid=error_count == 0,
                errors=[error for result in validations for error in result.errors],
                warnings=[warning for result in validations for warning in result.warnings],
            ),
            artifacts_modified=len(diffs),
            artifacts_valid=valid_count,
        )
