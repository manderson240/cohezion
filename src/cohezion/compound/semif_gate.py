"""SemIf/OpenJev 0.8B content veto for AutoDQA.

Why a veto and not a scorer: measured 2026-09-22 on the 114 adjudicated DQA cases
(`research/20260922-semif-laya-vs-von-dqa.md`), SemIf scored AUROC 0.977 / Brier 0.089 where Von
scored 0.688 and the production AutoDQA gate 0.537 -- and raw output LENGTH alone scores 0.829 on
that set, so only SemIf is clearly above the trivial baseline. On the same set, rejecting at
p < 0.3 loses 0 true answers and catches 68% of non-answers.

Why out-of-process: the checkpoint is `qwen3_5`, which the repo's transformers (4.57) does not
recognise. Bumping transformers to 5.x would move the torch/ROCm pins under the whole suite, so the
model is served by `scripts/ops/semif_dqa_server.py` from its own venv and reached over HTTP.

Contract (it sits in the executor's path):
  - never raises; any failure returns None and the caller leaves the verdict untouched (fail-open)
  - hard timeout, plus a circuit breaker so a hung service costs one timeout per BREAKER_SECONDS
    rather than one per evaluation
"""

from __future__ import annotations

import json
import os
import time
import urllib.request
from pathlib import Path


SEMIF_URL = os.environ.get("COHEZION_SEMIF_URL", "http://127.0.0.1:13399/score")
SEMIF_TIMEOUT_S = float(os.environ.get("COHEZION_SEMIF_TIMEOUT", "2.0"))
# t=0.3: on the measured set, 0 true answers lost, 68% of non-answers caught. t=0.5 also lost none
# but was chosen against; 0.3 keeps margin from the value the same data selected.
VETO_THRESHOLD = float(os.environ.get("COHEZION_SEMIF_THRESHOLD", "0.3"))
BREAKER_SECONDS = 120.0
_BREAKER = Path(os.environ.get("TMPDIR", "/tmp")) / "cohezion_semif_down"


def semif_p_yes(task_description: str, output: str, timeout: float | None = None) -> float | None:
    """P(the RESPONSE answers the TASK), or None when the judge is unavailable.

    None means UNKNOWN, never 0.0 -- conflating them would turn a transport fault into a
    confident rejection.
    """
    try:
        if time.time() - _BREAKER.stat().st_mtime < BREAKER_SECONDS:
            return None
    except OSError:
        pass
    body = json.dumps({"task": task_description, "response": output}).encode()
    req = urllib.request.Request(SEMIF_URL, body, {"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout or SEMIF_TIMEOUT_S) as r:
            p = json.load(r)["p"]
        return float(p)
    except Exception:
        try:
            _BREAKER.touch()
        except OSError:
            pass
        return None


def semif_veto(
    task_description: str,
    output: str,
    scorer=semif_p_yes,
    threshold: float | None = None,
) -> tuple[bool, float | None]:
    """(veto?, p). veto is True only when the judge answered AND was confidently negative."""
    p = scorer(task_description, output)
    if p is None:
        return False, None
    return p < (VETO_THRESHOLD if threshold is None else threshold), p
