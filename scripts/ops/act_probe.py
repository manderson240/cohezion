#!/usr/bin/env python3
"""ACT-step probe: can a LOCAL model turn one task into a red->green commit?

Minimal loop (2026-09-21). `LocalImprovementExecutor.execute_task` makes one chat
call and never edits files; `agent/unified_harness.py` has a `file_write` tool but no
patch application, no path allowlist and no test oracle. This loop supplies exactly
what those lack, and nothing else:

  1. an ORACLE test written by a human first, which the model may not touch;
  2. a bounded edit surface (top-level defs/constants of ONE file under src/),
     spliced by AST span -- no unified diffs, whose line numbers local models get wrong;
  3. a verify step (oracle + the module's existing tests) whose output is fed back;
  4. a commit only on green, naming the task id and the model.

Usage:
  act_probe.py --repo R --file src/x.py --target fn --oracle tests/t.py \
      [--extra-test tests/u.py ...] --task-id ID --task "text" --model M
  act_probe.py --self-test
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any


BASE_URL = "http://localhost:13305"
FENCE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)
ChatFn = Callable[[str], dict[str, Any]]


# ---------------------------------------------------------------- model boundary
class NotResidentError(RuntimeError):
    """No preferred model is verifiably resident: refuse rather than trigger a load."""


def resident_llms(base_url: str = BASE_URL) -> list[str] | None:
    """Resident LLM names per /api/v1/health, or None when the router cannot say."""
    try:
        with urllib.request.urlopen(base_url + "/api/v1/health", timeout=20) as r:  # noqa: S310
            data = json.loads(r.read())
    except Exception:  # instrument state, never fatal
        return None
    return [m["model_name"] for m in data.get("all_models_loaded", []) if m.get("type") == "llm"]


def make_chat_fn(
    models: list[str], *, max_tokens: int, timeout: float, base_url: str = BASE_URL
) -> ChatFn:
    """OpenAI-compatible call to the :13305 router; reads `content`, falls back to reasoning."""

    def chat(prompt: str) -> dict[str, Any]:
        resident = resident_llms(base_url)
        if resident is None:
            raise NotResidentError("health UNKNOWN: residency unverifiable")
        model = next((m for m in models if m in resident), None)
        if model is None:
            raise NotResidentError(f"none of {models} resident (resident: {resident})")
        body = json.dumps(
            {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.2,
            }
        ).encode()
        req = urllib.request.Request(  # noqa: S310
            base_url + "/v1/chat/completions",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            data = json.loads(r.read())
        msg = data["choices"][0]["message"]
        content = msg.get("content") or ""
        return {
            "text": content or msg.get("reasoning_content") or "",
            "content_empty": not content,
            "finish_reason": data["choices"][0].get("finish_reason"),
            "usage": data.get("usage"),
            "model": model,
        }

    chat.is_live = True  # type: ignore[attr-defined]
    return chat


# ---------------------------------------------------------------- edit surface
def _top_level_names(node: ast.stmt) -> list[str]:
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        return [node.name]
    if isinstance(node, ast.Assign):
        return [t.id for t in node.targets if isinstance(t, ast.Name)]
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return [node.target.id]
    return []


def _span(node: ast.stmt) -> tuple[int, int]:
    start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
    return start, node.end_lineno or node.lineno


def get_def_source(source: str, name: str) -> str:
    """Source text of the top-level definition/assignment called *name*."""
    lines = source.splitlines()
    for node in ast.parse(source).body:
        if name in _top_level_names(node):
            s, e = _span(node)
            return "\n".join(lines[s - 1 : e])
    raise KeyError(name)


def splice(source: str, replacement: str, anchor: str) -> str:
    """Replace top-level defs/constants named in *replacement*; insert new ones before *anchor*."""
    new_nodes = ast.parse(replacement).body
    if not new_nodes:
        raise ValueError("empty replacement")
    rep_lines = replacement.splitlines()
    lines = source.splitlines()
    existing: dict[str, tuple[int, int]] = {}
    for node in ast.parse(source).body:
        for n in _top_level_names(node):
            existing[n] = _span(node)
    edits: list[tuple[int, int, str]] = []  # (start, end, text); end < start means insert
    inserts: list[str] = []
    for node in new_nodes:
        names = _top_level_names(node)
        if not names:
            raise ValueError(f"unsupported top-level statement: {type(node).__name__}")
        s, e = _span(node)
        text = "\n".join(rep_lines[s - 1 : e])
        hit = next((existing[n] for n in names if n in existing), None)
        if hit:
            edits.append((hit[0], hit[1], text))
        else:
            inserts.append(text)
    if inserts:
        a = existing[anchor][0]
        edits.append((a, a - 1, "\n\n\n".join(inserts) + "\n\n"))
    for s, e, text in sorted(edits, key=lambda t: t[0], reverse=True):
        lines[s - 1 : max(e, s - 1)] = text.splitlines()
    out = "\n".join(lines) + "\n"
    compile(out, "<spliced>", "exec")
    return out


# ---------------------------------------------------------------- verify
def run_tests(repo: Path, python: str, tests: list[str], timeout: float = 300) -> tuple[bool, str]:
    """Run pytest on *tests*; return (green, output tail)."""
    # Fresh bytecode cache per run: a same-size edit written within the mtime granularity
    # of the previous run is otherwise served from a STALE .pyc (observed in the self-test).
    pyc = tempfile.mkdtemp(prefix="act_pyc_")
    env = {**os.environ, "PYTHONPATH": str(repo / "src"), "PYTHONPYCACHEPREFIX": pyc}
    try:
        p = subprocess.run(
            [python, "-m", "pytest", *tests, "-q", "-p", "no:cacheprovider", "--tb=short"],
            cwd=repo,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, "pytest TIMEOUT"
    finally:
        shutil.rmtree(pyc, ignore_errors=True)
    return p.returncode == 0, (p.stdout + p.stderr)[-3000:]


def build_prompt(
    task: str, file: str, defs: str, oracle_src: str, failure: str, history: list[str]
) -> str:
    """Task + editable defs + read-only oracle + current failure + last two attempts."""
    fb = "\n\n".join(history[-2:])
    return (
        f"You are fixing a bug in the Python file `{file}`.\n\nTASK:\n{task}\n\n"
        f"CURRENT CODE (top-level definitions you may replace):\n```python\n{defs}\n```\n\n"
        f"ACCEPTANCE TEST (read-only, you must NOT change it):\n```python\n{oracle_src}\n```\n\n"
        f"CURRENT TEST FAILURE:\n```\n{failure[-1500:]}\n```\n\n"
        + (f"YOUR PREVIOUS ATTEMPTS FAILED:\n{fb}\n\n" if fb else "")
        + "Reply with ONE ```python fenced block containing the COMPLETE new version of every "
        "top-level function/constant you change (you may add new module-level constants or "
        "functions). Do not include imports, tests, or unchanged definitions. No prose needed."
    )


def act_loop(
    *,
    repo: Path,
    file: str,
    targets: list[str],
    oracle: str,
    extra_tests: list[str],
    task: str,
    task_id: str,
    model: str,
    chat: ChatFn,
    python: str,
    max_iters: int,
    log: Path,
    commit: bool = True,
    max_call_errors: int = 12,
    call_backoff_s: float = 20.0,
) -> dict[str, Any]:
    """Propose -> splice -> verify -> feed back, up to *max_iters*; commit only on green."""
    if not file.startswith("src/") or file == oracle:
        raise ValueError(f"edit target must live under src/: {file}")
    path = repo / file
    original = path.read_text()
    oracle_src = (repo / oracle).read_text()
    tests = [oracle, *extra_tests]
    ok, failure = run_tests(repo, python, tests)
    if ok:
        return {"status": "ORACLE_ALREADY_GREEN"}
    history: list[str] = []
    t0 = time.monotonic()
    it = 0
    call_errors = 0
    while it < max_iters:
        it += 1
        defs = "\n\n\n".join(get_def_source(original, t) for t in targets)
        prompt = build_prompt(task, file, defs, oracle_src, failure, history)
        rec: dict[str, Any] = {
            "task_id": task_id,
            "iter": it,
            "model": model,
            "prompt_chars": len(prompt),
        }
        t = time.monotonic()
        try:
            reply = chat(prompt)
        except Exception as exc:
            rec.update(
                latency_s=round(time.monotonic() - t, 1),
                outcome=f"CALL_ERROR {type(exc).__name__}: {exc}",
            )
            _log(log, rec)
            # A router timeout is an INSTRUMENT failure, not a model attempt: it does not
            # consume an iteration, but has its own budget so a wedged router still ends.
            call_errors += 1
            it -= 1
            if call_errors > max_call_errors:
                return {
                    "status": "ROUTER_UNAVAILABLE",
                    "iterations": it,
                    "call_errors": call_errors,
                    "wall_s": round(time.monotonic() - t0, 1),
                }
            time.sleep(call_backoff_s)
            continue
        rec["model"] = reply.get("model", model)
        rec.update(
            latency_s=round(time.monotonic() - t, 1),
            content_empty=reply.get("content_empty"),
            finish_reason=reply.get("finish_reason"),
            usage=reply.get("usage"),
        )
        blocks = FENCE.findall(reply["text"])
        if not blocks:
            rec.update(outcome="FORMAT_ERROR no fenced block", reply=reply["text"][-800:])
            _log(log, rec)
            history.append(f"attempt {it}: no ```python block in reply")
            continue
        code = blocks[-1]
        rec["edit"] = code
        try:
            path.write_text(splice(original, code, anchor=targets[0]))
        except Exception as exc:
            path.write_text(original)
            rec["outcome"] = f"APPLY_ERROR {type(exc).__name__}: {exc}"
            _log(log, rec)
            history.append(f"attempt {it}:\n```python\n{code}\n```\nrejected: {exc}")
            continue
        ok, out = run_tests(repo, python, tests)
        oracle_intact = (repo / oracle).read_text() == oracle_src
        rec.update(tests_green=ok, oracle_intact=oracle_intact, test_tail=out[-600:])
        if ok and oracle_intact:
            rec["diff"] = _git(repo, "diff", "--", file)
            rec["outcome"] = "GREEN"
            _log(log, rec)
            sha = _commit(repo, file, task_id, rec["model"], targets, python) if commit else None
            return {
                "status": "GREEN",
                "iterations": it,
                "wall_s": round(time.monotonic() - t0, 1),
                "commit": sha,
                "model": rec["model"],
                "call_errors": call_errors,
            }
        path.write_text(original)
        rec["outcome"] = "RED"
        _log(log, rec)
        failure = out
        history.append(f"attempt {it}:\n```python\n{code}\n```\ntests still failed:\n{out[-700:]}")
    path.write_text(original)
    return {
        "status": "EXHAUSTED",
        "iterations": max_iters,
        "wall_s": round(time.monotonic() - t0, 1),
    }


def _log(log: Path, rec: dict[str, Any]) -> None:
    with log.open("a") as f:
        f.write(json.dumps(rec, default=str) + "\n")


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def _commit(
    repo: Path, file: str, task_id: str, model: str, targets: list[str], python: str
) -> str:
    ruff = Path(python).parent / "ruff"
    if ruff.exists():
        for cmd in (["format", file], ["check", "--fix", file]):
            subprocess.run([str(ruff), *cmd], cwd=repo, check=False, capture_output=True)
    _git(repo, "add", "--", file)
    _git(
        repo,
        "commit",
        "-q",
        "-m",
        f"fix(act-probe): {', '.join(targets)} [task: {task_id}] [author: local-model {model}]",
    )
    return _git(repo, "rev-parse", "--short", "HEAD").strip()


# ---------------------------------------------------------------- self-test
def self_test() -> int:
    """Fake model: a known-good edit must be committed, a known-bad one never."""
    good = "def value():\n    return 2\n"
    bad = "def value():\n    return 3\n"
    results = {}
    for label, replies in {
        "good": [bad, good],
        "bad": [bad, bad, "no fence here"],
        "flaky": ["RAISE", "RAISE", good],
    }.items():
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            (repo / "src/pkg").mkdir(parents=True)
            (repo / "tests").mkdir()
            (repo / "src/pkg/__init__.py").write_text("")
            (repo / "src/pkg/mod.py").write_text('"""m."""\n\n\ndef value():\n    return 1\n')
            (repo / "tests/test_mod.py").write_text(
                "from pkg.mod import value\n\n\ndef test_v():\n    assert value() == 2\n"
            )
            for c in (
                ["init", "-q"],
                ["config", "user.email", "t@t"],
                ["config", "user.name", "t"],
                ["add", "."],
                ["commit", "-q", "-m", "base"],
            ):
                _git(repo, *c)
            it = iter(replies)

            def fake(prompt: str, _it: Any = it) -> dict[str, Any]:
                r = next(_it)
                if r == "RAISE":
                    raise TimeoutError("simulated router timeout")
                return {"text": f"```python\n{r}```" if "def" in r else r, "content_empty": False}

            res = act_loop(
                repo=repo,
                file="src/pkg/mod.py",
                targets=["value"],
                oracle="tests/test_mod.py",
                extra_tests=[],
                task="make value() return 2",
                task_id="self-test",
                model="fake",
                chat=fake,
                python=sys.executable,
                max_iters=1 if label == "flaky" else len(replies),
                call_backoff_s=0.0,
                log=repo / "log.jsonl",
            )
            n_commits = len(_git(repo, "log", "--oneline").splitlines())
            results[label] = (res["status"], n_commits, (repo / "src/pkg/mod.py").read_text())
    checks = {
        "good edit committed": results["good"][:2] == ("GREEN", 2)
        and "return 2" in results["good"][2],
        "bad edit never committed": results["bad"][:2] == ("EXHAUSTED", 1),
        "bad edit rolled back": "return 1" in results["bad"][2],
        "router timeouts do not consume iterations": results["flaky"][:2] == ("GREEN", 2),
    }
    failed = [k for k, v in checks.items() if not v]
    if failed:
        print(f"act_probe self-test FAILED: {failed} {results}")
        return 1
    print("act_probe self-test OK: good edit committed, bad edit rejected + rolled back")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--repo", type=Path, default=Path.cwd())
    ap.add_argument("--file")
    ap.add_argument("--target", action="append", default=[])
    ap.add_argument("--oracle")
    ap.add_argument("--extra-test", action="append", default=[])
    ap.add_argument("--task")
    ap.add_argument("--task-id")
    ap.add_argument(
        "--model",
        action="append",
        default=[],
        help="preference order; each call uses the first CURRENTLY RESIDENT one (repeatable)",
    )
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument("--max-iters", type=int, default=5)
    ap.add_argument("--max-tokens", type=int, default=3072)
    ap.add_argument("--timeout", type=float, default=180)
    ap.add_argument(
        "--log",
        type=Path,
        default=Path(os.environ.get("TMPDIR", "/tmp")) / "act_probe_log.jsonl",
    )
    a = ap.parse_args()
    if a.self_test:
        return self_test()
    models = a.model or ["Qwen3-Coder-30B-A3B-Instruct-GGUF", "Gemma-4-31B-it-GGUF"]
    chat = make_chat_fn(models, max_tokens=a.max_tokens, timeout=a.timeout)
    res = act_loop(
        repo=a.repo,
        file=a.file,
        targets=a.target,
        oracle=a.oracle,
        extra_tests=a.extra_test,
        task=a.task,
        task_id=a.task_id,
        model="|".join(models),
        chat=chat,
        python=a.python,
        max_iters=a.max_iters,
        log=a.log,
    )
    print(json.dumps(res))
    return 0 if res["status"] == "GREEN" else 1


if __name__ == "__main__":
    sys.exit(main())
