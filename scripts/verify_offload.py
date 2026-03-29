import json
import subprocess
import sys


def call_mcp(method, params=None):
    request = {"jsonrpc": "2.0", "method": method, "id": 1}
    if params:
        request["params"] = params

    proc = subprocess.Popen(
        [
            "python3",
            "/home/mike-anderson/dev/cohezion/src/cohezion/skills/cohezion_mcp.py",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    stdout, stderr = proc.communicate(input=json.dumps(request) + "\n")
    if stderr:
        sys.stderr.write(f"--- BRIDGE STDERR ---\n{stderr}\n")
    return json.loads(stdout)


print("--- offload_task (Summarize Project) ---")
try:
    offload_resp = call_mcp(
        "tools/call",
        {
            "name": "offload_task",
            "arguments": {"query": "Summarize the project Cohezion in 2 sentences."},
        },
    )
    print(json.dumps(offload_resp, indent=2))
except Exception as e:
    print(f"FAILED: {e}")
