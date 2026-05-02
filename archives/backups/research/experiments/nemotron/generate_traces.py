import os
import subprocess

import pandas as pd
import torch


def install_vllm():
    try:
        import vllm

        print("vLLM already installed.")
        return True
    except ImportError:
        print("vLLM not found. Attempting install from local wheels...")
        dep_path = None
        for root, dirs, files in os.walk("/kaggle/input"):
            if "vllm" in root.lower() and any(f.endswith(".whl") for f in files):
                dep_path = root
                break

        if dep_path:
            cmd = f"pip install --no-index --find-links={dep_path} vllm"
            subprocess.run(cmd, shell=True)
            return True
        else:
            print("No local wheels found. Attempting online install...")
            try:
                subprocess.run("pip install vllm", shell=True)
                return True
            except Exception as e:
                print(f"Online install failed: {e}")
                return False


def generate_traces():
    if not install_vllm():
        print("CRITICAL: Failed to install vLLM. Exiting.")
        return

    from vllm import LLM, SamplingParams

    print("=== [1/5] Loading training data... ===")
    train_path = "/kaggle/input/nvidia-nemotron-model-reasoning-challenge/train.csv"
    if not os.path.exists(train_path):
        # Fallback for local testing
        train_path = "train.csv"
        if not os.path.exists(train_path):
            print("Creating dummy train.csv for testing...")
            df = pd.DataFrame(
                {"prompt": ["What is 2+2?", "Solve for x: 3x - 5 = 10"], "answer": ["4", "5"]}
            )
            df.to_csv("train.csv", index=False)
            train_path = "train.csv"

    df = pd.read_csv(train_path)

    print("=== [2/5] Initializing DeepSeek-R1-Distill-Qwen-32B... ===")
    # Find model path
    model_path = None
    for root, dirs, files in os.walk("/kaggle/input"):
        if "deepseek-r1-distill-qwen-32b" in root.lower():
            model_path = root
            break

    if not model_path:
        print(
            "WARNING: DeepSeek-R1-Distill-Qwen-32B not found in /kaggle/input. Using local hub if available."
        )
        model_path = "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B"

    # Initialize vLLM
    llm = LLM(
        model=model_path,
        tensor_parallel_size=torch.cuda.device_count(),
        gpu_memory_utilization=0.9,
        trust_remote_code=True,
        max_model_len=8192,
    )

    sampling_params = SamplingParams(
        temperature=0.6,
        top_p=0.95,
        max_tokens=2048,
    )

    print("=== [3/5] Generating reasoning traces... ===")
    prompts = [
        f"<|im_start|>user\n{p}\n<|im_end|>\n<|im_start|>assistant\n<thinking>\n"
        for p in df["prompt"]
    ]

    outputs = llm.generate(prompts, sampling_params)

    traces = []
    for output in outputs:
        generated_text = output.outputs[0].text
        # DeepSeek-R1 usually outputs </thinking> after the trace
        if "</thinking>" in generated_text:
            trace = generated_text.split("</thinking>")[0].strip()
        else:
            trace = generated_text.strip()
        traces.append(trace)

    df["reasoning_trace"] = traces

    print("=== [4/5] Formatting for Nemotron training... ===")
    # Format: <|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n<thinking>{trace}</thinking>\boxed{{{answer}}}<|im_end|>
    df["text"] = df.apply(
        lambda x: (
            f"<|im_start|>user\n{x['prompt']}<|im_end|>\n<|im_start|>assistant\n<thinking>{x['reasoning_trace']}</thinking>\\boxed{{{x['answer']}}}<|im_end|>"
        ),
        axis=1,
    )

    print("=== [5/5] Saving dataset with traces... ===")
    output_path = "train_with_traces.csv"
    df.to_csv(output_path, index=False)
    print(f"Saved {len(df)} traces to {output_path}")


if __name__ == "__main__":
    generate_traces()
