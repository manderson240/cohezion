#!/usr/bin/env python3
"""
Anthropic-to-Ollama API Proxy

Converts Anthropic API requests to Ollama native format.
"""

import json
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request
import urllib.error
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


def call_ollama(request: dict) -> dict:
    """Call Ollama native API."""
    model = request.get("model", DEFAULT_MODEL)
    ollama_model = MODEL_MAP.get(model, model)
    
    # Build prompt from messages
    lines = []
    
    system = request.get("system", "")
    if system:
        lines.append(f"System: {system}")
    
    for msg in request.get("messages", []):
        role = msg.get("role", "user")
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
        
        lines.append(f"{role.capitalize()}: {content}")
    
    lines.append("Assistant:")
    prompt = "\n".join(lines)
    
    ollama_request = {
        "model": ollama_model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": request.get("max_tokens", 1024),
        }
    }
    
    url = f"{OLLAMA_BASE}/api/generate"
    data = json.dumps(ollama_request).encode("utf-8")
    
    print(f"[OLLAMA] Calling {ollama_model} with {len(prompt)} chars prompt", flush=True)
    
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
            print(f"[OLLAMA] Got response: {len(result.get('response', ''))} chars", flush=True)
            return {
                "content": result.get("response", ""),
                "prompt_tokens": result.get("prompt_eval_count", 0),
                "completion_tokens": result.get("eval_count", 0),
            }
    except Exception as e:
        print(f"[OLLAMA] Error: {e}", flush=True)
        return {"error": str(e)}


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    
    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}", flush=True)
    
    def do_GET(self):
        self.send_error(501, "Use POST /v1/messages")
    
    def do_POST(self):
        print(f"\n=== POST {self.path} ===", flush=True)
        
        if self.path != "/v1/messages":
            self.send_error(404, "Not Found")
            return
        
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        print(f"Body: {body[:200]}..." if len(body) > 200 else f"Body: {body}", flush=True)
        
        try:
            request = json.loads(body)
        except json.JSONDecodeError as e:
            print(f"JSON Error: {e}", flush=True)
            self.send_error(400, "Invalid JSON")
            return
        
        model = request.get("model", DEFAULT_MODEL)
        result = call_ollama(request)
        
        if "error" in result:
            response = {
                "type": "error",
                "error": {"type": "api_error", "message": result["error"]}
            }
        else:
            response = {
                "id": f"msg_{uuid.uuid4().hex[:24]}",
                "type": "message",
                "role": "assistant",
                "model": model,
                "content": [{"type": "text", "text": result.get("content", "")}],
                "stop_reason": "end_turn",
                "usage": {
                    "input_tokens": result.get("prompt_tokens", 0),
                    "output_tokens": result.get("completion_tokens", 0),
                },
            }
        
        body = json.dumps(response).encode("utf-8")
        print(f"Sending {len(body)} bytes", flush=True)
        
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)
        print("Done!", flush=True)


class ThreadedHTTPServer(HTTPServer):
    """Handle requests in separate threads."""
    def process_request(self, request, client_address):
        thread = threading.Thread(target=self.process_request_thread, args=(request, client_address))
        thread.daemon = True
        thread.start()
    
    def process_request_thread(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except Exception:
            self.handle_error(request, client_address)
        finally:
            self.shutdown_request(request)


def main():
    port = 8082
    server = ThreadedHTTPServer(("127.0.0.1", port), Handler)
    print(f"Anthropic-to-Ollama proxy on http://127.0.0.1:{port}")
    print(f"Ollama: {OLLAMA_BASE}")
    print(f"Models: {MODEL_MAP}")
    print(f"\nUsage:")
    print(f"  ANTHROPIC_BASE_URL=http://localhost:{port} ANTHROPIC_API_KEY=unused ./target/release/claw")
    print(flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...", flush=True)
        server.shutdown()


if __name__ == "__main__":
    main()