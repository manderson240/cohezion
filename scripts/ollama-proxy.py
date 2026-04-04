#!/usr/bin/env python3
"""Simple Anthropic-to-Ollama proxy."""
import json
import socketserver
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import uuid
import sys

OLLAMA_BASE = "http://localhost:11434"
MODEL_MAP = {
    "claude-opus-4-6": "gemma4:26b",
    "claude-sonnet-4-6": "gemma4:e4b",
    "claude-haiku-4-5-20251213": "phi3:mini",
    "opus": "gemma4:26b",
    "sonnet": "gemma4:e4b",
    "haiku": "phi3:mini",
}
DEFAULT_MODEL = "phi3:mini"


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    
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
            print(f"Body: {body[:200]}", flush=True)
            request = json.loads(body)
            
            model = MODEL_MAP.get(request.get("model", DEFAULT_MODEL), DEFAULT_MODEL)
            print(f"Model: {model}", flush=True)
            
            # Build prompt
            lines = []
            for msg in request.get("messages", []):
                role = msg.get("role", "user").capitalize()
                content = msg.get("content", "")
                if isinstance(content, list):
                    parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
                    content = "\n".join(parts)
                lines.append(f"{role}: {content}")
            lines.append("Assistant:")
            prompt = "\n".join(lines)
            
            # Call Ollama
            ollama_req = json.dumps({
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": request.get("max_tokens", 1024)}
            }).encode()
            
            oreq = urllib.request.Request(
                f"{OLLAMA_BASE}/api/generate",
                data=ollama_req,
                headers={"Content-Type": "application/json"}
            )
            
            print(f"Calling Ollama...", flush=True)
            with urllib.request.urlopen(oreq, timeout=120) as resp:
                result = json.loads(resp.read().decode())
            
            print(f"Ollama returned: {len(result.get('response', ''))} chars", flush=True)
            
            content = result.get("response", "")
            
            response = {
                "id": f"msg_{uuid.uuid4().hex[:24]}",
                "type": "message",
                "role": "assistant",
                "model": request.get("model", DEFAULT_MODEL),
                "content": [{"type": "text", "text": content}],
                "stop_reason": "end_turn",
                "usage": {
                    "input_tokens": result.get("prompt_eval_count", 0),
                    "output_tokens": result.get("eval_count", 0),
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
    print(f"Proxy on http://127.0.0.1:{port}")
    print(f"Ollama: {OLLAMA_BASE}")
    print(f"Usage: ANTHROPIC_BASE_URL=http://localhost:{port} ANTHROPIC_API_KEY=x ./target/release/claw")
    server.serve_forever()


if __name__ == "__main__":
    main()