#!/usr/bin/env python3
"""
Anthropic-to-Ollama API Proxy with Gemma 4 Optimization

Converts Anthropic API requests to Ollama native format.
Optimized for AMD ROCm with 128GB unified memory.

Usage:
  python3 scripts/ollama-proxy.py [port]

Environment variables:
  ANTHROPIC_BASE_URL=http://localhost:8082
  ANTHROPIC_API_KEY=unused

Model mapping:
  haiku  -> gemma4:e4b (default, 9.6GB, balanced)
  sonnet -> gemma4:26b (18GB, MoE efficiency)
  opus   -> gemma4:31b (20GB, maximum quality)
"""

import json
import socketserver
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import uuid
import sys
import os

OLLAMA_BASE = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# Model mapping optimized for this system
# Cloud models (NO OOM risk - runs on ollama.com):
# - gemma4:31b-cloud: Best quality, zero local memory
# - gemma4:31b-cloud: Maximum quality, 256K context
MODEL_MAP = {
    # === CLOUD MODELS (RECOMMENDED - No OOM risk) ===
    "claude-opus-4-6": "gemma4:31b-cloud",
    "claude-sonnet-4-6": "gemma4:31b-cloud",
    "claude-haiku-4-5-20251213": "gemma4:e4b",  # Use local for fast response
    "opus-cloud": "gemma4:31b-cloud",
    "sonnet-cloud": "gemma4:31b-cloud",
    "haiku-cloud": "gemma4:31b-cloud",
    # === LOCAL MODELS (Memory-safe with limits) ===
    "opus": "gemma4:31b",  # 20GB - Max quality, 32K context ONLY
    "sonnet": "gemma4:26b",  # 18GB - MoE efficiency, 32K context
    "haiku": "gemma4:e4b",  # 9.6GB - Balanced, 64K context
    "fast": "phi3:mini",  # 2.2GB - Fastest, 128K context
    # === DIRECT ACCESS ===
    "cloud": "gemma4:31b-cloud",  # 31B cloud model
    "gemma4": "gemma4:e4b",
    "gemma4-e2b": "gemma4:e2b",
    "gemma4-e4b": "gemma4:e4b",
    "gemma4-26b": "gemma4:26b",
    "gemma4-31b": "gemma4:31b",
    "gemma4-31b-cloud": "gemma4:31b-cloud",
    "devstral": "devstral-small-2:24b",
    "phi3": "phi3:mini",
}
DEFAULT_MODEL = "gemma4:e4b"  # Safe default for local
DEFAULT_MODEL_CLOUD = "gemma4:31b-cloud"  # Best for complex tasks

# Gemma 4 recommended sampling parameters
SAMPLING_DEFAULTS = {
    "temperature": 1.0,
    "top_p": 0.95,
    "top_k": 64,
}

# Context window limits by model (to prevent OOM on unified memory)
# Based on Ollama research: https://ollama.com/library/gemma4
# Memory scales roughly: Model Size + (Context Length × Hidden Dim × Layers × 2 bytes)
MODEL_CONTEXT_LIMITS = {
    # Edge models - 128K native context
    "gemma4:e2b": 131072,  # 7.2GB - Can use full 128K
    "gemma4:e4b": 131072,  # 9.6GB - Can use full 128K
    # Workstation models - 256K native, but limit for memory safety
    "gemma4:26b": 32768,  # 18GB MoE - Limit to 32K (MoE is memory efficient)
    "gemma4:31b": 32768,  # 20GB Dense - Limit to 32K (more memory intensive)
    # Cloud model - no local memory limits
    "gemma4:31b-cloud": 262144,  # Runs on cloud, full 256K
    # Fast model - efficient
    "phi3:mini": 131072,  # 2.2GB - Can use full 128K
    # Default
    "default": 32768,  # Safe default for unified memory
}

# Default context (safe for unified memory - prevents OOM)
DEFAULT_NUM_CTX = 32768


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):
        model = getattr(self, "current_model", "unknown")
        print(f"[{self.log_date_time_string()}] [{model}] {format % args}", flush=True)

    def do_GET(self):
        self.send_error(501, "Use POST /v1/messages")

    def do_POST(self):
        print(f"\n=== POST {self.path} ===", flush=True)
        if self.path != "/v1/messages":
            self.send_error(404, "Not Found")
            return

        try:
            cl = int(self.headers.get("Content-Length", 0))
            print(f"Content-Length: {cl}", flush=True)
            body = self.rfile.read(cl).decode() if cl > 0 else "{}"
            print(f"Body: {body[:500]}..." if len(body) > 500 else f"Body: {body}", flush=True)
            request = json.loads(body)

            # Get model and map to Ollama
            requested_model = request.get("model", DEFAULT_MODEL)
            model = MODEL_MAP.get(requested_model, MODEL_MAP.get(DEFAULT_MODEL, DEFAULT_MODEL))
            self.current_model = model
            print(f"Model: {requested_model} -> {model}", flush=True)

            # Build prompt from messages
            lines = []

            # Add system prompt if present
            system = request.get("system", "")
            if system:
                lines.append(f"System: {system}")

            # Process messages
            for msg in request.get("messages", []):
                role = msg.get("role", "user").capitalize()
                content = msg.get("content", "")

                # Handle content array
                if isinstance(content, list):
                    parts = []
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "text":
                                parts.append(block.get("text", ""))
                            elif block.get("type") == "tool_result":
                                parts.append(str(block.get("content", "")))
                        else:
                            parts.append(str(block))
                    content = "\n".join(parts)

                lines.append(f"{role}: {content}")

            lines.append("Assistant:")
            prompt = "\n".join(lines)

            # Build Ollama request with Gemma 4 optimized settings
            max_tokens = request.get("max_tokens", 4096)

            # Get context window size - prioritize from request, then model limits, then default
            # This prevents OOM on unified memory systems
            requested_ctx = request.get("metadata", {}).get("num_ctx")
            model_ctx_limit = MODEL_CONTEXT_LIMITS.get(model, MODEL_CONTEXT_LIMITS["default"])

            if requested_ctx:
                # Client specified context - enforce model limit
                num_ctx = min(requested_ctx, model_ctx_limit)
                print(
                    f"Context: {num_ctx} (requested: {requested_ctx}, limit: {model_ctx_limit})",
                    flush=True,
                )
            else:
                # Use safe default for model
                num_ctx = min(DEFAULT_NUM_CTX, model_ctx_limit)

            ollama_request = {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": max_tokens,
                    "num_ctx": num_ctx,
                    "temperature": SAMPLING_DEFAULTS["temperature"],
                    "top_p": SAMPLING_DEFAULTS["top_p"],
                    "top_k": SAMPLING_DEFAULTS["top_k"],
                },
            }

            # Call Ollama
            print(f"Calling Ollama ({model})...", flush=True)
            ollama_url = f"{OLLAMA_BASE}/api/generate"
            oreq_data = json.dumps(ollama_request).encode()
            oreq = urllib.request.Request(
                ollama_url, data=oreq_data, headers={"Content-Type": "application/json"}
            )

            timeout = 300  # 5 minutes for large models
            with urllib.request.urlopen(oreq, timeout=timeout) as resp:
                result = json.loads(resp.read().decode())

            content = result.get("response", "")
            prompt_tokens = result.get("prompt_eval_count", 0)
            completion_tokens = result.get("eval_count", 0)

            print(
                f"Ollama returned: {len(content)} chars, {prompt_tokens}+{completion_tokens} tokens",
                flush=True,
            )

            # Build Anthropic-compatible response
            response = {
                "id": f"msg_{uuid.uuid4().hex[:24]}",
                "type": "message",
                "role": "assistant",
                "model": requested_model,  # Return requested model name
                "content": [{"type": "text", "text": content}],
                "stop_reason": "end_turn",
                "usage": {
                    "input_tokens": prompt_tokens,
                    "output_tokens": completion_tokens,
                },
            }

            body_bytes = json.dumps(response).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body_bytes)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body_bytes)
            self.wfile.flush()
            print(f"Sent {len(body_bytes)} bytes", flush=True)

        except Exception as e:
            import traceback

            traceback.print_exc()
            self.send_error(500, str(e))


class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    pass


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8082
    server = ThreadedHTTPServer(("127.0.0.1", port), Handler)

    print(f"""
╔═══════════════════════════════════════════════════════════════╗
║     Anthropic-to-Ollama Proxy (Gemma 4 Optimized)            ║
╠═══════════════════════════════════════════════════════════════╣
║  Proxy:     http://127.0.0.1:{port:<5}                          ║
║  Ollama:    {OLLAMA_BASE:<43}║
╠═══════════════════════════════════════════════════════════════╣
║  Model Mapping:                                              ║
║  haiku  -> gemma4:e4b  (9.6GB, balanced, default)            ║
║  sonnet -> gemma4:26b  (18GB, MoE efficiency, 256K context)   ║
║  opus   -> gemma4:31b  (20GB, maximum quality, 256K context)  ║
║  fast   -> phi3:mini  (2.2GB, fastest)                        ║
╠═══════════════════════════════════════════════════════════════╣
║  Gemma 4 Best Practices:                                     ║
║  - temperature: 1.0                                           ║
║  - top_p: 0.95                                               ║
║  - top_k: 64                                                 ║
║  - 26B MoE: Near-e4b speed with better quality                ║
╚═══════════════════════════════════════════════════════════════╝

Usage:
  cd claw-code
  ANTHROPIC_BASE_URL=http://localhost:{port} ANTHROPIC_API_KEY=unused \\
    ./target/release/claw --model haiku

""")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...", flush=True)
        server.shutdown()


if __name__ == "__main__":
    main()
