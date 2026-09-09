import json
import urllib.request


url = "http://127.0.0.1:13305/v1/chat/completions"

# Let's send a request and see what route_trace header or error Lemonade returns
payload = {
    "model": "user.cohezion-router",
    "messages": [{"role": "user", "content": "What is the speed of light?"}],
    "max_tokens": 10
}

req = urllib.request.Request(url, headers={"Content-Type": "application/json"}, data=json.dumps(payload).encode())
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        print("Status:", resp.status)
        print("Headers:", dict(resp.headers))
        print("Body:", resp.read().decode())
except Exception as e:
    print("Error:", e)
