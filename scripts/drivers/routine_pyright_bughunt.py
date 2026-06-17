#!/usr/bin/env python3
"""Routine run: Pyright error bughunting via local inference.

Batch mode (default --batch 5):
  1. Run pyright --outputjson on src/cohezion/ to collect all errors
  2. Load data/pyright_bughunt.jsonl + SurrealDB vault_neuron to find already-attempted issues
  3. Pick the next N unattempted errors (severity=error, not warning/info)
  4. For each: read context (±15 lines), POST to :13305, apply, verify, test
  5. Append WIN/LOSS record to JSONL + vault_neuron
  6. Push batch summary to Obsidian vault via SurrealDB for cross-session learning

Skipped categories (need package installs, not code fixes):
  - reportMissingModuleSource (⚠ — package present but no source stubs)
  - Third-party packages: aiohttp, aiofiles, camel.*, gaia.* → Task backlog only

Run manually:
    uv run python scripts/drivers/routine_pyright_bughunt.py
    uv run python scripts/drivers/routine_pyright_bughunt.py --batch 10

Schedule via CronCreate:
    CronCreate(schedule="17 */2 * * *", prompt="Run Pyright bughunt: uv run python scripts/drivers/routine_pyright_bughunt.py --batch 5")
"""

from __future__ import annotations

import argparse
import json
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_BUGHUNT_JSONL = _REPO_ROOT / "data" / "pyright_bughunt.jsonl"
_SRC_DIR = _REPO_ROOT / "src" / "cohezion"
_PYRIGHT_BIN = Path.home() / ".local" / "bin" / "pyright"
_PYTHON_BIN = _REPO_ROOT / ".venv" / "bin" / "python3"

# ── Inference ─────────────────────────────────────────────────────────────────
_LEMONADE_URL = "http://localhost:13305/v1/chat/completions"
_MODEL = "llama3.2-1b-FLM"

# ── Skip rules ────────────────────────────────────────────────────────────────
# These require package installs, not code edits
_SKIP_RULES = {
    "reportMissingModuleSource",  # ⚠ stub-only packages — not a code error
}
_SKIP_PACKAGES = {
    "aiohttp",
    "aiofiles",
    "camel",
    "gaia",  # optional/external deps
}

# ── Context lines around error ────────────────────────────────────────────────
_CONTEXT_LINES = 15


def _load_prior() -> dict[str, dict]:
    """Load prior bughunt records keyed by (file, line, rule)."""
    if not _BUGHUNT_JSONL.exists():
        return {}
    records: dict[str, dict] = {}
    with open(_BUGHUNT_JSONL) as f:
        for line in f:
            try:
                r = json.loads(line)
                key = r.get("issue_key", "")
                if key:
                    records[key] = r
            except Exception:
                pass
    return records


def _run_pyright() -> list[dict]:
    """Run pyright --outputjson and return list of error diagnostics."""
    result = subprocess.run(
        [str(_PYRIGHT_BIN), "--outputjson", str(_SRC_DIR)],
        capture_output=True,
        text=True,
        timeout=120,
    )
    raw = result.stdout + result.stderr
    start = raw.find("{")
    if start < 0:
        return []
    try:
        data = json.loads(raw[start:])
    except Exception:
        return []
    return [d for d in data.get("generalDiagnostics", []) if d.get("severity") == "error"]


def _should_skip(diag: dict) -> bool:
    """Return True if this diagnostic should be skipped (package install needed)."""
    rule = diag.get("rule", "")
    if rule in _SKIP_RULES:
        return True
    message = diag.get("message", "").lower()
    for pkg in _SKIP_PACKAGES:
        if f'"{pkg}' in message or f"'{pkg}" in message or f" {pkg}." in message:
            return True
    return False


def _issue_key(diag: dict) -> str:
    """Stable key for deduplication: file:line:rule."""
    file_path = diag.get("file", "")
    line = diag.get("range", {}).get("start", {}).get("line", 0)
    rule = diag.get("rule", diag.get("message", "")[:40])
    # Normalize file path to be relative
    try:
        rel = str(Path(file_path).relative_to(_REPO_ROOT))
    except ValueError:
        rel = file_path
    return f"{rel}:{line}:{rule}"


def _read_context(file_path: str, line_0based: int) -> str:
    """Read ±CONTEXT_LINES around the error line."""
    path = Path(file_path)
    if not path.exists():
        return ""
    lines = path.read_text().splitlines()
    start = max(0, line_0based - _CONTEXT_LINES)
    end = min(len(lines), line_0based + _CONTEXT_LINES + 1)
    numbered = [f"{i + 1:4d}│ {lines[i]}" for i in range(start, end)]
    return "\n".join(numbered)


def _query_lemonade(prompt: str, timeout: float = 20.0) -> str | None:
    """POST to :13305 OmniRouter. Returns None if offline."""
    payload = json.dumps(
        {
            "model": _MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 400,
            "temperature": 0.0,
        }
    ).encode()
    req = urllib.request.Request(  # noqa: S310
        _LEMONADE_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"].strip()
    except Exception as exc:
        print(f"  [13305 offline] {exc}")
        return None


def _load_win_patterns(rule: str, max_examples: int = 3) -> list[dict]:
    """Load prior WIN patterns for the same Pyright rule — used as few-shot examples."""
    patterns_file = _REPO_ROOT / "data" / "code_quality_patterns.jsonl"
    if not patterns_file.exists():
        return []
    matches: list[dict] = []
    with open(patterns_file) as f:
        for line in f:
            try:
                p = json.loads(line)
                if p.get("rule") == rule and p.get("fix_old") and p.get("fix_new"):
                    matches.append(p)
            except Exception:
                pass
    return matches[-max_examples:]  # most recent wins for this rule


def _build_fix_prompt(diag: dict, context: str) -> str:
    rule = diag.get("rule", "unknown")
    message = diag.get("message", "")
    line = diag.get("range", {}).get("start", {}).get("line", 0) + 1
    file_path = diag.get("file", "")

    # Inject prior WIN patterns as few-shot examples
    prior_wins = _load_win_patterns(rule)
    examples_block = ""
    if prior_wins:
        examples = "\n".join(
            f"  Example {i + 1}: Replace `{p['fix_old'][:80]}` → `{p['fix_new'][:80]}`"
            for i, p in enumerate(prior_wins)
        )
        examples_block = f"\nPrior successful fixes for {rule}:\n{examples}\n"

    return f"""Pyright error in {Path(file_path).name} at line {line}:
Rule: {rule}
Message: {message}
{examples_block}
Code context (line numbers shown):
{context}

Reply with ONLY a JSON object in this exact format:
{{"old_string": "<exact string to replace>", "new_string": "<replacement>", "explanation": "<one sentence>"}}

Rules:
- old_string must be an EXACT substring of the code above (copy-paste it)
- new_string must fix the Pyright error minimally
- For Optional member access: add `if x is None: return` or `assert x is not None` before the access
- For missing attributes on a class: use getattr(obj, 'attr', default) instead
- For impossible conditions: remove the dead block
- Do NOT change function signatures or add new imports unless absolutely necessary"""


def _apply_fix(file_path: str, old_string: str, new_string: str) -> bool:
    """Apply fix via string replacement. Returns True on success."""
    path = Path(file_path)
    if not path.exists():
        return False
    content = path.read_text()
    if old_string not in content:
        print(f"  [MISMATCH] old_string not found in {path.name}")
        return False
    if content.count(old_string) > 1:
        print(f"  [AMBIGUOUS] old_string appears {content.count(old_string)}x — skipping")
        return False
    path.write_text(content.replace(old_string, new_string, 1))
    return True


def _verify_fix(file_path: str, original_key: str) -> bool:
    """Re-run pyright on just this file. Return True if the error is gone."""
    result = subprocess.run(
        [str(_PYRIGHT_BIN), "--outputjson", file_path],
        capture_output=True,
        text=True,
        timeout=60,
    )
    raw = result.stdout + result.stderr
    start = raw.find("{")
    if start < 0:
        return True  # no output = no errors
    try:
        data = json.loads(raw[start:])
    except Exception:
        return True
    remaining = [d for d in data.get("generalDiagnostics", []) if d.get("severity") == "error"]
    # Check our specific issue is gone
    remaining_keys = {_issue_key(d) for d in remaining}
    return original_key not in remaining_keys


def _run_tests(file_path: str) -> tuple[bool, str]:
    """Run pytest on the test module corresponding to this file."""
    rel = Path(file_path).relative_to(_SRC_DIR)
    # Map src/cohezion/foo/bar.py → tests/foo/test_bar.py
    parts = list(rel.parts)
    if parts:
        parts[-1] = "test_" + parts[-1]
    test_path = _REPO_ROOT / "tests" / Path(*parts)
    if not test_path.exists():
        # Try tests/<module>/
        test_dir = _REPO_ROOT / "tests" / rel.parts[0]
        if test_dir.exists():
            test_path = test_dir
        else:
            return True, "no test file"

    result = subprocess.run(
        [
            str(_PYTHON_BIN),
            "-m",
            "pytest",
            str(test_path),
            "-q",
            "--tb=short",
            "--import-mode=append",
            "-p",
            "no:warnings",
        ],
        capture_output=True,
        text=True,
        timeout=60,
        cwd=_REPO_ROOT,
    )
    passed = result.returncode == 0
    summary = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else "no output"
    return passed, summary


def _append_record(record: dict) -> None:
    _BUGHUNT_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(_BUGHUNT_JSONL, "a") as f:
        f.write(json.dumps(record) + "\n")


def _push_to_cohezion(record: dict) -> None:
    """Push WIN/LOSS record into the Cohezion improvement loop.

    WINs: persist to vault_neuron (compound quality signal) + code_quality_patterns.jsonl
    LOSSes: persist to vault_neuron as negative signal for future retry decisions
    Both: synthesize pattern summary via :13305 for skill refinement.
    """
    outcome = record.get("outcome", "LOSS")

    # 1. Persist to SurrealDB vault_neuron — same table the compound loop reads
    _push_to_surrealdb(record)

    # 2. WINs go into code_quality_patterns.jsonl — training signal for future fix prompts
    if outcome == "WIN":
        patterns_file = _REPO_ROOT / "data" / "code_quality_patterns.jsonl"
        patterns_file.parent.mkdir(parents=True, exist_ok=True)
        pattern = {
            "rule": record.get("rule"),
            "fix_old": record.get("fix_old", "")[:150],
            "fix_new": record.get("fix_new", "")[:150],
            "explanation": record.get("explanation", ""),
            "file_module": Path(record.get("file", "")).parent.name,
            "timestamp": record.get("timestamp"),
        }
        with open(patterns_file, "a") as f:
            f.write(json.dumps(pattern) + "\n")
        print("  [PATTERN] Recorded WIN pattern → code_quality_patterns.jsonl")

    # 3. Synthesize improvement signal via :13305
    _synthesize_improvement(record)


def _push_to_surrealdb(record: dict) -> None:
    """Write bughunt outcome to vault_neuron for compound loop awareness."""
    outcome = record.get("outcome", "LOSS")
    issue_key = record.get("issue_key", "")[:60]
    success_val = "true" if outcome == "WIN" else "false"
    quality = "0.9" if outcome == "WIN" else "0.1"
    elapsed_ms = int(record.get("elapsed_s", 0) * 1000)
    model_val = json.dumps(_MODEL)
    sql = (
        f"INSERT INTO vault_neuron {{"
        f" task_id: 'pyright:{issue_key}',"
        f" category: 'code_quality',"
        f" success: {success_val},"
        f" tokens: 0,"
        f" node: 'npu',"
        f" model: {model_val},"
        f" quality_score: {quality},"
        f" elapsed_ms: {elapsed_ms},"
        f" recorded_at: time::now()"
        f"}};"
    )
    try:
        req = urllib.request.Request(  # noqa: S310
            "http://localhost:8001/sql",
            data=sql.encode(),
            headers={
                "Content-Type": "text/plain",
                "surreal-ns": "cohezion",
                "surreal-db": "main",
                "Accept": "application/json",
                "Authorization": "Basic cm9vdDpyb290",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:  # noqa: S310
            resp.read()
        print(f"  [SURREALDB] {outcome} persisted to vault_neuron")
    except Exception as exc:
        print(f"  [SURREALDB offline] {exc}")


def _synthesize_improvement(record: dict) -> None:
    """Ask :13305 to synthesize a reusable pattern from this WIN/LOSS."""
    outcome = record.get("outcome", "LOSS")
    rule = record.get("rule", "unknown")
    explanation = record.get("explanation", "")
    if not explanation:
        return

    prompt = (
        f"Pyright fix {'succeeded' if outcome == 'WIN' else 'failed'} for rule {rule}. "
        f"Explanation: {explanation}. "
        f"In one sentence: what general pattern should future fixes follow for this rule?"
    )
    synthesis = _query_lemonade(prompt, timeout=10.0)
    if synthesis:
        print(f"  [SYNTHESIS] {synthesis[:120]}")


def _query_surrealdb_wins() -> set[str]:
    """Pull issue keys already marked WIN in vault_neuron. Skip re-attempting them."""
    sql = "SELECT task_id FROM vault_neuron WHERE category = 'code_quality' AND success = true;"
    try:
        req = urllib.request.Request(  # noqa: S310
            "http://localhost:8001/sql",
            data=sql.encode(),
            headers={
                "Content-Type": "text/plain",
                "surreal-ns": "cohezion",
                "surreal-db": "main",
                "Accept": "application/json",
                "Authorization": "Basic cm9vdDpyb290",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:  # noqa: S310
            data = json.loads(resp.read())
        results = data[0].get("result", []) if isinstance(data, list) else []
        # task_id format: "pyright:<issue_key>"
        return {
            r["task_id"].removeprefix("pyright:")
            for r in results
            if isinstance(r, dict) and str(r.get("task_id", "")).startswith("pyright:")
        }
    except Exception:
        return set()


def _push_batch_summary_to_vault(batch_results: list[dict], elapsed_s: float) -> None:
    """Write batch WIN/LOSS summary to vault_neuron for cross-session learning."""
    wins = sum(1 for r in batch_results if r.get("outcome") == "WIN")
    total = len(batch_results)
    if total == 0:
        return
    rules_fixed = [r.get("rule", "") for r in batch_results if r.get("outcome") == "WIN"]
    summary_text = (
        f"Batch bughunt: {wins}/{total} WINs in {elapsed_s:.0f}s. "
        f"Rules fixed: {', '.join(set(rules_fixed)) or 'none'}"
    )
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    sql = (
        f"INSERT INTO vault_neuron {{"
        f" task_id: 'pyright:batch:{ts}', "
        f" category: 'bughunt_summary', "
        f" success: {str(wins > 0).lower()}, "
        f" tokens: 0, node: 'npu', model: {json.dumps(_MODEL)}, "
        f" quality_score: {round(wins / total, 2)}, "
        f" elapsed_ms: {int(elapsed_s * 1000)}, "
        f" recorded_at: time::now(), "
        f" summary: {json.dumps(summary_text)}"
        f"}};"
    )
    try:
        req = urllib.request.Request(  # noqa: S310
            "http://localhost:8001/sql",
            data=sql.encode(),
            headers={
                "Content-Type": "text/plain",
                "surreal-ns": "cohezion",
                "surreal-db": "main",
                "Accept": "application/json",
                "Authorization": "Basic cm9vdDpyb290",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=3.0) as resp:  # noqa: S310
            resp.read()
        print(f"  [VAULT] Batch summary persisted: {summary_text}")
    except Exception as exc:
        print(f"  [VAULT offline] {exc}")


def _process_one(target: dict, t_start: datetime) -> dict | None:
    """Process a single diagnostic. Returns the final record dict, or None if skipped early."""
    target_key = _issue_key(target)
    file_path = target.get("file", "")
    line = target.get("range", {}).get("start", {}).get("line", 0)
    rule = target.get("rule", "unknown")
    message = target.get("message", "")
    rel_file = str(Path(file_path).relative_to(_REPO_ROOT)) if file_path else "?"

    print(f"\n[TARGET] {rel_file}:{line + 1} [{rule}]")
    print(f"  {message}")

    context = _read_context(file_path, line)
    if not context:
        print("  [SKIP] Could not read file context")
        rec = {
            "issue_key": target_key,
            "file": rel_file,
            "line": line + 1,
            "rule": rule,
            "message": message,
            "outcome": "SKIP",
            "reason": "no context",
            "timestamp": t_start.isoformat(),
        }
        _append_record(rec)
        return rec

    print("  Querying :13305...")
    prompt = _build_fix_prompt(target, context)
    response = _query_lemonade(prompt)

    fix_old = fix_new = explanation = ""
    if response:
        json_start = response.find("{")
        json_end = response.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            try:
                fix_data = json.loads(response[json_start:json_end])
                fix_old = fix_data.get("old_string", "")
                fix_new = fix_data.get("new_string", "")
                explanation = fix_data.get("explanation", "")
                print(f"  Fix: {explanation}")
            except json.JSONDecodeError:
                print(f"  [PARSE ERROR] Response: {response[:200]}")

    if not fix_old or fix_old == fix_new:
        print("  [LOSS] No actionable fix from :13305")
        rec = {
            "issue_key": target_key,
            "file": rel_file,
            "line": line + 1,
            "rule": rule,
            "message": message,
            "outcome": "LOSS",
            "reason": "no fix from inference",
            "lemonade_response": response,
            "timestamp": t_start.isoformat(),
        }
        _append_record(rec)
        _push_to_cohezion(rec)
        return rec

    applied = _apply_fix(file_path, fix_old, fix_new)
    if not applied:
        print("  [LOSS] Fix string not found in file")
        rec = {
            "issue_key": target_key,
            "file": rel_file,
            "line": line + 1,
            "rule": rule,
            "message": message,
            "outcome": "LOSS",
            "reason": "old_string mismatch",
            "fix_old": fix_old[:100],
            "fix_new": fix_new[:100],
            "timestamp": t_start.isoformat(),
        }
        _append_record(rec)
        _push_to_cohezion(rec)
        return rec

    print("  Verifying fix with pyright...")
    error_gone = _verify_fix(file_path, target_key)

    tests_passed, test_summary = _run_tests(file_path)
    print(f"  Tests: {test_summary}")

    outcome = "WIN" if (error_gone and tests_passed) else "LOSS"

    if outcome == "LOSS":
        print("  [REVERT] Fix didn't pass verification — reverting")
        Path(file_path).write_text(Path(file_path).read_text().replace(fix_new, fix_old, 1))

    elapsed = (datetime.now(timezone.utc) - t_start).total_seconds()
    print(f"[{outcome}] {rel_file}:{line + 1} in {elapsed:.1f}s")

    rec = {
        "issue_key": target_key,
        "file": rel_file,
        "line": line + 1,
        "rule": rule,
        "message": message,
        "fix_old": fix_old[:200],
        "fix_new": fix_new[:200],
        "explanation": explanation,
        "error_gone": error_gone,
        "tests_passed": tests_passed,
        "test_summary": test_summary,
        "outcome": outcome,
        "elapsed_s": round(elapsed, 1),
        "timestamp": t_start.isoformat(),
    }
    _append_record(rec)
    _push_to_cohezion(rec)
    return rec


def main() -> None:
    parser = argparse.ArgumentParser(description="Pyright bughunt via local inference")
    parser.add_argument(
        "--batch", type=int, default=5, help="Number of issues to attempt per run (default: 5)"
    )
    args = parser.parse_args()

    t_start = datetime.now(timezone.utc)
    print(f"[START] Pyright bughunt — batch={args.batch} — {t_start.isoformat()}")

    # Load prior attempts from JSONL + SurrealDB WINs (skip already-won issues)
    prior = _load_prior()
    vault_wins = _query_surrealdb_wins()
    prior_keys: set[str] = set(prior.keys()) | vault_wins
    wins_total = sum(1 for r in prior.values() if r.get("outcome") == "WIN") + len(vault_wins)
    print(
        f"  Prior records: {len(prior)} (JSONL) + {len(vault_wins)} vault WINs = {len(prior_keys)} skip keys"
    )
    print(f"  Cumulative WINs: {wins_total}")

    # Run pyright once — reuse results across the batch
    print("  Running pyright...")
    diagnostics = _run_pyright()
    errors = [d for d in diagnostics if not _should_skip(d)]
    print(f"  Found {len(diagnostics)} errors total, {len(errors)} actionable")

    # Collect unattempted issues up to batch size
    candidates: list[dict] = []
    for d in errors:
        if len(candidates) >= args.batch:
            break
        if _issue_key(d) not in prior_keys:
            candidates.append(d)

    if not candidates:
        print("  [DONE] All actionable errors have been attempted.")
        return

    print(f"  Processing {len(candidates)} issues (of {args.batch} requested)...")
    batch_results: list[dict] = []
    processed_keys: set[str] = set()

    for i, target in enumerate(candidates):
        key = _issue_key(target)
        if key in processed_keys:
            continue
        print(f"\n--- Issue {i + 1}/{len(candidates)} ---")
        rec = _process_one(target, t_start)
        if rec:
            batch_results.append(rec)
            processed_keys.add(key)
            prior_keys.add(key)  # don't retry same key within this batch

    # Batch summary
    elapsed_total = (datetime.now(timezone.utc) - t_start).total_seconds()
    wins = sum(1 for r in batch_results if r.get("outcome") == "WIN")
    losses = sum(1 for r in batch_results if r.get("outcome") == "LOSS")
    skips = sum(1 for r in batch_results if r.get("outcome") == "SKIP")
    print(
        f"\n[BATCH SUMMARY] {wins} WINs / {losses} LOSSes / {skips} SKIPs in {elapsed_total:.1f}s"
    )

    if batch_results:
        _push_batch_summary_to_vault(batch_results, elapsed_total)


if __name__ == "__main__":
    main()
