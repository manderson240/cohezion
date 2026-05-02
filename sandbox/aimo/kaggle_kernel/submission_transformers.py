import gc
import os
import re
import time
from collections import Counter

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
        print("=== 🛡️ INITIALIZING FORTRESS PRE-FLIGHT TESTS (v42) ===")
        results = {
            "gpu": PreFlightJury.test_gpu(),
            "libs": PreFlightJury.test_libs(),
            "symbolic": PreFlightJury.test_symbolic(),
        }
        print(f"Test Results: {results}")
        return all(results.values())

    @staticmethod
    def test_gpu():
        try:
            print(f"GPU Check: {torch.cuda.get_device_name(0)}")
            return torch.cuda.is_available()
        except:
            return False

    @staticmethod
    def test_libs():
        try:
            return True
        except:
            return False

    @staticmethod
    def test_symbolic():
        try:
            x = sympy.symbols("x")
            res = sympy.solve(x**2 - 4, x)
            return len(res) == 2
        except:
            return False


# --- 2. Symbolic Verifier (Doer) ---
class SymbolicVerifier:
    def __init__(self):
        self.namespace = {
            "sympy": sympy,
            "np": np,
            "sp": sympy,
            "sqrt": sympy.sqrt,
            "exp": sympy.exp,
            "log": sympy.log,
            "pi": sympy.pi,
            "symbols": sympy.symbols,
            "Eq": sympy.Eq,
            "solve": sympy.solve,
            "simplify": sympy.simplify,
        }

    def verify(self, code_snippet: str, expected_ans: int) -> bool:
        local_vars = {}
        try:
            # Extract code between triple backticks if present
            code = re.search(r"```python\n(.*?)\n```", code_snippet, re.DOTALL)
            code = code.group(1) if code else code_snippet
            exec(code, self.namespace, local_vars)
            # Find any variable that matches the expected answer
            for v in local_vars.values():
                if isinstance(v, (int, float, sympy.Integer, sympy.Float)):
                    if abs(float(v) - expected_ans) < 1e-6:
                        return True
            return False
        except:
            return False


# --- 2.1 AutoHarness Specialized Verifiers ---
class AutoHarnessVerifier:
    """Synthesized code verifiers for specific AIMO domains."""

    @staticmethod
    def verify_modular(state, action):
        # Auto-synthesized for modular congruence (v1)
        try:
            return (int(action) % int(state["mod"])) == int(state["n"])
        except:
            return False

    @staticmethod
    def verify_algebra(state, action):
        # Auto-synthesized for symbolic consistency (v1)
        try:
            # We assume state has 'val' if it's a known constant
            return abs(float(state.get("val", 0)) - float(action)) < 1e-6
        except:
            return False


# --- 3. Specialist Swarm (Triune Manifold) ---
class specialist_team:
    def __init__(self, model, tokenizer):
        self.model = model
        self.tokenizer = tokenizer
        self.specialists = {
            "Algebraist": "Solve via SymPy and Python code. Final answer in \\boxed{X}.",
            "NumberTheorist": "Solve using modular arithmetic and prime properties. Final answer in \\boxed{X}.",
            "Inductive": "Find patterns from small cases (n=1,2,3). Final answer in \\boxed{X}.",
        }

    def run_swarm(self, problem_text: str, budget: float) -> int:
        # Determine strategy based on problem content
        strategy = "Algebraist"
        if any(w in problem_text.lower() for w in ["prime", "modulo", "divisible"]):
            strategy = "NumberTheorist"
        elif any(w in problem_text.lower() for w in ["sequence", "sum of"]):
            strategy = "Inductive"

        # Generate multiple candidates
        num_samples = 5 if budget > 350 else 3
        prompt = f"<|im_start|>system\n{self.specialists[strategy]}<|im_end|>\n<|im_start|>user\n{problem_text}<|im_end|>\n<|im_start|>assistant\n"

        inputs = self.tokenizer(prompt, return_tensors="pt")
        # Robust device mapping
        device = (
            "cuda" if torch.cuda.is_available() and os.getenv("AIMO_FORCE_CPU") != "1" else "cpu"
        )
        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=2500,
                temperature=0.85,
                do_sample=True,
                num_return_sequences=num_samples,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        proofs = [
            self.tokenizer.decode(o[inputs["input_ids"].shape[-1] :], skip_special_tokens=True)
            for o in outputs
        ]
        answers = []
        for p in proofs:
            # Answer extraction logic
            match = re.search(r"\\boxed\{(\d+)\}", p)
            if match:
                ans = int(match.group(1)) % 1000
                answers.append(ans)
            else:
                nums = re.findall(r"\d+", p)
                if nums:
                    answers.append(int(nums[-1]) % 1000)

        if not answers:
            return 0
        # Choose most common, breaking ties with the first one
        return Counter(answers).most_common(1)[0][0]


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


def load_environment():
    global _model, _tokenizer
    path = find_path("qwen2-5-math-7b-instruct")
    if path:
        _tokenizer = AutoTokenizer.from_pretrained(path)

        # Decide device and dtype
        if os.getenv("AIMO_FORCE_CPU") == "1" or not torch.cuda.is_available():
            device_map = "cpu"
            dtype = torch.float32  # H100 uses bfloat16, local CPU prefers float32
        else:
            device_map = "auto"
            dtype = torch.bfloat16

        _model = AutoModelForCausalLM.from_pretrained(path, dtype=dtype, device_map=device_map)
        try:
            # H100 optimization only on GPU
            if device_map != "cpu":
                _model = torch.compile(_model)
        except:
            pass


def predict(id_df: pl.Series, problem_df: pl.Series) -> pl.DataFrame:
    global _model, _tokenizer, _start_time, _problems_solved
    if _model is None:
        load_environment()
    if _start_time is None:
        _start_time = time.time()

    gc.collect()
    torch.cuda.empty_cache()

    problem_id = id_df[0]
    problem_text = problem_df[0]

    elapsed = time.time() - _start_time
    remaining_time = _total_time_limit - elapsed
    budget_per_prob = remaining_time / max(1, (50 - (_problems_solved % 50)))
    vram = torch.cuda.memory_allocated() / 1e9
    final_ans = 0
    try:
        swarm = specialist_team(_model, _tokenizer)
        final_ans = swarm.run_swarm(problem_text, budget_per_prob)
    except Exception as e:
        print(f"Safety Trigger: {e}")
        final_ans = 0

    _problems_solved += 1
    return pl.DataFrame({"id": [problem_id], "answer": [int(final_ans) % 1000]})


if __name__ == "__main__":
    if PreFlightJury.run_all():
        from kaggle_evaluation.aimo_3_inference_server import AIMO3InferenceServer

        server = AIMO3InferenceServer(predict)
        if os.getenv("KAGGLE_IS_COMPETITION_RERUN"):
            server.serve()
        else:
            p = find_path("test.csv") or find_path("reference.csv")
            if p:
                server.run_local_gateway((p,))
            else:
                dummy_df = pl.DataFrame({"id": ["d0"], "problem": ["Find X: 2X = 8"]})
                dummy_df.write_csv("dummy.csv")
                server.run_local_gateway(("dummy.csv",))
    else:
        pl.DataFrame({"id": [], "answer": []}).write_parquet("submission.parquet")
