import os
import re
import sys
from typing import Optional

import polars as pl
import torch


# Setup path for Kaggle evaluation API
sys.path.append('/kaggle/input/ai-mathematical-olympiad-progress-prize-3')
import kaggle_evaluation.aimo_3_inference_server


MODEL_PATH = "/kaggle/input/qwen2-5-math-7b-instruct"

# We use a global model instance to only load it once.
global_model = None
global_tokenizer = None
USE_VLLM = False

def load_model():
    global global_model, global_tokenizer, USE_VLLM
    
    try:
        from vllm import LLM, SamplingParams
        USE_VLLM = True
        print("Using vLLM for inference.", flush=True)
        # 1. Initialize vLLM with Qwen2.5 Math
        global_model = LLM(
            model=MODEL_PATH,
            tensor_parallel_size=1, 
            trust_remote_code=True,
            gpu_memory_utilization=0.95,
            enforce_eager=True, 
            max_model_len=4096
        )
        global_tokenizer = SamplingParams(
            temperature=0.2,
            max_tokens=2048,
            stop=["<|im_end|>"]
        )
    except Exception as e:
        print(f"Failed to load vLLM: {e}. Falling back to Transformers.", flush=True)
        USE_VLLM = False
        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
        global_tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH)
        model = AutoModelForCausalLM.from_pretrained(
            MODEL_PATH,
            torch_dtype=torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16,
            device_map="auto"
        )
        global_model = pipeline(
            "text-generation",
            model=model,
            tokenizer=global_tokenizer,
            max_new_tokens=2048,
            temperature=0.2,
            do_sample=True,
            return_full_text=False
        )

def solve(problem: str) -> str:
    prompt = f"<|im_start|>system\nPlease reason step by step, and put your final answer within \\boxed{{}}.<|im_end|>\n<|im_start|>user\n{problem}<|im_end|>\n<|im_start|>assistant\n"
    
    if USE_VLLM:
        outputs = global_model.generate([prompt], global_tokenizer, use_tqdm=False)
        return outputs[0].outputs[0].text
    else:
        out = global_model(prompt)
        return out[0]['generated_text']

def extract_answer(text: str) -> int:
    match = re.search(r'\\boxed\{(\d+)\}', text)
    if match:
        return int(match.group(1)) % 100000
    numbers = re.findall(r'\d+', text)
    if numbers:
        return int(numbers[-1]) % 100000
    return 0

def predict(id_: pl.DataFrame, question: pl.DataFrame, answer: Optional[pl.DataFrame] = None) -> pl.DataFrame:
    # Ensure model is loaded on the first call
    if global_model is None:
        load_model()
        
    problem_id = id_.item(0, 0)
    problem_text = question.item(0, 0)
    
    response = solve(problem_text)
    prediction = extract_answer(response)
    
    return pl.DataFrame({'id': [problem_id], 'answer': [prediction]})

if __name__ == "__main__":
    inference_server = kaggle_evaluation.aimo_3_inference_server.AIMO3InferenceServer(predict)
    if os.getenv('KAGGLE_IS_COMPETITION_RERUN'):
        inference_server.serve()
    else:
        # Use local file during interactive run
        inference_server.run_local_gateway(
            ('/kaggle/input/ai-mathematical-olympiad-progress-prize-3/test.csv',)
        )
