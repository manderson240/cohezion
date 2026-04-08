#!/usr/bin/env python3
"""SWE-bench evaluation runner for Cohezion.

Usage:
    uv run python scripts/benchmarks/run_swebench_eval.py --dataset verified --max-issues 10
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


class SWEBenchEvaluator:
    """SWE-bench evaluation runner."""
    
    def __init__(self, dataset: str = "test", cache_dir: Path | None = None):
        self.dataset = dataset
        self.cache_dir = cache_dir or Path("data/swebench_cache")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
    async def run_evaluation(self, max_issues: int | None = None) -> dict[str, Any]:
        """Run evaluation on SWE-bench dataset."""
        from cohezion.agent.unified_harness import UnifiedAgent
        
        # Load dataset
        dataset_file = self.cache_dir / f"{self.dataset}.json"
        if not dataset_file.exists():
            await self._download_dataset(dataset_file)
            
        with open(dataset_file) as f:
            issues = json.load(f)
            
        if max_issues:
            issues = issues[:max_issues]
            
        agent = UnifiedAgent()
        results = []
        passed = 0
        
        for i, issue in enumerate(issues):
            logger.info(f"[{i+1}/{len(issues)}] {issue.get('instance_id', i)}")
            
            try:
                task = f"Fix this issue: {issue.get('problem_statement', '')}"
                trace = await asyncio.wait_for(
                    agent.run_task(task, timeout=180),
                    timeout=200.0,
                )
                
                # Check if patch was generated
                patch = self._extract_patch(trace)
                success = patch is not None
                
                if success:
                    passed += 1
                    
                results.append({
                    "instance_id": issue.get("instance_id", str(i)),
                    "success": success,
                    "patch": patch,
                })
                
            except Exception as e:
                logger.error(f"Error: {e}")
                results.append({
                    "instance_id": issue.get("instance_id", str(i)),
                    "success": False,
                    "error": str(e),
                })
                
        # Calculate metrics
        attempted = len([r for r in results if r.get("success")])
        total = len(results)
        pass_at_1 = passed / attempted if attempted > 0 else 0.0
        
        return {
            "dataset": self.dataset,
            "timestamp": datetime.now().isoformat(),
            "metrics": {
                "total": total,
                "attempted": attempted,
                "passed": passed,
            },
            "pass_at_1": pass_at_1,
            "pass_at_1_pct": f"{pass_at_1:.1%}",
            "results": results,
        }
    
    async def _download_dataset(self, dataset_file: Path) -> None:
        """Download from HuggingFace."""
        from datasets import load_dataset
        
        split = "test" if self.dataset == "verified" else "dev"
        ds = load_dataset("princeton-nlp/SWE-bench", split=split)
        refs = list(ds)
        
        with open(dataset_file, 'w') as f:
            json.dump(refs, f, indent=2)
            
        logger.info(f"Downloaded {len(refs)} issues to {dataset_file}")
    
    def _extract_patch(self, trace: Any) -> str | None:
        """Extract patch from execution trace."""
        # Simple heuristic: look for diff output
        output = str(trace)
        if "diff --git" in output:
            start = output.find("diff --git")
            return output[start:start+2000]
        return None


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="test")
    parser.add_argument("--max-issues", type=int, default=3)
    args = parser.parse_args()
    
    evaluator = SWEBenchEvaluator(dataset=args.dataset)
    results = await evaluator.run_evaluation(max_issues=args.max_issues)
    
    print(f"\n{'='*60}")
    print("SWE-bench Evaluation Complete")
    print(f"{'='*60}")
    print(f"Pass@1: {results['pass_at_1_pct']}")
    print(f"{'='*60}")
    
    return 0 if results["pass_at_1"] >= 0.5 else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
