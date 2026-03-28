import os
import sys
import json
import time
import pandas as pd
from typing import Dict, Any

# Add official classes to path
sys.path.append(os.path.join(os.getcwd(), "sandbox/aimo/input"))
from kaggle_evaluation.aimo_3_inference_server import AIMO3InferenceServer

# Import our local components
from swarm_coordinator import SwarmCoordinator
from base_specialist import BaseSpecialist
from knower_auditor import KnowerAuditor

class ProductionSwarm:
    def __init__(self):
        self.coordinator = SwarmCoordinator()
        self.auditor = KnowerAuditor()
        self.start_time = time.time()
        self.problems_solved = 0
        self.total_time_limit = 5 * 3600 # 5 hours

    def predict(self, test_df: pd.DataFrame) -> int:
        """
        The core prediction function required by AIMO3InferenceServer.
        """
        problem_id = test_df.iloc[0]['id']
        problem_text = test_df.iloc[0]['problem']
        
        # 1. Telemetry & Time Budgeting
        elapsed = time.time() - self.start_time
        remaining_time = self.total_time_limit - elapsed
        remaining_problems = 110 - self.problems_solved
        time_per_problem = remaining_time / max(1, remaining_problems)
        
        print(f"\n[Problem {self.problems_solved+1}/110] Time Budget: {time_per_problem:.1f}s")

        # 2. Plan the Journey
        task = self.coordinator.plan_journey(problem_id, problem_text)
        
        # 3. Dual-Run Execution (Adversarial TDD)
        # We'll use Cloud Specialists during development for speed
        run_results = []
        reasoning_chains = []
        
        for run_id in [1, 2]:
            # Use Gemini 2.0 Flash for dev speed
            # In production, this would be a local vLLM call to DeepSeek-R1-70B
            specialist = BaseSpecialist(task.assigned_specialists[0], model_name="gemini-2.0-flash")
            response = specialist.solve(problem_text)
            answer = specialist.extract_answer(response)
            run_results.append(answer)
            reasoning_chains.append(response)
            
        # 4. Knower Audit
        audit = self.auditor.audit_runs(run_results, reasoning_chains)
        final_answer = audit['final_answer']
        
        self.problems_solved += 1
        return int(final_answer)

def main():
    swarm = ProductionSwarm()
    server = AIMO3InferenceServer(swarm.predict)
    
    # Check if we are in rerun mode
    if os.getenv('KAGGLE_IS_COMPETITION_RERUN'):
        server.serve()
    else:
        # Run local gateway against downloaded test.csv
        test_csv = os.path.abspath("sandbox/aimo/input/test.csv")
        print(f"Running local gateway against: {test_csv}")
        server.run_local_gateway((test_csv,))

if __name__ == "__main__":
    main()
