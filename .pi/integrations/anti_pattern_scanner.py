#!/usr/bin/env python3
"""
Anti-Pattern Guardian - Scan codebase for AGENTS.md documented anti-patterns.

Mines AGENTS.md for anti-patterns, then scans codebase for instances.
Outputs PatternRepository-compatible format for Cohezion bridge integration.

Usage: python3 anti_pattern_scanner.py
"""

from __future__ import annotations

import json
import logging
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Anti-patterns extracted from AGENTS.md
ANTI_PATTERNS = [
    {
        "id": "mock-wrong-import-level",
        "name": "Mock After Import",
        "category": "test-isolation",
        "severity": "critical",
        "description": "Mocking at import level after target already imported",
        "correct_pattern": '@patch("cohezion.swarm.compound_client.get_compound_client")',
        "wrong_pattern": 'with patch("cohezion.api.compound_client")',
        "detection": r'with patch\(["\'][^"\']*\.compound_client["\']',
        "files_to_check": ["tests/**/*.py"],
        "remediation": "Mock at source using decorator pattern before import",
    },
    {
        "id": "blocking-io-in-async",
        "name": "Blocking I/O in Async Function",
        "category": "async-pattern",
        "severity": "critical",
        "description": "Using blocking calls (requests, open) in async context",
        "correct_pattern": "async with httpx.AsyncClient(timeout=10.0)",
        "wrong_pattern": "requests.get(url).json()",
        "detection": r"requests\.get\(|requests\.post\(",
        "files_to_check": ["src/**/*.py"],
        "remediation": "Use httpx.AsyncClient or asyncio.to_thread for blocking calls",
    },
    {
        "id": "bare-pip-install",
        "name": "Bare pip Install",
        "category": "dependency-management",
        "severity": "medium",
        "description": "Using pip directly instead of uv",
        "correct_pattern": "uv run ... or uv pip install",
        "wrong_pattern": "pip install",
        "detection": r"^pip\s+(install|uninstall)",
        "files_to_check": ["*.md", "*.txt", "*.sh", "*.yml", "*.yaml"],
        "remediation": "Use uv for all Python package operations",
    },
    {
        "id": "singleton-state-bleed",
        "name": "Singleton State Bleed in Tests",
        "category": "test-isolation",
        "severity": "high",
        "description": "Tests pass individually but fail in suite due to singleton pollution",
        "correct_pattern": "Reset singletons in conftest.py",
        "wrong_pattern": "No singleton reset between tests",
        "detection": r"cohezion\.(api|swarm)\._\w+\s*=",
        "files_to_check": ["tests/**/*.py"],
        "remediation": "Reset module-level singletons in conftest.py fixtures",
    },
    {
        "id": "catch-all-exception",
        "name": "Bare Exception Handler",
        "category": "error-handling",
        "severity": "high",
        "description": "Using bare except: or except Exception without specific types",
        "correct_pattern": "except SpecificError as e:",
        "wrong_pattern": "except:",
        "detection": r"except\s*:\s*$|except\s+Exception\s*:",
        "files_to_check": ["src/**/*.py"],
        "remediation": "Use specific exception types with circuit breakers",
    },
]


@dataclass
class AntiPatternInstance:
    """Single instance of an anti-pattern in codebase."""

    anti_pattern_id: str
    file_path: str
    line_number: int
    line_content: str
    context: str  # ±3 lines
    confidence: float
    suggested_fix: str


@dataclass
class AntiPatternGuardianReport:
    """Complete scan report."""

    scanned_files: int
    patterns_found: dict[str, list[AntiPatternInstance]]
    summary: dict[str, Any]


def scan_file(filepath: Path, pattern: dict) -> list[AntiPatternInstance]:
    """Scan single file for anti-pattern."""
    instances = []

    try:
        content = filepath.read_text()
        lines = content.split("\n")

        for i, line in enumerate(lines):
            if re.search(pattern["detection"], line):
                # Get context
                start = max(0, i - 3)
                end = min(len(lines), i + 4)
                context = "\n".join(lines[start:end])

                # Calculate confidence
                confidence = 0.9 if pattern["detection"] in line else 0.7

                instances.append(
                    AntiPatternInstance(
                        anti_pattern_id=pattern["id"],
                        file_path=str(filepath),
                        line_number=i + 1,
                        line_content=line.strip(),
                        context=context,
                        confidence=confidence,
                        suggested_fix=pattern["remediation"],
                    )
                )
    except Exception as e:
        logger.warning(f"Failed to scan {filepath}: {e}")

    return instances


def find_files(pattern: str) -> list[Path]:
    """Find files matching glob pattern."""
    import glob

    files = []
    for p in pattern.split(","):
        matched = glob.glob(p, recursive=True)
        files.extend(Path(f) for f in matched if Path(f).is_file())
    return files


def scan_codebase() -> AntiPatternGuardianReport:
    """Scan entire codebase for anti-patterns."""
    all_instances = []
    scanned_files = 0

    for anti_pattern in ANTI_PATTERNS:
        logger.info(f"Scanning for: {anti_pattern['name']}")

        for file_pattern in anti_pattern["files_to_check"]:
            files = find_files(file_pattern)
            scanned_files += len(files)

            for filepath in files:
                instances = scan_file(filepath, anti_pattern)
                all_instances.extend(instances)

                if instances:
                    logger.warning(f"  Found {len(instances)} in {filepath}")

    # Group by anti-pattern type
    patterns_found = {}
    for instance in all_instances:
        if instance.anti_pattern_id not in patterns_found:
            patterns_found[instance.anti_pattern_id] = []
        patterns_found[instance.anti_pattern_id].append(instance)

    # Calculate summary
    summary = {
        "critical": sum(
            1 for ap in ANTI_PATTERNS if ap["severity"] == "critical" and ap["id"] in patterns_found
        ),
        "high": sum(
            1 for ap in ANTI_PATTERNS if ap["id"] in patterns_found and ap["severity"] == "high"
        ),
        "medium": sum(
            1 for ap in ANTI_PATTERNS if ap["id"] in patterns_found and ap["severity"] == "medium"
        ),
        "total_instances": len(all_instances),
        "unique_anti_patterns": len(patterns_found),
    }

    return AntiPatternGuardianReport(
        scanned_files=scanned_files, patterns_found=patterns_found, summary=summary
    )


def export_to_pattern_repository(report: AntiPatternGuardianReport, output_path: Path):
    """Export in PatternRepository format."""

    # Convert to CodeAntiPattern format
    anti_patterns_for_repo = []

    for ap_id, instances in report.patterns_found.items():
        pattern_def = next((ap for ap in ANTI_PATTERNS if ap["id"] == ap_id), None)
        if not pattern_def:
            continue

        files_affected = list(set(inst.file_path for inst in instances))

        anti_patterns_for_repo.append(
            {
                "name": pattern_def["name"],
                "category": pattern_def["category"],
                "description": pattern_def["description"],
                "file_paths": files_affected,
                "severity": pattern_def["severity"],
                "risk_level": 5 if pattern_def["severity"] == "critical" else 3,
                "remediation": pattern_def["remediation"],
                "code_example": pattern_def["wrong_pattern"],
                "frequency": len(instances),
                "confidence": min(1.0, sum(inst.confidence for inst in instances) / len(instances)),
                "first_seen": "2026-04-02",
                "last_seen": "2026-04-02",
                "instances": [
                    {
                        "file": inst.file_path,
                        "line": inst.line_number,
                        "content": inst.line_content,
                        "context": inst.context,
                    }
                    for inst in instances
                ],
            }
        )

    # Write to buffer (PatternRepository format)
    output = {
        "anti_patterns": anti_patterns_for_repo,
        "scan_metadata": {
            "timestamp": "2026-04-02T14:45:00Z",
            "scanned_files": report.scanned_files,
            "summary": report.summary,
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2, default=str)

    return output_path


def export_pr_skill_definition(report: AntiPatternGuardianReport):
    """Create a new PRIME skill from discovered patterns."""

    skill_content = """---
name: anti-pattern-guardian
description: Automated detection and remediation of codebase anti-patterns. 
  Scans for AGENTS.md documented issues including mock isolation, async blocking,
  singleton pollution, and bare exception handlers. Use when reviewing code or
  setting up CI quality gates.
metadata:
  version: "0.1"
  generated_from: "AGENTS.md mining"
---

# SKILL: ANTI_PATTERN_GUARDIAN_PRIME

## DOMAIN EXPERTISE

You are the **Anti-Pattern Guardian** - detecting code constructs that violate
Cohezion engineering standards before they cause issues.

## ANTI-PATTERNS DATABASE

"""

    # Add discovered anti-patterns
    for ap_id, instances in report.patterns_found.items():
        pattern_def = next((ap for ap in ANTI_PATTERNS if ap["id"] == ap_id), None)
        if not pattern_def:
            continue

        skill_content += f"""### {pattern_def["name"]} ({len(instances)} instances)
- **Severity:** {pattern_def["severity"]}
- **Category:** {pattern_def["category"]}
- **Detection:** `{pattern_def["wrong_pattern"][:50]}...`
- **Remediation:** {pattern_def["remediation"]}
- **Files Affected:** {len(set(inst.file_path for inst in instances))}

"""

    skill_content += """
## INSTRUCTION

### 1. Scan Codebase
```bash
python3 .pi/integrations/anti_pattern_scanner.py
```

### 2. Review Findings
Check `.pi/integrations/anti_pattern_inventory.json` for:
- Critical severity (fix immediately)
- High severity (fix before commit)
- Medium severity (address in backlog)

### 3. Auto-Remediate
For detected instances, suggest:
- Mock isolation: Use @patch at source
- Async blocking: Replace requests with httpx
- Singleton reset: Add conftest.py fixture
- Exceptions: Use specific error types

### 4. CI Integration
Add to pre-commit hooks:
```yaml
- repo: local
  hooks:
  - id: anti-pattern-guardian
    entry: python3 .pi/integrations/anti_pattern_scanner.py
    language: python
```

## PATTERNS

### Critical Pattern
- Always scan before major refactoring
- Fix critical anti-patterns first
- Document exceptions in code comments  

## CITATIONS
- AGENTS.md (source of truth for anti-patterns)
- PatternRepository (Cohezion persistence layer)

## VERSION
v0.1 - Initial scan results from AGENTS.md mining

## SEE ALSO
- PI_INTEGRATION_PRIME.md
- TESTING_PRIME.md
- RELIABILITY_PRIME.md
"""

    return skill_content


def main():
    """Main entry point."""
    logger.info("=" * 50)
    logger.info("Anti-Pattern Guardian - Scanning Codebase")
    logger.info("=" * 50)

    # Run scan
    report = scan_codebase()

    # Display results
    logger.info("\n" + "=" * 50)
    logger.info("SCAN COMPLETE")
    logger.info("=" * 50)
    logger.info(f"Files scanned: {report.scanned_files}")
    logger.info(f"Anti-patterns found: {report.summary['unique_anti_patterns']}")
    logger.info(f"Total instances: {report.summary['total_instances']}")
    logger.info(f"  Critical: {report.summary['critical']}")
    logger.info(f"  High: {report.summary['high']}")
    logger.info(f"  Medium: {report.summary['medium']}")

    # Export to PatternRepository format
    inventory_path = Path(".pi/integrations/anti_pattern_inventory.json")
    export_to_pattern_repository(report, inventory_path)
    logger.info(f"\nInventory written: {inventory_path}")

    # Generate skill definition
    skill_content = export_pr_skill_definition(report)
    skill_path = Path("src/cohezion/skills/ANTI_PATTERN_GUARDIAN_PRIME.md")
    with open(skill_path, "w") as f:
        f.write(skill_content)
    logger.info(f"PRIME skill written: {skill_path}")

    # Update skill index
    logger.info("\nReindexing skills...")
    import subprocess

    subprocess.run(["python3", ".pi/integrations/index_skills.py"], check=False)

    logger.info("\n" + "=" * 50)
    logger.info("Anti-Pattern Guardian Ready")
    logger.info("=" * 50)
    logger.info("Use: pi /cohezion skill anti-pattern-guardian")
    logger.info("Or: python3 .pi/integrations/anti_pattern_scanner.py")

    return 0


if __name__ == "__main__":
    exit(main())
