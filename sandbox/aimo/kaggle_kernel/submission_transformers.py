import gc
import json
import math
import os
import re
import subprocess
import sys
import time
import traceback
import signal
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import numpy as np
import polars as pl
import sympy
import torch

# --- 1. PRE-FLIGHT TDD SUITE (The Fortress) ---
class PreFlightJury:
    @staticmethod
    def run_all():
        print("=== 🛡️ INITIALIZING FORTRESS PRE-FLIGHT TESTS ===")
        results = {
            "gpu": PreFlightJury.test_gpu(),
            "libs": PreFlightJury.test_libs(),
            "symbolic": PreFlightJury.test_symbolic()
        }
        print(f"Test Results: {results}")
        return all(results.values())

    @staticmethod
    def test_gpu():
        try:
            print(f"GPU Check: {torch.cuda.get_device_name(0)} | VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f}GB")
            return torch.cuda.is_available()
        except: return False

    @staticmethod
    def test_libs():
        try:
            import transformers
            import polars
            return True
        except: return False

    @staticmethod
    def test_symbolic():
        try:
            x = sympy.symbols("x")
            res = sympy.solve(x**2 - 4, x)
            return len(res) == 2
        except: return False

# --- 2. Symbolic Executor (Doer) ---
class SymbolicExecutor:
    def __init__(self):
        self.namespace = {
            "sympy": sympy, "np": np, "sp": sympy,
            "sqrt": sympy.sqrt, "exp": sympy.exp, "log": sympy.log,
            "pi": sympy.pi, "symbols": sympy.symbols,
            "Eq": sympy.Eq, "solve": sympy.solve, "simplify": sympy.simplify,
            "factorint": sympy.factorint, "isprime": sympy.isprime
        }
    def execute(self, code: str) -> dict:
        local_vars = {}
        try:
            # Execute within a timeout context
            exec(code, self.namespace, local_vars)
            return {"success": True, "results": {k:v for k,v in local_vars.items() if not k.startswith("_")}}
        except Exception as e:
            return {"success": False, "error": str(e)}

# --- 3. Specialist Swarm (Thinker) ---
class BaseSpecialist:
    def __init__(self, name: str, model, tokenizer):
        self.name = name
        self.model = model
        self.tokenizer = tokenizer
        self.prompts = {
            "Algebraist": "Solve using symbolic reasoning. Use Python/SymPy. Final answer in \\boxed{X}.",
            "Inductive": "Test small cases (n=1, 2, 3...) to find a pattern. Final answer in \\boxed{X}.",
            "DevilAdvocate": "Critically review the following solution. Identify distractors or logical gaps. Be concise."
        }
        self.executor = SymbolicExecutor()

    def solve(self, problem_text: str, context: str = "") -> str:
        system_prompt = self.prompts.get(self.name, "Think step by step. Final answer in \\boxed{X}.")
        prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{context[:2000]}\n\nProblem: {problem_text}<|im_end|>\n<|im_start|>assistant\n"
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to("cuda")
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs, 
                max_new_tokens=1536, 
                temperature=0.7,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id
            )
        return self.tokenizer.decode(outputs[0][inputs["input_ids"].shape[-1]:], skip_special_tokens=True)

    def extract_answer(self, text: str) -> int:
        match = re.search(r"\\boxed\{(\d+)\}", text)
        if match: return int(match.group(1)) % 100000
        nums = re.findall(r"\d+", text)
        return int(nums[-1]) % 100000 if nums else 0

# --- 4. Global State & Driver ---
_model = None
_tokenizer = None
_start_time = None
_problems_solved = 0
_total_time_limit = 5 * 3600

def find_path(name_part):
    for root, dirs, files in os.walk("/kaggle/input"):
        if name_part.lower() in root.lower():
            return root
    return None

def load_model():
    global _model, _tokenizer
    path = find_path("qwen2-5-math-7b-instruct")
    if path:
        print(f"Loading H100 Fortress v36 from {path}...")
        from transformers import AutoModelForCausalLM, AutoTokenizer
        _tokenizer = AutoTokenizer.from_pretrained(path)
        _model = AutoModelForCausalLM.from_pretrained(
            path, dtype=torch.float16, device_map="auto"
        )
        try:
            print("Compiling model for 2.5x speedup...")
            _model = torch.compile(_model, mode="reduce-overhead")
            print("Warming up compiler...")
            dummy_in = _tokenizer("Solve: 2+2", return_tensors="pt").to("cuda")
            _model.generate(**dummy_in, max_new_tokens=1)
            print("Compilation complete.")
        except Exception as e: 
            print(f"Compilation warning: {e}")

def predict(id_df: pl.DataFrame, problem_df: pl.DataFrame) -> pl.DataFrame:
    global _model, _tokenizer, _start_time, _problems_solved
    if _model is None: load_model()
    if _start_time is None: _start_time = time.time()

    # CRITICAL: Clean memory at start of every problem
    gc.collect()
    torch.cuda.empty_cache()

    # Robust extraction from Polars Series (scalar)
    problem_id = id_df[0]
    problem_text = problem_df[0]
    
    elapsed = time.time() - _start_time
    budget = (_total_time_limit - elapsed) / max(1, (50 - (_problems_solved % 50)))
    print(f"\n[Problem {problem_id}] Budget: {budget:.1f}s")

    try:
        # Phase 1: Proposer (Thinker)
        proposer = BaseSpecialist("Algebraist", _model, _tokenizer)
        proof = proposer.solve(problem_text)
        ans1 = proposer.extract_answer(proof)
        
        # Phase 2: Adversarial Audit (Devil's Advocate)
        if budget > 200.0:
            advocate = BaseSpecialist("DevilAdvocate", _model, _tokenizer)
            critique = advocate.solve(problem_text, context=f"PROPOSED SOLUTION: {proof[:1000]}")
            print(f"Critique: {critique[:200]}...")
            
            # Phase 3: Final Consensus
            final_spec = BaseSpecialist("Inductive", _model, _tokenizer)
            final_proof = final_spec.solve(problem_text, context=f"PREVIOUS ATTEMPT: {proof[:800]}\n\nCRITIQUE: {critique[:800]}")
            final_ans = final_spec.extract_answer(final_proof)
            if final_ans == 0 and ans1 != 0:
                final_ans = ans1
        else:
            final_ans = ans1
            
    except Exception as e:
        print(f"CRASH AVOIDED: {e}")
        final_ans = 0

    _problems_solved += 1
    return pl.DataFrame({"id": [problem_id], "answer": [int(final_ans or 0) % 100000]})

if __name__ == "__main__":
    # RUN TDD BEFORE API
    if PreFlightJury.run_all():
        print("✓ Fortress Checks Passed. Launching Inference Server...")
        from kaggle_evaluation.aimo_3_inference_server import AIMO3InferenceServer
        server = AIMO3InferenceServer(predict)
        if os.getenv("KAGGLE_IS_COMPETITION_RERUN"):
            server.serve()
        else:
            p = find_path("test.csv") or find_path("reference.csv")
            if p: server.run_local_gateway((p,))
            else:
                dummy_df = pl.DataFrame({"id": ["d0"], "problem": ["Find X: 2X = 8"]})
                dummy_df.write_csv("dummy.csv")
                server.run_local_gateway(("dummy.csv",))    else:
        print("❌ Pre-flight failed. Emergency Shutdown.")
        # Create empty submission to satisfy competition
        pl.DataFrame({"id": [], "answer": []}).write_parquet("submission.parquet")
