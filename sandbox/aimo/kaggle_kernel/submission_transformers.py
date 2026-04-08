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
from transformers import AutoModelForCausalLM, AutoTokenizer

# --- 0. Stability Reference ---
# This script implements the Cohezion Kaggle Stability Protocol (April 2026).
# See: conductor/tracks/aimo_progress_prize_3_20260319/KAGGLE_STABILITY_PROTOCOL.md

# --- 1. PRE-FLIGHT TDD SUITE ---
class PreFlightJury:
    @staticmethod
    def run_all():
        print("=== 🛡️ INITIALIZING FORTRESS PRE-FLIGHT TESTS (v38) ===")
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

# --- 2. Symbolic Executor (Doer) ---
class SymbolicExecutor:
    def __init__(self):
        self.namespace = {
            "sympy": sympy, "np": np, "sp": sympy,
            "sqrt": sympy.sqrt, "exp": sympy.exp, "log": sympy.log,
            "pi": sympy.pi, "symbols": sympy.symbols,
            "Eq": sympy.Eq, "solve": sympy.solve, "simplify": sympy.simplify
        }
    def execute(self, code: str) -> dict:
        local_vars = {}
        try:
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
            "Algebraist": "Solve using symbolic reasoning. Final answer in \\boxed{X}.",
            "Inductive": "Test small cases first to find a pattern. Final answer in \\boxed{X}.",
            "DevilAdvocate": "Critically review the following solution. Find exactly one error. Be concise."
        }

    def solve(self, problem_text: str, context: str = "", num_samples: int = 1) -> list[str]:
        system_prompt = self.prompts.get(self.name, "Think step by step. Final answer in \\boxed{X}.")
        # SOTA 2026: Truncate context to protect context window (4096 cap)
        prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{context[:1500]}\n\nProblem: {problem_text}<|im_end|>\n<|im_start|>assistant\n"
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to("cuda")
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs, 
                max_new_tokens=2500, # Increased for v38 
                temperature=0.9,
                do_sample=True,
                num_return_sequences=num_samples,
                pad_token_id=self.tokenizer.eos_token_id
            )
        return [self.tokenizer.decode(out[inputs["input_ids"].shape[-1]:], skip_special_tokens=True) for out in outputs]

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
        if name_part.lower() in root.lower(): return root
    return None

def load_model():
    global _model, _tokenizer
    path = find_path("qwen2-5-math-7b-instruct")
    if path:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        _tokenizer = AutoTokenizer.from_pretrained(path)
        _model = AutoModelForCausalLM.from_pretrained(path, dtype=torch.float16, device_map="auto")
        try:
            _model = torch.compile(_model, mode="reduce-overhead")
            dummy_in = _tokenizer("Solve: 2+2", return_tensors="pt").to("cuda")
            _model.generate(**dummy_in, max_new_tokens=1)
        except: pass

def predict(id_df: pl.Series, problem_df: pl.Series) -> pl.DataFrame:
    global _model, _tokenizer, _start_time, _problems_solved
    if _model is None: load_model()
    if _start_time is None: _start_time = time.time()

    gc.collect()
    torch.cuda.empty_cache()

    # CRITICAL: Robust scalar extraction
    problem_id = id_df[0]
    problem_text = problem_df[0]
    
    elapsed = time.time() - _start_time
    budget = (_total_time_limit - elapsed) / max(1, (50 - (_problems_solved % 50)))
    print(f"\n[Problem {problem_id}] Budget: {budget:.1f}s | VRAM: {torch.cuda.memory_allocated()/1e9:.1f}GB")

    final_ans = 0
    try:
        # Batched Run 1
        num_samples = 4 if budget > 200.0 else 2
        proposer = BaseSpecialist("Algebraist", _model, _tokenizer)
        proofs = proposer.solve(problem_text, num_samples=num_samples)
        answers = [proposer.extract_answer(p) for p in proofs]
        
        counts = Counter(answers)
        if counts and counts.most_common(1)[0][1] >= num_samples * 0.5:
            final_ans = counts.most_common(1)[0][0]
        else:
            final_ans = answers[0]
            proof = proofs[0]
            # Adversarial Refinement
            if budget > 220.0:
                advocate = BaseSpecialist("DevilAdvocate", _model, _tokenizer)
                critique = advocate.solve(problem_text, context=f"PROPOSED SOLUTION: {proof[:1000]}")[0]
                
                final_spec = BaseSpecialist("Inductive", _model, _tokenizer)
                final_proof = final_spec.solve(problem_text, context=f"PREVIOUS: {proof[:800]}\nCRITIQUE: {critique[:800]}")[0]
                refined_ans = final_spec.extract_answer(final_proof)
                
                if refined_ans != 0: final_ans = refined_ans # Safety Net
            
    except Exception as e:
        print(f"Safety Trigger: {e}")
        final_ans = final_ans or 0

    _problems_solved += 1
    return pl.DataFrame({"id": [problem_id], "answer": [int(final_ans) % 100000]})

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
