#!/usr/bin/env python3
"""Serve SemIf/OpenJev 0.8B as the DQA content judge for `cohezion.compound.semif_gate`.

Runs in its OWN venv, not the repo's: the checkpoint is `qwen3_5`, which needs transformers >= 5,
while the repo pins 4.57 under torch/ROCm. Keeping it out-of-process is what lets the gate exist
without moving those pins.

    /home/mike-anderson/dev/cohezion/.cache/clones/von-venv/bin/python \
        scripts/ops/semif_dqa_server.py            # listens on 127.0.0.1:13399

POST /score  {"task": "...", "response": "..."}  ->  {"p": 0.97, "ms": 812}
GET  /health                                     ->  {"ok": true, "model": "...", "loaded_s": 12.4}

Localhost only: this loads a 1.5 GB model and runs untrusted text through it; it is not hardened
for anything but loopback.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer


DEFAULT_MODEL = "/home/mike-anderson/dev/cohezion/.cache/clones/openjev-semif"
SUBFOLDER = "qwen3.5-0.8b-nli-v2s-long"
# Pinned wording: the same hypothesis the 114-case measurement used. Changing it invalidates the
# calibrated threshold in semif_gate.VETO_THRESHOLD (these judges are wording-sensitive).
HYPOTHESIS = "The RESPONSE correctly and completely answers the TASK."

_JEV = None
_LOADED_S = 0.0


def _load(model_dir: str):
    global _JEV, _LOADED_S
    sys.path.insert(0, model_dir)
    from modeling_openjev import OpenJevCrossEncoder

    t0 = time.time()
    _JEV = OpenJevCrossEncoder(model_dir, subfolder=SUBFOLDER)
    # Warm the graph before /health reports ok. The FIRST scored call is several seconds while a
    # warm one is ~200 ms; without this the client's 2 s timeout trips its circuit breaker on the
    # very first request and the gate stays silent for BREAKER_SECONDS (observed 2026-09-22).
    p_yes("warmup", "warmup")
    _LOADED_S = time.time() - t0
    print(f"SemIf loaded+warmed in {_LOADED_S:.1f}s from {model_dir}/{SUBFOLDER}", flush=True)


def p_yes(task: str, response: str) -> float:
    premise = f"TASK: {task}\nRESPONSE: {response}"
    row = _JEV.predict([(premise, HYPOTHESIS)])[0]
    return float(row[1])  # [contradiction, entailment, neutral]


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send(200, {"ok": _JEV is not None, "model": SUBFOLDER, "loaded_s": _LOADED_S})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path != "/score":
            self._send(404, {"error": "not found"})
            return
        try:
            n = int(self.headers.get("Content-Length", "0"))
            d = json.loads(self.rfile.read(n) or b"{}")
            t0 = time.time()
            p = p_yes(d.get("task", ""), d.get("response", ""))
            self._send(200, {"p": p, "ms": round((time.time() - t0) * 1000)})
        except Exception as e:  # a judge failure must look like "unavailable", not like a verdict
            self._send(500, {"error": f"{type(e).__name__}: {e}"})

    def log_message(self, fmt, *args):  # quiet
        pass


def main() -> int:
    ap = argparse.ArgumentParser(description="SemIf DQA judge server")
    ap.add_argument("--model-dir", default=DEFAULT_MODEL)
    ap.add_argument("--port", type=int, default=13399)
    a = ap.parse_args()
    _load(a.model_dir)
    print(f"listening on 127.0.0.1:{a.port}", flush=True)
    HTTPServer(("127.0.0.1", a.port), Handler).serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
