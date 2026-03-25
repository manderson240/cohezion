"""Compound engineering operations.

Decisions, experiments, patterns, context retrieval.
"""

import asyncio
import math
import re
import threading
from datetime import UTC, datetime

from .obsidian_ops import ObsidianOps
from .vault_ops import VaultOps


def relevance_score(
    match_count: int,
    last_accessed: str = "",
    access_count: int = 0,
    half_life_days: float = 90.0,
) -> float:
    """Compute relevance with temporal decay and access frequency boost.

    Score = match_count * decay_factor * access_boost
    - decay_factor: exponential decay, half-life of 90 days (configurable)
    - access_boost: log(1 + access_count), minimum 1.0
    """
    if last_accessed:
        try:
            last_dt = datetime.fromisoformat(last_accessed.replace("Z", "+00:00"))
            now = datetime.now(UTC)
            days_ago = max((now - last_dt).days, 0)
            decay = math.exp(-0.693 * days_ago / half_life_days)
        except (ValueError, TypeError):
            decay = 0.5
    else:
        decay = 0.5  # Unknown age gets 50% weight

    boost = max(math.log1p(access_count), 1.0)

    return match_count * decay * boost


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
        date = datetime.now(UTC).strftime("%Y-%m-%d")
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
        date = datetime.now(UTC).strftime("%Y-%m-%d")
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
        date = datetime.now(UTC).strftime("%Y-%m-%d")
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

        # Count matches per path
        path_counts: dict[str, int] = {}
        for r in flat_results:
            p = r["path"]
            path_counts[p] = path_counts.get(p, 0) + 1

        # Deduplicate by path, keeping one entry per path
        seen: set[str] = set()
        deduped = []
        for r in flat_results:
            if r["path"] not in seen:
                seen.add(r["path"])
                r["match_count"] = path_counts[r["path"]]
                deduped.append(r)

        # Fetch neuron metadata and compute decay-weighted relevance scores
        unique_paths = [r["path"] for r in deduped]
        metadata = self._fetch_neuron_metadata_batch(unique_paths)

        for r in deduped:
            meta = metadata.get(r["path"], {})
            r["relevance_score"] = relevance_score(
                r["match_count"],
                meta.get("last_accessed", ""),
                meta.get("access_count", 0),
            )

        deduped.sort(key=lambda r: r["relevance_score"], reverse=True)

        top_results = deduped[:20]

        # Fire-and-forget: update access tracking for returned results
        self._track_access([r["path"] for r in top_results])

        return top_results

    def _fetch_neuron_metadata_batch(self, paths: list[str]) -> dict[str, dict]:
        """Fetch last_accessed and access_count for vault paths from SurrealDB.

        Returns a dict keyed by path. Missing paths or any SurrealDB error
        returns an empty dict for that path (graceful degradation).
        """
        if not paths:
            return {}

        async def _query() -> dict[str, dict]:
            from .vault_graph.client import get_graph_client

            client = get_graph_client()
            placeholders = ", ".join(f"'{p.replace(chr(39), chr(92)+chr(39))}'" for p in paths)
            rows = await client.query(
                f"SELECT path, last_accessed, access_count FROM neuron "
                f"WHERE path IN [{placeholders}];"
            )
            return {row["path"]: row for row in rows if "path" in row}

        try:
            return asyncio.run(_query())
        except RuntimeError:
            # Event loop already running (e.g. inside async context) — skip metadata
            return {}
        except Exception:
            # SurrealDB unavailable or any other error — fall back gracefully
            return {}

    def _track_access(self, paths: list[str]) -> None:
        """Fire-and-forget: update last_accessed and access_count in SurrealDB.

        Runs in a daemon thread so it never blocks the search response.
        Silently ignores all errors (SurrealDB may be unavailable).
        """
        if not paths:
            return

        now_iso = datetime.now(UTC).isoformat()

        def _run() -> None:
            async def _update() -> None:
                from .vault_graph.client import get_graph_client

                client = get_graph_client()
                for path in paths:
                    path_esc = path.replace("'", "\\'")
                    try:
                        await client.execute(
                            f"UPDATE neuron SET last_accessed = '{now_iso}', "
                            f"access_count += 1 WHERE path = '{path_esc}';"
                        )
                    except Exception:
                        pass  # Per-path failures are non-fatal

            try:
                asyncio.run(_update())
            except Exception:
                pass  # Never let tracking crash the server

        threading.Thread(target=_run, daemon=True).start()

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
date: {v["date"]}
project: {v["project"]}
status: accepted
tags: [decision, {v["project"]}]
---
# {v["title"]}

## Context
{v["context"]}

## Decision
{v["decision"]}

## Rationale
{v["rationale"]}

## Alternatives Considered
{v["alternatives"]}

## Consequences
- ...

## Related
- ...
"""

    def _build_experiment_content(self, v: dict) -> str:
        return f"""---
date: {v["date"]}
project: {v["project"]}
status: in-progress
outcome: inconclusive
tags: [experiment, {v["project"]}]
---
# {v["title"]}

## Hypothesis
{v["hypothesis"]}

## Method
{v["method"]}

## Results
{v["result"]}

## Learnings
{v["learnings"]}

## Follow-up
- ...
"""

    def _build_pattern_content(self, v: dict) -> str:
        return f"""---
date: {v["date"]}
source_project: {v["project"]}
tags: [pattern, {v["domain"]}]
---
# {v["pattern_name"]}

## Problem
What recurring problem does this solve?

## Solution
{v["description"]}

## Example
```
{v["code_example"]}
```

## When to Use
- ...

## When NOT to Use
- ...

## Related Decisions
- ...
"""
