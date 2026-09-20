"""TaskPilot Learnability Curriculum Engine with SurrealDB Graph Integration.
=============================================================================
Inspired by Microsoft Research's FrogNano technical report:
"Training a 4B Coding Agent via Online Task Synthesis"

Core Invariants:
1. Zero-Gradient Avoidance:
   - Tasks with solve_rate == 0.0 (too hard) or solve_rate == 1.0 (too easy)
     yield negligible learning signal.
2. The Learnability Frontier:
   - Tasks with 0.10 <= solve_rate <= 0.50 provide maximum policy gradient
     for compact coding agents (4B/8B scale).
3. SurrealDB Knowledge Graph Maximization:
   - Tasks are stored in `synthetic_task` table in SurrealDB (`vault` db).
   - Tasks are linked to associative `neuron` nodes via `linked_to` graph relations.
   - SurrealQL queries retrieve the active learnable frontier with zero latency.
"""

from __future__ import annotations

import base64
import json
import logging
import time
import urllib.request
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, cast


logger = logging.getLogger(__name__)


class FrontierStatus(StrEnum):
    TOO_HARD = "too_hard"  # solve_rate < 0.10
    LEARNABILITY_FRONTIER = "frontier"  # 0.10 <= solve_rate <= 0.50
    TOO_EASY = "too_easy"  # solve_rate > 0.50


@dataclass(frozen=True, slots=True)
class SyntheticTask:
    task_id: str
    title: str
    target_module: str
    prompt: str
    test_code: str
    attempts: int = 0
    successes: int = 0
    solve_rate: float = 0.0
    status: FrontierStatus = FrontierStatus.TOO_HARD
    associated_neurons: list[str] = field(default_factory=list)


class LearnabilityCurriculumEngine:
    """Manages the synthetic task curriculum and learnability frontier in SurrealDB."""

    def __init__(
        self,
        surreal_url: str = "http://localhost:8001/sql",
        min_frontier_rate: float = 0.10,
        max_frontier_rate: float = 0.50,
    ) -> None:
        self.surreal_url = surreal_url
        self.min_frontier_rate = min_frontier_rate
        self.max_frontier_rate = max_frontier_rate
        self._auth = base64.b64encode(b"root:root").decode()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        """Ensure synthetic_task and related tables exist in SurrealDB."""
        init_sql = (
            "DEFINE TABLE IF NOT EXISTS synthetic_task SCHEMALESS; "
            "DEFINE TABLE IF NOT EXISTS harness_rollout SCHEMALESS;"
        )
        self._execute_surql(init_sql)

    def _execute_surql(self, query: str) -> list[dict[str, Any]]:
        """Execute a SurrealQL query against SurrealDB vault."""
        req = urllib.request.Request(  # noqa: S310
            self.surreal_url,
            data=query.encode("utf-8"),
            headers={
                "surreal-ns": "cohezion",
                "surreal-db": "vault",
                "Authorization": f"Basic {self._auth}",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=3.0) as resp:  # noqa: S310
                if resp.status == 200:
                    from cohezion.storage.surreal_http import checked_statements

                    return checked_statements(
                        json.loads(resp.read().decode("utf-8")), status_code=resp.status
                    )
        except Exception as e:
            logger.warning("SurrealDB query failed: %s", e)
        return []

    def classify_frontier_status(self, attempts: int, successes: int) -> FrontierStatus:
        """Classify task according to the FrogNano learnability frontier rule."""
        if attempts <= 0:
            return FrontierStatus.LEARNABILITY_FRONTIER  # New candidate task
        rate = successes / attempts
        if rate < self.min_frontier_rate:
            return FrontierStatus.TOO_HARD
        elif rate > self.max_frontier_rate:
            return FrontierStatus.TOO_EASY
        return FrontierStatus.LEARNABILITY_FRONTIER

    def register_synthetic_task(
        self,
        task_id: str,
        title: str,
        target_module: str,
        prompt: str,
        test_code: str,
        associated_neurons: list[str] | None = None,
    ) -> SyntheticTask:
        """Register a new synthetic task in SurrealDB and relate it to knowledge neurons."""
        neurons = associated_neurons or []
        record_id = f"task_{task_id}"
        task_payload = {
            "task_id": task_id,
            "title": title,
            "target_module": target_module,
            "prompt": prompt,
            "test_code": test_code,
            "attempts": 0,
            "successes": 0,
            "solve_rate": 0.0,
            "status": FrontierStatus.LEARNABILITY_FRONTIER.value,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }

        surql = (
            f"DELETE synthetic_task:{record_id}; "
            f"CREATE synthetic_task:{record_id} CONTENT {json.dumps(task_payload)};"
        )
        self._execute_surql(surql)

        # Graph edge: Link knowledge neurons to synthetic task
        for n_id in neurons:
            clean_nid = n_id if ":" in n_id else f"neuron:{n_id}"
            rel_query = f"RELATE {clean_nid}->evaluates->synthetic_task:{record_id};"
            self._execute_surql(rel_query)

        return SyntheticTask(
            task_id=task_id,
            title=title,
            target_module=target_module,
            prompt=prompt,
            test_code=test_code,
            attempts=0,
            successes=0,
            solve_rate=0.0,
            status=FrontierStatus.LEARNABILITY_FRONTIER,
            associated_neurons=neurons,
        )

    def record_rollout_result(self, task_id: str, passed: bool) -> SyntheticTask | None:
        """Update attempts, successes, solve rate, and frontier status in SurrealDB."""
        record_id = f"task_{task_id}"
        query = f"SELECT * FROM synthetic_task:{record_id};"
        res = self._execute_surql(query)

        if not res or not isinstance(res[0].get("result"), list) or not res[0]["result"]:
            logger.warning("Task %s not found in SurrealDB", task_id)
            return None

        task_data = res[0]["result"][0]
        attempts = task_data.get("attempts", 0) + 1
        successes = task_data.get("successes", 0) + (1 if passed else 0)
        solve_rate = round(successes / attempts, 4)
        new_status = self.classify_frontier_status(attempts, successes)

        update_query = (
            f"UPDATE synthetic_task:{record_id} SET "
            f"attempts = {attempts}, successes = {successes}, "
            f"solve_rate = {solve_rate}, status = '{new_status.value}';"
        )
        self._execute_surql(update_query)

        return SyntheticTask(
            task_id=task_id,
            title=task_data.get("title", ""),
            target_module=task_data.get("target_module", ""),
            prompt=task_data.get("prompt", ""),
            test_code=task_data.get("test_code", ""),
            attempts=attempts,
            successes=successes,
            solve_rate=solve_rate,
            status=new_status,
        )

    def query_active_frontier_tasks(self, limit: int = 10) -> list[dict[str, Any]]:
        """Retrieve tasks strictly on the learnability frontier (0.10 <= solve_rate <= 0.50)."""
        surql = (
            f"SELECT * FROM synthetic_task "
            f"WHERE status = '{FrontierStatus.LEARNABILITY_FRONTIER.value}' "
            f"ORDER BY created_at DESC LIMIT {limit};"
        )
        res = self._execute_surql(surql)
        if res and res[0].get("result"):
            return cast("list[dict[str, Any]]", res[0]["result"])
        return []
