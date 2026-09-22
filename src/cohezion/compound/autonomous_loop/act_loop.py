"""ACT loop: turn one task into a red->green commit, or into nothing.

Extracted from ``scripts/ops/act_probe.py`` (first local-model commit a4b2002b0); consumed
by ``LocalImprovementExecutor``. Human-written ORACLE test first (model may not touch it);
edits bounded to top-level defs of ONE src/ file, spliced by AST span (no unified diffs);
oracle + module tests re-run with a fresh bytecode cache and fed back on RED; commit only
on green, naming the task id and the model.
"""

from __future__ import annotations

import ast
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any


BASE_URL = "http://localhost:13305"
FENCE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)
ChatFn = Callable[[str], dict[str, Any]]


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
    """OpenAI-compatible call to the :13305 router using the first RESIDENT model of *models*."""

    def chat(prompt: str) -> dict[str, Any]:
        resident = resident_llms(base_url)
        if resident is None:
            raise NotResidentError("health UNKNOWN: residency unverifiable")
        model = next((m for m in models if m in resident), None)
        if model is None:
            raise NotResidentError(f"none of {models} resident (resident: {resident})")
        # Model-card params: Qwen3-family gets "/no_think", thinking models their overhead
        # budget. Without it Qwen3.6 spent all 3072 tokens thinking.
        try:
            from cohezion.inference.model_card_harness import ModelCardHarness

            params = ModelCardHarness.from_live_api().get_params("code", model)
            final_prompt, extra = params.apply(prompt)
            budget = max(max_tokens, params.max_tokens)
            if "/no_think" in (params.prompt_prefix or ""):
                # Qwen3.6 ignores the /no_think soft switch (measured 2026-09-21: 300/300
                # tokens of reasoning, empty content); only the template kwarg disables it.
                extra = {**extra, "chat_template_kwargs": {"enable_thinking": False}}
        except Exception:  # resolver unavailable: plain call
            final_prompt, extra, budget = prompt, {}, max_tokens
        msgs = [{"role": "user", "content": final_prompt}]
        body = {"model": model, "messages": msgs, "max_tokens": budget, "temperature": 0.2}
        hdr = {"Content-Type": "application/json"}
        url = base_url + "/v1/chat/completions"
        req = urllib.request.Request(url, json.dumps({**body, **extra}).encode(), hdr)  # noqa: S310
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            data = json.loads(r.read())
        msg = data["choices"][0]["message"]
        content = msg.get("content") or ""
        truncated = (data.get("usage") or {}).get("completion_tokens", 0) >= budget
        # Mine reasoning_content only when generation finished: a truncated think-stream
        # yields code FRAGMENTS (observed: IndentationError x3).
        fallback = "" if truncated else (msg.get("reasoning_content") or "")
        text = content or fallback
        return {"text": text, "truncated": truncated, "usage": data.get("usage"), "model": model}

    return chat


def _top_level_names(node: ast.stmt) -> list[str]:
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
        return [node.name]
    if isinstance(node, ast.Assign):
        return [t.id for t in node.targets if isinstance(t, ast.Name)]
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return [node.target.id]
    return []


def _import_names(node: ast.stmt) -> list[str]:
    if isinstance(node, ast.Import):
        return [a.asname or a.name.split(".")[0] for a in node.names]
    if isinstance(node, ast.ImportFrom):
        return [a.asname or a.name for a in node.names]
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
    rep_lines, lines = replacement.splitlines(), source.splitlines()
    existing = {n: _span(node) for node in ast.parse(source).body for n in _top_level_names(node)}
    imported = {n for node in ast.parse(source).body for n in _import_names(node)}
    edits: list[tuple[int, int, str]] = []  # (start, end, text); end < start means insert
    inserts: list[str] = []
    for node in new_nodes:
        if isinstance(node, ast.Import | ast.ImportFrom):
            # Models restate imports the file already has; that is a no-op, not an error.
            # A NEW import is refused with an actionable reason (the bare "unsupported
            # Import" gave the model nothing to act on: 5/5 identical retries, 2026-09-21).
            new = [n for n in _import_names(node) if n not in imported]
            if new:
                raise ValueError(
                    f"top-level `{ast.unparse(node)}` adds {new}, not imported by the file; "
                    "remove it and import inside the function body instead"
                )
            continue
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


_RUNNER_BROKEN_MARKERS = (
    "No module named pytest",
    "ERROR: file or directory not found",
    "no tests ran",
)


def run_tests(repo: Path, python: str, tests: list[str], timeout: float = 300) -> tuple[bool, str]:
    """Run pytest on *tests*; return (green, output tail)."""
    # Fresh bytecode cache per run: a same-size edit written within the mtime granularity
    # of the previous run is otherwise served from a STALE .pyc (observed in the self-test).
    pyc = tempfile.mkdtemp(prefix="act_pyc_")
    env = {**os.environ, "PYTHONPATH": str(repo / "src"), "PYTHONPYCACHEPREFIX": pyc}
    cmd = [python, "-m", "pytest", *tests, "-q", "-p", "no:cacheprovider", "--tb=short"]
    try:
        p = subprocess.run(
            cmd, cwd=repo, env=env, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired:
        return False, "pytest TIMEOUT"
    finally:
        shutil.rmtree(pyc, ignore_errors=True)
    return p.returncode == 0, (p.stdout + p.stderr)[-3000:]


def _module_name(file: str) -> str:
    """Dotted module for a ``src/``-relative path (``__init__.py`` -> its package)."""
    parts = list(Path(file).with_suffix("").parts)
    if parts and parts[0] == "src":
        parts = parts[1:]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def _imported_modules(path: Path, own_module: str) -> set[str]:
    """Every dotted name *path* imports (``from a import b`` yields ``a`` and ``a.b``)."""
    try:
        tree = ast.parse(path.read_text(errors="replace"))
    except (SyntaxError, ValueError, OSError):
        return set()
    pkg = own_module.split(".")
    out: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.update(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:  # relative: resolve against the importing module's package
                base = pkg[: len(pkg) - node.level] if node.level <= len(pkg) else []
                mod = ".".join(base + ([node.module] if node.module else []))
            else:
                mod = node.module or ""
            if mod:
                out.add(mod)
                out.update(f"{mod}.{a.name}" for a in node.names)
    return out


def caller_tests(
    repo: Path, file: str, exclude: set[str] | None = None, cap: int = 20
) -> list[str]:
    """Test files that exercise *file*'s callers: they import it, or a src module that does.

    Static scan, one hop through src/. Same-package tests first, then direct importers,
    capped at *cap*. Oracle/extra tests go in *exclude* (repo-relative paths).
    """
    target = _module_name(file)
    if not target:
        return []
    leaf = target.rsplit(".", 1)[-1]
    targets = {target}
    src = repo / "src"
    for f in sorted(src.rglob("*.py")) if src.is_dir() else []:
        rel = f.relative_to(repo).as_posix()
        if rel == file or leaf not in f.read_text(errors="replace"):
            continue
        mod = _module_name(rel)
        if target in _imported_modules(f, mod if f.name != "__init__.py" else mod + ".x"):
            targets.add(mod)
    leaves = {t.rsplit(".", 1)[-1] for t in targets}
    same_pkg = "/".join(["tests", *target.split(".")[1:-1]])
    found: list[tuple[bool, bool, str]] = []
    tests_dir = repo / "tests"
    for f in sorted(tests_dir.rglob("*.py")) if tests_dir.is_dir() else []:
        rel = f.relative_to(repo).as_posix()
        if (exclude and rel in exclude) or not (
            f.name.startswith("test_") or f.stem.endswith("_test")
        ):
            continue
        text = f.read_text(errors="replace")
        if not any(lf in text for lf in leaves):
            continue
        hits = _imported_modules(f, _module_name(rel)) & targets
        if hits:
            in_pkg = rel.startswith(same_pkg + "/") if same_pkg != "tests" else True
            found.append((not in_pkg, target not in hits, rel))
    return [rel for *_k, rel in sorted(found)[:cap]]


def _baseline_green(
    repo: Path, python: str, files: list[str], timeout: float, budget_s: float
) -> list[str]:
    """The subset of *files* green BEFORE the edit: pre-existing red is not the model's fault."""
    if not files:
        return []
    ok, _ = run_tests(repo, python, files, timeout)
    if ok:
        return files
    deadline, keep = time.monotonic() + budget_s, []
    for f in files:
        if time.monotonic() > deadline:
            break
        if run_tests(repo, python, [f], timeout)[0]:
            keep.append(f)
    return keep


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
    confirm_repeats: int = 3,
    callers: list[str] | None = None,
    caller_cap: int = 20,
    caller_timeout: float = 300,
) -> dict[str, Any]:
    """Propose -> splice -> verify -> feed back, up to *max_iters*; commit only on green.

    A single green run can be a fluke (order-dependent oracle, uninitialised state, timing).
    Before committing, the first GREEN is re-run *confirm_repeats - 1* more times; any red
    repeat means the candidate is FLAKY_ORACLE, never committed, and the file is restored.
    Pattern from EverMind-AI/Raven's Evolver (K=3 confirmation gate), adapted: we have no
    second arm to compare against, so this confirms determinism rather than significance.

    Status GREEN / EXHAUSTED / ROUTER_UNAVAILABLE / RUNNER_BROKEN / FLAKY_ORACLE /
    ORACLE_ALREADY_GREEN (non-discriminating).

    Caller regression guard: *callers* None (default) auto-selects ``caller_tests`` (test
    files importing the edited module or a src module that imports it); ``[]`` disables it.
    Only callers green on the ORIGINAL file are kept, then run with the oracle on every
    attempt: an edit that satisfies the oracle but breaks a caller is RED, never committed.
    (2026-09-21: commit 2b81df1ca passed its oracle and broke ``oom_guard.pre_load_gate``.)
    """
    oracle_file = repo / oracle.split("::", 1)[0]  # *oracle* may be a pytest node id
    if not file.startswith("src/") or repo / file == oracle_file:
        raise ValueError(f"edit target must live under src/: {file}")
    path = repo / file
    original = path.read_text()
    oracle_src = oracle_file.read_text()
    tests = [oracle, *extra_tests]
    ok, failure = run_tests(repo, python, tests)
    if ok:
        return {"status": "ORACLE_ALREADY_GREEN"}
    if any(marker in failure for marker in _RUNNER_BROKEN_MARKERS):
        # The oracle could not RUN (no pytest, bad node id): an instrument failure. Asking the
        # model to fix it burns every iteration and ends EXHAUSTED, blaming the model.
        return {"status": "RUNNER_BROKEN", "python": python, "detail": failure[-400:]}
    if callers is None:
        skip = {t.split("::", 1)[0] for t in tests}
        callers = caller_tests(repo, file, exclude=skip, cap=caller_cap)
    guarded = _baseline_green(repo, python, callers, caller_timeout, budget_s=caller_timeout)
    _log(log, {"task_id": task_id, "caller_tests": guarded, "caller_candidates": callers})
    tests = [*tests, *guarded]
    run_timeout = 300 + (caller_timeout if guarded else 0)
    history: list[str] = []
    t0 = time.monotonic()
    it = call_errors = 0
    while it < max_iters:
        it += 1
        defs = "\n\n\n".join(get_def_source(original, t) for t in targets)
        prompt = build_prompt(task, file, defs, oracle_src, failure, history)
        rec: dict[str, Any] = {"task_id": task_id, "iter": it, "model": model}
        t = time.monotonic()
        try:
            reply = chat(prompt)
        except Exception as exc:
            rec["outcome"] = f"CALL_ERROR {type(exc).__name__}: {exc}"
            _log(log, rec)
            # A router error is an INSTRUMENT failure, not a model attempt: it does not
            # consume an iteration, but has its own budget so a wedged router still ends.
            call_errors += 1
            it -= 1
            if call_errors > max_call_errors:
                wall = round(time.monotonic() - t0, 1)
                return {"status": "ROUTER_UNAVAILABLE", "iterations": it, "wall_s": wall}
            time.sleep(call_backoff_s)
            continue
        rec["model"] = reply.get("model", model)
        rec.update(latency_s=round(time.monotonic() - t, 1), truncated=reply.get("truncated"))
        rec["usage"] = reply.get("usage")
        blocks = FENCE.findall(reply["text"])
        if not blocks:
            rec.update(outcome="FORMAT_ERROR no fenced block", reply=reply["text"][-800:])
            _log(log, rec)
            history.append(f"attempt {it}: no ```python block in reply")
            continue
        code = rec["edit"] = blocks[-1]
        try:
            path.write_text(splice(original, code, anchor=targets[0]))
        except Exception as exc:
            path.write_text(original)
            rec["outcome"] = f"APPLY_ERROR {type(exc).__name__}: {exc}"
            _log(log, rec)
            history.append(f"attempt {it}:\n```python\n{code}\n```\nrejected: {exc}")
            continue
        ok, out = run_tests(repo, python, tests, run_timeout)
        oracle_intact = oracle_file.read_text() == oracle_src
        rec.update(tests_green=ok, oracle_intact=oracle_intact, test_tail=out[-600:])
        if ok and oracle_intact:
            rec["outcome"] = "GREEN"
            _log(log, rec)
            for rep in range(2, confirm_repeats + 1):
                r_ok, r_out = run_tests(repo, python, tests, run_timeout)
                _log(log, {"task_id": task_id, "iter": it, "confirm": rep, "green": r_ok})
                if not r_ok:
                    path.write_text(original)
                    return {
                        "status": "FLAKY_ORACLE",
                        "iterations": it,
                        "wall_s": round(time.monotonic() - t0, 1),
                        "failed_on_confirm": rep,
                        "detail": r_out[-400:],
                    }
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
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a") as f:
        f.write(json.dumps(rec, default=str) + "\n")


def git(repo: Path, *args: str) -> str:
    """Run git in *repo*; raise on failure; return stdout."""
    p = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)
    return p.stdout


def _commit(
    repo: Path, file: str, task_id: str, model: str, targets: list[str], python: str
) -> str:
    ruff = Path(python).parent / "ruff"
    if ruff.exists():
        for cmd in (["format", file], ["check", "--fix", file]):
            subprocess.run([str(ruff), *cmd], cwd=repo, check=False, capture_output=True)
    git(repo, "add", "--", file)
    msg = f"fix(act-loop): {', '.join(targets)} [task: {task_id}] [author: local-model {model}]"
    git(repo, "commit", "-q", "-m", msg)
    return git(repo, "rev-parse", "--short", "HEAD").strip()
