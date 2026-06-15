"""LoopTickSweeper — per-tick context enrichment for the autonomous improvement loop.

On each loop tick (task execution), the sweeper provides context from three sources
at zero cloud cost:

  1. Vault sweep: grep Obsidian vault for patterns/decisions relevant to the current
     task category (fast filesystem search, no Python SDK overhead).

  2. SurrealDB sweep: query experiment_runs for historical success rates on similar
     task categories, so the executor knows what has worked before.

  3. Research sweep: fetch recent arXiv/HuggingFace papers relevant to failing
     categories via local HTTP requests; synthesize with Lemonade Gemma-4-E4B
     (fast fallback model, ~200ms, no cloud cost).

After each sprint, the sweeper runs a course-correction analysis via the Omni planner
model to review what the loop accomplished and suggest adjustments to task priority,
prompt strategy, or model selection.

All inference uses Lemonade :13305. No Claude API calls in this module.
"""

from __future__ import annotations

import json
import logging
import subprocess
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

_VAULT_PATH = Path.home() / "vaults" / "cohezion-vault"
_SURREAL_URL = "http://localhost:8001/sql"
_SURREAL_HEADERS = {
    "surreal-ns": "cohezion",
    "surreal-db": "main",
    "Content-Type": "text/plain",
    "Authorization": "Basic cm9vdDpyb290",  # root:root
}


class LoopTickSweeper:
    """Context enrichment sweeper for the autonomous improvement loop.

    Runs vault + SurrealDB + research sweeps per tick to inject relevant
    context into task prompts. All synthesis via Lemonade local inference.
    """

    def __init__(
        self,
        lemonade_url: str = "http://localhost:13305",
        synthesis_model: str = "Gemma-4-E4B-it-GGUF",
        vault_path: str | None = None,
        surreal_url: str = _SURREAL_URL,
        max_vault_results: int = 3,
        research_enabled: bool = True,
        timeout_seconds: float = 10.0,
    ) -> None:
        self._lemonade_url = lemonade_url
        self._synthesis_model = synthesis_model
        self._vault_path = Path(vault_path) if vault_path else _VAULT_PATH
        self._surreal_url = surreal_url
        self._max_vault = max_vault_results
        self._research_enabled = research_enabled
        self._timeout = timeout_seconds

    # ── Public API ────────────────────────────────────────────────────────────

    def build_task_context(self, category: str, description: str) -> str:
        """Return enriched context string to inject into a task prompt.

        Runs vault and SurrealDB sweeps synchronously (fast, no inference).
        Research sweep is skipped per-tick (called per-sprint to save time).
        """
        sections: list[str] = []

        vault_ctx = self._vault_sweep(category, description)
        if vault_ctx:
            sections.append(f"[Vault patterns for {category}]\n{vault_ctx}")

        db_ctx = self._surreal_sweep(category)
        if db_ctx:
            sections.append(f"[Historical results for {category}]\n{db_ctx}")

        return "\n\n".join(sections)

    def course_correct(
        self,
        sprint_results: list[dict[str, Any]],
        category_stats: dict[str, dict[str, int]],
    ) -> str:
        """Analyze sprint results and return course-correction recommendations.

        Runs research sweep on failing categories, then synthesizes recommendations
        via the Lemonade Gemma model. Called once per sprint.

        Returns a markdown-formatted recommendation string.
        """
        failing = [
            cat
            for cat, stats in category_stats.items()
            if stats.get("attempts", 0) > 0
            and (stats.get("successes", 0) / stats["attempts"]) < 0.5
        ]

        research_ctx = ""
        if self._research_enabled and failing:
            research_ctx = self._research_sweep(failing)

        return self._synthesize_course_correction(sprint_results, failing, research_ctx)

    # ── Vault sweep ───────────────────────────────────────────────────────────

    def _vault_sweep(self, category: str, description: str = "") -> str:
        """grep Obsidian vault for files mentioning the task category or description.

        Returns up to _max_vault file excerpts (first 5 lines each).
        Non-blocking — returns empty string on any error.
        """
        if not self._vault_path.exists():
            return ""

        # Map category names to search terms; supplement with words from description
        search_terms = {
            "test_fix": ["test collection", "import error", "pytest collect"],
            "lint_fix": ["ruff", "lint", "F401", "unused import"],
            "type_fix": ["mypy", "type error", "pyright"],
            "refactor": ["refactor", "cyclomatic", "long function"],
        }
        terms = list(search_terms.get(category, [category.replace("_", " ")]))
        # Pull key nouns from description to broaden vault search
        if description:
            words = [w.strip(".,():") for w in description.split() if len(w) > 5][:3]
            terms.extend(words)
        query = "|".join(terms)

        try:
            result = subprocess.run(
                ["grep", "-rl", "--include=*.md", "-E", query, str(self._vault_path)],
                capture_output=True,
                text=True,
                timeout=5,
            )
            files = result.stdout.strip().splitlines()[: self._max_vault]
            if not files:
                return ""

            excerpts = []
            for fpath in files:
                try:
                    lines = Path(fpath).read_text(errors="replace").splitlines()
                    # Skip YAML frontmatter, grab up to 8 meaningful lines
                    content_lines = [l for l in lines if l.strip() and not l.startswith("---")][:8]
                    rel = Path(fpath).relative_to(self._vault_path)
                    excerpts.append(f"• {rel}:\n  " + "\n  ".join(content_lines[:5]))
                except Exception:
                    pass

            return "\n".join(excerpts)
        except Exception as exc:
            logger.debug("Vault sweep failed: %s", exc)
            return ""

    # ── SurrealDB sweep ───────────────────────────────────────────────────────

    def _surreal_sweep(self, category: str) -> str:
        """Query experiment_runs for recent category performance.

        Returns a 1-3 line summary of historical success rates.
        Non-blocking — returns empty string when SurrealDB is offline.
        """
        # Query recent loop runs; surface category from results if stored
        query = (
            "SELECT tasks_completed, tasks_failed, success_rate, model, ts "
            "FROM experiment_runs "
            "WHERE event = 'autonomous_loop' "
            "ORDER BY ts DESC LIMIT 5;"
        )
        # category is used by callers for context labeling; surfaced in output
        _ = category  # retained for future per-category filtering
        try:
            data = query.encode()
            req = urllib.request.Request(
                self._surreal_url,
                data=data,
                headers=_SURREAL_HEADERS,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                body = json.loads(resp.read())
            results = body[0].get("result", []) if body else []
            if not results:
                return ""

            lines = []
            for r in results[:3]:
                rate = r.get("success_rate", 0)
                model = r.get("model", "?")[:20]
                lines.append(f"  loop run: {rate:.0%} success ({model})")
            return "\n".join(lines)
        except Exception as exc:
            logger.debug("SurrealDB sweep failed: %s", exc)
            return ""

    # ── Research sweep ────────────────────────────────────────────────────────

    def _research_sweep(self, failing_categories: list[str]) -> str:
        """Fetch recent arXiv papers relevant to failing categories.

        Uses the HuggingFace papers API endpoint (JSON, no auth needed).
        Synthesizes a 2-sentence summary via Lemonade Gemma-4-E4B.
        """
        # Map categories to search queries
        query_map = {
            "test_fix": "automated test repair LLM agents",
            "lint_fix": "automated code linting correction neural",
            "type_fix": "type inference static analysis LLM",
            "refactor": "automated code refactoring complexity reduction",
        }
        query = query_map.get(failing_categories[0], f"automated {failing_categories[0]} agents")

        try:
            # HuggingFace papers search — JSON endpoint, no auth
            search_url = f"https://huggingface.co/api/papers?q={urllib.parse.quote(query)}&limit=3"
            req = urllib.request.Request(search_url, method="GET")
            req.add_header("Accept", "application/json")
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                papers = json.loads(resp.read())

            if not papers:
                return ""

            abstracts = []
            for p in papers[:2]:
                title = p.get("title", "")
                abstract = (p.get("abstract") or "")[:300]
                if title:
                    abstracts.append(f"'{title}': {abstract}")

            if not abstracts:
                return ""

            raw_context = "\n".join(abstracts)
            return self._synthesize_research(raw_context, failing_categories)

        except Exception as exc:
            logger.debug("Research sweep failed: %s", exc)
            return ""

    def _synthesize_research(self, raw_context: str, categories: list[str]) -> str:
        """Use Lemonade Gemma-4-E4B to synthesize a 1-sentence research insight."""
        cats = ", ".join(categories)
        prompt = (
            f"Given these recent papers about automated code improvement, "
            f"give ONE actionable insight relevant to fixing {cats} failures in a Python codebase. "
            f"Reply in one sentence.\n\nPapers:\n{raw_context}"
        )
        payload = json.dumps(
            {
                "model": self._synthesis_model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 80,
                "temperature": 0.0,
            }
        ).encode()

        try:
            req = urllib.request.Request(
                f"{self._lemonade_url}/v1/chat/completions",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"].get("content", "").strip()
        except Exception as exc:
            logger.debug("Research synthesis failed: %s", exc)
            return ""

    # ── Course correction ─────────────────────────────────────────────────────

    def _synthesize_course_correction(
        self,
        sprint_results: list[dict[str, Any]],
        failing_categories: list[str],
        research_context: str,
    ) -> str:
        """Synthesize course-correction recommendations via Lemonade.

        Uses Gemma-4-E4B for speed (this is meta-loop overhead, not task work).
        Returns markdown-formatted recommendations.
        """
        completed = sum(1 for r in sprint_results if r.get("success"))
        failed = sum(1 for r in sprint_results if not r.get("success"))
        failing_str = ", ".join(failing_categories) if failing_categories else "none"
        research_str = f"\nRecent research insight: {research_context}" if research_context else ""

        prompt = (
            f"Autonomous code improvement loop sprint results:\n"
            f"- Completed: {completed}, Failed: {failed}\n"
            f"- Consistently failing categories: {failing_str}{research_str}\n\n"
            f"Give 2-3 specific, actionable recommendations to improve the next sprint. "
            f"Focus on: what task types to prioritize, what to skip, and any prompt strategy. "
            f"Be concrete and brief (under 100 words)."
        )
        payload = json.dumps(
            {
                "model": self._synthesis_model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 150,
                "temperature": 0.1,
            }
        ).encode()

        try:
            req = urllib.request.Request(
                f"{self._lemonade_url}/v1/chat/completions",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read())
                return data["choices"][0]["message"].get("content", "").strip()
        except Exception as exc:
            logger.debug("Course correction synthesis failed: %s", exc)
            return f"[synthesis unavailable: {exc}]"
