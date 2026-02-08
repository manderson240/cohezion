"""Compound engineering operations.

Decisions, experiments, patterns, context retrieval.
"""

import re
from datetime import datetime, timezone

from .obsidian_ops import ObsidianOps
from .vault_ops import VaultOps


class CompoundOps:
    """Higher-level operations that build compound knowledge over time."""

    def __init__(self, vault: VaultOps, obsidian: ObsidianOps):
        self.vault = vault
        self.obsidian = obsidian

    def log_decision(
        self,
        project: str,
        title: str,
        context: str,
        decision: str,
        rationale: str,
        alternatives_considered: str = "",
    ) -> str:
        """Create an Architecture Decision Record."""
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        slug = self._slugify(title)
        path = f"decisions/{date}-{slug}.md"

        variables = {
            "date": date,
            "project": project,
            "title": title,
            "context": context,
            "decision": decision,
            "rationale": rationale,
            "alternatives": alternatives_considered or "None documented.",
        }

        try:
            return self.obsidian.create_from_template("decisions", path, variables)
        except FileNotFoundError:
            # Fallback: create inline if template missing
            content = self._build_decision_content(variables)
            self.vault.write(path, content)
            return f"Created decision record: {path}"

    def log_experiment(
        self,
        project: str,
        hypothesis: str,
        method: str,
        result: str = "",
        learnings: str = "",
        title: str = "",
    ) -> str:
        """Log an experiment."""
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        exp_title = title or hypothesis[:60]
        slug = self._slugify(exp_title)
        path = f"experiments/{date}-{slug}.md"

        variables = {
            "date": date,
            "project": project,
            "title": exp_title,
            "hypothesis": hypothesis,
            "method": method,
            "result": result or "Pending.",
            "learnings": learnings or "Pending.",
        }

        try:
            return self.obsidian.create_from_template("experiments", path, variables)
        except FileNotFoundError:
            content = self._build_experiment_content(variables)
            self.vault.write(path, content)
            return f"Created experiment log: {path}"

    def extract_pattern(
        self,
        source_path: str,
        pattern_name: str,
        description: str,
        code_example: str = "",
        domain: str = "general",
    ) -> str:
        """Extract a reusable pattern from project work."""
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        slug = self._slugify(pattern_name)
        path = f"patterns/{slug}.md"

        # Determine project from source path
        project = source_path.split("/")[1] if "/" in source_path else "general"

        variables = {
            "date": date,
            "project": project,
            "domain": domain,
            "pattern_name": pattern_name,
            "description": description,
            "code_example": code_example or "# No example provided",
        }

        try:
            return self.obsidian.create_from_template("patterns", path, variables)
        except FileNotFoundError:
            content = self._build_pattern_content(variables)
            self.vault.write(path, content)
            return f"Created pattern: {path}"

    def find_relevant_context(
        self, query: str, project: str | None = None
    ) -> list[dict]:
        """Search for prior decisions, patterns, and experiments.

        Searches across decisions/, patterns/, experiments/, and
        concepts/ directories. Optionally scoped to a project.
        """
        results = {
            "decisions": [],
            "patterns": [],
            "experiments": [],
            "concepts": [],
            "projects": [],
        }

        search_dirs = ["decisions", "patterns", "experiments", "concepts", "projects"]

        for directory in search_dirs:
            try:
                matches = self.vault.search(query, scope="folder", folder=directory)
                for match in matches:
                    # If project-scoped, filter by project tag/frontmatter
                    if project and not self._matches_project(match, project):
                        continue
                    results[directory].append(match)
            except (FileNotFoundError, ValueError):
                continue

        # Flatten and annotate
        flat_results = []
        for category, matches in results.items():
            for match in matches:
                match["category"] = category
                flat_results.append(match)

        # Sort by relevance (more matches in a file = more relevant)
        path_counts: dict[str, int] = {}
        for r in flat_results:
            p = r["path"]
            path_counts[p] = path_counts.get(p, 0) + 1

        flat_results.sort(key=lambda r: path_counts.get(r["path"], 0), reverse=True)

        # Deduplicate by path, keeping the first (highest relevance) entry
        seen = set()
        deduped = []
        for r in flat_results:
            if r["path"] not in seen:
                seen.add(r["path"])
                r["match_count"] = path_counts[r["path"]]
                deduped.append(r)

        return deduped[:20]  # Cap at 20 results

    def _matches_project(self, match: dict, project: str) -> bool:
        """Check if a search match belongs to a specific project."""
        try:
            content = self.vault.read(match["path"])
            return project.lower() in content.lower()
        except (FileNotFoundError, UnicodeDecodeError):
            return False

    def _slugify(self, text: str) -> str:
        """Convert text to a URL/filename-safe slug."""
        text = text.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_]+", "-", text)
        text = re.sub(r"-+", "-", text)
        return text[:80].strip("-")

    def _build_decision_content(self, v: dict) -> str:
        return f"""---
date: {v['date']}
project: {v['project']}
status: accepted
tags: [decision, {v['project']}]
---
# {v['title']}

## Context
{v['context']}

## Decision
{v['decision']}

## Rationale
{v['rationale']}

## Alternatives Considered
{v['alternatives']}

## Consequences
- ...

## Related
- ...
"""

    def _build_experiment_content(self, v: dict) -> str:
        return f"""---
date: {v['date']}
project: {v['project']}
status: in-progress
outcome: inconclusive
tags: [experiment, {v['project']}]
---
# {v['title']}

## Hypothesis
{v['hypothesis']}

## Method
{v['method']}

## Results
{v['result']}

## Learnings
{v['learnings']}

## Follow-up
- ...
"""

    def _build_pattern_content(self, v: dict) -> str:
        return f"""---
date: {v['date']}
source_project: {v['project']}
tags: [pattern, {v['domain']}]
---
# {v['pattern_name']}

## Problem
What recurring problem does this solve?

## Solution
{v['description']}

## Example
```
{v['code_example']}
```

## When to Use
- ...

## When NOT to Use
- ...

## Related Decisions
- ...
"""
