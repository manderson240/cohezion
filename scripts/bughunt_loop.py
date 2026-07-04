"""Bughunt loop — autonomous local-inference bug scanner for the Cohezion codebase.

Uses Lemonade :13305 (deepseek-r1-0528-8b-FLM, reasoning tier) to scan Python
files for bugs at $0 cost. Part of the quarter-on-a-string protocol.

Findings are appended to ~/.cohezion/bughunt_findings.jsonl for SurrealDB ingestion.
File-scan state (round-robin) lives in ~/.cohezion/bughunt_state.json.

Usage:
    uv run python scripts/bughunt_loop.py              # single pass, 3 files
    uv run python scripts/bughunt_loop.py --loop       # continuous, 60s between scans
    uv run python scripts/bughunt_loop.py --dir src/cohezion/compound --n 5
    uv run python scripts/bughunt_loop.py --file src/cohezion/compound/executor.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path

import httpx

logger = logging.getLogger("bughunt")

# ── Config ─────────────────────────────────────────────────────────────────

LEMONADE_URL = "http://localhost:13305"
PRIMARY_MODEL = "Gemma-4-E4B-it-GGUF"
FALLBACK_MODEL = "Qwen3-0.6B-GGUF"
STATE_PATH = Path.home() / ".cohezion" / "bughunt_state.json"
FINDINGS_PATH = Path.home() / ".cohezion" / "bughunt_findings.jsonl"
MAX_FILE_CHARS = 6000
LOOP_DELAY_SECONDS = 60

_SYSTEM = (
    "You are a Python code auditor. Analyze the provided code for real bugs.\n"
    "Output ONLY a JSON array (no markdown fences, no commentary).\n"
    "Each element: {\"file\": str, \"line\": int|null, \"severity\": "
    "\"critical\"|\"high\"|\"medium\"|\"low\", "
    "\"category\": \"null_deref\"|\"type_error\"|\"async_safety\"|"
    "\"missing_error_handling\"|\"resource_leak\"|\"logic_bug\"|\"security\"|\"dead_code\", "
    "\"description\": str, \"suggested_fix\": str}.\n"
    "Return [] if no bugs found. Only report real bugs, not style issues."
)

_VERIFY_SYSTEM = (
    "You are a skeptical code reviewer. You are given a bug finding report and the relevant code.\n"
    "Your job is to TRY TO REFUTE the finding — look for reasons it might be a false positive.\n"
    "Output ONLY a JSON object: {\"refuted\": true|false, \"reason\": str}.\n"
    "Set refuted=true if the code is actually correct and the finding is wrong.\n"
    "Set refuted=false if the bug is real and cannot be explained away.\n"
    "Default to refuted=true if uncertain."
)


# ── File selection ──────────────────────────────────────────────────────────

def _collect_targets(root: Path) -> list[Path]:
    """Return all .py files under root, excluding __pycache__ and test files."""
    return sorted(
        p for p in root.rglob("*.py")
        if "__pycache__" not in str(p)
        and "test_" not in p.name
        and p.name != "conftest.py"
    )


def _pick_next(targets: list[Path], n: int) -> list[Path]:
    """Round-robin: pick n files starting from last-scanned index."""
    if not targets:
        return []
    state: dict = {}
    if STATE_PATH.exists():
        try:
            state = json.loads(STATE_PATH.read_text())
        except Exception:
            state = {}
    idx = int(state.get("next_idx", 0)) % len(targets)
    picked = [targets[(idx + i) % len(targets)] for i in range(min(n, len(targets)))]
    state["next_idx"] = (idx + n) % len(targets)
    state["last_run"] = datetime.now(UTC).isoformat()
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))
    return picked


# ── Lemonade call ───────────────────────────────────────────────────────────

# Backend map: model → llamacpp_backend required by OmniRouter
_MODEL_BACKENDS: dict[str, str] = {
    PRIMARY_MODEL: "vulkan",  # Gemma-4-E4B: iGPU via Vulkan (~15 TPS)
    FALLBACK_MODEL: "cpu",    # Qwen3-0.6B: tiny, CPU fallback
}


async def _load_model(model: str, lemonade_url: str) -> bool:
    """Pre-load model via /api/v1/load. OmniRouter requires backend on GGUF models."""
    backend = _MODEL_BACKENDS.get(model, "auto")
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{lemonade_url}/api/v1/load",
                json={"model_name": model, "llamacpp_backend": backend, "ctx_size": 4096},
            )
            data = resp.json()
            return data.get("status") == "success"
    except Exception as exc:
        logger.debug("Load request failed for %s: %s", model, exc)
        return False


async def _verify_finding(finding: dict, code: str, model: str, lemonade_url: str) -> bool:
    """Second-pass adversarial check. Returns True if the finding is confirmed (not refuted)."""
    snippet = f"File: {finding.get('file','?')}, line {finding.get('line','?')}\n"
    snippet += f"Bug reported: [{finding.get('severity','?').upper()}] {finding.get('description','')}\n\n"
    snippet += f"```python\n{code[:3000]}\n```"
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                f"{lemonade_url}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": _VERIFY_SYSTEM},
                        {"role": "user", "content": snippet},
                    ],
                    "max_tokens": 200,
                    "temperature": 0.0,
                },
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        logger.debug("Verify call failed: %s", exc)
        return True  # assume confirmed on error (conservative)
    raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    raw = re.sub(r"```(?:json)?\n?(.*?)```", r"\1", raw, flags=re.DOTALL).strip()
    start, end = raw.find("{"), raw.rfind("}") + 1
    if start == -1 or end == 0:
        return True
    try:
        verdict = json.loads(raw[start:end])
        return not verdict.get("refuted", True)  # refuted=True → not confirmed
    except json.JSONDecodeError:
        return True


async def _analyze_file(path: Path, lemonade_url: str = LEMONADE_URL, verify: bool = False) -> list[dict]:
    """Send one file to Lemonade reasoning tier and parse bug findings."""
    try:
        code = path.read_text(errors="replace")[:MAX_FILE_CHARS]
    except OSError as exc:
        logger.warning("Cannot read %s: %s", path, exc)
        return []

    user_msg = f"File: {path}\n\n```python\n{code}\n```"

    content = "[]"
    for model in (PRIMARY_MODEL, FALLBACK_MODEL):
        # Pre-load model — OmniRouter evicts on idle; load takes ~4s
        if not await _load_model(model, lemonade_url):
            logger.debug("Could not pre-load %s, skipping", model)
            continue
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{lemonade_url}/v1/chat/completions",
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": _SYSTEM},
                            {"role": "user", "content": user_msg},
                        ],
                        "max_tokens": 512,
                        "temperature": 0.0,
                    },
                )
                resp.raise_for_status()
                content = resp.json()["choices"][0]["message"]["content"].strip()
                break
        except Exception as exc:
            logger.warning("Model %s failed for %s: %s", model, path.name, exc)
    else:
        if content == "[]":
            return []

    # Strip <think>...</think> blocks emitted by reasoning models
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
    # Strip markdown fences if present
    content = re.sub(r"```(?:json)?\n?(.*?)```", r"\1", content, flags=re.DOTALL).strip()

    start = content.find("[")
    end = content.rfind("]") + 1
    if start == -1 or end == 0:
        logger.debug("No JSON array in response for %s", path.name)
        return []

    try:
        findings = json.loads(content[start:end])
    except json.JSONDecodeError as exc:
        logger.debug("JSON parse error for %s: %s", path.name, exc)
        return []

    # Stamp file path and scan timestamp
    ts = datetime.now(UTC).isoformat()
    last_model = model
    for f in findings:
        if isinstance(f, dict):
            f.setdefault("file", str(path))
            f["scanned_at"] = ts
            f["model"] = last_model

    candidates = [f for f in findings if isinstance(f, dict)]

    if not verify or not candidates:
        return candidates

    # Second-pass adversarial verification: try to refute each finding
    confirmed = []
    for f in candidates:
        f["verified"] = False
        if await _verify_finding(f, code, last_model, lemonade_url):
            f["verified"] = True
            confirmed.append(f)
        else:
            logger.debug("  Refuted: %s (line %s)", f.get("description", "")[:60], f.get("line"))
    return confirmed


# ── Persistence ─────────────────────────────────────────────────────────────

def _log_findings(findings: list[dict]) -> None:
    FINDINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FINDINGS_PATH.open("a") as fh:
        for f in findings:
            fh.write(json.dumps(f) + "\n")


def _print_summary(findings: list[dict], path: Path) -> None:
    if not findings:
        logger.info("  %s — no bugs found", path.name)
        return
    for f in findings:
        sev = f.get("severity", "?").upper()
        cat = f.get("category", "?")
        ln = f.get("line")
        desc = f.get("description", "")[:80]
        loc = f":{ln}" if ln else ""
        logger.info("  [%s] %s%s (%s) — %s", sev, path.name, loc, cat, desc)


# ── Main ────────────────────────────────────────────────────────────────────

async def run_once(targets: list[Path], verify: bool = False) -> list[dict]:
    all_findings: list[dict] = []
    for path in targets:
        logger.info("Scanning %s ...", path)
        findings = await _analyze_file(path, verify=verify)
        _print_summary(findings, path)
        _log_findings(findings)
        all_findings.extend(findings)
    logger.info(
        "Pass complete — %d files, %d findings (logged to %s)",
        len(targets),
        len(all_findings),
        FINDINGS_PATH,
    )
    return all_findings


async def run_loop(root: Path, n: int, verify: bool = False) -> None:
    targets = _collect_targets(root)
    logger.info("Bughunt loop starting — %d files in pool, %d per pass", len(targets), n)
    while True:
        batch = _pick_next(targets, n)
        if not batch:
            logger.warning("No targets found under %s — sleeping 60s", root)
            await asyncio.sleep(60)
            continue
        await run_once(batch, verify=verify)
        logger.info("Sleeping %ds before next pass ...", LOOP_DELAY_SECONDS)
        await asyncio.sleep(LOOP_DELAY_SECONDS)


def main() -> None:
    ap = argparse.ArgumentParser(description="Autonomous local-inference bug scanner")
    ap.add_argument("--dir", default="src/cohezion", help="Root directory to scan")
    ap.add_argument("--file", help="Scan a single file instead of directory")
    ap.add_argument("--n", type=int, default=3, help="Files per pass")
    ap.add_argument("--loop", action="store_true", help="Run continuously")
    ap.add_argument("--verify", action="store_true", help="Adversarial second-pass: refute false positives")
    ap.add_argument("--verbose", "-v", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    repo_root = Path(__file__).resolve().parent.parent

    if args.file:
        targets = [Path(args.file).resolve()]
        asyncio.run(run_once(targets, verify=args.verify))
    elif args.loop:
        root = (repo_root / args.dir).resolve()
        asyncio.run(run_loop(root, args.n, verify=args.verify))
    else:
        root = (repo_root / args.dir).resolve()
        targets = _collect_targets(root)
        batch = _pick_next(targets, args.n)
        asyncio.run(run_once(batch, verify=args.verify))


if __name__ == "__main__":
    main()
