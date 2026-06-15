"""Process Reward Model (PRM) for step-level scoring in CompoundExecutor.

Addresses the gap identified by arXiv:2509.02547 (Agentic RL Survey):
MakerCheckerVerifier gives one final outcome verdict, but PRMs score each
intermediate step, providing dense reward signal to SkillRefiner.

The dense reward signal enables SkillRefiner to identify WHICH step of the
11-step pipeline caused quality loss — not just whether the final output failed.

Usage inside CompoundExecutor.execute_task()::

    prm = build_process_reward_model()
    record_id = prm.begin_execution(task_description)

    # After each key step
    verdict = prm.record_step(record_id, "3", "execute_fn", output, "Produce task output")

    record = prm.finalize(record_id)
    metrics.update(prm.to_metrics_dict(record))
"""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.request
import uuid
from dataclasses import dataclass, field
from typing import Any

from cohezion.inference.config import LEMONADE_BASE_URL


logger = logging.getLogger(__name__)

_PRM_TIMEOUT_SECONDS: float = 6.0

_PRM_SYSTEM_PROMPT = (
    "You are a step quality evaluator for an AI pipeline. "
    "Rate the quality of this intermediate step output on a scale of 0-10. "
    "0 = completely wrong or useless. 10 = perfect, exactly what was expected. "
    "Reply with exactly one integer (0-10) and nothing else."
)


@dataclass
class StepVerdict:
    """Quality verdict for one pipeline step.

    score: 0.0-1.0 (normalized from 0-10 integer rating)
    is_pass: True when score >= 0.6
    reason: raw text from the scoring model (may be empty on error)
    latency_seconds: wall-clock time for the scoring call
    """

    step_id: str = ""
    step_name: str = ""
    score: float = 0.5  # neutral default
    is_pass: bool = True
    reason: str = ""
    latency_seconds: float = 0.0


@dataclass
class StepScoreRecord:
    """Collected step verdicts for one execution.

    dense_reward: mean score across all steps (0.0-1.0)
    """

    record_id: str
    task_description: str
    verdicts: list[StepVerdict] = field(default_factory=list)

    @property
    def dense_reward(self) -> float:
        if not self.verdicts:
            return 0.5
        return sum(v.score for v in self.verdicts) / len(self.verdicts)

    @property
    def pass_rate(self) -> float:
        if not self.verdicts:
            return 1.0
        return sum(1 for v in self.verdicts if v.is_pass) / len(self.verdicts)

    @property
    def min_step_score(self) -> float:
        if not self.verdicts:
            return 0.5
        return min(v.score for v in self.verdicts)


class ProcessRewardModel:
    """Step-level quality scorer using Lemonade :13305.

    Scores each intermediate step of the CompoundExecutor pipeline independently,
    yielding a dense reward signal rather than a single outcome verdict.

    HTTP calls use urllib.request for mock-patchability:
        @patch("cohezion.compound.process_reward_model.urllib.request.urlopen")

    Non-blocking by design: all errors return neutral StepVerdict(score=0.5).
    """

    def __init__(
        self,
        lemonade_url: str = LEMONADE_BASE_URL,
        model: str = "Gemma-4-E4B-it-GGUF",
        enabled: bool = True,
        timeout_seconds: float = _PRM_TIMEOUT_SECONDS,
    ) -> None:
        self.lemonade_url = lemonade_url
        self.model = model
        self.enabled = enabled
        self.timeout_seconds = timeout_seconds
        self._records: dict[str, StepScoreRecord] = {}

    def begin_execution(self, task_description: str) -> str:
        """Start a new step-score record for one executor run.

        Returns a record_id to pass into record_step() and finalize().
        """
        record_id = f"prm_{uuid.uuid4().hex[:12]}"
        self._records[record_id] = StepScoreRecord(
            record_id=record_id,
            task_description=task_description,
        )
        return record_id

    def record_step(
        self,
        record_id: str,
        step_id: str,
        step_name: str,
        step_output: str,
        expected_behavior: str,
    ) -> StepVerdict:
        """Score a pipeline step and append to the record.

        Args:
            record_id: From begin_execution().
            step_id: Pipeline step number ("3", "3.5", "7", …).
            step_name: Human label ("execute_fn", "maker_checker", "skill_refiner").
            step_output: What the step produced (truncated to 800 chars internally).
            expected_behavior: What the step was supposed to do.

        Returns:
            StepVerdict — never raises, returns neutral on error.
        """
        record = self._records.get(record_id)
        if record is None:
            logger.warning("PRM: unknown record_id %s, returning neutral verdict", record_id)
            return StepVerdict(step_id=step_id, step_name=step_name)

        verdict = self.score_step(step_id, step_name, step_output, expected_behavior)
        record.verdicts.append(verdict)
        return verdict

    def finalize(self, record_id: str) -> StepScoreRecord:
        """Return the completed record and remove it from active tracking."""
        record = self._records.pop(record_id, None)
        if record is None:
            logger.warning("PRM: finalize called on unknown record_id %s", record_id)
            return StepScoreRecord(record_id=record_id, task_description="")
        return record

    def score_step(
        self,
        step_id: str,
        step_name: str,
        step_output: str,
        expected_behavior: str,
    ) -> StepVerdict:
        """Score a single step via Lemonade :13305.

        Non-blocking: returns neutral StepVerdict(score=0.5) on any error.
        """
        if not self.enabled:
            return StepVerdict(
                step_id=step_id,
                step_name=step_name,
                score=0.5,
                is_pass=True,
                reason="prm_disabled",
            )

        t0 = time.monotonic()
        try:
            score, raw = self._call_scorer(step_output, expected_behavior)
            latency = time.monotonic() - t0
            return StepVerdict(
                step_id=step_id,
                step_name=step_name,
                score=score,
                is_pass=score >= 0.6,
                reason=raw[:200],
                latency_seconds=latency,
            )
        except Exception as exc:
            latency = time.monotonic() - t0
            logger.debug("PRM scorer failed (non-blocking): %s", exc)
            return StepVerdict(
                step_id=step_id,
                step_name=step_name,
                score=0.5,
                is_pass=True,
                reason=f"prm_error: {type(exc).__name__}",
                latency_seconds=latency,
            )

    def _call_scorer(self, step_output: str, expected_behavior: str) -> tuple[float, str]:
        """HTTP call to :13305 for step scoring. Returns (normalized_score, raw_text)."""
        user_content = f"Expected: {expected_behavior[:400]}\n\nActual output:\n{step_output[:800]}"
        payload = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": _PRM_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                "max_tokens": 8,
                "temperature": 0.0,
            }
        ).encode()

        req = urllib.request.Request(  # noqa: S310
            f"{self.lemonade_url}/v1/chat/completions",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:  # noqa: S310
            body = json.loads(resp.read())

        raw = body["choices"][0]["message"]["content"].strip()
        return self._parse_score(raw), raw

    def _parse_score(self, raw: str) -> float:
        """Extract integer 0-10 from model reply, normalize to 0.0-1.0."""
        match = re.search(r"\d+", raw)
        if not match:
            return 0.5
        value = int(match.group())
        return max(0.0, min(1.0, value / 10.0))

    @staticmethod
    def to_metrics_dict(record: StepScoreRecord) -> dict[str, Any]:
        """Return PRM metrics for insertion into CompoundExecutor metrics dict."""
        return {
            "prm_dense_reward": round(record.dense_reward, 4),
            "prm_step_count": len(record.verdicts),
            "prm_pass_rate": round(record.pass_rate, 4),
            "prm_min_step_score": round(record.min_step_score, 4),
        }


def build_process_reward_model(
    lemonade_url: str = LEMONADE_BASE_URL,
    *,
    enabled: bool = True,
    timeout_seconds: float = _PRM_TIMEOUT_SECONDS,
) -> ProcessRewardModel:
    """Build a ProcessRewardModel wired to Lemonade :13305.

    Uses Gemma-4-E4B as the scorer — always present in the Strix Halo
    :13305 catalog, fast iGPU, ctx=16384 (N3-safe), good reasoning depth
    for step quality assessment.
    """
    return ProcessRewardModel(
        lemonade_url=lemonade_url,
        enabled=enabled,
        timeout_seconds=timeout_seconds,
    )
