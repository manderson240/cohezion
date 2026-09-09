import json
import urllib.request


# Probe lemond's internal status
req = urllib.request.Request("http://127.0.0.1:13305/api/v1/models")
try:
    with urllib.request.urlopen(req, timeout=3) as resp:
        data = json.loads(resp.read().decode())
        print("Active lemond models response keys:", list(data.keys()) if isinstance(data, dict) else "list")
except Exception as e:
    print("Failed /api/v1/models:", e)
