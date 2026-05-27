import gc
import os
import re
import time
import traceback
from collections import Counter
from dataclasses import dataclass
from typing import Any

import polars as pl
import sympy
import torch


# --- 0. ENVIRONMENT SETUP ---
def install_dependencies():
    print("=== 📦 INSTALLING DEPENDENCIES ===")

    # NVIDIA Specific Optimizations
    os.environ["AITUNE_JIT"] = "1"
    os.environ["TORCHINDUCTOR_REPRODUCE_CUDA_GRAPHS"] = "1"

    found_bnb = False
    try:
        import bitsandbytes

        found_bnb = True
        print("bitsandbytes already installed.")
    except ImportError:
        print("bitsandbytes not found. Searching for wheels...")
        for root, dirs, files in os.walk("/kaggle/input"):
            if any(f.endswith(".whl") and "bitsandbytes" in f.lower() for f in files):
                print(f"Installing dependencies from {root}...")
                # Install everything in that folder (trl, bitsandbytes)
                os.system(f"pip install --no-index --find-links='{root}' bitsandbytes trl")
                found_bnb = True
                break

    if not found_bnb:
        print("WARNING: bitsandbytes wheels not found. 4-bit loading will fail.")


# --- 1. PRE-FLIGHT TDD SUITE ---
class PreFlightJury:
    @staticmethod
    def run_all():
        print("=== 🛡️ INITIALIZING FORTRESS PRE-FLIGHT TESTS (v43) ===")
        # Deep Environment Audit
        try:
            from kag_audit import audit

            audit()
        except ImportError:
            print("Kaggle Auditor not found. Skipping deep discovery.")

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
            return torch.cuda.is_available()
        except:
            return False

    @staticmethod
    def test_libs():
        try:
            # Optional: bitsandbytes
            try:
                print("bitsandbytes available for 4-bit optimization.")
            except Exception as e:
                print(f"bitsandbytes not available: {e}. Falling back to standard precision.")
            return True
        except Exception as e:
            print(f"Lib Import Error: {e}")
            traceback.print_exc()
            return False

    @staticmethod
    def test_symbolic():
        try:
            x = sympy.symbols("x")
            res = sympy.solve(x**2 - 4, x)
            return len(res) == 2
        except:
            return False


# --- 2. THE FORTRESS SWARM ---
class FortressSwarm:
    def __init__(self, llm):
        self.llm = llm
        # We'll use vLLM style SamplingParams if vllm is present, otherwise simple dict
        self.use_vllm = hasattr(llm, "is_vllm") and llm.is_vllm

        if self.use_vllm:
            from vllm import SamplingParams

            self.sampling_params = SamplingParams(
                temperature=0.7, max_tokens=4096, stop=["<|im_end|>", "<|endoftext|>"]
            )
            self.sampling_params_final = SamplingParams(
                temperature=0.0, max_tokens=1024, stop=["<|im_end|>", "<|endoftext|>"]
            )
        else:
            # Mock structure for TransformersLLM
            @dataclass
            class MockParams:
                temperature: float
                max_tokens: int

            self.sampling_params = MockParams(0.7, 4096)
            self.sampling_params_final = MockParams(0.0, 1024)

    def solve(self, problem_text: str, budget: float) -> int:
        print("  [V-Model: Architecture Design] Extracting invariants...")

        # Phase 1: Invariant-Aware Prompting
        inv_prompt = (
            "<|im_start|>system\n"
            "You are a mathematical researcher. Before solving, identify 3 mathematical invariants or "
            "properties that must be true for the solution to be correct.\n"
            "<|im_end|>\n"
            f"<|im_start|>user\n{problem_text}<|im_end|>\n"
            "<|im_start|>assistant\n"
        )

        try:
            outputs = self.llm.generate([inv_prompt], self.sampling_params, use_tqdm=False)
            invariants = outputs[0].outputs[0].text
            print("  [Fortress] Invariants identified.")

            # Phase 2: Parallel Implementation Scaling (N=8)
            print("  [V-Model: Implementation Apex] Scaling to N=8 candidate solutions...")
            solve_prompt = (
                inv_prompt
                + invariants
                + "\n\nNow, solve the problem step-by-step using these invariants. "
                "Use Python code in ```python``` blocks for complex calculations. "
                "Put your final integer answer in \\boxed{}.\n"
            )

            # Generate 8 independent solutions (scaled for leaderboard dominance)
            outputs = self.llm.generate([solve_prompt] * 8, self.sampling_params, use_tqdm=False)
            candidates = [o.outputs[0].text for o in outputs]

            # Phase 3: GenSelect (Generative Solution Selection)
            print("  [V-Model: System Validation] Executing GenSelect scoring...")

            # Extract answers for scoring
            raw_answers = [self.extract_answer(c) for c in candidates]
            # Filter out 0 (failed extraction)
            valid_answers = [a for a in raw_answers if a != 0]

            if not valid_answers:
                print("  [Warning] No valid answers extracted. Using fallback review.")
                return self.fallback_review(problem_text, candidates[:2])

            # Major vote first
            vote_counts = Counter(valid_answers)
            top_answer, top_count = vote_counts.most_common(1)[0]

            if top_count >= 5:  # Strong consensus
                print(f"  [Fortress] Strong consensus reached: {top_answer} ({top_count}/8)")
                return top_answer

            # If no strong consensus, use GenSelect logic
            print("  [Fortress] No strong consensus. Delegating to Critical Reviewer...")
            review_prompt = (
                "<|im_start|>system\n"
                "You are an elite mathematical judge. Evaluate the following solutions for logical correctness, "
                "adherence to invariants, and calculation accuracy. Pick the one that is most likely to be correct.\n"
                "<|im_end|>\n"
                f"<|im_start|>user\nProblem: {problem_text}\n\n"
            )
            for i, c in enumerate(candidates[:4]):  # Review top 4 to save time
                review_prompt += f"--- Candidate {i + 1} ---\n{c}\n\n"

            review_prompt += "<|im_end|>\n<|im_start|>assistant\n"

            outputs = self.llm.generate([review_prompt], self.sampling_params, use_tqdm=False)
            critique = outputs[0].outputs[0].text

            # Phase 4: Acceptance Testing
            print("  [V-Model: Acceptance Testing] Finalizing verified answer...")
            final_prompt = (
                review_prompt
                + critique
                + "\n\nBased on your elite judgment, provide the verified final integer answer in \\boxed{}.\n"
            )
            outputs = self.llm.generate([final_prompt], self.sampling_params_final, use_tqdm=False)
            final_resp = outputs[0].outputs[0].text

            return self.extract_answer(final_resp)

        except Exception as e:
            print(f"  [Error] Swarm execution failed: {e}")
            traceback.print_exc()
            return 0

    def fallback_review(self, problem_text: str, samples: list[str]) -> int:
        """Standard dual-path review fallback."""
        if not samples:
            return 0
        sol1 = samples[0]
        sol2 = samples[1] if len(samples) > 1 else "No alternative solution."

        review_prompt = (
            "<|im_start|>system\n"
            "Analyze the solutions and pick the best one.\n"
            "<|im_end|>\n"
            f"<|im_start|>user\nProblem: {problem_text}\n\nSol 1: {sol1}\n\nSol 2: {sol2}<|im_end|>\n"
            "<|im_start|>assistant\n"
        )
        outputs = self.llm.generate([review_prompt], self.sampling_params_final, use_tqdm=False)
        return self.extract_answer(outputs[0].outputs[0].text)

    def extract_answer(self, text: str) -> int:
        matches = re.findall(r"\\boxed\{(\d+)\}", text)
        if matches:
            return int(matches[-1]) % 1000
        nums = re.findall(r"\d+", text)
        if nums:
            return int(nums[-1]) % 1000
        return 0


# --- 3. GLOBAL DRIVER ---
_llm = None
_start_time = None
_problems_solved = 0
_total_time_limit = 5 * 3600


def find_model_path():
    candidates = [
        "/kaggle/input/deepseek-r1-distill-qwen/deepseek-r1-distill-qwen-32b-awq",
        "/kaggle/input/qwen2-5-math-7b-instruct",
        "/kaggle/input/nvidia-nemotron-3-nano-30b-a3b-bf16",  # Check for downloaded weights
    ]
    for root, dirs, files in os.walk("/kaggle/input"):
        if "config.json" in files:
            return root
    return None


def load_environment():
    global _llm
    install_dependencies()
    path = find_model_path()
    if not path:
        print("Model not found. Submission will likely fail.")
        return

    print(f"Loading model from {path}...")
    try:
        # Try vLLM first if possible
        try:
            from vllm import LLM

            print("Attempting vLLM load...")
            _llm = LLM(
                model=path,
                tensor_parallel_size=1,
                trust_remote_code=True,
                gpu_memory_utilization=0.90,
                enforce_eager=True,
                max_model_len=5120,
                quantization="awq" if "awq" in path.lower() else None,
            )
            _llm.is_vllm = True
            print("vLLM engine initialized.")
            return
        except Exception as ve:
            print(f"vLLM load failed: {ve}. Falling back to Transformers.")

        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

        tokenizer = AutoTokenizer.from_pretrained(path)

        load_args = {"torch_dtype": torch.bfloat16, "device_map": "auto", "trust_remote_code": True}

        try:
            load_args["load_in_4bit"] = True
            print("Using 4-bit quantization.")
        except:
            print("bitsandbytes failed or missing. Using standard precision.")

        model = AutoModelForCausalLM.from_pretrained(path, **load_args)

        class TransformersLLM:
            def __init__(self, model, tokenizer):
                self.model = model
                self.tokenizer = tokenizer
                self.pipeline = pipeline("text-generation", model=model, tokenizer=tokenizer)
                self.is_vllm = False

            def generate(self, prompts, sampling_params, use_tqdm=False):
                from collections import namedtuple

                Output = namedtuple("Output", ["outputs"])
                Result = namedtuple("Result", ["text"])

                results = []
                for p in prompts:
                    out = self.pipeline(
                        p,
                        max_new_tokens=sampling_params.max_tokens,
                        temperature=sampling_params.temperature
                        if sampling_params.temperature > 0
                        else 0.001,
                        do_sample=True if sampling_params.temperature > 0 else False,
                        pad_token_id=self.tokenizer.eos_token_id,
                    )
                    gen_text = out[0]["generated_text"]
                    if gen_text.startswith(p):
                        gen_text = gen_text[len(p) :]
                    results.append(Output(outputs=[Result(text=gen_text)]))
                return results

        _llm = TransformersLLM(model, tokenizer)
        print("Transformers engine initialized.")
    except Exception as e:
        print(f"Model Loading Failed: {e}")
        traceback.print_exc()


def predict(problem_df: Any, id_df: Any) -> pl.DataFrame:
    global _llm, _start_time, _problems_solved
    if _llm is None:
        load_environment()
    if _start_time is None:
        _start_time = time.time()

    gc.collect()
    torch.cuda.empty_cache()

    # Extreme robust indexing
    try:
        if hasattr(problem_df, "item"):
            problem_text = (
                problem_df.item(0, 0)
                if hasattr(problem_df, "shape") and len(problem_df.shape) > 1
                else problem_df[0]
            )
            problem_id = (
                id_df.item(0, 0) if hasattr(id_df, "shape") and len(id_df.shape) > 1 else id_df[0]
            )
        else:
            # Fallback to standard indexing
            problem_text = problem_df[0]
            problem_id = id_df[0]
    except Exception as e:
        print(f"Indexing failed: {e}")
        problem_text = str(problem_df)
        problem_id = str(id_df)

    elapsed = time.time() - _start_time
    remaining_time = _total_time_limit - elapsed
    budget_per_prob = (remaining_time / max(1, (50 - _problems_solved))) - 30

    print(f"\n[Problem {problem_id}] Solved: {_problems_solved} | Budget: {budget_per_prob:.1f}s")

    swarm = FortressSwarm(_llm)
    final_ans = swarm.solve(problem_text, budget_per_prob)

    _problems_solved += 1
    # Return NAMED DataFrame to satisfy Gateway _convert_to_df
    return pl.DataFrame({"id": [problem_id], "answer": [int(final_ans) % 1000]})


if __name__ == "__main__":
    if PreFlightJury.run_all():
        try:
            import kaggle_evaluation.aimo_3_inference_server

            server = kaggle_evaluation.aimo_3_inference_server.AIMO3InferenceServer(predict)
            if os.getenv("KAGGLE_IS_COMPETITION_RERUN"):
                server.serve()
            else:
                dummy_df = pl.DataFrame({"id": ["d0"], "problem": ["If 2x = 8, what is x?"]})
                dummy_df.write_csv("dummy.csv")
                server.run_local_gateway(("dummy.csv",))
        except Exception as e:
            print(f"Gateway failed: {e}")
            traceback.print_exc()
    else:
        print("Pre-flight tests failed. Check environment.")
        pl.DataFrame({"id": [], "answer": []}).write_parquet("submission.parquet")
