import os
import subprocess
import sys
import time
import site


def install():
    print("Executing background vLLM 0.7.3 installation...")
    # Find dependency path
    dep_path = None
    for root, dirs, files in os.walk("/kaggle/input"):
        if "vllm-0-7-3-many" in root or "vllm-wheel-py3-12" in root:
            dep_path = root
            break

    if dep_path:
        print(f"Found dependencies at {dep_path}. Installing...")
        cmd = f"pip install --user --no-index --find-links={dep_path} vllm"
        subprocess.run(cmd, shell=True)

        # Ensure user site is in path for THIS process if needed,
        # but the main goal is the NEXT process.
        user_site = site.getusersitepackages()
        sys.path.insert(0, user_site)
        os.environ["PYTHONPATH"] = f"{user_site}:{os.environ.get('PYTHONPATH', '')}"
        os.environ["TRITON_PTXAS_PATH"] = "/usr/local/cuda/bin/ptxas"

        print("Installation complete. Launching vLLM API server...")

        # Find model path
        model_path = None
        for root, dirs, files in os.walk("/kaggle/input"):
            if "math-7b" in root.lower() or "deepseek-r1" in root.lower():
                model_path = root
                break

        if model_path:
            # Launch vLLM OpenAI-compatible server in background
            # We use python -m vllm.entrypoints.openai.api_server
            server_cmd = [
                sys.executable,
                "-m",
                "vllm.entrypoints.openai.api_server",
                "--model",
                model_path,
                "--tensor-parallel-size",
                str(subprocess.check_output(["nvidia-smi", "-L"]).count(b"UUID")),
                "--gpu-memory-utilization",
                "0.85",
                "--max-model-len",
                "8192",
                "--trust-remote-code",
                "--port",
                "8000",
            ]

            if "awq" in model_path.lower():
                server_cmd += ["--quantization", "awq"]

            print(f"Executing: {' '.join(server_cmd)}")
            return subprocess.Popen(server_cmd)
    return None


if __name__ == "__main__":
    p = install()
    if p:
        # Keep process alive
        try:
            while True:
                time.sleep(60)
                if p.poll() is not None:
                    print("Server process died. Restarting...")
                    p = install()
        except KeyboardInterrupt:
            p.terminate()
