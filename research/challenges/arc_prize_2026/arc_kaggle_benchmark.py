import json
import os
import time
import numpy as np
from arc_agi2_evaluator import ARCAGI2Evaluator

class ARCKaggleBenchmark:
    """Benchmark tool for ARC-AGI-2 tasks."""
    def __init__(self, data_dir="data/arc-agi-2-repo/data/training"):
        self.evaluator = ARCAGI2Evaluator(data_dir=data_dir)
        self.data_dir = data_dir
        
    def run_benchmark(self, limit=10):
        print(f"Running ARC-AGI-2 benchmark on {limit} tasks...")
        task_files = sorted(os.listdir(self.data_dir))[:limit]
        
        results = []
        for filename in task_files:
            task_id = filename.split('.')[0]
            start_time = time.time()
            try:
                prediction = self.evaluator.solve_task(task_id)
                duration = time.time() - start_time
                
                # Check accuracy (placeholder for real logic)
                # In ARC-AGI-2, we compare the predicted grid with the solution
                task = self.evaluator.load_task(task_id)
                ground_truth = task['test'][0]['output']
                
                is_correct = self._compare_grids(prediction, ground_truth)
                
                results.append({
                    "task_id": task_id,
                    "is_correct": is_correct,
                    "duration": duration
                })
                print(f"  Task {task_id}: {'PASSED' if is_correct else 'FAILED'} ({duration:.2f}s)")
            except Exception as e:
                print(f"  Task {task_id}: ERROR ({e})")
                
        self._summarize(results)

    def _compare_grids(self, g1, g2):
        return np.array_equal(np.array(g1), np.array(g2))

    def _summarize(self, results):
        total = len(results)
        passed = sum(1 for r in results if r['is_correct'])
        avg_time = sum(r['duration'] for r in results) / total if total > 0 else 0
        
        print("\n--- Benchmark Summary ---")
        print(f"Total Tasks: {total}")
        print(f"Passed:      {passed}")
        print(f"Accuracy:    {(passed/total)*100:.2f}%")
        print(f"Avg Time:    {avg_time:.2f}s")

if __name__ == "__main__":
    benchmark = ARCKaggleBenchmark()
    benchmark.run_benchmark(limit=5)
