"""
Async Workflow Orchestrator.

Complete async communication workflow:
1. Check Google Keep for tasks
2. Execute tasks autonomously
3. Update Keep with results
4. Send email notification

Usage at session start:
    python -m cohezion.mcp.async_workflow check
    python -m cohezion.mcp.async_workflow run
"""

import argparse
import asyncio
import json
import logging
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from cohezion.mcp.keep_integration import get_task_queue, Task
from cohezion.mcp.email_notifier import notify_completion

logger = logging.getLogger(__name__)


class AsyncWorkflowOrchestrator:
    """
    Orchestrates async task execution from Keep.
    """
    
    # Task handlers - maps task keywords to functions
    TASK_HANDLERS = {
        "simulate": "run_simulation",
        "simulation": "run_simulation",
        "debate": "run_debate",
        "analyze": "run_analysis",
        "audit": "run_audit",
        "deploy": "run_deploy",
        "test": "run_tests",
    }
    
    def __init__(self):
        self.results: list[dict] = []
        self.output_dir = Path("src/cohezion/knowledge_graph/universe_nodes/workflows")
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    async def check_queue(self) -> dict:
        """Check and report task queue."""
        queue, source = await get_task_queue()
        
        report = {
            "source": queue.source,
            "fetched_at": queue.fetched_at,
            "total_tasks": len(queue.tasks),
            "pending": len(queue.pending()),
            "tasks": [
                {"title": t.title, "priority": t.priority, "status": t.status}
                for t in queue.tasks
            ],
        }
        
        logger.info(f"Queue: {report['pending']} pending tasks from {report['source']}")
        return report
    
    def classify_task(self, task: Task) -> str:
        """Classify task to determine handler."""
        title_lower = task.title.lower()
        
        for keyword, handler in self.TASK_HANDLERS.items():
            if keyword in title_lower:
                return handler
        
        return "run_generic"
    
    async def execute_task(self, task: Task) -> dict:
        """Execute a single task."""
        handler_name = self.classify_task(task)
        handler = getattr(self, handler_name, self.run_generic)
        
        logger.info(f"Executing: {task.title} -> {handler_name}")
        
        start = datetime.now(UTC)
        try:
            result = await handler(task)
            status = "success"
        except Exception as e:
            result = {"error": str(e)}
            status = "failed"
            logger.error(f"Task failed: {e}")
        
        duration = (datetime.now(UTC) - start).total_seconds()
        
        return {
            "task": task.title,
            "handler": handler_name,
            "status": status,
            "duration_seconds": duration,
            "result": result,
        }
    
    async def run_simulation(self, task: Task) -> dict:
        """Run simulation task."""
        from cohezion.swarm.mass_simulator import run_mass_simulation
        
        # Parse count from task title
        import re
        match = re.search(r'(\d+)', task.title)
        count = int(match.group(1)) if match else 100
        count = min(count, 100000)  # Safety cap
        
        result = run_mass_simulation(count)
        return result.to_dict()
    
    async def run_debate(self, task: Task) -> dict:
        """Run debate task."""
        from cohezion.swarm.democratic_debate import run_improvement_debate
        
        session = await run_improvement_debate()
        return session.final_consensus or {}
    
    async def run_analysis(self, task: Task) -> dict:
        """Run analysis task."""
        from cohezion.learning.semantic_analyzer import run_semantic_analysis
        
        analysis = run_semantic_analysis()
        return {
            "nodes_analyzed": analysis.nodes_analyzed,
            "clusters": len(analysis.clusters),
            "gaps": [g.area for g in analysis.capability_gaps],
        }
    
    async def run_audit(self, task: Task) -> dict:
        """Run platform audit."""
        from cohezion.healing.platform_audit import run_audit, print_audit
        
        audit = run_audit("async")
        return audit.summary
    
    async def run_deploy(self, task: Task) -> dict:
        """Placeholder for deploy task."""
        return {"status": "deploy requires manual confirmation"}
    
    async def run_tests(self, task: Task) -> dict:
        """Run tests."""
        import subprocess
        
        result = subprocess.run(
            ["uv", "run", "pytest", "tests/", "-q", "--tb=no"],
            capture_output=True, text=True, timeout=60
        )
        
        return {
            "passed": "passed" in result.stdout,
            "output": result.stdout[-200:],
        }
    
    async def run_generic(self, task: Task) -> dict:
        """Generic task handler."""
        return {"message": f"Task '{task.title}' acknowledged but no specific handler found"}
    
    async def run_all_pending(self, notify: bool = True) -> list[dict]:
        """Execute all pending tasks."""
        queue, source = await get_task_queue()
        pending = queue.pending()
        
        if not pending:
            logger.info("No pending tasks")
            return []
        
        logger.info(f"Executing {len(pending)} pending tasks")
        
        for task in pending:
            result = await self.execute_task(task)
            self.results.append(result)
            
            # Mark complete if supported
            if hasattr(source, 'mark_complete'):
                await source.mark_complete(task) if asyncio.iscoroutinefunction(source.mark_complete) else source.mark_complete(task)
            
            # Notify per task
            if notify and result["status"] == "success":
                summary = json.dumps(result["result"], indent=2)[:500]
                await notify_completion(task.title, summary)
        
        # Save workflow results
        self._save_results()
        
        return self.results
    
    def _save_results(self):
        """Save workflow results."""
        output_file = self.output_dir / f"workflow_{int(datetime.now().timestamp())}.json"
        with open(output_file, "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        logger.info(f"Results saved to {output_file}")


async def main():
    parser = argparse.ArgumentParser(description="Cohezion Async Workflow")
    parser.add_argument("command", choices=["check", "run"], help="Command to execute")
    parser.add_argument("--no-notify", action="store_true", help="Disable email notifications")
    args = parser.parse_args()
    
    orchestrator = AsyncWorkflowOrchestrator()
    
    if args.command == "check":
        report = await orchestrator.check_queue()
        print(json.dumps(report, indent=2))
    
    elif args.command == "run":
        results = await orchestrator.run_all_pending(notify=not args.no_notify)
        print(f"Completed {len(results)} tasks")
        for r in results:
            print(f"  - {r['task']}: {r['status']}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")
    asyncio.run(main())
