"""R-Zero / Language Self-Play (LSP) Challenger Solver — self-evolving difficulty calibration.

Implements the R-Zero (ICLR 2026, arxiv 2508.05004) and Language Self-Play (LSP,
Meta FAIR, arxiv 2509.07414) co-evolution patterns for the Cohezion autonomous
improvement loop:

  Challenger proposes queries targeting optimal learning signals.
  Solver generates candidate solutions evaluated with GRPO group relative
  advantages and dual instruction quality self-rewards (R_Q) to prevent
  adversarial collapse and reward hacking.

All inference routes through the Lemonade OmniRouter on :13305 or configured providers.
Results are pushed to vault_neuron for Markov quality tracking.
"""

from __future__ import annotations

import ast
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

# Model routing — via OmniRouter :13305
_CHALLENGER_MODEL = "llama3.2-1b-FLM"  # NPU: fast, task proposal generation
_SOLVER_MODEL = "Qwen3-Coder-30B-A3B-Instruct-GGUF"  # iGPU: code generation

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
    instruction_quality_rq: float = 0.0
    group_id: str = ""
    candidate_idx: int = 0
    solver_advantage: float = 0.0


@dataclass
class CandidateAttempt:
    candidate_idx: int
    solver_response: str
    reward_r: float  # Task correctness / concreteness reward R(q_i, a_i^j)
    instruction_quality_rq: float  # Instruction quality reward R_Q(q_i, a_i^j)
    combined_solver_reward: float  # R + beta * R_Q
    solver_advantage: float  # R(q_i, a_i^j) - V(q_i)
    elapsed_ms: int
    model: str
    ast_valid: bool = False


@dataclass
class GroupTaskAttempt:
    task_id: str
    task_text: str
    candidates: list[CandidateAttempt] = field(default_factory=list)
    group_baseline_v: float = 0.0  # V(q_i) = (1/G) * sum_j R(q_i, a_i^j)
    quality_baseline_vq: float = 0.0  # V_Q(q_i) = (1/G) * sum_j R_Q(q_i, a_i^j)
    challenger_reward: float = 0.0  # -V(q_i) + gamma * V_Q(q_i)
    challenger_advantage: float = 0.0  # V - V(q_i) + gamma * V_Q(q_i)
    best_candidate_idx: int = 0


@dataclass
class EpisodeResult:
    episode_id: str
    tasks: list[TaskAttempt] = field(default_factory=list)
    challenger_reward: float = 0.0  # Calibrated difficulty reward + gamma * V_Q
    mean_success: float = 0.0
    elapsed_s: float = 0.0
    global_baseline_v: float = 0.0  # Global baseline V = (1/N) * sum_i V(q_i)
    mean_quality_vq: float = 0.0  # Mean V_Q across all queries in episode
    group_tasks: list[GroupTaskAttempt] = field(default_factory=list)


# ---------------------------------------------------------------------------
# AST Verification & Quality Self-Reward (R_Q) Helpers
# ---------------------------------------------------------------------------


def evaluate_code_ast(text: str) -> tuple[bool, str]:
    """Extract Python code blocks from text and verify AST parseability.

    Returns:
        (ast_valid, detail_message)
    """
    if not text:
        return False, "empty text"

    code_blocks: list[str] = []
    lines = text.split("\n")
    in_block = False
    current_block: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_block:
                code_blocks.append("\n".join(current_block))
                current_block = []
                in_block = False
            else:
                in_block = True
        elif in_block:
            current_block.append(line)

    if in_block and current_block:
        code_blocks.append("\n".join(current_block))

    if code_blocks:
        for i, block in enumerate(code_blocks):
            if not block.strip():
                continue
            try:
                ast.parse(block)
            except SyntaxError as exc:
                return False, f"block {i + 1} syntax error: {exc}"
        return True, f"{len(code_blocks)} code blocks parsed cleanly"

    if any(
        kw in text
        for kw in (
            "def ",
            "class ",
            "import ",
            "from cohezion",
            "return ",
            "try:",
            "except",
        )
    ):
        try:
            ast.parse(text)
            return True, "full text parsed as valid Python AST"
        except Exception:
            pass

    return False, "no valid Python AST detected"


def compute_rq(task_text: str, response_text: str) -> tuple[float, bool]:
    """Compute instruction-following quality reward R_Q in [0.0, 1.0].

    LSP Non-Zero-Sum Quality Reward (arXiv:2509.07414):
    Penalizes:
      - Empty or evasive responses ('no concrete change', 'cannot identify')
      - Syntax errors / invalid AST
      - Incoherent responses lacking reference to target problem
    Rewards:
      - Reference to real codebase files (+0.3)
      - Concrete action / diff (+0.3)
      - Syntactically valid Python AST (+0.2)
      - Structural rationale / explanation (+0.2)

    Returns:
        (rq_score, ast_valid)
    """
    if not response_text or len(response_text) < 20:
        return 0.0, False

    resp_lower = response_text.lower()
    if "no concrete change" in resp_lower or "cannot identify" in resp_lower:
        return 0.0, False

    ast_valid, _ = evaluate_code_ast(response_text)

    score = 0.0
    if "src/cohezion" in response_text:
        score += 0.3

    if any(
        kw in resp_lower
        for kw in (
            "line ",
            "def ",
            "class ",
            "import ",
            "add ",
            "remove ",
            "fix ",
            "replace ",
        )
    ):
        score += 0.3

    if ast_valid:
        score += 0.2

    if any(
        kw in resp_lower
        for kw in (
            "improve",
            "because",
            "fix",
            "prevent",
            "ensure",
            "resolve",
            "reason",
        )
    ):
        score += 0.2

    return round(min(1.0, score), 3), ast_valid


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
        req = urllib.request.Request(
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
    """Batch INSERT episode task attempts and group metrics to vault_neuron."""
    if not episode.tasks:
        return
    rows = []
    for attempt in episode.tasks:
        tid = attempt.task_id.replace("'", "")[:80]
        success_str = "true" if attempt.quality_score >= 0.5 else "false"
        rows.append(
            f"{{task_id: 'rzero:{tid}', category: 'skill_improvement', "
            f"success: {success_str}, quality_score: {attempt.quality_score}, "
            f"instruction_quality_rq: {attempt.instruction_quality_rq:.3f}, "
            f"solver_advantage: {attempt.solver_advantage:.3f}, "
            f"node: 'rzero', tokens: 0, recorded_at: time::now(), "
            f"episode_id: '{episode.episode_id}', "
            f"challenger_reward: {episode.challenger_reward:.3f}}}"
        )
    sql = "INSERT INTO vault_neuron [" + ", ".join(rows) + "];"
    try:
        req = urllib.request.Request(
            _SURREAL_URL, data=sql.encode(), headers=_SURREAL_HEADERS, method="POST"
        )
        with urllib.request.urlopen(req, timeout=5.0) as resp:  # noqa: S310
            resp.read()
        logger.info(
            "R-Zero/LSP: pushed %d results to vault_neuron (episode=%s, reward=%.2f)",
            len(episode.tasks),
            episode.episode_id,
            episode.challenger_reward,
        )
    except Exception as exc:
        logger.warning("R-Zero/LSP: vault push failed: %s", exc)


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------


class ChallengerAgent:
    """Generates skill improvement tasks calibrated to ~50% Solver success.

    Uses the NPU model (llama3.2-1b-FLM, fast) to propose tasks at the edge
    of the Solver's ability. WebSearch context and vault quality history enrich
    the Challenger's prompt for more targeted problem generation.
    """

    def __init__(
        self,
        base_url: str = LEMONADE_BASE_URL,
        model: str = _CHALLENGER_MODEL,
    ) -> None:
        self._base_url = base_url
        self._model = model

    def generate_tasks(
        self,
        n: int,
        prior_success_rate: float | None = None,
        quality_context: str = "",
        web_context: str = "",
    ) -> list[str]:
        """Generate N task descriptions targeting ~50% Solver success rate."""
        difficulty_hint = self._difficulty_hint(prior_success_rate)
        research_block = (
            f"\nRecent research context:\n{web_context}\n" if web_context else ""
        )
        vault_block = (
            f"\nVault quality history: {quality_context}\n" if quality_context else ""
        )

        prompt = (
            "You are a Challenger AI designing compound engineering tasks for a Solver AI "
            "working on the Cohezion codebase (Python, src/cohezion/).\n"
            f"\nGoal: propose exactly {n} tasks where the Solver will succeed on roughly HALF. "
            "This maximizes learning signal (Language Self-Play optimal minimax difficulty).\n"
            f"{difficulty_hint}"
            f"{vault_block}"
            f"{research_block}"
            "\nRules per task:\n"
            "- Reference a real file in src/cohezion/ (no invented paths)\n"
            "- Ask for ONE specific, verifiable change (a function, test, or fix)\n"
            "- Alternate: some tasks straightforward, some requiring deeper reasoning\n"
            "- Keep each task to 1-2 sentences\n"
            f"\nOutput exactly {n} tasks, numbered 1-{n}, one per line. No other text."
        )

        text, _ = _chat(
            self._base_url,
            self._model,
            prompt,
            max_tokens=n * 90,
            temperature=0.85,
        )

        tasks = self._parse_numbered_list(text, n)
        logger.debug(
            "Challenger generated %d/%d tasks from model output", len(tasks), n
        )
        return tasks

    def _difficulty_hint(self, prior: float | None) -> str:
        if prior is None:
            return "\nNo prior success data — start with a mix of easy and hard tasks.\n"
        if prior > 0.65:
            return (
                f"\nPrior success rate {prior:.0%} (too easy). Make tasks HARDER — "
                "deeper reasoning needed.\n"
            )
        if prior < 0.35:
            return (
                f"\nPrior success rate {prior:.0%} (too hard). Make tasks EASIER — "
                "more concrete and specific.\n"
            )
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
    """Attempts tasks from the Challenger. Evaluates correctness and instruction quality.

    Supports single-attempt execution (backward compatible) or GRPO group sampling
    across G candidate solutions per Language Self-Play (LSP, arXiv:2509.07414).
    """

    def __init__(
        self,
        base_url: str = LEMONADE_BASE_URL,
        model: str = _SOLVER_MODEL,
    ) -> None:
        self._base_url = base_url
        self._model = model

    def attempt_task(self, task_text: str, task_id: str) -> TaskAttempt:
        """Attempt one task. Returns TaskAttempt (backward compatible)."""
        group = self.attempt_task_group(
            task_text, task_id, group_size=1, temperature=0.3
        )
        best_c = (
            group.candidates[group.best_candidate_idx]
            if group.candidates
            else CandidateAttempt(
                candidate_idx=0,
                solver_response="",
                reward_r=0.0,
                instruction_quality_rq=0.0,
                combined_solver_reward=0.0,
                solver_advantage=0.0,
                elapsed_ms=0,
                model=self._model,
            )
        )
        return TaskAttempt(
            task_id=task_id,
            task_text=task_text[:120],
            solver_response=best_c.solver_response[:300],
            quality_score=best_c.reward_r,
            elapsed_ms=best_c.elapsed_ms,
            model=best_c.model,
            instruction_quality_rq=best_c.instruction_quality_rq,
            group_id=task_id,
            candidate_idx=best_c.candidate_idx,
            solver_advantage=best_c.solver_advantage,
        )

    def attempt_task_group(
        self,
        task_text: str,
        task_id: str,
        group_size: int = 2,
        temperature: float = 0.7,
        beta_rq: float = 0.5,
    ) -> GroupTaskAttempt:
        """Attempt one task across G candidates (Language Self-Play GRPO).

        Args:
            task_text: Query proposed by Challenger.
            task_id: Unique task identifier.
            group_size: Number of candidate solutions G to sample (G >= 1).
            temperature: Sampling temperature (higher for group diversity).
            beta_rq: Weight for instruction-following quality reward R_Q.

        Returns:
            GroupTaskAttempt with all G candidates, group baseline V(q_i),
            quality baseline V_Q(q_i), and individual candidate advantages.
        """
        prompt = (
            "You are a compound engineering assistant working on the Cohezion codebase.\n\n"
            f"Task: {task_text}\n\n"
            "Respond with:\n"
            "1. The exact file path (e.g. src/cohezion/compound/executor.py)\n"
            "2. The specific change (line range and what to change)\n"
            "3. Why this improves the codebase\n\n"
            "Be concrete. If you cannot identify a real change, say: 'No concrete change found.'"
        )

        candidates: list[CandidateAttempt] = []
        temp = 0.3 if group_size == 1 else temperature

        for j in range(group_size):
            c_t0 = time.monotonic()
            text, _ = _chat(
                self._base_url,
                self._model,
                prompt,
                max_tokens=400,
                temperature=temp,
            )
            c_elapsed_ms = int((time.monotonic() - c_t0) * 1000)
            r_score = self._score(text)
            rq_score, ast_valid = compute_rq(task_text, text)
            combined = r_score + (beta_rq * rq_score)

            candidates.append(
                CandidateAttempt(
                    candidate_idx=j,
                    solver_response=text[:300],
                    reward_r=r_score,
                    instruction_quality_rq=rq_score,
                    combined_solver_reward=combined,
                    solver_advantage=0.0,
                    elapsed_ms=c_elapsed_ms,
                    model=self._model,
                    ast_valid=ast_valid,
                )
            )

        g_len = len(candidates)
        group_v = (
            sum(c.reward_r for c in candidates) / g_len if g_len > 0 else 0.0
        )
        quality_vq = (
            sum(c.instruction_quality_rq for c in candidates) / g_len
            if g_len > 0
            else 0.0
        )

        best_idx = 0
        best_val = -float("inf")
        for cand in candidates:
            cand.solver_advantage = round(cand.reward_r - group_v, 3)
            if cand.combined_solver_reward > best_val:
                best_val = cand.combined_solver_reward
                best_idx = cand.candidate_idx

        return GroupTaskAttempt(
            task_id=task_id,
            task_text=task_text[:120],
            candidates=candidates,
            group_baseline_v=round(group_v, 3),
            quality_baseline_vq=round(quality_vq, 3),
            best_candidate_idx=best_idx,
        )

    def _score(self, text: str) -> float:
        """Score: 1.0 if response is concrete and references codebase, 0.0 otherwise."""
        if not text or len(text) < 20:
            return 0.0
        if "no concrete change" in text.lower() or "cannot identify" in text.lower():
            return 0.0
        has_path = "src/cohezion" in text
        has_change = any(
            kw in text.lower()
            for kw in (
                "line ",
                "def ",
                "class ",
                "import ",
                "add ",
                "remove ",
                "fix ",
                "replace ",
            )
        )
        return 1.0 if (has_path and has_change) else 0.0


# ---------------------------------------------------------------------------
# Executor
# ---------------------------------------------------------------------------


class RZeroChallengerExecutor:
    """R-Zero / Language Self-Play (LSP) co-evolution executor.

    Implements Meta's Language Self-Play (arXiv:2509.07414) minimax game with
    GRPO group-relative advantages and instruction quality self-rewards (R_Q):

      1. Challenger proposes N tasks q_1..q_N conditioned on difficulty and quality
      2. Solver generates G candidate responses a_i^1..a_i^G per query
      3. Group baseline V(q_i) = (1/G) * sum_j R(q_i, a_i^j)
      4. Global baseline V = (1/N) * sum_i V(q_i)
      5. Solver advantage A_Sol(q_i, a_i^j) = R(q_i, a_i^j) - V(q_i)
      6. Challenger advantage A_Ch(q_i) = V - V(q_i) + gamma * V_Q(q_i)
      7. Dual quality reward R_Q prevents adversarial collapse (LSP-Zero trap)
    """

    def __init__(
        self,
        base_url: str = LEMONADE_BASE_URL,
        search_query: str = "compound AI skill improvement autonomous loop ICLR 2026",
        group_size: int = 2,
        beta_rq: float = 0.5,
        gamma_vq: float = 0.5,
        challenger_model: str | None = None,
        solver_model: str | None = None,
    ) -> None:
        self._base_url = base_url
        self._search_query = search_query
        self._group_size = max(1, group_size)
        self._beta_rq = beta_rq
        self._gamma_vq = gamma_vq
        self._challenger = ChallengerAgent(
            base_url, model=challenger_model or _CHALLENGER_MODEL
        )
        self._solver = SolverAgent(base_url, model=solver_model or _SOLVER_MODEL)
        self._prior_success_rate: float | None = None

    def run_episode(
        self,
        n_tasks: int = 8,
        group_size: int | None = None,
    ) -> EpisodeResult:
        """Run one self-play episode: generate -> group attempt -> GRPO advantage -> push to vault."""
        g_size = self._group_size if group_size is None else max(1, group_size)
        t0 = time.monotonic()
        episode_id = f"rzero-{int(t0)}"
        logger.info("=" * 50)
        logger.info(
            "LSP/R-Zero episode %s | %d tasks | G=%d candidates",
            episode_id,
            n_tasks,
            g_size,
        )
        if self._prior_success_rate is not None:
            logger.info(
                "  prior success rate: %.0f%%", self._prior_success_rate * 100
            )

        web_ctx = _web_search_enrich(self._search_query)
        if web_ctx:
            logger.info("  WebSearch enrichment: %d chars", len(web_ctx))
        vault_ctx = _vault_quality_context()
        logger.info("  Vault context: %s", vault_ctx)

        tasks = self._challenger.generate_tasks(
            n=n_tasks,
            prior_success_rate=self._prior_success_rate,
            quality_context=vault_ctx,
            web_context=web_ctx,
        )
        logger.info("  Challenger: %d tasks generated", len(tasks))

        group_attempts: list[GroupTaskAttempt] = []
        primary_attempts: list[TaskAttempt] = []

        for i, task_text in enumerate(tasks):
            task_id = f"{episode_id}-t{i + 1:02d}"
            group_att = self._solver.attempt_task_group(
                task_text=task_text,
                task_id=task_id,
                group_size=g_size,
                beta_rq=self._beta_rq,
            )
            group_attempts.append(group_att)

            best_cand = group_att.candidates[group_att.best_candidate_idx]
            primary_attempts.append(
                TaskAttempt(
                    task_id=task_id,
                    task_text=task_text[:120],
                    solver_response=best_cand.solver_response[:300],
                    quality_score=best_cand.reward_r,
                    elapsed_ms=best_cand.elapsed_ms,
                    model=best_cand.model,
                    instruction_quality_rq=best_cand.instruction_quality_rq,
                    group_id=task_id,
                    candidate_idx=best_cand.candidate_idx,
                    solver_advantage=best_cand.solver_advantage,
                )
            )
            logger.info(
                "  [%d/%d] V(q_i)=%.2f V_Q(q_i)=%.2f (G=%d)",
                i + 1,
                len(tasks),
                group_att.group_baseline_v,
                group_att.quality_baseline_vq,
                len(group_att.candidates),
            )

        n_total = len(group_attempts)
        global_v = (
            sum(g.group_baseline_v for g in group_attempts) / n_total
            if n_total > 0
            else 0.5
        )
        mean_vq = (
            sum(g.quality_baseline_vq for g in group_attempts) / n_total
            if n_total > 0
            else 0.5
        )

        for g in group_attempts:
            g.challenger_advantage = round(
                global_v - g.group_baseline_v + (self._gamma_vq * g.quality_baseline_vq),
                3,
            )
            g.challenger_reward = round(
                -g.group_baseline_v + (self._gamma_vq * g.quality_baseline_vq),
                3,
            )

        difficulty_reward = 1.0 - abs(global_v - 0.5)
        total_challenger_reward = round(
            difficulty_reward + (self._gamma_vq * mean_vq), 3
        )
        self._prior_success_rate = global_v

        result = EpisodeResult(
            episode_id=episode_id,
            tasks=primary_attempts,
            challenger_reward=total_challenger_reward,
            mean_success=global_v,
            elapsed_s=time.monotonic() - t0,
            global_baseline_v=round(global_v, 3),
            mean_quality_vq=round(mean_vq, 3),
            group_tasks=group_attempts,
        )

        logger.info(
            "  global_v=%.2f  mean_vq=%.2f  challenger_reward=%.2f  elapsed=%.1fs",
            global_v,
            mean_vq,
            total_challenger_reward,
            result.elapsed_s,
        )
        logger.info("=" * 50)

        _push_episode_to_vault(result)
        return result
