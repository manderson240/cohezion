"""ACT loop: turn one task into a red->green commit, or into nothing.

Extracted from ``scripts/ops/act_probe.py`` (first local-model commit a4b2002b0); consumed
by ``LocalImprovementExecutor``. Human-written ORACLE test first (model may not touch it);
edits bounded to top-level defs of ONE src/ file, spliced by AST span (no unified diffs);
oracle + module tests re-run with a fresh bytecode cache and fed back on RED; commit only
on green, naming the task id and the model.
"""

from __future__ import annotations

import ast
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Any


BASE_URL = "http://localhost:13305"
FENCE = re.compile(r"```(?:python|py)?\s*\n(.*?)```", re.DOTALL)
ChatFn = Callable[[str], dict[str, Any]]
# Admission gate: model_id -> object with ``ok`` / ``reason`` (hotswap.SwapResult).
AdmitFn = Callable[[str], Any]


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


_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")


def _check_rel(path: str, root: str, what: str) -> None:
    """*path* must be a plain relative ``.py`` path under *root*/ (no ``..``, no anchor)."""
    pp = PurePosixPath(path)
    if (
        not path
        or "\\" in path
        or "\x00" in path
        or pp.is_absolute()
        or ".." in pp.parts
        or pp.parts[:1] != (root,)
        or len(pp.parts) < 2
        or pp.suffix != ".py"
    ):
        raise ValueError(f"{what} must be a relative .py path under {root}/: {path!r}")


def check_act_spec(
    file: str, oracle: str, targets: list[str], extra_tests: list[str] | tuple[str, ...] = ()
) -> None:
    """Repo-free validation of an ACT spec; raises ValueError. Shared with the work-queue API.

    Security finding C1 (2026-09-22): ``file.startswith("src/")`` accepted
    ``src/../cloud-vault-mcp/.../auth.py`` and *oracle* was not checked at all, so a spec
    could make the loop commit edits to auth/CI code or run pytest on ``/tmp/x_test.py``
    (and the conftest.py beside it).
    """
    check_act_fields(file, oracle, targets)
    for t in extra_tests:
        _check_rel(str(t).split("::", 1)[0], "tests", "oracle test")


def check_act_fields(
    file: str | None = None, oracle: str | None = None, targets: list[str] | None = None
) -> None:
    """Validate whichever ACT fields are given (None = not supplied); raises ValueError."""
    if file is not None:
        _check_rel(file, "src", "edit target")
    if oracle is not None:
        _check_rel(str(oracle).split("::", 1)[0], "tests", "oracle test")
    if targets is not None and (
        not targets or not all(isinstance(t, str) and _IDENT.match(t) for t in targets)
    ):
        raise ValueError(f"edit targets must be Python identifiers: {targets!r}")


def _is_git_repo(repo: Path) -> bool:
    return (repo / ".git").exists()


def resolve_act_paths(
    repo: Path, file: str, oracle: str, targets: list[str], extra_tests: list[str] = ()
) -> Path:
    """Validate the spec against *repo*; return the edit target's path (C1).

    Beyond :func:`check_act_spec`: every path must resolve to itself (no symlinked
    component can redirect it outside src/ or tests/), exist, and -- in a git repo -- the
    edit target must be tracked, so a GREEN commit can only ever touch a known source file.
    """
    check_act_spec(file, oracle, targets, extra_tests)
    base = repo.resolve()
    rels = [(file, "src")] + [(str(t).split("::", 1)[0], "tests") for t in [oracle, *extra_tests]]
    for rel, root in rels:
        want = base / rel
        if want.resolve() != want or not want.resolve().is_relative_to(base / root):
            raise ValueError(f"path escapes {root}/ via a symlink: {rel!r}")
        if not want.is_file():
            raise ValueError(f"no such file: {rel!r}")
    if _is_git_repo(repo):
        try:
            git(repo, "ls-files", "--error-unmatch", "--", file)
        except subprocess.CalledProcessError as exc:
            raise ValueError(f"edit target is not tracked by git: {file!r}") from exc
    return base / file


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


def _has_call(node: ast.AST) -> bool:
    return any(
        isinstance(n, ast.Call | ast.Await | ast.Yield | ast.YieldFrom) for n in ast.walk(node)
    )


def _decorator_dumps(node: ast.AST | None) -> set[str]:
    """Every decorator expression anywhere in *node* (the ones the model may restate)."""
    if node is None:
        return set()
    return {
        ast.dump(d)
        for n in ast.walk(node)
        for d in getattr(n, "decorator_list", [])
        if isinstance(n, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
    }


def _check_import_time(node: ast.stmt, allowed_decorators: set[str], where: str) -> None:
    """Refuse model code that would RUN when the module is imported (security finding C2).

    A def's body runs only when called (that is the point: the oracle calls it). But its
    decorators, default values and annotations, a class body, and an assignment's value all
    execute at import time -- during pytest collection and in every importer. Those may not
    call anything, and decorators must be ones the original definition already had.
    """
    exprs: list[ast.AST] = []
    decorators = list(getattr(node, "decorator_list", []))
    for d in decorators:
        if ast.dump(d) not in allowed_decorators:
            raise ValueError(f"{where}: new decorator `{ast.unparse(d)}` is not allowed")
    if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
        a = node.args
        exprs += [*a.defaults, *(d for d in a.kw_defaults if d is not None)]
        args = [*a.posonlyargs, *a.args, *a.kwonlyargs, a.vararg, a.kwarg]
        exprs += [x.annotation for x in args if x is not None and x.annotation is not None]
        if node.returns is not None:
            exprs.append(node.returns)
    elif isinstance(node, ast.ClassDef):
        exprs += [*node.bases, *(k.value for k in node.keywords)]
        for st in node.body:
            if isinstance(st, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                _check_import_time(st, allowed_decorators, f"{where}.{st.name}")
            elif isinstance(st, ast.Assign | ast.AnnAssign | ast.Expr | ast.Pass):
                exprs.append(st)
            else:
                raise ValueError(f"{where}: `{type(st).__name__}` in a class body is not allowed")
    elif isinstance(node, ast.Assign | ast.AnnAssign):
        exprs.append(node)
    for e in exprs:
        if _has_call(e):
            raise ValueError(f"{where}: `{ast.unparse(e)}` would run code at import time")


def splice(source: str, replacement: str, anchor: str, *, allowed: set[str]) -> str:
    """Replace the top-level definitions named in *allowed* with their versions in *replacement*.

    Only definitions whose name is in *allowed* (the task's edit targets) may appear: any
    other def, assignment, expression, decorator or class body is refused (security finding
    C2, 2026-09-22 -- ``X = __import__("os").system(...)`` and a replacement of a NON-target
    function were both accepted). A new name in *allowed* is inserted before *anchor*.
    """
    new_nodes = ast.parse(replacement).body
    if not new_nodes:
        raise ValueError("empty replacement")
    rep_lines, lines = replacement.splitlines(), source.splitlines()
    src_body = ast.parse(source).body
    existing = {n: _span(node) for node in src_body for n in _top_level_names(node)}
    originals = {n: node for node in src_body for n in _top_level_names(node)}
    imported = {n for node in src_body for n in _import_names(node)}
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
        assigned = (
            node.targets
            if isinstance(node, ast.Assign)
            else [node.target]
            if isinstance(node, ast.AnnAssign)
            else []
        )
        if not names or not all(isinstance(t, ast.Name) for t in assigned):
            raise ValueError(f"unsupported top-level statement: {type(node).__name__}")
        outside = [n for n in names if n not in allowed]
        if outside:
            raise ValueError(
                f"`{', '.join(outside)}` is not an edit target ({sorted(allowed)}); "
                "change only those definitions and put helpers inside the function body"
            )
        _check_import_time(node, _decorator_dumps(originals.get(names[0])), names[0])
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

# run_tests' tail when the pytest subprocess hit its timeout. A timed-out verify is an
# INSTRUMENT outcome (loaded box, hung fixture, runaway edit), not a verdict on the edit.
PYTEST_TIMEOUT = "pytest TIMEOUT"


# Verification runs MODEL-WRITTEN code (the edited def's body, called by the oracle). It gets
# no credentials: only these variables survive from the daemon's environment (C2).
_VERIFY_ENV_ALLOW = ("PATH", "LANG", "LC_ALL", "LC_CTYPE", "TZ", "COHEZION_JOURNEY_PERSIST")


def verify_env(repo: Path, scratch: Path) -> dict[str, str]:
    """Allow-listed environment for a verify run; HOME/TMPDIR/pycache live in *scratch*."""
    env = {k: os.environ[k] for k in _VERIFY_ENV_ALLOW if k in os.environ}
    env.setdefault("PATH", "/usr/bin:/bin")
    (scratch / "tmp").mkdir(parents=True, exist_ok=True)
    env.update(
        PYTHONPATH=str(repo / "src"),
        # Fresh bytecode cache per run: a same-size edit written within the mtime
        # granularity of the previous run is otherwise served from a STALE .pyc.
        PYTHONPYCACHEPREFIX=str(scratch / "pyc"),
        HOME=str(scratch),
        TMPDIR=str(scratch / "tmp"),
    )
    return env


def _namespace_prefix() -> tuple[str, ...]:
    try:
        from cohezion.compound.sandboxed_exec import bwrap_prefix
    except ImportError:
        return ()
    return bwrap_prefix()


def verify_isolation() -> str:
    """Which boundary the verify run gets: ``bwrap`` or ``env-scrub-only``.

    ``env-scrub-only`` (bwrap missing or user namespaces denied) means NO filesystem or
    network boundary: the model's code runs with this UID's file access. The commit-time
    integrity check (:func:`_tampered`) and hook-less commits are then the only controls.
    """
    return "bwrap" if _namespace_prefix() else "env-scrub-only"


def verify_argv(repo: Path, python: str, scratch: Path) -> list[str]:
    """bwrap wrapper for a verify run: read-only root (incl. the repo and .git), no network,
    private /tmp; only *scratch* is writable. ``[]`` when namespaces are unavailable."""
    prefix = _namespace_prefix()
    if not prefix:
        return []
    root, py_dir, tmp = str(repo.resolve()), str(Path(python).parent), str(scratch)
    return [
        *prefix,
        # Re-expose paths the private /tmp may have shadowed.
        "--ro-bind", root, root, "--ro-bind", py_dir, py_dir, "--bind", tmp, tmp,
        "--chdir", root,
    ]  # fmt: skip


def run_tests(repo: Path, python: str, tests: list[str], timeout: float = 300) -> tuple[bool, str]:
    """Run pytest on *tests*; return (green, output tail).

    Sandboxed per security finding C2: scrubbed env always, bwrap (read-only repo and .git,
    ``--unshare-all`` so no network) when the host allows namespaces.
    """
    scratch = Path(tempfile.mkdtemp(prefix="act_verify_"))
    cmd = [python, "-m", "pytest", *tests, "-q", "-p", "no:cacheprovider", "--tb=short"]
    try:
        p = subprocess.run(
            [*verify_argv(repo, python, scratch), *cmd],
            cwd=repo,
            env=verify_env(repo, scratch),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False, PYTEST_TIMEOUT
    finally:
        shutil.rmtree(scratch, ignore_errors=True)
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
        "definition shown above that you change. Only those definitions may appear: no new "
        "top-level functions, constants, decorators or statements (put helpers and imports "
        "inside the function body). Do not include tests or unchanged definitions. "
        "No prose needed."
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
    caller_cap: int = 10,  # 20 oom_guard callers measured 76s per run; x3 confirm repeats
    caller_timeout: float = 300,
    admit: AdmitFn | None = None,
    admit_models: list[str] | None = None,
    max_verify_timeouts: int = 2,
) -> dict[str, Any]:
    """Propose -> splice -> verify -> feed back, up to *max_iters*; commit only on green.

    A single green run can be a fluke (order-dependent oracle, uninitialised state, timing).
    Before committing, the first GREEN is re-run *confirm_repeats - 1* more times; any red
    repeat means the candidate is FLAKY_ORACLE, never committed, and the file is restored.
    Pattern from EverMind-AI/Raven's Evolver (K=3 confirmation gate), adapted: we have no
    second arm to compare against, so this confirms determinism rather than significance.

    Status GREEN / EXHAUSTED / ROUTER_UNAVAILABLE / ADMISSION_REFUSED / RUNNER_BROKEN /
    FLAKY_ORACLE / VERIFY_TIMEOUT / ORACLE_ALREADY_GREEN (non-discriminating).

    Verify timeouts: a pytest run that hits its timeout is an instrument failure like
    RUNNER_BROKEN, not a RED attempt. It is logged as outcome VERIFY_TIMEOUT, the file is
    restored, the attempt does not consume a model iteration and is not fed back as a test
    failure. Its own budget (*max_verify_timeouts*) still bounds a runaway edit that hangs
    every run; exceeding it (or a timeout before the first model call, or on a confirm
    repeat) returns status VERIFY_TIMEOUT.

    Admission gate: when *admit* is given (production: ``hotswap.ensure_resident``), every
    chat call is preceded by admitting the first of *admit_models* (default ``[model]``) the
    gate accepts. A residency check alone is not enough: another session can evict the
    model and the router then loads it on demand, bypassing the RAM floor. If the gate
    refuses every candidate the loop returns ADMISSION_REFUSED at once -- a safety-gate
    outcome, not a model failure, and not retried through the call-error budget.

    Caller regression guard: *callers* None (default) auto-selects ``caller_tests`` (test
    files importing the edited module or a src module that imports it); ``[]`` disables it.
    Only callers green on the ORIGINAL file are kept, then run with the oracle on every
    attempt: an edit that satisfies the oracle but breaks a caller is RED, never committed.
    (2026-09-21: commit 2b81df1ca passed its oracle and broke ``oom_guard.pre_load_gate``.)
    """
    path = resolve_act_paths(repo, file, oracle, targets, extra_tests)
    oracle_file = repo.resolve() / oracle.split("::", 1)[0]  # *oracle* may be a pytest node id
    original = path.read_text()
    oracle_src = oracle_file.read_text()
    # The model's text must never outlive a failure (C1): every exit path -- including an
    # exception from pytest, the splice, or the commit -- restores *original* unless the
    # edit was committed (or deliberately kept green with commit=False).
    keep = False
    try:
        res = _act_iterations(
            repo=repo, file=file, path=path, original=original, oracle=oracle,
            oracle_file=oracle_file, oracle_src=oracle_src, targets=targets,
            extra_tests=extra_tests, task=task, task_id=task_id, model=model, chat=chat,
            python=python, max_iters=max_iters, log=log, commit=commit,
            max_call_errors=max_call_errors, call_backoff_s=call_backoff_s,
            confirm_repeats=confirm_repeats, callers=callers, caller_cap=caller_cap,
            caller_timeout=caller_timeout, admit=admit, admit_models=admit_models,
            max_verify_timeouts=max_verify_timeouts,
        )  # fmt: skip
        keep = res.get("status") == "GREEN"
        return res
    finally:
        if not keep:
            path.write_text(original)


def _act_iterations(
    *,
    repo: Path,
    file: str,
    path: Path,
    original: str,
    oracle: str,
    oracle_file: Path,
    oracle_src: str,
    targets: list[str],
    extra_tests: list[str],
    task: str,
    task_id: str,
    model: str,
    chat: ChatFn,
    python: str,
    max_iters: int,
    log: Path,
    commit: bool,
    max_call_errors: int,
    call_backoff_s: float,
    confirm_repeats: int,
    callers: list[str] | None,
    caller_cap: int,
    caller_timeout: float,
    admit: AdmitFn | None,
    admit_models: list[str] | None,
    max_verify_timeouts: int,
) -> dict[str, Any]:
    """Body of :func:`act_loop`; the caller owns restoring *path* on every non-GREEN exit."""
    tests = [oracle, *extra_tests]
    ok, failure = run_tests(repo, python, tests)
    if ok:
        return {"status": "ORACLE_ALREADY_GREEN"}
    if failure == PYTEST_TIMEOUT:
        return {"status": "VERIFY_TIMEOUT", "iterations": 0, "detail": "pre-edit oracle run"}
    if any(marker in failure for marker in _RUNNER_BROKEN_MARKERS):
        # The oracle could not RUN (no pytest, bad node id): an instrument failure. Asking the
        # model to fix it burns every iteration and ends EXHAUSTED, blaming the model.
        return {"status": "RUNNER_BROKEN", "python": python, "detail": failure[-400:]}
    if callers is None:
        skip = {t.split("::", 1)[0] for t in tests}
        callers = caller_tests(repo, file, exclude=skip, cap=caller_cap)
    guarded = _baseline_green(repo, python, callers, caller_timeout, budget_s=caller_timeout)
    _log(
        log,
        {
            "task_id": task_id,
            "caller_tests": guarded,
            "caller_candidates": callers,
            "verify_isolation": verify_isolation(),
        },
    )
    # Last point before MODEL code runs: everything after this is compared against it.
    baseline = _repo_fingerprint(repo, file) if commit else None
    tests = [*tests, *guarded]
    run_timeout = 300 + (caller_timeout if guarded else 0)
    history: list[str] = []
    t0 = time.monotonic()
    it = call_errors = verify_timeouts = 0
    last_model = model
    while it < max_iters:
        it += 1
        defs = "\n\n\n".join(get_def_source(original, t) for t in targets)
        prompt = build_prompt(task, file, defs, oracle_src, failure, history)
        rec: dict[str, Any] = {"task_id": task_id, "iter": it, "model": model}
        if admit is not None:
            refusals = _admission_refusals(admit, admit_models or [model])
            if refusals is not None:
                rec["outcome"] = "ADMISSION_REFUSED"
                rec["refusals"] = refusals
                _log(log, rec)
                return {
                    "status": "ADMISSION_REFUSED",
                    "iterations": it - 1,
                    "wall_s": round(time.monotonic() - t0, 1),
                    "detail": refusals,
                }
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
        rec["model"] = last_model = reply.get("model", model)
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
            path.write_text(splice(original, code, anchor=targets[0], allowed=set(targets)))
            # Format BEFORE verification: the commit must be exactly the bytes that went
            # green (correctness C7 -- `ruff check --fix` after the K=3 confirmation could
            # delete an "unused" re-export and commit code no run had tested).
            _format(repo, file, python)
        except Exception as exc:
            path.write_text(original)
            rec["outcome"] = f"APPLY_ERROR {type(exc).__name__}: {exc}"
            _log(log, rec)
            history.append(f"attempt {it}:\n```python\n{code}\n```\nrejected: {exc}")
            continue
        ok, out = run_tests(repo, python, tests, run_timeout)
        if out == PYTEST_TIMEOUT:
            path.write_text(original)
            rec["outcome"] = "VERIFY_TIMEOUT"
            _log(log, rec)
            verify_timeouts += 1
            it -= 1  # the runner, not the model, failed to produce a verdict
            if verify_timeouts > max_verify_timeouts:
                return {
                    "status": "VERIFY_TIMEOUT",
                    "iterations": it,
                    "wall_s": round(time.monotonic() - t0, 1),
                    "verify_timeouts": verify_timeouts,
                }
            continue
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
                    if r_out == PYTEST_TIMEOUT:
                        return {
                            "status": "VERIFY_TIMEOUT",
                            "iterations": it,
                            "wall_s": round(time.monotonic() - t0, 1),
                            "failed_on_confirm": rep,
                        }
                    return {
                        "status": "FLAKY_ORACLE",
                        "iterations": it,
                        "wall_s": round(time.monotonic() - t0, 1),
                        "failed_on_confirm": rep,
                        "detail": r_out[-400:],
                    }
            tamper = _tampered(repo, file, baseline) if commit else []
            if tamper:
                _log(
                    log, {"task_id": task_id, "iter": it, "outcome": "TAMPERED", "changed": tamper}
                )
                return {
                    "status": "TAMPERED",
                    "iterations": it,
                    "wall_s": round(time.monotonic() - t0, 1),
                    "detail": tamper[:20],
                }
            try:
                sha = (
                    _commit(repo, file, task_id, rec["model"], targets, python) if commit else None
                )
            except (OSError, subprocess.SubprocessError) as exc:
                _log(log, {"task_id": task_id, "iter": it, "outcome": f"COMMIT_FAILED {exc}"})
                return {
                    "status": "COMMIT_FAILED",
                    "iterations": it,
                    "wall_s": round(time.monotonic() - t0, 1),
                    "detail": str(exc)[-400:],
                }
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
        # The model that made the last attempt: the caller credits the failure to its engine.
        "model": last_model,
    }


def _admission_refusals(admit: AdmitFn, models: list[str]) -> dict[str, str] | None:
    """None once *admit* accepts one of *models* (in order); else each model's refusal."""
    refusals: dict[str, str] = {}
    for m in models:
        try:
            result = admit(m)
        except Exception as exc:  # a gate that cannot decide has not admitted
            refusals[m] = f"{type(exc).__name__}: {exc}"
            continue
        if getattr(result, "ok", False):
            return None
        refusals[m] = str(getattr(result, "reason", result))
    return refusals


def _log(log: Path, rec: dict[str, Any]) -> None:
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a") as f:
        f.write(json.dumps(rec, default=str) + "\n")


def git(repo: Path, *args: str) -> str:
    """Run git in *repo*; raise on failure; return stdout."""
    p = subprocess.run(["git", *args], cwd=repo, capture_output=True, text=True, check=True)
    return p.stdout


# Every git call made after model code has run: no hooks, no fsmonitor command (C2).
# Consequence: ACT commits on act/* branches have NOT been through the repo's pre-commit
# battery. Landing one needs the normal gates (automerge_guard) -- never fast-forward blind.
_SAFE_GIT = ("-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false")


def _repo_fingerprint(repo: Path, file: str) -> dict[str, Any] | None:
    """Git control files + working-tree status, EXCLUDING the edit target; None if no repo.

    Taken before model code first runs and compared before committing. A verify run that
    plants a hook, rewrites .git/config (hooksPath, fsmonitor, filters), drops an untracked
    conftest.py/.gitattributes, or touches any other file aborts the commit (TAMPERED).
    It detects PERSISTENT changes only: a write that is undone before the check (a transient
    edit during the verify window) is invisible to it. bwrap's read-only mounts, when
    available, are what prevent those.
    """
    if not _is_git_repo(repo):
        return None
    dirs = {
        Path(repo, d).resolve()
        for d in git(repo, "rev-parse", "--git-dir", "--git-common-dir").split()
    }
    files: dict[str, str] = {}
    for d in sorted(dirs):
        for sub in ("config", "hooks", "info"):
            top = d / sub
            for f in sorted([top, *top.rglob("*")] if top.is_dir() else [top]):
                if f.is_symlink():
                    files[str(f)] = "link:" + os.readlink(f)
                elif f.is_file():
                    files[str(f)] = (
                        f"{f.stat().st_mode:o}:{hashlib.sha256(f.read_bytes()).hexdigest()}"
                    )
    status = git(repo, *_SAFE_GIT, "status", "--porcelain=v1", "--untracked-files=all")
    lines = sorted(ln for ln in status.splitlines() if ln[3:] != file)
    return {"git_dirs": sorted(map(str, dirs)), "files": files, "status": lines}


def _tampered(repo: Path, file: str, baseline: dict[str, Any] | None) -> list[str]:
    """What changed outside *file* since *baseline* (empty = clean)."""
    if baseline is None:
        return []
    now = _repo_fingerprint(repo, file) or {}
    diffs = [k for k in set(baseline["files"]) | set(now.get("files", {}))
             if baseline["files"].get(k) != now.get("files", {}).get(k)]  # fmt: skip
    diffs += sorted(set(now.get("status", [])) ^ set(baseline["status"]))
    return diffs


def _format(repo: Path, file: str, python: str) -> None:
    """ruff format + fix *file* in place, with the venv's ruff if it has one."""
    ruff = Path(python).parent / "ruff"
    if ruff.exists():
        for cmd in (["format", file], ["check", "--fix", file]):
            subprocess.run([str(ruff), *cmd], cwd=repo, check=False, capture_output=True)


def _one_line(text: str, cap: int = 120) -> str:
    """Card-supplied text as ONE printable line: a newline could forge commit trailers
    (``Co-Authored-By:``, ``Signed-off-by:``) in the message."""
    return "".join(ch if ch.isprintable() else " " for ch in str(text))[:cap]


def _commit(
    repo: Path, file: str, task_id: str, model: str, targets: list[str], python: str
) -> str:
    names, tid, who = (_one_line(x) for x in (", ".join(targets), task_id, model))
    msg = f"fix(act-loop): {names} [task: {tid}] [author: local-model {who}]"
    try:
        git(repo, *_SAFE_GIT, "add", "--", file)
        git(repo, *_SAFE_GIT, "commit", "-q", "--no-verify", "-m", msg)
    except subprocess.CalledProcessError:
        # A failed commit (hook, index lock, no identity) must not leave the edit STAGED:
        # the next task's commit would sweep it in under its own task id. The caller
        # restores the working file; this unstages it.
        subprocess.run(["git", *_SAFE_GIT, "reset", "-q", "--", file], cwd=repo, check=False)
        raise
    return git(repo, "rev-parse", "--short", "HEAD").strip()
