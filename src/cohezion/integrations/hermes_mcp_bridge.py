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

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any


# === Path setup for Cohezion imports ===
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parents[2]  # src/cohezion/integrations/ -> src/cohezion/ -> src/ -> project_root
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
        registry["skills"].append({
            "name": name,
            "category": category,
            "path": str(fpath),
        })
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
        is_cohezion = any(tag in text for tag in ["project: cohezion", "cohezion", "legacy-name:", "converted: true"])
        if not is_cohezion:
            continue
        rel = root.relative_to(hermes_skills_dir)
        parts = rel.parts
        skill_name = parts[-2] if len(parts) >= 2 else root.parent.name
        category = parts[0] if parts else "unknown"
        skills.append({
            "name": skill_name,
            "category": category,
            "full_path": str(root),
        })
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
        results.append({
            "path": str(p.relative_to(root_path)),
            "lines": lines,
            "depth": depth,
        })
    return results


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
            "inputSchema": {"type": "object", "properties": {}}},
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
    ]


# === MCP Tool Handlers ===
def _handle_crawl(args: dict) -> dict:
    sub = args.get("subdirectory", "").strip().strip("/")
    root = Path(PROJECT_ROOT) / "src" / "cohezion" / sub if sub else Path(PROJECT_ROOT) / "src" / "cohezion"
    if not root.exists():
        return {"error": f"Path not found: {root}"}
    tree = _crawl_tree(str(root), max_depth=args.get("max_depth", 4), pattern=args.get("pattern", "*.py"))
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
    chunk = lines[offset:offset + limit]
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
    cmd = args["command"]
    timeout = args.get("timeout", 60)
    python = _resolve_python()
    return _run_command([python, "-m", "cohezion"] + cmd.split(), timeout=timeout)


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
    chunk = lines[offset:offset + limit]
    return {
        "path": rel,
        "total_lines": len(lines),
        "offset": offset + 1,
        "content": "\n".join(f"{i + offset + 1}|{ln}" for i, ln in enumerate(chunk)),
    }


_TOOL_DISPATCH = {
    "cohezion_crawl_codebase": _handle_crawl,
    "cohezion_list_skills": _handle_list_skills,
    "cohezion_get_skill": _handle_get_skill,
    "cohezion_port_skill_to_hermes": _handle_port_skill,
    "cohezion_batch_port_skills": _handle_batch_port,
    "cohezion_run_cli": _handle_run_cli,
    "cohezion_hermes_status": _handle_status,
    "cohezion_read_source": _handle_read_source,
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
            print(json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "cohezion-hermes-bridge", "version": "1.0.0"},
                },
            }))

        elif method == "tools/list":
            print(json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": _tools_list()},
            }))

        elif method == "tools/call":
            params = request.get("params", {})
            name = params.get("name", "")
            arguments = params.get("arguments", {})
            handler = _TOOL_DISPATCH.get(name)
            try:
                if handler is None:
                    raise ValueError(f"Unknown tool: {name}")
                result = handler(arguments)
                print(json.dumps({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]},
                }))
            except Exception as exc:
                logger.error("Tool call error: %s", exc)
                print(json.dumps({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32000, "message": str(exc)},
                }))

        else:
            print(json.dumps({
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method '{method}' not found"},
            }))

        sys.stdout.flush()


if __name__ == "__main__":
    _try_imports()
    run_mcp_stdio()
