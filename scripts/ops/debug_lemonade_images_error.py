import base64
import json
import urllib.request


with open("/home/mike-anderson/dev/cohezion/docs/assets/matsumoto_plates/track_photo_page_139.png", "rb") as f:
    b64 = base64.b64encode(f.read()).decode("utf-8")

payload = {
    "model": "TRELLIS-3D",
    "prompt": "3d reconstruction of takaaki matsumoto nuclear track ring",
    "image": f"data:image/png;base64,{b64}"
}

req = urllib.request.Request(
    "http://localhost:13305/v1/images/generations",
    headers={"Content-Type": "application/json"},
    data=json.dumps(payload).encode("utf-8")
)

try:
    with urllib.request.urlopen(req) as resp:
        print("Success:", resp.read()[:200])
except urllib.error.HTTPError as e:
    print("HTTP Error Body:", e.read().decode("utf-8"))
except Exception as e:
    print("Other error:", e)
