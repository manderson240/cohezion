import os
import subprocess
import time


def get_kernel_status():
    result = subprocess.run(
        ["uv", "run", "kaggle", "kernels", "status", "manderson240/aimo-3-cohezion-baseline"],
        capture_output=True, text=True
    )
    return result.stdout.strip()

def submit_to_competition():
    print("Attempting to submit to competition...")
    result = subprocess.run(
        [
            "uv", "run", "kaggle", "competitions", "submit", 
            "-c", "ai-mathematical-olympiad-progress-prize-3", 
            "-k", "manderson240/aimo-3-cohezion-baseline", 
            "-v", "1", 
            "-f", "submission.csv", 
            "-m", "Baseline Submission via vLLM"
        ],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.stderr:
        print("Error:", result.stderr)

if __name__ == "__main__":
    os.environ["KAGGLE_API_TOKEN"] = "KGAT_ea8510184dd779e5ee8e296260c0ac1c"
    
    while True:
        status = get_kernel_status()
        print(f"[{time.strftime('%H:%M:%S')}] Status: {status}")
        
        if "COMPLETE" in status.upper():
            submit_to_competition()
            break
        elif "ERROR" in status.upper() or "FAIL" in status.upper():
            print("Kernel execution failed. Cannot submit.")
            break
            
        time.sleep(30)
