"""R-Zero Challenger Solver — self-evolving task difficulty calibration.

Implements the R-Zero (ICLR 2026, arxiv 2508.05004) co-evolution pattern for
the Cohezion autonomous improvement loop:

  ChallengerAgent generates skill improvement tasks targeting ~50% Solver
  success rate (maximum learning signal per task). Challenger reward =
  1 - |mean_success - 0.5|. Prior episode success rate feeds back into
  difficulty hints for the next episode.

  Optional WebSearch enrichment: mcp-cli web-search/search injects fresh
  research context into the Challenger's task generation prompt.

All inference routes through the Lemonade OmniRouter on :13305.
Results are pushed to vault_neuron for Markov quality tracking.
"""

from __future__ import annotations

import json
import logging
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from cohezion.config.defaults import LEMONADE_BASE_URL


logger = logging.getLogger(__name__)

# Model routing — both via OmniRouter :13305
_CHALLENGER_MODEL = "llama3.2-1b-FLM"  # NPU: fast, task proposal generation
_SOLVER_MODEL = "Gemma-4-E4B-it-GGUF"  # iGPU: stronger, attempts tasks

_SURREAL_URL = "http://localhost:8001/sql"
_SURREAL_HEADERS = {
    "Content-Type": "text/plain",
    "surreal-ns": "cohezion",
    "surreal-db": "main",
    "Accept": "application/json",
    "Authorization": "Basic cm9vdDpyb290",
}


@dataclass
class TaskAttempt:
    task_id: str
    task_text: str
    solver_response: str
    quality_score: float  # 1.0 = concrete improvement found, 0.0 = vague/empty
    elapsed_ms: int
    model: str


@dataclass
class EpisodeResult:
    episode_id: str
    tasks: list[TaskAttempt] = field(default_factory=list)
    challenger_reward: float = 0.0  # 1 - |mean_success - 0.5|
    mean_success: float = 0.0
    elapsed_s: float = 0.0


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------


def _chat(
    base_url: str,
    model: str,
    prompt: str,
    max_tokens: int = 512,
    timeout: float = 60.0,
    temperature: float = 0.7,
) -> tuple[str, dict[str, Any]]:
    """POST /v1/chat/completions via OmniRouter. Returns (text, raw_response)."""
    payload = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
    ).encode()
    req = urllib.request.Request(  # noqa: S310
        f"{base_url.rstrip('/')}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            data = json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        logger.warning("OmniRouter HTTP %d for model %s", exc.code, model)
        return "", {}
    except Exception as exc:
        logger.warning("OmniRouter request failed (%s): %s", model, exc)
        return "", {}

    choices = data.get("choices", [])
    if not choices:
        return "", data
    msg = choices[0].get("message", {})
    # Promote reasoning_content → content for thinking-mode models (Gemma-4-*)
    text = msg.get("content") or msg.get("reasoning_content") or ""
    return text.strip(), data


def _web_search_enrich(query: str, max_chars: int = 800) -> str:
    """Pull fresh research context via mcp-cli web-search. Fails gracefully."""
    try:
        arg = json.dumps({"query": query, "num_results": 3})
        result = subprocess.run(
            ["mcp-cli", "web-search/search", arg, "--raw"],
            capture_output=True,
            text=True,
            timeout=10.0,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()[:max_chars]
    except Exception as exc:
        logger.debug("WebSearch enrichment unavailable: %s", exc)
    return ""


def _vault_quality_context() -> str:
    """Pull recent 24h skill_improvement quality from SurrealDB."""
    sql = (
        "SELECT math::mean(quality_score) AS avg_q, count() AS n "
        "FROM vault_neuron WHERE category = 'skill_improvement' "
        "AND recorded_at > time::now() - 1d GROUP ALL;"
    )
    try:
        req = urllib.request.Request(  # noqa: S310
            _SURREAL_URL, data=sql.encode(), headers=_SURREAL_HEADERS, method="POST"
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:  # noqa: S310
            data = json.loads(resp.read())
        rows = data[0].get("result", []) if isinstance(data, list) else []
        if rows:
            r = rows[0]
            return f"{r.get('n', 0)} tasks in last 24h, avg_quality={r.get('avg_q', 0):.2f}"
    except Exception as exc:
        logger.debug("Vault quality context query failed: %s", exc)
    return "no recent quality data"


def _push_episode_to_vault(episode: EpisodeResult) -> None:
    """Batch INSERT episode task attempts to vault_neuron."""
    if not episode.tasks:
        return
    rows = []
    for attempt in episode.tasks:
        tid = attempt.task_id.replace("'", "")[:80]
        success_str = "true" if attempt.quality_score >= 0.5 else "false"
        rows.append(
            f"{{task_id: 'rzero:{tid}', category: 'skill_improvement', "
            f"success: {success_str}, quality_score: {attempt.quality_score}, "
            f"node: 'rzero', tokens: 0, recorded_at: time::now(), "
            f"episode_id: '{episode.episode_id}', "
            f"challenger_reward: {episode.challenger_reward:.3f}}}"
        )
    sql = "INSERT INTO vault_neuron [" + ", ".join(rows) + "];"
    try:
        req = urllib.request.Request(  # noqa: S310
            _SURREAL_URL, data=sql.encode(), headers=_SURREAL_HEADERS, method="POST"
        )
        with urllib.request.urlopen(req, timeout=5.0) as resp:  # noqa: S310
            resp.read()
        logger.info(
            "R-Zero: pushed %d results to vault_neuron (episode=%s, reward=%.2f)",
            len(episode.tasks),
            episode.episode_id,
            episode.challenger_reward,
        )
    except Exception as exc:
        logger.warning("R-Zero: vault push failed: %s", exc)


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------


class ChallengerAgent:
    """Generates skill improvement tasks calibrated to ~50% Solver success.

    Uses the NPU model (llama3.2-1b-FLM, fast) to propose tasks at the edge
    of the Solver's ability. WebSearch context and vault quality history enrich
    the Challenger's prompt for more targeted problem generation.
    """

    def __init__(self, base_url: str = LEMONADE_BASE_URL) -> None:
        self._base_url = base_url

    def generate_tasks(
        self,
        n: int,
        prior_success_rate: float | None = None,
        quality_context: str = "",
        web_context: str = "",
    ) -> list[str]:
        """Generate N task descriptions targeting ~50% Solver success rate."""
        difficulty_hint = self._difficulty_hint(prior_success_rate)
        research_block = f"\nRecent research context:\n{web_context}\n" if web_context else ""
        vault_block = f"\nVault quality history: {quality_context}\n" if quality_context else ""

        prompt = (
            f"You are a Challenger AI designing compound engineering tasks for a Solver AI "
            f"working on the Cohezion codebase (Python, src/cohezion/).\n"
            f"\nGoal: propose exactly {n} tasks where the Solver will succeed on roughly HALF. "
            f"This maximizes learning signal (R-Zero optimal difficulty).\n"
            f"{difficulty_hint}"
            f"{vault_block}"
            f"{research_block}"
            f"\nRules per task:\n"
            f"- Reference a real file in src/cohezion/ (no invented paths)\n"
            f"- Ask for ONE specific, verifiable change (a function, test, or fix)\n"
            f"- Alternate: some tasks straightforward, some requiring deeper reasoning\n"
            f"- Keep each task to 1-2 sentences\n"
            f"\nOutput exactly {n} tasks, numbered 1-{n}, one per line. No other text."
        )

        text, _ = _chat(
            self._base_url,
            _CHALLENGER_MODEL,
            prompt,
            max_tokens=n * 90,
            temperature=0.85,
        )

        tasks = self._parse_numbered_list(text, n)
        logger.debug("Challenger generated %d/%d tasks from model output", len(tasks), n)
        return tasks

    def _difficulty_hint(self, prior: float | None) -> str:
        if prior is None:
            return "\nNo prior success data — start with a mix of easy and hard tasks.\n"
        if prior > 0.65:
            return f"\nPrior success rate {prior:.0%} (too easy). Make tasks HARDER — deeper reasoning needed.\n"
        if prior < 0.35:
            return f"\nPrior success rate {prior:.0%} (too hard). Make tasks EASIER — more concrete and specific.\n"
        return (
            f"\nPrior success rate {prior:.0%} (well-calibrated). Maintain this difficulty level.\n"
        )

    def _parse_numbered_list(self, text: str, n: int) -> list[str]:
        """Parse 'N. task text' lines from model output."""
        tasks: list[str] = []
        _FALLBACK = (
            "Review src/cohezion/compound/executor.py and identify one function "
            "missing a return type annotation or a docstring for its error path."
        )
        if not text:
            return [_FALLBACK] * n

        for line in text.split("\n"):
            line = line.strip()
            if not line:
                continue
            # Strip "1. " / "1) " / "1: " prefixes
            for sep in (". ", ") ", ": "):
                prefix = line.split(sep, 1)
                if len(prefix) == 2 and prefix[0].strip().isdigit():
                    line = prefix[1].strip()
                    break
            if line:
                tasks.append(line)
            if len(tasks) >= n:
                break

        while len(tasks) < n:
            tasks.append(_FALLBACK)
        return tasks[:n]


class SolverAgent:
    """Attempts tasks from the Challenger. Returns a quality_score (0.0 or 1.0).

    Uses the iGPU model (Gemma-4-E4B-it-GGUF) via OmniRouter for stronger
    reasoning. A concrete response (specific file + change) scores 1.0;
    vague or empty responses score 0.0.
    """

    def __init__(self, base_url: str = LEMONADE_BASE_URL) -> None:
        self._base_url = base_url

    def attempt_task(self, task_text: str, task_id: str) -> TaskAttempt:
        """Attempt one task. Returns TaskAttempt with binary quality_score."""
        prompt = (
            "You are a compound engineering assistant working on the Cohezion codebase.\n\n"
            f"Task: {task_text}\n\n"
            "Respond with:\n"
            "1. The exact file path (e.g. src/cohezion/compound/executor.py)\n"
            "2. The specific change (line range and what to change)\n"
            "3. Why this improves the codebase\n\n"
            "Be concrete. If you cannot identify a real change, say: 'No concrete change found.'"
        )
        t0 = time.monotonic()
        text, _ = _chat(
            self._base_url,
            _SOLVER_MODEL,
            prompt,
            max_tokens=400,
            temperature=0.3,
        )
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        quality = self._score(text)

        return TaskAttempt(
            task_id=task_id,
            task_text=task_text[:120],
            solver_response=text[:300],
            quality_score=quality,
            elapsed_ms=elapsed_ms,
            model=_SOLVER_MODEL,
        )

    def _score(self, text: str) -> float:
        """Binary score: 1.0 if response is concrete, 0.0 otherwise."""
        if not text or len(text) < 20:
            return 0.0
        if "no concrete change" in text.lower() or "cannot identify" in text.lower():
            return 0.0
        # Must reference a real codebase path and propose a change
        has_path = "src/cohezion" in text
        has_change = any(
            kw in text.lower()
            for kw in ("line ", "def ", "class ", "import ", "add ", "remove ", "fix ", "replace ")
        )
        return 1.0 if (has_path and has_change) else 0.0


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------


class RZeroChallengerExecutor:
    """R-Zero co-evolution executor: Challenger ↔ Solver difficulty calibration.

    Each call to run_episode() completes one co-evolution cycle:
      1. Enrich Challenger with WebSearch + vault context
      2. Challenger generates N tasks targeting ~50% success
      3. Solver attempts each task sequentially
      4. Challenger reward = 1 - |mean_success - 0.5|
      5. Prior success rate stored for next episode's difficulty hint
      6. Results pushed to vault_neuron

    Typical usage:
        executor = RZeroChallengerExecutor()
        for _ in range(3):
            result = executor.run_episode(n_tasks=8)
            print(f"Episode reward: {result.challenger_reward:.2f}")
    """

    def __init__(
        self,
        base_url: str = LEMONADE_BASE_URL,
        search_query: str = "compound AI skill improvement autonomous loop ICLR 2026",
    ) -> None:
        self._base_url = base_url
        self._search_query = search_query
        self._challenger = ChallengerAgent(base_url)
        self._solver = SolverAgent(base_url)
        self._prior_success_rate: float | None = None

    def run_episode(self, n_tasks: int = 8) -> EpisodeResult:
        """Run one R-Zero episode: generate → attempt → reward → push to vault."""
        t0 = time.monotonic()
        episode_id = f"rzero-{int(t0)}"
        logger.info("=" * 50)
        logger.info("R-Zero episode %s | %d tasks", episode_id, n_tasks)
        if self._prior_success_rate is not None:
            logger.info("  prior success rate: %.0f%%", self._prior_success_rate * 100)

        # Enrich Challenger with online + vault context
        web_ctx = _web_search_enrich(self._search_query)
        if web_ctx:
            logger.info("  WebSearch enrichment: %d chars", len(web_ctx))
        vault_ctx = _vault_quality_context()
        logger.info("  Vault context: %s", vault_ctx)

        # Challenger proposes tasks
        tasks = self._challenger.generate_tasks(
            n=n_tasks,
            prior_success_rate=self._prior_success_rate,
            quality_context=vault_ctx,
            web_context=web_ctx,
        )
        logger.info("  Challenger: %d tasks generated", len(tasks))

        # Solver attempts each task
        attempts: list[TaskAttempt] = []
        wins = 0
        for i, task_text in enumerate(tasks):
            task_id = f"{episode_id}-t{i + 1:02d}"
            attempt = self._solver.attempt_task(task_text, task_id)
            attempts.append(attempt)
            win = attempt.quality_score >= 0.5
            wins += int(win)
            logger.info(
                "  [%d/%d] %s q=%.1f %dms",
                i + 1,
                len(tasks),
                "WIN" if win else "LOSS",
                attempt.quality_score,
                attempt.elapsed_ms,
            )

        # Challenger reward
        mean_success = wins / len(attempts) if attempts else 0.5
        challenger_reward = 1.0 - abs(mean_success - 0.5)
        self._prior_success_rate = mean_success

        result = EpisodeResult(
            episode_id=episode_id,
            tasks=attempts,
            challenger_reward=challenger_reward,
            mean_success=mean_success,
            elapsed_s=time.monotonic() - t0,
        )

        logger.info(
            "  mean_success=%.0f%%  challenger_reward=%.2f  elapsed=%.1fs",
            mean_success * 100,
            challenger_reward,
            result.elapsed_s,
        )
        logger.info("=" * 50)

        _push_episode_to_vault(result)
        return result
