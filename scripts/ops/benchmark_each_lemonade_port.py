import json
import urllib.request


ports = [8004, 8005, 8006, 13305]

for p in ports:
    url = f"http://127.0.0.1:{p}/v1/models"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=2) as resp:
            data = json.loads(resp.read().decode())
            models = [m.get("id") for m in data.get("data", [])]
            print(f"Port {p}: ONLINE -> {models}")
    except Exception as e:
        print(f"Port {p}: OFFLINE/ERROR -> {e}")
