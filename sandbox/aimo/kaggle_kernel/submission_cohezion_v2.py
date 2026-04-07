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
import requests
import sympy

# --- 1. Kaggle Infrastructure Handshake ---
try:
    import torch
except ImportError:
    torch = None

HAS_VLLM = False
HAS_INSTALLED = False

def find_path(name_part):
    """Recursively search for a path in /kaggle/input."""
    for root, dirs, files in os.walk("/kaggle/input"):
        if name_part.lower() in root.lower():
            return root
    return None

def install_dependencies():
    """Install vLLM from offline dataset if missing."""
    global HAS_VLLM, HAS_INSTALLED
    
    import site
    import importlib
    user_site = site.getusersitepackages()
    if user_site not in sys.path:
        sys.path.insert(0, user_site)
        
    try:
        from vllm import LLM, SamplingParams
        HAS_VLLM = True
        return
    except ImportError:
        pass
        
    print("Searching for vLLM wheels...")
    dep_path = find_path("vllm-wheel-py3-12") or find_path("vllm-0-7-3-many")
    
    if dep_path:
        print(f"Found dependencies at {dep_path}. Installing with --user...")
        import glob
        wheels = glob.glob(os.path.join(dep_path, "**/*.whl"), recursive=True)
        if wheels:
            wheels.sort(key=lambda x: "vllm" in x)
            cmd = f"pip install --user --no-index --find-links={dep_path} " + " ".join(wheels)
            subprocess.run(cmd, shell=True)
        try:
            importlib.invalidate_caches()
            from vllm import LLM, SamplingParams
            HAS_VLLM = True
            print("vLLM installed successfully.")
            # Disk space hardening: clear pip cache
            subprocess.run("rm -rf /root/.cache/pip", shell=True)
        except Exception as e:
            print(f"Failed to import vLLM after install: {e}")
    else:
        print("No dependency dataset found.")
    
    HAS_INSTALLED = True

# Path to Kaggle evaluation API
sys.path.append("/kaggle/input/ai-mathematical-olympiad-progress-prize-3")
try:
    from kaggle_evaluation.aimo_3_inference_server import AIMO3InferenceServer
except ImportError:
    class AIMO3InferenceServer:
        def __init__(self, predict_fn): self.predict = predict_fn
        def serve(self): print("Serving...")
        def run_local_gateway(self, paths): print(f"Mock gateway for {paths}")

# --- 2. Symbolic Executor (Doer) ---
class SymbolicExecutor:
    def __init__(self):
        self.namespace = {
            "sympy": sympy, "np": np, "sp": sympy,
            "sqrt": sympy.sqrt, "exp": sympy.exp, "log": sympy.log,
            "sin": sympy.sin, "cos": sympy.cos, "tan": sympy.tan,
            "pi": sympy.pi, "I": sympy.I, "symbols": sympy.symbols,
            "Eq": sympy.Eq, "solve": sympy.solve, "nsolve": sympy.nsolve,
            "simplify": sympy.simplify, "expand": sympy.expand, "factor": sympy.factor,
            "limit": sympy.limit, "diff": sympy.diff, "integrate": sympy.integrate,
            "Sum": sympy.Sum, "Product": sympy.Product, "oo": sympy.oo,
            "isprime": sympy.isprime, "primerange": sympy.primerange,
            "factorint": sympy.factorint, "gcd": sympy.gcd, "lcm": sympy.lcm,
            "mod_inverse": sympy.mod_inverse,
        }

    def execute(self, code: str) -> dict:
        local_vars = {}
        exec_globals = {**self.namespace}
        try:
            exec(code, exec_globals, local_vars)
            clean_results = {}
            for k, v in local_vars.items():
                if k.startswith("_"): continue
                if hasattr(v, "evalf"):
                    try: clean_results[k] = float(v.evalf())
                    except: clean_results[k] = str(v)
                else: clean_results[k] = v
            return {"success": True, "results": clean_results}
        except Exception as e:
            return {"success": False, "error": str(e)}

# --- 3. Knower Auditor (Knower) ---
class KnowerAuditor:
    def audit_runs(self, run_results: list, reasoning_chains: list) -> dict:
        r1 = run_results[0] if len(run_results) > 0 else None
        r2 = run_results[1] if len(run_results) > 1 else None
        is_consistent = (r1 == r2) and (r1 is not None)
        
        entropy = 0.0 if is_consistent else 0.5
        if r1 is None or r2 is None: entropy += 0.25
        weight = 1.0 + 1.0 / (entropy + 0.1)

        final_answer = r1 if is_consistent else None
        if r1 is None and r2 is None: final_answer = 0

        return {
            "consistent": is_consistent,
            "entropy": entropy,
            "weight": weight,
            "final_answer": final_answer,
            "action": "COMMIT" if is_consistent else "TIE_BREAKER",
        }

    def resolve_tie(self, r1, r2, r3, reasoning_chains=None) -> int:
        if not reasoning_chains or len(reasoning_chains) < 3:
            votes = [r1, r2, r3]
            counts = {v: votes.count(v) for v in set(votes)}
            return max(counts, key=counts.get)
        
        weights = []
        for chain in reasoning_chains:
            ent = 0.1 + (max(0, len(chain) - 5000) / 20000.0)
            weights.append(1.0 + 1.0 / (ent + 0.1))
            
        vote_scores = {}
        for ans, w in zip([r1, r2, r3], weights):
            if ans is not None:
                vote_scores[ans] = vote_scores.get(ans, 0.0) + w
        return max(vote_scores, key=vote_scores.get) if vote_scores else 0

# --- 4. Specialist Swarm (Thinker) ---
class BaseSpecialist:
    def __init__(self, name: str, llm_instance=None):
        self.name = name
        self.llm = llm_instance
        self.prompts = {
            "Algebraist": "Solve using symbolic reasoning. Use Python/SymPy. Final answer in \\boxed{X}.",
            "NumberTheorist": "Focus on modular arithmetic. Use Python/SymPy. Final answer in \\boxed{X}.",
            "Geometer": "Convert geometry to algebraic constraints. Use Python/SymPy. Final answer in \\boxed{X}.",
            "Combinatorist": "Focus on counting. Use Python/SymPy. Final answer in \\boxed{X}.",
            "InductiveReasoning": "Test small cases first. Final answer in \\boxed{X}.",
            "GoalOriented": "Work backwards from the goal. Final answer in \\boxed{X}."
        }
        self.executor = SymbolicExecutor()

    def solve(self, problem_text: str) -> str:
        system_prompt = self.prompts.get(self.name, "Think step by step. Final answer in \\boxed{X}.")
        prompt = f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{problem_text}<|im_end|>\n<|im_start|>assistant\n"
        
        if self.llm:
            try:
                from vllm import SamplingParams
                params = SamplingParams(temperature=1.0, max_tokens=8192, stop=["<|im_end|>"])
                outputs = self.llm.generate([prompt], params, use_tqdm=False)
                response = outputs[0].outputs[0].text
                
                code_match = re.search(r"```python\s*\n(.*?)```", response, re.DOTALL)
                if code_match:
                    exec_res = self.executor.execute(code_match.group(1).strip())
                    if exec_res.get("success"):
                        prompt += response + f"\n\nExecution Result: {exec_res['results']}\n\nFinal Answer in \\boxed{{}}:"
                        outputs = self.llm.generate([prompt], params, use_tqdm=False)
                        response += "\n" + outputs[0].outputs[0].text
                return response
            except Exception as e:
                print(f"LLM Solve Error: {e}")
                return "\\boxed{0}"
        return "\\boxed{0}"

    def extract_answer(self, text: str) -> int:
        match = re.search(r"\\boxed\{(\d+)\}", text)
        if match: return int(match.group(1)) % 100000
        nums = re.findall(r"\d+", text)
        return int(nums[-1]) % 100000 if nums else 0

# --- 5. Global State & Prediction ---
_llm = None
_auditor = KnowerAuditor()
_start_time = None
_problems_solved = 0
_total_time_limit = 5 * 3600
_safety_threshold = 30.0

def load_vllm():
    global _llm, HAS_VLLM, HAS_INSTALLED
    if not HAS_VLLM and not HAS_INSTALLED:
        install_dependencies()
        
    MODEL_PATH = find_path("qwen2-5-math-7b-instruct") or \
                 find_path("deepseek-r1-distill-qwen-32b-awq-casperhansen") or \
                 find_path("deepseek-r1-distill-qwen-32b")
    
    DRAFTER_PATH = find_path("qwen2-5-math-1-5b-instruct") or find_path("Qwen2.5-Math-1.5B-Instruct")
                 
    if HAS_VLLM and MODEL_PATH:
        print(f"Loading vLLM from {MODEL_PATH}...")
        from vllm import LLM
        llm_kwargs = {
            "model": MODEL_PATH,
            "tensor_parallel_size": 1,
            "gpu_memory_utilization": 0.85,
            "enforce_eager": True,
            "max_model_len": 8192,
            "trust_remote_code": True,
            "quantization": "awq" if "awq" in MODEL_PATH.lower() else None
        }
        if torch and torch.cuda.device_count() > 1:
            llm_kwargs["tensor_parallel_size"] = torch.cuda.device_count()
            llm_kwargs["gpu_memory_utilization"] = 0.90
            
        if DRAFTER_PATH:
            print(f"Enabling Speculative Decoding with Drafter: {DRAFTER_PATH}")
            llm_kwargs["speculative_model"] = DRAFTER_PATH
            llm_kwargs["num_speculative_tokens"] = 5
            
        try:
            _llm = LLM(**llm_kwargs)
        except Exception as e:
            print(f"vLLM Init Failed: {e}")
    else:
        print(f"Cannot load LLM. HAS_VLLM={HAS_VLLM}, MODEL_PATH={MODEL_PATH}")

def predict(id_df: pl.DataFrame, problem_df: pl.DataFrame) -> pl.DataFrame:
    global _llm, _start_time, _problems_solved
    if _llm is None: load_vllm()
    if _start_time is None: _start_time = time.time()

    if _problems_solved > 0 and _problems_solved % 10 == 0:
        gc.collect()
        if torch: torch.cuda.empty_cache()

    problem_id = id_df[0, 0]
    problem_text = problem_df[0, 0]

    elapsed = time.time() - _start_time
    remaining_time = _total_time_limit - elapsed
    remaining_problems = 50 - (_problems_solved % 50)
    budget = remaining_time / max(1, remaining_problems)

    print(f"Problem {problem_id} | Budget: {budget:.1f}s")

    if budget < _safety_threshold or _llm is None:
        _problems_solved += 1
        return pl.DataFrame({"id": [problem_id], "answer": [0]})

    strategies = ["Algebraist", "InductiveReasoning", "GoalOriented", "NumberTheorist"]
    s1 = strategies[_problems_solved % len(strategies)]
    s2 = strategies[(_problems_solved + 1) % len(strategies)]

    # Dual Run
    spec1 = BaseSpecialist(s1, _llm)
    r1 = spec1.solve(problem_text)
    ans1 = spec1.extract_answer(r1)

    spec2 = BaseSpecialist(s2, _llm)
    r2 = spec2.solve(problem_text)
    ans2 = spec2.extract_answer(r2)

    audit = _auditor.audit_runs([ans1, ans2], [r1, r2])
    final_answer = audit["final_answer"]

    if audit["action"] == "TIE_BREAKER" and budget > 180.0:
        print("Divergence. Tie-breaker run...")
        s3 = strategies[(_problems_solved + 2) % len(strategies)]
        spec3 = BaseSpecialist(s3, _llm)
        r3 = spec3.solve(problem_text)
        ans3 = spec3.extract_answer(r3)
        final_answer = _auditor.resolve_tie(ans1, ans2, ans3, [r1, r2, r3])
    elif final_answer is None:
        final_answer = ans1

    _problems_solved += 1
    return pl.DataFrame({"id": [problem_id], "answer": [int(final_answer or 0) % 100000]})

if __name__ == "__main__":
    if not HAS_VLLM and not HAS_INSTALLED:
        install_dependencies()
        
    from kaggle_evaluation.aimo_3_inference_server import AIMO3InferenceServer
    server = AIMO3InferenceServer(predict)
    if os.getenv("KAGGLE_IS_COMPETITION_RERUN"):
        server.serve()
    else:
        found_path = None
        for root, dirs, files in os.walk("/kaggle/input"):
            if "test.csv" in files:
                found_path = os.path.join(root, "test.csv")
                break
            if "reference.csv" in files:
                found_path = os.path.join(root, "reference.csv")
        
        if found_path:
            print(f"Running local gateway against: {found_path}")
            server.run_local_gateway((found_path,))
        else:
            print("No test files found. Dummy run.")
            dummy_df = pl.DataFrame({"id": ["dummy_0"], "problem": ["2+2"]})
            dummy_df.write_csv("dummy_test.csv")
            server.run_local_gateway(("dummy_test.csv",))
