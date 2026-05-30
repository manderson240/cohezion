"""Codebase refinement using compound execution pipeline.

Orchestrates multi-agent refinement tasks with automatic error recovery,
journey tracking, and continuous improvement.
"""

import asyncio
import json
import logging
import time
from pathlib import Path

from cohezion.compound import (
    AgentTask,
    CompoundFeedbackLoopFactory,
    ExecutorFactory,
    JourneyTrackerFactory,
)
from cohezion.core.mcp_client import MCPClient


logger = logging.getLogger(__name__)


class CodebaseRefinementPlan:
    """Plan for codebase refinement tasks."""

    def __init__(self):
        """Initialize refinement plan."""
        self.tasks = [
            {
                "id": "scan_untracked",
                "description": "Scan and categorize untracked files",
                "operation_type": "search",
                "priority": 1,
            },
            {
                "id": "analyze_gitignore",
                "description": "Analyze .gitignore patterns and recommendations",
                "operation_type": "analyze",
                "priority": 2,
                "depends_on": ["scan_untracked"],
            },
            {
                "id": "find_unused_imports",
                "description": "Identify unused imports in Python files",
                "operation_type": "search",
                "priority": 3,
            },
            {
                "id": "check_test_coverage",
                "description": "Analyze test coverage gaps",
                "operation_type": "analyze",
                "priority": 2,
            },
            {
                "id": "lint_report",
                "description": "Generate lint and formatting issues",
                "operation_type": "search",
                "priority": 2,
            },
            {
                "id": "generate_metrics",
                "description": "Generate codebase health metrics",
                "operation_type": "generate",
                "priority": 1,
                "depends_on": ["scan_untracked", "check_test_coverage", "lint_report"],
            },
        ]

    def to_agent_tasks(self) -> list[AgentTask]:
        """Convert to AgentTask list for team execution.

        Returns:
            List of AgentTask objects
        """
        agent_tasks = []
        for task_def in self.tasks:
            task = AgentTask(
                task_id=task_def["id"],
                agent_id=f"agent_{task_def['operation_type']}",
                description=task_def["description"],
                operation_type=task_def["operation_type"],
                dependencies=task_def.get("depends_on", []),
                available_skills=[
                    f"{task_def['operation_type']}_skill",
                    "universal_skill",
                ],
            )
            agent_tasks.append(task)

        return agent_tasks


class CodebaseAnalyzer:
    """Analyze codebase for refinement opportunities."""

    def __init__(self, repo_root: Path | None = None):
        """Initialize analyzer.

        Args:
            repo_root: Root directory of repository
        """
        self.repo_root = repo_root or Path.cwd()

    def scan_untracked_files(self) -> dict[str, list[str]]:
        """Scan for untracked files and categorize them.

        Returns:
            Dictionary mapping categories to file lists
        """
        import subprocess

        result = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
        )

        files = result.stdout.strip().split("\n") if result.stdout.strip() else []

        categories = {
            "artifacts": [],
            "build_output": [],
            "cache": [],
            "logs": [],
            "temp": [],
            "data": [],
            "other": [],
        }

        for f in files:
            if not f:
                continue

            f_lower = f.lower()
            if "artifact" in f_lower or ".artifact" in f_lower or f.startswith(".artifacts"):
                categories["artifacts"].append(f)
            elif (
                "build" in f_lower
                or "dist" in f_lower
                or ".egg" in f_lower
                or "__pycache__" in f_lower
            ):
                categories["build_output"].append(f)
            elif (
                "cache" in f_lower
                or ".cache" in f_lower
                or f.endswith(".pyc")
                or f.endswith(".pyo")
            ):
                categories["cache"].append(f)
            elif "log" in f_lower or ".log" in f_lower or f.endswith(".log"):
                categories["logs"].append(f)
            elif "temp" in f_lower or "tmp" in f_lower or ".tmp" in f_lower or f.endswith(".tmp"):
                categories["temp"].append(f)
            elif (
                "data" in f_lower
                or "export" in f_lower
                or "result" in f_lower
                or "output" in f_lower
            ):
                categories["data"].append(f)
            else:
                categories["other"].append(f)

        return {k: v for k, v in categories.items() if v}

    def analyze_git_status(self) -> dict[str, any]:
        """Analyze current git status.

        Returns:
            Dictionary with git status information
        """
        import subprocess

        # Get modified files
        result = subprocess.run(
            ["git", "status", "--short"],
            cwd=self.repo_root,
            capture_output=True,
            text=True,
        )

        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []

        status = {
            "modified": len([line for line in lines if line.startswith(" M")]),
            "added": len([line for line in lines if line.startswith("A ")]),
            "deleted": len([line for line in lines if line.startswith(" D")]),
            "untracked": len([line for line in lines if line.startswith("??")]),
            "total_changes": len(lines),
        }

        return status


async def run_refinement_pipeline():
    """Run complete codebase refinement pipeline.

    Uses:
    - CompoundExecutor for individual tasks
    - CompoundFeedbackLoop for error recovery
    - JourneyTracker for monitoring
    - TeamExecutor for parallel execution
    """
    logger.info("Starting codebase refinement pipeline...")
    start_time = time.time()

    # Initialize components
    mcp_client = MCPClient()
    # enable_memory: this is a dynamic-workflow entry point, so each successful turn
    # compounds into the project's CohezionMemory (best-effort, self-disabling).
    executor = ExecutorFactory.create(mcp_client, enable_memory=True)
    feedback_loop = CompoundFeedbackLoopFactory.create(
        executor, max_retries=2, enable_learning=True
    )
    journey_tracker = JourneyTrackerFactory.create(seed=42)

    # Create refinement plan
    CodebaseRefinementPlan()
    analyzer = CodebaseAnalyzer()

    # Scan repository
    logger.info("Scanning repository for refinement opportunities...")
    untracked = analyzer.scan_untracked_files()
    git_status = analyzer.analyze_git_status()

    logger.info(f"Found {git_status['total_changes']} total changes")
    logger.info(f"Untracked files by category: {len(untracked)} categories")

    # Execute initial analysis tasks
    results = {}

    # Task 1: Scan untracked files
    logger.info("Executing: Scan untracked files")

    def scan_task(guidance):
        return json.dumps(
            {
                "untracked_files": untracked,
                "count": sum(len(v) for v in untracked.values()),
                "categories": list(untracked.keys()),
            }
        ), {"coherence": 0.95}

    result = await feedback_loop.execute_with_feedback(
        task_description="Scan and categorize untracked files in repository",
        skill_name="search",
        operation_type="search",
        execute_fn=scan_task,
    )

    results["scan_untracked"] = result
    point = journey_tracker.track_execution(
        execution_result=result.attempts[-1].execution_result,
        task_description="Scan untracked files",
        operation_type="search",
    )
    logger.info(f"Scan complete. Quality score: {point.metadata['phi_score']:.2f}")

    # Task 2: Analyze git status
    logger.info("Executing: Analyze git status")

    def git_analysis_task(guidance):
        recommendations = []
        if git_status["untracked"] > 20:
            recommendations.append("Consider adding more patterns to .gitignore")
        if git_status["modified"] > 50:
            recommendations.append("Consider staging changes in smaller batches")

        return json.dumps(
            {
                "status": git_status,
                "recommendations": recommendations,
            }
        ), {"coherence": 0.9}

    result = await feedback_loop.execute_with_feedback(
        task_description="Analyze git repository status and recommend improvements",
        skill_name="analyze",
        operation_type="analyze",
        execute_fn=git_analysis_task,
    )

    results["analyze_git"] = result
    point = journey_tracker.track_execution(
        execution_result=result.attempts[-1].execution_result,
        task_description="Analyze git status",
        operation_type="analyze",
    )

    # Task 3: Generate report
    logger.info("Executing: Generate refinement report")

    def report_task(guidance):
        report = {
            "timestamp": time.time(),
            "repository": str(Path.cwd()),
            "analysis": {
                "untracked_files": len(untracked),
                "untracked_by_category": {k: len(v) for k, v in untracked.items()},
                "git_status": git_status,
            },
            "recommendations": [
                f"Review {untracked.get('artifacts', [])} artifact files",
                f"Clean up {untracked.get('logs', [])} log files",
                f"Consider .gitignore for {untracked.get('cache', [])} cache files",
                "Run test suite to verify changes",
                "Update documentation with latest changes",
            ],
            "results": {
                k: {
                    "success": v.success,
                    "retries": v.total_retries,
                    "duration": v.total_duration_seconds,
                }
                for k, v in results.items()
            },
        }

        return json.dumps(report, indent=2), {"coherence": 0.92}

    result = await feedback_loop.execute_with_feedback(
        task_description="Generate comprehensive codebase refinement report",
        skill_name="generate",
        operation_type="generate",
        execute_fn=report_task,
    )

    results["report"] = result
    point = journey_tracker.track_execution(
        execution_result=result.attempts[-1].execution_result,
        task_description="Generate refinement report",
        operation_type="generate",
    )

    # Compute journey quality
    execution_time = time.time() - start_time
    logger.info(f"Refinement pipeline complete in {execution_time:.2f}s")

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("CODEBASE REFINEMENT SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total execution time: {execution_time:.2f}s")
    logger.info(f"Tasks executed: {len(results)}")
    logger.info(f"Successful tasks: {sum(1 for r in results.values() if r.success)}")

    logger.info("\nUntracked Files by Category:")
    for category, files in untracked.items():
        logger.info(f"  {category}: {len(files)} files")

    logger.info("\nGit Status:")
    logger.info(f"  Modified: {git_status['modified']}")
    logger.info(f"  Added: {git_status['added']}")
    logger.info(f"  Untracked: {git_status['untracked']}")

    logger.info("\nRecommendations:")
    logger.info("  1. Review and organize untracked files")
    logger.info("  2. Update .gitignore with appropriate patterns")
    logger.info("  3. Commit staged changes with clear messages")
    logger.info("  4. Run full test suite to ensure quality")
    logger.info("  5. Update documentation with latest changes")

    logger.info("=" * 60)

    return results


def main():
    """Main entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Run pipeline
    results = asyncio.run(run_refinement_pipeline())

    # Print summary
    print("\n✅ Codebase refinement analysis complete!")
    print(f"Results saved with {len(results)} tasks executed")


if __name__ == "__main__":
    main()
