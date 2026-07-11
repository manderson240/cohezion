"""
Cohezion MCP Bridge for Hermes Agent
=====================================
Hermes-native MCP bridge that exposes Cohezion capabilities
to Hermes via stdio JSON-RPC protocol.

Usage:
    hermes mcp add cohezion \
        --command "python3" \
        --args "src/cohezion/integrations/hermes_mcp_bridge.py"
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any


# === Path setup for Cohezion imports ===
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[
    2
]  # src/cohezion/integrations/ -> src/cohezion/ -> src/ -> project_root
cohezion_src = PROJECT_ROOT / "src"
if str(cohezion_src) not in sys.path:
    sys.path.insert(0, str(cohezion_src))

# Optional: set COHEZION_ROOT env var for downstream modules
os.environ.setdefault("COHEZION_ROOT", str(PROJECT_ROOT))

# === Logging (stderr only — stdout is the MCP channel) ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [MCP] %(levelname)s: %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger("cohezion-hermes-bridge")

# === Optional Cohezion imports (best-effort) ===
_resource_monitor: Any = None
_hallucination_resolver: Any = None
_offload_manager: Any = None


def _try_imports():
    global _resource_monitor, _hallucination_resolver, _offload_manager
    try:
        from cohezion.reliability.monitor import ResourceMonitor

        _resource_monitor = ResourceMonitor()
    except Exception:
        pass
    try:
        from cohezion.reliability.resolver import HallucinationResolver

        _hallucination_resolver = HallucinationResolver()
    except Exception:
        pass
    try:
        from cohezion.reliability.offload_manager import OffloadManager

        _offload_manager = OffloadManager()
    except Exception:
        pass


# === Skill discovery from local filesystem ===
def _cohezion_skill_registry() -> dict[str, Any]:
    """Load Cohezion skill metadata from src/cohezion/skills/*.md."""
    registry: dict[str, Any] = {"skills": [], "categories": set()}
    skills_dir = Path(PROJECT_ROOT) / "src" / "cohezion" / "skills"
    if not skills_dir.exists():
        return registry

    for fpath in sorted(skills_dir.glob("*.md")):
        name = fpath.stem
        # Skip non-skill files
        if "README" in name or name.startswith("__"):
            continue
        first_lines = "\n".join(fpath.read_text(encoding="utf-8").splitlines()[:20])
        # Guess category from content keywords
        category = "general"
        if "FLUME" in first_lines or "VAE" in first_lines or "manifold" in first_lines.lower():
            category = "mlops"
        elif "MCP" in first_lines or "server" in first_lines.lower():
            category = "mcp"
        elif "HIHO" in first_lines or "stability" in first_lines.lower():
            category = "engineering"
        elif "SWARM" in first_lines or "orchestrat" in first_lines.lower():
            category = "orchestration"
        elif "ARC" in first_lines or "prize" in first_lines.lower():
            category = "competition"
        registry["skills"].append(
            {
                "name": name,
                "category": category,
                "path": str(fpath),
            }
        )
        registry["categories"].add(category)

    registry["categories"] = sorted(registry["categories"])
    return registry


def _list_local_hermes_skills():
    """Discover local Hermes skills linked to Cohezion by reading frontmatter."""
    hermes_skills_dir = Path.home() / ".hermes" / "skills"
    skills = []
    for root in hermes_skills_dir.rglob("SKILL.md"):
        content = root.read_text(encoding="utf-8", errors="ignore").splitlines()[:20]
        text = "\n".join(content)
        # Look for cohezion tag/project in frontmatter
        is_cohezion = any(
            tag in text
            for tag in ["project: cohezion", "cohezion", "legacy-name:", "converted: true"]
        )
        if not is_cohezion:
            continue
        rel = root.relative_to(hermes_skills_dir)
        parts = rel.parts
        skill_name = parts[-2] if len(parts) >= 2 else root.parent.name
        category = parts[0] if parts else "unknown"
        skills.append(
            {
                "name": skill_name,
                "category": category,
                "full_path": str(root),
            }
        )
    return skills


# === File-tree utility for code crawling ===
def _crawl_tree(root: str, max_depth: int = 4, pattern: str = "*.py") -> list[dict]:
    """Return a lightweight tree of Python files with line counts."""
    results: list[dict] = []
    root_path = Path(root).resolve()
    for p in root_path.rglob(pattern):
        depth = len(p.relative_to(root_path).parts) - 1
        if depth > max_depth:
            continue
        try:
            with open(p, "rb") as f:
                lines = sum(1 for _ in f)
        except Exception:
            lines = 0
        results.append(
            {
                "path": str(p.relative_to(root_path)),
                "lines": lines,
                "depth": depth,
            }
        )
    return results


# === Local inference configuration ===
# Tier dispatch defaults route through the :13305 OmniRouter (fans out to
# NPU/iGPU/CPU on demand); still env-overridable for bespoke topologies.
_NPU_PORT = int(os.environ.get("COHEZION_NPU_PORT", 13305))
_IGPU_PORT = int(os.environ.get("COHEZION_IGPU_PORT", 13305))
_CPU_PORT = int(os.environ.get("COHEZION_CPU_PORT", 13305))

# Model IDs loaded by default on each tier (overridable via env)
_NPU_MODEL = os.environ.get("COHEZION_NPU_MODEL", "llama3.2-1b-FLM")
_IGPU_MODEL = os.environ.get("COHEZION_IGPU_MODEL", "Gemma-4-E4B-it-GGUF")
_CPU_MODEL = os.environ.get("COHEZION_CPU_MODEL", "Gemma-4-31B-it-GGUF")


def _lemonade_complete(
    port: int, model_id: str, prompt: str, max_tokens: int = 512, timeout: int = 10
) -> str:
    """Call lemonade OpenAI-compatible /v1/chat/completions. Returns response text or raises."""
    import urllib.request

    payload = json.dumps(
        {
            "model": model_id,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "stream": False,
        }
    ).encode()
    req = urllib.request.Request(
        f"http://localhost:{port}/v1/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        d = json.loads(resp.read())
    return d["choices"][0]["message"]["content"]


def _lemonade_models(port: int, timeout: int = 2) -> list[str]:
    """Return list of model IDs loaded on a lemonade port, or [] on failure."""
    import urllib.request

    try:
        req = urllib.request.Request(f"http://localhost:{port}/v1/models")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            d = json.loads(resp.read())
        return [m["id"] for m in d.get("data", [])]
    except Exception:
        return []


# === Python execution helper ===
def _resolve_python() -> str:
    """Find the right Python: venv first, then sys.executable."""
    venv_candidates = [
        PROJECT_ROOT / ".venv" / "bin" / "python",
        PROJECT_ROOT / ".venv" / "bin" / "python3",
        PROJECT_ROOT / ".venv-arc" / "bin" / "python",
    ]
    for p in venv_candidates:
        if p.exists():
            return str(p)
    return sys.executable


def _run_command(cmd_parts: list[str], timeout: int = 60) -> dict:
    """Execute a subprocess command synchronously."""
    import subprocess  # local import to avoid circular deps

    # Inject PYTHONPATH so cohezion imports work
    env = os.environ.copy()
    src_path = str(PROJECT_ROOT / "src")
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = src_path + os.pathsep + env["PYTHONPATH"]
    else:
        env["PYTHONPATH"] = src_path
    try:
        result = subprocess.run(
            cmd_parts,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(PROJECT_ROOT),
            env=env,
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": f"timed out after {timeout}s"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def _run_python(code: str, timeout: int = 10) -> dict:
    """Execute Python inside the Cohezion environment (best-effort)."""
    return _run_command([_resolve_python(), "-c", code], timeout=timeout)


# === MCP Tool Definitions ===
def _tools_list() -> list[dict[str, Any]]:
    return [
        {
            "name": "cohezion_crawl_codebase",
            "description": (
                "Crawl the Cohezion codebase tree for a given subdirectory. "
                "Returns relative file paths, line counts, and depth."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "subdirectory": {
                        "type": "string",
                        "description": "Subdir under src/cohezion/ to crawl (e.g. 'flume')",
                        "default": "",
                    },
                    "max_depth": {
                        "type": "integer",
                        "description": "Max recursion depth",
                        "default": 4,
                    },
                    "pattern": {
                        "type": "string",
                        "description": "File glob pattern",
                        "default": "*.py",
                    },
                },
                "required": [],
            },
        },
        {
            "name": "cohezion_list_skills",
            "description": (
                "List all Cohezion PRIME skills and categories. "
                "Use this before selecting a skill to execute."
            ),
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "cohezion_get_skill",
            "description": (
                "Read the full content of a named Cohezion PRIME skill. "
                "Input is the .md filename stem (e.g. 'FLUME_METHODOLOGY_PRIME')."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "Skill filename stem",
                    },
                    "max_lines": {
                        "type": "integer",
                        "description": "Max lines to return (default 200)",
                        "default": 200,
                    },
                },
                "required": ["skill_name"],
            },
        },
        {
            "name": "cohezion_port_skill_to_hermes",
            "description": (
                "Port a single Cohezion PRIME skill to Hermes format using the "
                "built-in converter. Writes to ~/.hermes/skills/<category>/<name>/SKILL.md."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "skill_name": {
                        "type": "string",
                        "description": "PRIME skill filename stem (e.g. 'FLUME_METHODOLOGY_PRIME')",
                    },
                    "dry_run": {
                        "type": "boolean",
                        "default": False,
                    },
                },
                "required": ["skill_name"],
            },
        },
        {
            "name": "cohezion_batch_port_skills",
            "description": (
                "Batch-port multiple PRIME skills to Hermes. Accepts a list of skill names."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "skill_names": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of PRIME skill stems",
                    },
                    "dry_run": {"type": "boolean", "default": False},
                },
                "required": ["skill_names"],
            },
        },
        {
            "name": "cohezion_run_cli",
            "description": (
                "Execute a Cohezion CLI command (python -m cohezion …). "
                "Runs safely in project venv with 60s timeout."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": (
                            "CLI sub-command and args, e.g. 'simulate --example hello'"
                        ),
                    },
                    "timeout": {"type": "integer", "default": 60},
                },
                "required": ["command"],
            },
        },
        {
            "name": "cohezion_hermes_status",
            "description": (
                "Return status of the Cohezion ↔ Hermes bridge: "
                "loaded modules, skill counts, local Hermes skill count."
            ),
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "cohezion_read_source",
            "description": (
                "Read a Cohezion source file with optional offset/limit. "
                "Returns line-numbered content."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "relative_path": {
                        "type": "string",
                        "description": "Path relative to project root (e.g. 'src/cohezion/flume/vae.py')",
                    },
                    "offset": {"type": "integer", "default": 1},
                    "limit": {"type": "integer", "default": 100},
                },
                "required": ["relative_path"],
            },
        },
        {
            "name": "cohezion_infer",
            "description": (
                "Send a prompt to the Cohezion local inference stack running on Strix Halo AMD silicon. "
                "Automatically routes NPU → iGPU → CPU (tiered fallback). "
                "NPU (llama3.2-1b-FLM) is fastest (~450ms). "
                "Use tier='npu'/'igpu'/'cpu' to pin to a specific tier, or leave 'auto' for automatic fallback. "
                "Returns the model response along with which tier was used and latency."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "The prompt or question to send to the local model",
                    },
                    "max_tokens": {
                        "type": "integer",
                        "description": "Maximum tokens in the response (default 512)",
                        "default": 512,
                    },
                    "tier": {
                        "type": "string",
                        "description": "Inference tier: 'auto' (default), 'npu', 'igpu', or 'cpu'",
                        "default": "auto",
                        "enum": ["auto", "npu", "igpu", "cpu"],
                    },
                },
                "required": ["prompt"],
            },
        },
        {
            "name": "cohezion_inference_status",
            "description": (
                "Check the status of all Cohezion local inference nodes (NPU/iGPU/CLaSp/CPU). "
                "Reports which nodes are up, which models are loaded, and live TTFT from the NPU. "
                "Also reports available system memory."
            ),
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "cohezion_zerolang_run",
            "description": (
                "Execute a Zerolang (.0) program using the local `zero` CLI. "
                "Accepts either inline code (as a string) or a file path to a .0 file. "
                "Zerolang is an agent-first language designed for AI agents — use cohezion_infer "
                "with tier='igpu' to generate Zerolang code, then pass it here to run it. "
                "Returns stdout, stderr, exit code, and execution latency."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Inline Zerolang source code to execute (use this or file_path)",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to an existing .0 file to run (use this or code)",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Max execution time in seconds (default 15)",
                        "default": 15,
                    },
                },
            },
        },
        {
            "name": "cohezion_zerolang_check",
            "description": (
                "Validate a Zerolang (.0) program without running it. "
                "Returns whether the code is valid and any diagnostic messages. "
                "Use this before cohezion_zerolang_run to catch syntax errors."
            ),
            "inputSchema": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Inline Zerolang source code to validate",
                    },
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to a .0 file to validate",
                    },
                },
            },
        },
    ]


# === MCP Tool Handlers ===
def _handle_crawl(args: dict) -> dict:
    sub = args.get("subdirectory", "").strip().strip("/")
    root = (
        Path(PROJECT_ROOT) / "src" / "cohezion" / sub
        if sub
        else Path(PROJECT_ROOT) / "src" / "cohezion"
    )
    if not root.exists():
        return {"error": f"Path not found: {root}"}
    tree = _crawl_tree(
        str(root), max_depth=args.get("max_depth", 4), pattern=args.get("pattern", "*.py")
    )
    total_lines = sum(n["lines"] for n in tree)
    return {
        "root": str(root.relative_to(PROJECT_ROOT)),
        "files": len(tree),
        "total_lines": total_lines,
        "tree": tree[:200],  # cap for JSON-RCP payload size
    }


def _handle_list_skills(_args: dict) -> dict:
    reg = _cohezion_skill_registry()
    return {
        "count": len(reg["skills"]),
        "categories": reg["categories"],
        "skills": reg["skills"],
        "local_hermes_skills": _list_local_hermes_skills(),
    }


def _handle_get_skill(args: dict) -> dict:
    name = args["skill_name"]
    fpath = Path(PROJECT_ROOT) / "src" / "cohezion" / "skills" / f"{name}.md"
    if not fpath.exists():
        return {"error": f"Skill not found: {name}", "suggestion": f"Looked in {fpath}"}
    lines = fpath.read_text(encoding="utf-8").splitlines()
    limit = args.get("max_lines", 200)
    offset = max(0, args.get("offset", 1) - 1)
    chunk = lines[offset : offset + limit]
    return {
        "skill_name": name,
        "total_lines": len(lines),
        "returned_lines": len(chunk),
        "offset": offset + 1,
        "content": "\n".join(chunk),
    }


def _handle_port_skill(args: dict) -> dict:
    """Delegate to the existing PRIME-to-Hermes converter."""
    name = args["skill_name"]
    dry = args.get("dry_run", False)
    converter = PROJECT_ROOT / "scripts" / "prime_to_hermes_converter.py"
    if not converter.exists():
        return {"error": "Converter script not found", "path": str(converter)}

    cmd_parts = [sys.executable, str(converter), "--skill", name]
    if dry:
        cmd_parts.append("--dry-run")

    import subprocess

    try:
        result = subprocess.run(cmd_parts, capture_output=True, text=True, timeout=30)
        return {
            "skill_name": name,
            "dry_run": dry,
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except Exception as e:
        return {"error": str(e)}


def _handle_batch_port(args: dict) -> dict:
    names = args.get("skill_names", [])
    dry = args.get("dry_run", False)
    results = []
    for name in names:
        results.append({"name": name, **(_handle_port_skill({"skill_name": name, "dry_run": dry}))})
    successes = sum(1 for r in results if r.get("success"))
    return {"total": len(names), "successes": successes, "results": results}


def _handle_run_cli(args: dict) -> dict:
    """Execute a Cohezion CLI command via python -m cohezion."""
    import shlex

    cmd = args["command"]
    timeout = args.get("timeout", 60)
    python = _resolve_python()
    return _run_command([python, "-m", "cohezion", *shlex.split(cmd)], timeout=timeout)


def _handle_status(_args: dict) -> dict:
    reg = _cohezion_skill_registry()
    hermes_local = _list_local_hermes_skills()
    return {
        "bridge_version": "1.0.0",
        "project_root": str(PROJECT_ROOT),
        "cohezion_skills_count": len(reg["skills"]),
        "cohezion_categories": reg["categories"],
        "hermes_local_skills": len(hermes_local),
        "modules_loaded": {
            "resource_monitor": _resource_monitor is not None,
            "hallucination_resolver": _hallucination_resolver is not None,
            "offload_manager": _offload_manager is not None,
        },
    }


def _handle_read_source(args: dict) -> dict:
    rel = args["relative_path"].strip().strip("/")
    fpath = PROJECT_ROOT / rel
    if not fpath.exists():
        return {"error": f"File not found: {fpath}"}
    try:
        lines = fpath.read_text(encoding="utf-8").splitlines()
    except Exception as e:
        return {"error": str(e)}
    offset = max(0, args.get("offset", 1) - 1)
    limit = args.get("limit", 100)
    chunk = lines[offset : offset + limit]
    return {
        "path": rel,
        "total_lines": len(lines),
        "offset": offset + 1,
        "content": "\n".join(f"{i + offset + 1}|{ln}" for i, ln in enumerate(chunk)),
    }


def _handle_infer(args: dict) -> dict:
    """Route a prompt through the local inference stack with tiered fallback."""
    import time

    prompt = args["prompt"]
    max_tokens = args.get("max_tokens", 512)
    tier_pref = args.get("tier", "auto")

    tiers = {
        "npu": (_NPU_PORT, _NPU_MODEL, 5),
        "igpu": (_IGPU_PORT, _IGPU_MODEL, 15),
        "cpu": (_CPU_PORT, _CPU_MODEL, 45),
    }

    if tier_pref != "auto":
        order = [tier_pref] if tier_pref in tiers else list(tiers.keys())
    else:
        order = ["npu", "igpu", "cpu"]

    escalations = 0
    for tier_name in order:
        port, model_id, timeout = tiers[tier_name]
        t0 = time.perf_counter()
        try:
            text = _lemonade_complete(
                port, model_id, prompt, max_tokens=max_tokens, timeout=timeout
            )
            latency_ms = int((time.perf_counter() - t0) * 1000)
            if text and text.strip():
                return {
                    "response": text.strip(),
                    "tier_used": tier_name,
                    "model": model_id,
                    "port": port,
                    "latency_ms": latency_ms,
                    "escalations": escalations,
                }
            # Empty response — escalate
            escalations += 1
            logger.warning("Tier %s returned empty response, escalating", tier_name)
        except Exception as exc:
            escalations += 1
            logger.warning("Tier %s failed (%s), escalating", tier_name, exc)

    return {
        "error": "All inference tiers failed or returned empty",
        "escalations": escalations,
        "tiers_tried": order,
    }


def _handle_inference_status(_args: dict) -> dict:
    """Report live status of all inference nodes and NPU TTFT probe."""
    import time

    # Diagnostic-only: probe each legacy per-lane server's live status for the
    # status report. NOT a dispatch bypass — production traffic goes via :13305.
    # Kept per-port so the report reflects which individual servers are up.
    node_configs = [
        (13306, "npu", _NPU_MODEL),  # allow-direct-port: diagnostic status probe, not dispatch
        (13307, "igpu", _IGPU_MODEL),  # allow-direct-port: diagnostic status probe, not dispatch
        (13308, "clasp", "Gemma-4-E2B-it-GGUF"),  # allow-direct-port: diagnostic status probe
        (13309, "cpu", _CPU_MODEL),  # allow-direct-port: diagnostic status probe, not dispatch
    ]

    nodes = []
    for port, role, default_model in node_configs:
        models = _lemonade_models(port, timeout=2)
        nodes.append(
            {
                "port": port,
                "role": role,
                "status": "up" if models else "offline",
                "loaded_models": models[:3],  # cap list length
            }
        )

    # NPU TTFT probe (1-token completion)
    npu_ttft_ms = None
    if nodes[0]["status"] == "up":
        t0 = time.perf_counter()
        try:
            _lemonade_complete(_NPU_PORT, _NPU_MODEL, "hi", max_tokens=1, timeout=8)
            npu_ttft_ms = int((time.perf_counter() - t0) * 1000)
        except Exception:
            pass

    # Available memory
    mem_available_gib = None
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemAvailable"):
                    mem_available_gib = int(line.split()[1]) // (1024 * 1024)
                    break
    except Exception:
        pass

    # lemonade version
    lemonade_version = None
    try:
        import subprocess

        r = subprocess.run(["lemonade", "--version"], capture_output=True, text=True, timeout=3)
        lemonade_version = r.stdout.strip() or r.stderr.strip()
    except Exception:
        pass

    return {
        "nodes": nodes,
        "npu_ttft_ms": npu_ttft_ms,
        "memory_available_gib": mem_available_gib,
        "lemonade_version": lemonade_version,
    }


def _zerolang_bin() -> str:
    """Return the zero CLI path: ~/.zero/bin/zero if present, else fall back to PATH."""
    candidate = os.path.expanduser("~/.zero/bin/zero")
    return candidate if os.path.exists(candidate) else "zero"


def _zerolang_run_cmd(cmd: str, code: str, file_path: str, timeout: int) -> dict:
    """Shared runner for both 'run' and 'check' subcommands."""
    import subprocess
    import tempfile
    import time

    code = (code or "").strip()
    file_path = (file_path or "").strip()

    if not code and not file_path:
        return {"error": "Provide 'code' (inline source) or 'file_path' (path to .0 file)"}

    cleanup = False
    run_path = file_path
    if code:
        try:
            tmp = tempfile.NamedTemporaryFile(suffix=".0", mode="w", delete=False, encoding="utf-8")
            tmp.write(code)
            tmp.close()
            run_path = tmp.name
            cleanup = True
        except OSError as e:
            return {"error": f"Failed to write temp file: {e}"}

    t0 = time.perf_counter()
    try:
        result = subprocess.run(
            [_zerolang_bin(), cmd, run_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "latency_ms": latency_ms,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"timed out after {timeout}s"}
    except FileNotFoundError:
        return {
            "error": "zero CLI not found — install: curl -fsSL https://zerolang.ai/install.sh | bash"
        }
    finally:
        if cleanup and run_path and os.path.exists(run_path):
            with contextlib.suppress(OSError):
                os.unlink(run_path)


def _handle_zerolang_run(args: dict) -> dict:
    """Execute a Zerolang program with `zero run`."""
    return _zerolang_run_cmd(
        cmd="run",
        code=args.get("code", ""),
        file_path=args.get("file_path", ""),
        timeout=args.get("timeout", 15),
    )


def _handle_zerolang_check(args: dict) -> dict:
    """Validate a Zerolang program with `zero check`."""
    result = _zerolang_run_cmd(
        cmd="check",
        code=args.get("code", ""),
        file_path=args.get("file_path", ""),
        timeout=args.get("timeout", 10),
    )
    if "error" not in result:
        result["valid"] = result["success"]
        result["diagnostics"] = result.get("stderr", "") or result.get("stdout", "")
    return result


_TOOL_DISPATCH = {
    "cohezion_crawl_codebase": _handle_crawl,
    "cohezion_list_skills": _handle_list_skills,
    "cohezion_get_skill": _handle_get_skill,
    "cohezion_port_skill_to_hermes": _handle_port_skill,
    "cohezion_batch_port_skills": _handle_batch_port,
    "cohezion_run_cli": _handle_run_cli,
    "cohezion_hermes_status": _handle_status,
    "cohezion_read_source": _handle_read_source,
    "cohezion_infer": _handle_infer,
    "cohezion_inference_status": _handle_inference_status,
    "cohezion_zerolang_run": _handle_zerolang_run,
    "cohezion_zerolang_check": _handle_zerolang_check,
}


# === MCP stdio loop ===
def run_mcp_stdio():
    """Run the MCP JSON-RPC loop over stdin/stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            logger.warning("Ignoring non-JSON line")
            continue

        req_id = request.get("id")
        method = request.get("method", "")

        if method == "initialize":
            print(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {"tools": {}},
                            "serverInfo": {"name": "cohezion-hermes-bridge", "version": "1.0.0"},
                        },
                    }
                )
            )

        elif method == "tools/list":
            print(
                json.dumps(
                    {
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {"tools": _tools_list()},
                    }
                )
            )

        elif method == "tools/call":
            params = request.get("params", {})
            name = params.get("name", "")
            arguments = params.get("arguments", {})
            handler = _TOOL_DISPATCH.get(name)
            try:
                if handler is None:
                    raise ValueError(f"Unknown tool: {name}")
                result = handler(arguments)
                print(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "result": {
                                "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
                            },
                        }
                    )
                )
            except Exception as exc:
                logger.error("Tool call error: %s", exc)
                print(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "error": {"code": -32000, "message": str(exc)},
                        }
                    )
                )

        else:
            # MCP notifications (e.g. notifications/initialized) have id=None.
            # Sending an error response to a notification is a protocol violation —
            # silently ignore them. Only respond to genuine unknown requests with an id.
            if req_id is not None:
                print(
                    json.dumps(
                        {
                            "jsonrpc": "2.0",
                            "id": req_id,
                            "error": {"code": -32601, "message": f"Method '{method}' not found"},
                        }
                    )
                )
            else:
                logger.debug("Ignoring notification: %s", method)

        sys.stdout.flush()


if __name__ == "__main__":
    _try_imports()
    run_mcp_stdio()
