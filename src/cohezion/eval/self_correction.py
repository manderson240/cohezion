"""Self-correction loop for generate-test-regenerate cycles.

Implements iterative refinement with configurable retry limits,
temperature variation, timeout handling, and JourneyTracker integration.
"""

import asyncio
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from cohezion.compound.journey_tracker import JourneyTracker


logger = logging.getLogger(__name__)


@dataclass
class AttemptResult:
    """Result of a single generation attempt."""

    attempt_index: int
    solution: str
    test_results: dict[str, bool]
    all_passed: bool
    phi_score: float
    duration_seconds: float
    error: str | None = None


@dataclass
class CorrectionConfig:
    """Configuration for self-correction loop."""

    max_attempts: int = 5
    initial_temperature: float = 0.2
    temperature_increment: float = 0.2
    max_temperature: float = 1.0
    timeout_seconds: float = 30.0
    selection_strategy: str = "first_pass"  # "first_pass" | "best_score" | "best_phi"


@dataclass
class CorrectionLoopResult:
    """Result of a complete self-correction cycle."""

    final_solution: str | None
    all_passed: bool
    attempts: list[AttemptResult]
    best_phi_score: float
    total_duration_seconds: float
    selected_index: int
    error: str | None = None


class SelfCorrectionLoop:
    """Generate → Test → Regenerate cycle with phi_score tracking.

    Implements iterative solution refinement with:
    - Best-of-n selection (first passing, best score, or best phi)
    - Temperature variation across attempts
    - Configurable timeouts
    - JourneyTracker integration for FLUME trajectory monitoring

    Example:
        ```python
        loop = SelfCorrectionLoop(
            generate_fn=my_agent.generate,
            test_fn=my_agent.test,
            config=CorrectionConfig(max_attempts=3),
        )

        result = loop.run(
            problem="Implement quicksort",
            context={"task_id": "test-001"},
        )

        if result.all_passed:
            print(f"Solution found: {result.final_solution}")
        ```
    """

    def __init__(
        self,
        generate_fn: Callable[..., tuple[str, dict[str, Any]]],
        test_fn: Callable[[str], dict[str, bool]],
        config: CorrectionConfig | None = None,
        journey_tracker: JourneyTracker | None = None,
    ):
        """Initialize self-correction loop.

        Args:
            generate_fn: Function that generates a solution.
                Signature: (prompt, **params) -> (solution_str, metadata_dict)
            test_fn: Function that tests a solution.
                Signature: (solution_str) -> {test_name: passed_bool}
            config: Configuration for the loop behavior
            journey_tracker: Optional JourneyTracker for phi_score monitoring
        """
        self.generate_fn = generate_fn
        self.test_fn = test_fn
        self.config = config or CorrectionConfig()
        self.journey_tracker = journey_tracker

    def run(
        self,
        problem: str,
        context: dict[str, Any] | None = None,
        **generate_kwargs: Any,
    ) -> CorrectionLoopResult:
        """Run the self-correction loop.

        Args:
            problem: The problem description/prompt
            context: Additional context for tracking
            **generate_kwargs: Additional parameters for generate_fn

        Returns:
            CorrectionLoopResult with all attempts and final solution
        """
        context = context or {}
        attempts: list[AttemptResult] = []
        start_time = time.time()
        best_phi = 0.0

        logger.info(
            "Starting self-correction loop: max_attempts=%d, strategy=%s",
            self.config.max_attempts,
            self.config.selection_strategy,
        )

        for attempt_idx in range(self.config.max_attempts):
            temperature = min(
                self.config.initial_temperature
                + attempt_idx * self.config.temperature_increment,
                self.config.max_temperature,
            )

            logger.debug("Attempt %d: temperature=%.2f", attempt_idx + 1, temperature)

            try:
                result = self._attempt_generation(
                    problem=problem,
                    attempt_index=attempt_idx,
                    temperature=temperature,
                    timeout=self.config.timeout_seconds,
                    **generate_kwargs,
                )
            except TimeoutError:
                result = AttemptResult(
                    attempt_index=attempt_idx,
                    solution="",
                    test_results={},
                    all_passed=False,
                    phi_score=0.0,
                    duration_seconds=self.config.timeout_seconds,
                    error=f"Timeout after {self.config.timeout_seconds}s",
                )
            except Exception as e:
                result = AttemptResult(
                    attempt_index=attempt_idx,
                    solution="",
                    test_results={},
                    all_passed=False,
                    phi_score=0.0,
                    duration_seconds=time.time() - start_time,
                    error=str(e),
                )

            attempts.append(result)
            best_phi = max(best_phi, result.phi_score)

            if result.all_passed and self.config.selection_strategy == "first_pass":
                logger.info(
                    "Found passing solution at attempt %d (phi=%.3f)",
                    attempt_idx + 1,
                    result.phi_score,
                )
                break

        total_duration = time.time() - start_time

        selected = self._select_best_solution(attempts)

        logger.info(
            "Self-correction: attempts=%d, passed=%s, best_phi=%.3f, dur=%.2fs",
            len(attempts),
            selected.all_passed if selected else False,
            best_phi,
            total_duration,
        )

        return CorrectionLoopResult(
            final_solution=selected.solution if selected else None,
            all_passed=selected.all_passed if selected else False,
            attempts=attempts,
            best_phi_score=best_phi,
            total_duration_seconds=total_duration,
            selected_index=selected.attempt_index if selected else -1,
        )

    def _attempt_generation(
        self,
        problem: str,
        attempt_index: int,
        temperature: float,
        timeout: float,
        **generate_kwargs: Any,
    ) -> AttemptResult:
        """Execute a single generation attempt with timeout.

        Args:
            problem: The problem description
            attempt_index: Index of this attempt
            temperature: Temperature for generation
            timeout: Timeout in seconds
            **generate_kwargs: Additional generation parameters

        Returns:
            AttemptResult with solution, test results, and metrics
        """
        start_time = time.time()

        try:
            solution, metadata = self.generate_fn(
                problem,
                temperature=temperature,
                attempt=attempt_index,
                **generate_kwargs,
            )
        except Exception as e:
            return AttemptResult(
                attempt_index=attempt_index,
                solution="",
                test_results={},
                all_passed=False,
                phi_score=0.0,
                duration_seconds=time.time() - start_time,
                error=f"Generation error: {e}",
            )

        try:
            test_results = self.test_fn(solution)
        except Exception as e:
            return AttemptResult(
                attempt_index=attempt_index,
                solution=solution,
                test_results={},
                all_passed=False,
                phi_score=0.0,
                duration_seconds=time.time() - start_time,
                error=f"Test error: {e}",
            )

        all_passed = all(test_results.values()) if test_results else False

        phi_score = self._compute_phi_score(
            test_results=test_results,
            attempt=attempt_index,
            metadata=metadata,
        )

        duration = time.time() - start_time

        if self.journey_tracker and self.journey_tracker.get_recent_point_count() > 0:
            last_point = self.journey_tracker.get_last_point()
            if last_point:
                phi_score = (last_point.metadata or {}).get("phi_score", phi_score)

        return AttemptResult(
            attempt_index=attempt_index,
            solution=solution,
            test_results=test_results,
            all_passed=all_passed,
            phi_score=phi_score,
            duration_seconds=duration,
        )

    def _compute_phi_score(
        self,
        test_results: dict[str, bool],
        attempt: int,
        metadata: dict[str, Any],
    ) -> float:
        """Compute phi_score for an attempt.

        Args:
            test_results: Dictionary of test names to pass status
            attempt: Attempt index
            metadata: Generation metadata

        Returns:
            Phi score (0.0-1.0)
        """
        if not test_results:
            return 0.0

        pass_rate = sum(test_results.values()) / len(test_results)

        coherence = pass_rate

        smoothness = 1.0 if attempt == 0 else 0.8

        convergence = 1.0 if pass_rate > 0 else 0.5

        phi = coherence * 0.5 + smoothness * 0.3 + convergence * 0.2

        if "phi_score" in metadata:
            phi = (phi + metadata["phi_score"]) / 2

        return max(0.0, min(1.0, phi))

    def _select_best_solution(
        self,
        attempts: list[AttemptResult],
    ) -> AttemptResult | None:
        """Select the best solution based on selection strategy.

        Args:
            attempts: List of all attempt results

        Returns:
            Selected AttemptResult or None if no attempts
        """
        if not attempts:
            return None

        passing = [a for a in attempts if a.all_passed]

        if not passing:
            if self.config.selection_strategy == "best_phi":
                return max(attempts, key=lambda a: a.phi_score)
            return attempts[0]

        if self.config.selection_strategy == "first_pass":
            return passing[0]

        if self.config.selection_strategy == "best_phi":
            return max(passing, key=lambda a: a.phi_score)

        return max(passing, key=lambda a: sum(a.test_results.values()))


class AsyncSelfCorrectionLoop(SelfCorrectionLoop):
    """Async version of SelfCorrectionLoop for async generate/test functions."""

    async def run(
        self,
        problem: str,
        context: dict[str, Any] | None = None,
        **generate_kwargs: Any,
    ) -> CorrectionLoopResult:
        """Run the async self-correction loop.

        Args:
            problem: The problem description/prompt
            context: Additional context for tracking
            **generate_kwargs: Additional parameters for generate_fn

        Returns:
            CorrectionLoopResult with all attempts and final solution
        """
        context = context or {}
        attempts: list[AttemptResult] = []
        start_time = time.time()
        best_phi = 0.0

        logger.info(
            "Starting async self-correction loop: max_attempts=%d, strategy=%s",
            self.config.max_attempts,
            self.config.selection_strategy,
        )

        for attempt_idx in range(self.config.max_attempts):
            temperature = min(
                self.config.initial_temperature
                + attempt_idx * self.config.temperature_increment,
                self.config.max_temperature,
            )

            logger.debug("Attempt %d: temperature=%.2f", attempt_idx + 1, temperature)

            try:
                result = await asyncio.wait_for(
                    self._async_attempt_generation(
                        problem=problem,
                        attempt_index=attempt_idx,
                        temperature=temperature,
                        **generate_kwargs,
                    ),
                    timeout=self.config.timeout_seconds,
                )
            except TimeoutError:
                result = AttemptResult(
                    attempt_index=attempt_idx,
                    solution="",
                    test_results={},
                    all_passed=False,
                    phi_score=0.0,
                    duration_seconds=self.config.timeout_seconds,
                    error=f"Timeout after {self.config.timeout_seconds}s",
                )
            except Exception as e:
                result = AttemptResult(
                    attempt_index=attempt_idx,
                    solution="",
                    test_results={},
                    all_passed=False,
                    phi_score=0.0,
                    duration_seconds=time.time() - start_time,
                    error=str(e),
                )

            attempts.append(result)
            best_phi = max(best_phi, result.phi_score)

            if result.all_passed and self.config.selection_strategy == "first_pass":
                logger.info(
                    "Found passing solution at attempt %d (phi=%.3f)",
                    attempt_idx + 1,
                    result.phi_score,
                )
                break

        total_duration = time.time() - start_time

        selected = self._select_best_solution(attempts)

        logger.info(
            "Async self-correction: attempts=%d, passed=%s, best_phi=%.3f, dur=%.2fs",
            len(attempts),
            selected.all_passed if selected else False,
            best_phi,
            total_duration,
        )

        return CorrectionLoopResult(
            final_solution=selected.solution if selected else None,
            all_passed=selected.all_passed if selected else False,
            attempts=attempts,
            best_phi_score=best_phi,
            total_duration_seconds=total_duration,
            selected_index=selected.attempt_index if selected else -1,
        )

    async def _async_attempt_generation(
        self,
        problem: str,
        attempt_index: int,
        temperature: float,
        **generate_kwargs: Any,
    ) -> AttemptResult:
        """Execute a single async generation attempt.

        Args:
            problem: The problem description
            attempt_index: Index of this attempt
            temperature: Temperature for generation
            **generate_kwargs: Additional generation parameters

        Returns:
            AttemptResult with solution, test results, and metrics
        """
        start_time = time.time()

        try:
            solution, metadata = await self.generate_fn(
                problem,
                temperature=temperature,
                attempt=attempt_index,
                **generate_kwargs,
            )
        except Exception as e:
            return AttemptResult(
                attempt_index=attempt_index,
                solution="",
                test_results={},
                all_passed=False,
                phi_score=0.0,
                duration_seconds=time.time() - start_time,
                error=f"Generation error: {e}",
            )

        try:
            test_results = await self.test_fn(solution)
        except Exception as e:
            return AttemptResult(
                attempt_index=attempt_index,
                solution=solution,
                test_results={},
                all_passed=False,
                phi_score=0.0,
                duration_seconds=time.time() - start_time,
                error=f"Test error: {e}",
            )

        all_passed = all(test_results.values()) if test_results else False

        phi_score = self._compute_phi_score(
            test_results=test_results,
            attempt=attempt_index,
            metadata=metadata,
        )

        duration = time.time() - start_time

        if self.journey_tracker and self.journey_tracker.get_recent_point_count() > 0:
            last_point = self.journey_tracker.get_last_point()
            if last_point:
                phi_score = (last_point.metadata or {}).get("phi_score", phi_score)

        return AttemptResult(
            attempt_index=attempt_index,
            solution=solution,
            test_results=test_results,
            all_passed=all_passed,
            phi_score=phi_score,
            duration_seconds=duration,
        )
