import os
import sys
import subprocess

print("=== Kaggle Environment Check ===")
print(f"Python version: {sys.version}")

try:
    import vllm
    print(f"vLLM version: {vllm.__version__}")
except ImportError:
    print("vLLM is NOT installed.")

try:
    import torch
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"GPU: {torch.cuda.get_device_name(0)}")
except ImportError:
    print("PyTorch is NOT installed.")

print("\n=== Checking Input Paths ===")
for root, dirs, files in os.walk("/kaggle/input"):
    if "test.csv" in files or "model" in root.lower() or "deepseek" in root.lower():
        print(f"Found: {root}")
        # Limit output
        if "deepseek" in root.lower():
            print(f"Files in {root}: {files[:5]}")
