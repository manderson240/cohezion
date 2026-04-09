import gc
import json
import math
import os
import re
import subprocess
import sys
import time
import traceback
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import numpy as np
import polars as pl
import sympy
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# --- 1. PRE-FLIGHT TDD SUITE ---
class PreFlightJury:
    @staticmethod
    def run_all():
        print("=== 🛡️ INITIALIZING FORTRESS PRE-FLIGHT TESTS (v42) ===")
        results = {"gpu": PreFlightJury.test_gpu(), "libs": PreFlightJury.test_libs(), "symbolic": PreFlightJury.test_symbolic()}
        print(f"Test Results: {results}")
        return all(results.values())

    @staticmethod
    def test_gpu():
        try:
            print(f"GPU Check: {torch.cuda.get_device_name(0)}")
            return torch.cuda.is_available()
        except: return False

    @staticmethod
    def test_libs():
        try:
            import transformers, polars
            return True
        except: return False

    @staticmethod
    def test_symbolic():
        try:
            x = sympy.symbols("x")
            res = sympy.solve(x**2 - 4, x)
            return len(res) == 2
        except: return False

# --- 2. Specialist Swarm (Triune Manifold) ---
class specialist_team:
    def __init__(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer
        self.specialists = {
            "Algebraist": "Solve via SymPy and Python code. Final answer in \\boxed{X}.",
            "NumberTheorist": "Solve using modular arithmetic and prime properties. Final answer in \\boxed{X}.",
            "Inductive": "Find patterns from small cases (n=1,2,3). Final answer in \\boxed{X}."
        }

    def run_swarm(self, problem_text: str, budget: float) -> int:
        strategy = "Algebraist"
        if any(w in problem_text.lower() for w in ["prime", "modulo", "divisible"]):
            strategy = "NumberTheorist"
        elif any(w in problem_text.lower() for w in ["sequence", "sum of"]):
            strategy = "Inductive"

        num_samples = 5 if budget > 350 else 3
        prompt = f"<|im_start|>system\n{self.specialists[strategy]}<|im_end|>\n<|im_start|>user\n{problem_text}<|im_end|>\n<|im_start|>assistant\n"
        inputs = self.tokenizer(prompt, return_tensors="pt").to("cuda")
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs, 
                max_new_tokens=2500,
                temperature=0.85,
                do_sample=True,
                num_return_sequences=num_samples,
                pad_token_id=self.tokenizer.eos_token_id
            )
        
        proofs = [self.tokenizer.decode(o[inputs["input_ids"].shape[-1]:], skip_special_tokens=True) for o in outputs]
        answers = []
        for p in proofs:
            match = re.search(r"\\boxed\{(\d+)\}", p)
            if match:
                ans = int(match.group(1)) % 1000
                answers.append(ans)
            else:
                nums = re.findall(r"\d+", p)
                if nums: answers.append(int(nums[-1]) % 1000)

        if not answers: return 0
        return Counter(answers).most_common(1)[0][0]

# --- 3. Global Driver ---
_model = None
_tokenizer = None
_start_time = None
_problems_solved = 0
_total_time_limit = 5 * 3600

def find_path(name_part):
    for root, dirs, files in os.walk("/kaggle/input"):
        if name_part.lower() in root.lower(): return root
    return None

def load_environment():
    global _model, _tokenizer
    # Attempt local download if not found in input
    path = find_path("qwen2-5-math-7b-instruct")
    if not path:
        print("Model not found in /kaggle/input. Downloading via kagglehub...")
        import kagglehub
        path = kagglehub.model_download('metheven/qwen2-5-math-7b-instruct/transformers/default')
    
    _tokenizer = AutoTokenizer.from_pretrained(path)
    _model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.bfloat16, device_map="auto")
    try:
        _model = torch.compile(_model)
    except: pass

def predict(id_df: pl.Series, problem_df: pl.Series) -> pl.DataFrame:
    global _model, _tokenizer, _start_time, _problems_solved
    if _model is None: load_environment()
    if _start_time is None: _start_time = time.time()

    gc.collect()
    torch.cuda.empty_cache()

    problem_id = id_df[0]
    problem_text = problem_df[0]
    
    elapsed = time.time() - _start_time
    remaining_time = _total_time_limit - elapsed
    budget_per_prob = remaining_time / max(1, (50 - _problems_solved))
    
    print(f"\n[Problem {problem_id}] Budget: {budget_per_prob:.1f}s | Solved: {_problems_solved}")

    swarm = specialist_team(_model, _tokenizer)
    final_ans = swarm.run_swarm(problem_text, budget_per_prob)

    _problems_solved += 1
    return pl.DataFrame({"id": [problem_id], "answer": [int(final_ans) % 1000]})

if __name__ == "__main__":
    if PreFlightJury.run_all():
        from kaggle_evaluation.aimo_3_inference_server import AIMO3InferenceServer
        server = AIMO3InferenceServer(predict)
        if os.getenv("KAGGLE_IS_COMPETITION_RERUN"): server.serve()
        else:
            p = find_path("test.csv") or find_path("reference.csv")
            if p: server.run_local_gateway((p,))
            else:
                dummy_df = pl.DataFrame({"id": ["d0"], "problem": ["Find X: 2X = 8"]})
                dummy_df.write_csv("dummy.csv")
                server.run_local_gateway(("dummy.csv",))
    else:
        pl.DataFrame({"id": [], "answer": []}).write_parquet("submission.parquet")
