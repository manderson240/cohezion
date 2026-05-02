import json
import os
import shutil
from datetime import datetime

import polars as pl
from knowledge_graft import KnowledgeGraft
from swarm_driver import run_simulation


class MathResearchHarness:
    """
    Abstracted Research Orchestrator inspired by karpathy/autoresearch.
    Manages the lifecycle of reasoning experiments.
    """

    def __init__(self):
        self.log_file = "research_results.tsv"
        self.prompt_file = "specialist_prompts.json"
        self.backup_dir = "backups"
        os.makedirs(self.backup_dir, exist_ok=True)
        self.grafter = KnowledgeGraft()

        if not os.path.exists(self.log_file):
            with open(self.log_file, "w") as f:
                f.write("timestamp\thypothesis\taccuracy\tstability\tbest\n")

    def backup_config(self, label: str):
        shutil.copy(self.prompt_file, f"{self.backup_dir}/prompts_{label}.json")

    def restore_config(self, label: str):
        shutil.copy(f"{self.backup_dir}/prompts_{label}.json", self.prompt_file)

    def log_result(self, hypothesis: str, accuracy: float, stability: float, is_best: bool):
        timestamp = datetime.now().isoformat()
        with open(self.log_file, "a") as f:
            f.write(f"{timestamp}\t{hypothesis}\t{accuracy}\t{stability}\t{is_best}\n")

        # Compound Engineering: Graft winning strategies into skills
        if is_best:
            self.grafter.graft_winning_strategy(hypothesis, accuracy)

    def run_experiment(self, hypothesis: str):
        print(f"\n[RESEARCH] Running Experiment: {hypothesis}")
        log_path = f"logs/experiment_{int(time.time())}.log"
        os.makedirs("logs", exist_ok=True)

        try:
            import sys
            from io import StringIO

            # Capture stdout
            old_stdout = sys.stdout
            redirected_output = StringIO()
            sys.stdout = redirected_output

            try:
                accuracy, stability = run_simulation()
            finally:
                sys.stdout = old_stdout

            output_text = redirected_output.getvalue()
            with open(log_path, "w") as f:
                f.write(f"Hypothesis: {hypothesis}\n")
                f.write(f"Accuracy: {accuracy}, Stability: {stability}\n")
                f.write("-" * 40 + "\n")
                f.write(output_text)

            return accuracy, stability
        except Exception as e:
            print(f"[RESEARCH] Experiment Failed: {e!s}")
            return 0.0, 0.0

    def propose_mutation(self, current_prompts: dict):
        """
        Uses a high-reasoning model to analyze recent results and propose a mutation.
        """
        # Read the last few results to provide context
        history = ""
        if os.path.exists(self.log_file):
            df = pl.read_csv(self.log_file, separator="\t")
            history = df.tail(5).collect().to_string()

        # We'll use our local 'Thinker' model (deepseek-r1:7b) to propose the mutation
        # This is the "Lead Researcher" role
        ollama_url = "http://localhost:11434/api/chat"
        system_prompt = "You are the Lead Research Director for an AIMO reasoning swarm. Your goal is to mutate the specialist prompts to maximize accuracy."
        user_prompt = f"""
Current Specialist Prompts:
{json.dumps(current_prompts, indent=2)}

Recent Research History:
{history}

Based on the failures and successes above, propose a specific improvement to the prompts.
Focus on ONE architectural change (e.g. better chain-of-thought, tool usage, or verification).
Output the new full prompts JSON only.
"""
        try:
            payload = {
                "model": "deepseek-r1:7b",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "options": {"temperature": 0.7},
            }
            import requests

            response = requests.post(ollama_url, json=payload, timeout=120)
            response.raise_for_status()
            res_json = response.json()
            raw_content = res_json.get("message", {}).get("content", "")

            # Extract JSON from CoT response
            import re

            json_match = re.search(r"\{.*\}", raw_content, re.DOTALL)
            if json_match:
                new_prompts = json.loads(json_match.group(0))
                # Generate a short description for the hypothesis
                desc_payload = {
                    "model": "phi4:latest",
                    "prompt": f"Summarize this logic change in 10 words: {raw_content[:500]}",
                    "stream": False,
                }
                desc_res = requests.post(
                    "http://localhost:11434/api/generate", json=desc_payload, timeout=30
                )
                mutation_desc = desc_res.json().get("response", "LLM-driven mutation").strip()
                return new_prompts, mutation_desc
        except Exception as e:
            print(f"[HARNESS] LLM mutation failed: {e!s}")

        # Fallback to simple mutation if LLM fails
        new_prompts = current_prompts.copy()
        for s in new_prompts:
            new_prompts[s] += " Refine logic for better clarity."
        return new_prompts, "Fallback: Basic refinement."


if __name__ == "__main__":
    harness = MathResearchHarness()

    # 1. Baseline Run
    print("Establishing Baseline...")
    acc, stab = harness.run_experiment("Baseline Configuration")
    harness.log_result("Baseline", acc, stab, True)
    harness.backup_config("best")

    # 2. Start Loop
    # In a real overnight run, this would loop and use an LLM to evolve the prompts.
    # We'll set up the infrastructure so the Lead Agent can take over.
    with open("specialist_prompts.json") as f:
        current_prompts = json.load(f)

    mutated_prompts, hypothesis = harness.propose_mutation(current_prompts)

    with open("specialist_prompts.json", "w") as f:
        json.dump(mutated_prompts, f, indent=2)

    new_acc, new_stab = harness.run_experiment(hypothesis)

    is_best = new_acc > acc
    harness.log_result(hypothesis, new_acc, new_stab, is_best)

    if is_best:
        print("Success! New best configuration found.")
        harness.backup_config("best")
    else:
        print("Experiment failed to improve baseline. Reverting.")
        harness.restore_config("best")
