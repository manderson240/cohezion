#!/usr/bin/env python3
"""
Local Ollama Model Manager

Manages local Ollama models for GPU kernel optimization research.
Features:
- Load/unload models
- Context size optimization
- Memory monitoring
- Parallel inference

Usage:
    python local_model_manager.py list
    python local_model_manager.py load qwen2.5-coder:14b
    python local_model_manager.py unload qwen2.5-coder:14b
    python local_model_manager.py test qwen2.5-coder:14b
    python local_model_manager.py stats
"""

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass

import psutil


@dataclass
class ModelInfo:
    name: str
    size_gb: float
    context_length: int
    quantization: str
    loaded: bool = False
    memory_mb: float = 0.0


class OllamaManager:
    """Manages Ollama models for local inference."""

    # Models and their optimized context sizes
    OPTIMIZED_MODELS = {
        "qwen2.5-coder:14b": {
            "context": 131072,  # 128K (safe limit)
            "threads": 16,
            "gpu": 0,  # CPU only on this machine
        },
        "deepseek-r1:7b": {
            "context": 131072,  # 128K
            "threads": 16,
            "gpu": 0,
        },
        "qwen2.5-coder:7b": {
            "context": 32768,  # Max for this model
            "threads": 8,
            "gpu": 0,
        },
        "gemma3:4b-256k": {
            "context": 131072,  # Gemma3 benefits from smaller ctx
            "threads": 8,
            "gpu": 0,
        },
        "cohezion_v2": {
            "context": 40960,  # Capped by model
            "threads": 8,
            "gpu": 0,
        },
    }

    def __init__(self):
        self.api_base = "http://localhost:11434/api"
        self.process = psutil.Process()

    def _curl(self, endpoint: str, data: dict = None, timeout: int = 5) -> dict:
        """Make curl request to Ollama API."""
        cmd = ["curl", "-s", f"{self.api_base}/{endpoint}"]
        if data:
            import urllib.error
            import urllib.request

            req = urllib.request.Request(
                f"{self.api_base}/{endpoint}",
                data=json.dumps(data).encode(),
                headers={"Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    return json.loads(resp.read())
            except urllib.error.URLError as e:
                return {"error": str(e)}
        else:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            if result.returncode == 0:
                return json.loads(result.stdout)
            return {"error": result.stderr}

    def list_models(self) -> list[ModelInfo]:
        """List all available models."""
        response = self._curl("tags")
        models = []

        for model in response.get("models", []):
            name = model.get("name", "unknown")
            size_bytes = model.get("size", 0)

            # Get detailed info
            info = self._curl("show", {"name": name}, timeout=10)

            ctx_length = 0
            quant = "unknown"
            for line in info.get("details", "").split("\n"):
                if "context length" in line:
                    ctx_length = int(line.split(":")[-1].strip())
                elif "quantization" in line:
                    quant = line.split(":")[-1].strip()

            models.append(
                ModelInfo(
                    name=name,
                    size_gb=size_bytes / (1024**3),
                    context_length=ctx_length,
                    quantization=quant,
                )
            )

        return models

    def load_model(self, name: str, context: int = None, threads: int = None) -> bool:
        """Load a model into memory."""
        if name not in self.OPTIMIZED_MODELS:
            print(f"Warning: {name} not in optimized list, using defaults")
            opts = {}
        else:
            opts = self.OPTIMIZED_MODELS[name].copy()

        if context:
            opts["num_ctx"] = context
        if threads:
            opts["num_thread"] = threads

        opts.setdefault("num_ctx", 32768)
        opts.setdefault("num_thread", 8)
        opts.setdefault("num_gpu", 0)

        print(
            f"Loading {name} with context={opts['num_ctx']}, threads={opts.get('num_thread', 'auto')}"
        )

        # Generate a small prompt to trigger loading
        response = self._curl(
            "generate",
            {"model": name, "prompt": "Hello", "stream": False, "options": opts},
            timeout=60,
        )

        if "error" in response:
            print(f"Error loading model: {response['error']}")
            return False

        print(f"Model {name} loaded successfully")
        return True

    def unload_model(self, name: str) -> bool:
        """Unload a model (stop the runner process)."""
        # Find and kill the runner process
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                cmdline = proc.info.get("cmdline", [])
                if cmdline and "ollama" in " ".join(cmdline) and name in " ".join(cmdline):
                    print(f"Killing Ollama runner for {name}: PID {proc.pid}")
                    proc.terminate()
                    proc.wait(timeout=5)
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        print(f"Could not find running process for {name}")
        return False

    def generate(
        self,
        model: str,
        prompt: str,
        context: int = None,
        system: str = None,
        temperature: float = 0.7,
        stream: bool = False,
    ) -> dict:
        """Generate text with a model."""
        opts = {
            "num_ctx": context or self.OPTIMIZED_MODELS.get(model, {}).get("context", 32768),
            "num_gpu": 0,  # CPU only
            "temperature": temperature,
        }

        if system:
            prompt = f"{system}\n\n{prompt}"

        data = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
            "options": opts,
        }

        response = self._curl("generate", data, timeout=300)
        return response

    def test_model(self, model: str, context: int = None) -> dict:
        """Test a model's inference."""
        print(f"\n=== Testing {model} ===")

        # Test 1: Simple prompt
        print("Test 1: Simple prompt...")
        start = time.time()
        response = self.generate(model, "Explain MFMA instructions in one sentence.", context)
        elapsed = time.time() - start

        if "error" in response:
            print(f"Error: {response['error']}")
            return {"error": response["error"]}

        print(f"Response: {response.get('response', 'N/A')[:200]}")
        print(f"Time: {elapsed:.2f}s")

        # Test 2: Context handling
        print("\nTest 2: Long context handling...")
        long_prompt = "Explain " + "GPU kernel optimization. " * 1000
        start = time.time()
        response = self.generate(model, long_prompt, context)
        elapsed = time.time() - start

        if "error" not in response:
            print(f"Long prompt processed successfully ({elapsed:.2f}s)")
            print(f"Response: {response.get('response', '')[:200]}")
        else:
            print(f"Long prompt failed: {response['error']}")

        return {
            "model": model,
            "context": context,
            "time": elapsed,
            "success": "error" not in response,
        }

    def get_memory_stats(self) -> dict:
        """Get memory usage statistics."""
        mem = psutil.virtual_memory()

        # Find Ollama processes
        ollama_procs = []
        for proc in psutil.process_iter(["pid", "name", "cmdline", "memory_info"]):
            try:
                if "ollama" in proc.info["name"].lower():
                    ollama_procs.append(
                        {
                            "pid": proc.pid,
                            "name": " ".join(proc.info["cmdline"][:3]),
                            "memory_mb": proc.info["memory_info"].rss / (1024**2),
                        }
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        return {
            "system": {
                "total_gb": mem.total / (1024**3),
                "available_gb": mem.available / (1024**3),
                "used_gb": mem.used / (1024**3),
                "percent": mem.percent,
            },
            "ollama_processes": ollama_procs,
            "total_ollama_mb": sum(p["memory_mb"] for p in ollama_procs),
        }

    def stats(self):
        """Print statistics."""
        stats = self.get_memory_stats()

        print("\n=== SYSTEM MEMORY ===")
        s = stats["system"]
        print(f"Total: {s['total_gb']:.1f} GB")
        print(f"Available: {s['available_gb']:.1f} GB")
        print(f"Used: {s['used_gb']:.1f} GB ({s['percent']:.1f}%)")

        print("\n=== OLLAMA PROCESSES ===")
        for proc in stats["ollama_processes"]:
            print(f"  PID {proc['pid']}: {proc['memory_mb']:.1f} MB - {proc['name'][:60]}")

        print(
            f"\nTotal Ollama Memory: {stats['total_ollama_mb']:.1f} MB ({stats['total_ollama_mb'] / 1024:.2f} GB)"
        )


def main():
    parser = argparse.ArgumentParser(description="Ollama Model Manager")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list", help="List available models")

    load_parser = subparsers.add_parser("load", help="Load a model")
    load_parser.add_argument("model", help="Model name")
    load_parser.add_argument("--context", type=int, help="Context size")
    load_parser.add_argument("--threads", type=int, help="CPU threads")

    unload_parser = subparsers.add_parser("unload", help="Unload a model")
    unload_parser.add_argument("model", help="Model name")

    test_parser = subparsers.add_parser("test", help="Test a model")
    test_parser.add_argument("model", help="Model name")
    test_parser.add_argument("--context", type=int, help="Context size")

    subparsers.add_parser("stats", help="Show memory statistics")

    args = parser.parse_args()

    manager = OllamaManager()

    if args.command == "list":
        models = manager.list_models()
        print("\n=== AVAILABLE MODELS ===")
        for m in models:
            loaded = " [LOADED]" if m.loaded else ""
            print(f"  {m.name}")
            print(
                f"    Size: {m.size_gb:.1f} GB | Context: {m.context_length} | Quant: {m.quantization}{loaded}"
            )

    elif args.command == "load":
        success = manager.load_model(args.model, args.context, args.threads)
        sys.exit(0 if success else 1)

    elif args.command == "unload":
        success = manager.unload_model(args.model)
        sys.exit(0 if success else 1)

    elif args.command == "test":
        result = manager.test_model(args.model, args.context)
        if "error" in result:
            sys.exit(1)

    elif args.command == "stats":
        manager.stats()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
