"""Child-process bootstrap for ``sandboxed_exec.run_untrusted`` (security finding H5, durable half).

Run as ``python -I _sandbox_child.py <path-to-safe_exec.py>`` with a JSON payload on stdin. Stdlib
only: it loads ``safe_exec.py`` by FILE PATH so the child never executes cohezion's package
``__init__`` chain (a larger surface and seconds of import time).

Order is the whole design — everything that needs a file descriptor or a new process happens
BEFORE the limits, and the untrusted code runs only AFTER every limit has been applied:
  1. read payload, import allow-listed modules + requested bindings (needs open()),
  2. apply rlimits — NPROC=0 (no fork/os.system), NOFILE=3 (no open()/socket), FSIZE=0,
     AS (memory), CPU. If ANY setrlimit fails we exit WITHOUT executing (fail closed),
  3. exec inside ``safe_exec_globals`` (the in-process allow-list stays as defense in depth),
  4. write one JSON result line to fd 1 with ``os.write`` (sys.stdout is a capture buffer).
"""

import contextlib
import importlib
import importlib.abc
import importlib.util
import io
import json
import linecache
import os
import resource
import signal
import sys
import sysconfig
import traceback


# Without this, a write that trips RLIMIT_FSIZE kills the process with SIGXFSZ and NO output
# (measured: bare rc=120). Ignoring it turns the violation into a catchable OSError.
signal.signal(signal.SIGXFSZ, signal.SIG_IGN)


def _emit(obj: dict) -> None:
    os.write(1, (json.dumps(obj, default=_coerce) + "\n").encode())


def _coerce(value):
    """JSON fallback: sympy-style numbers become floats when exact-evaluable, else str."""
    if hasattr(value, "tolist"):
        return value.tolist()
    if getattr(value, "is_Integer", False):
        return int(value)
    if hasattr(value, "evalf"):
        try:
            return float(value.evalf())
        except (TypeError, ValueError):
            return str(value)
    return str(value)


def _normalize(value):
    """JSON object keys must be strings, so ``{2: 3}`` would silently become ``{"2": 3}`` — a
    semantic change (e.g. factorint's integer primes turn into strings). A dict with any
    non-string key is returned as its ``str()`` instead, which is exactly what the pre-port
    in-process executor's consumers rendered into their prompts."""
    if isinstance(value, dict):
        if all(isinstance(k, str) for k in value):
            return {k: _normalize(v) for k, v in value.items()}
        return str(value)
    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]
    return value


def _jsonable(value):
    try:
        return json.loads(json.dumps(_normalize(value), default=_coerce))
    except (TypeError, ValueError, RecursionError):
        return str(value)


def _apply_limits(cpu_s: int, mem_bytes: int) -> None:
    for name, soft_hard in (
        ("RLIMIT_CPU", (cpu_s, cpu_s + 1)),
        ("RLIMIT_AS", (mem_bytes, mem_bytes)),
        ("RLIMIT_FSIZE", (0, 0)),
        ("RLIMIT_NPROC", (0, 0)),
        ("RLIMIT_NOFILE", (3, 3)),
    ):
        resource.setrlimit(getattr(resource, name), soft_hard)


class _PreloadedSourceFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Serve lazy submodule imports (sympy does many) from sources read BEFORE the limits.

    Under NOFILE=3 the normal path finder cannot open anything, so e.g. ``sympy.solve`` failed
    with EMFILE on its first lazy import. Only ``.py`` files under already-imported allow-listed
    or explicitly bound packages, plus the pure-Python stdlib (sympy lazily imports e.g.
    ``dataclasses``), are preloaded — sympy ~850 files/16 MB/0.12 s, stdlib ~530 files/9 MB/0.09 s
    measured — so it can never be used to read an arbitrary path. Importability is NOT the
    boundary: an importable ``subprocess`` still cannot fork under RLIMIT_NPROC=0.
    """

    _SKIP_DIRS = frozenset(
        {
            "tests",
            "test",
            "__pycache__",
            "site-packages",
            "idlelib",
            "tkinter",
            "turtledemo",
            "ensurepip",
            "venv",
        }
    )

    def __init__(self, roots: set) -> None:
        self._sources: dict = {}
        for root in roots:
            mod = sys.modules.get(root)
            for pkg_dir in list(getattr(mod, "__path__", []) or []):
                self._scan(root, pkg_dir)
        self._scan("", sysconfig.get_paths()["stdlib"])

    def _scan(self, root: str, top: str) -> None:
        for dirpath, dirnames, filenames in os.walk(top):
            dirnames[:] = [d for d in dirnames if d not in self._SKIP_DIRS]
            rel = os.path.relpath(dirpath, top)
            parts = [p for p in [root, *([] if rel == "." else rel.split(os.sep))] if p]
            for fname in filenames:
                if not fname.endswith(".py"):
                    continue
                is_pkg = fname == "__init__.py"
                name = ".".join(parts if is_pkg else [*parts, fname[:-3]])
                if not name or name in self._sources:
                    continue
                path = os.path.join(dirpath, fname)
                with open(path, "rb") as fh:
                    self._sources[name] = (path, fh.read(), is_pkg)

    def find_spec(self, fullname, path=None, target=None):
        entry = self._sources.get(fullname)
        if entry is None:
            return None
        origin, _, is_pkg = entry
        spec = importlib.util.spec_from_loader(fullname, self, origin=origin, is_package=is_pkg)
        if spec is not None:
            spec.has_location = True
            if is_pkg:
                spec.submodule_search_locations = [os.path.dirname(origin)]
        return spec

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        spec = module.__spec__
        if spec is None:
            raise ImportError(f"no spec for {module.__name__}")
        origin, source, _ = self._sources[spec.name]
        exec(compile(source, origin, "exec"), module.__dict__)  # noqa: S102 — trusted package source


def main() -> None:
    payload = json.loads(sys.stdin.read())
    spec = importlib.util.spec_from_file_location("_cz_safe_exec", sys.argv[1])
    if spec is None or spec.loader is None:
        _emit({"ok": False, "error": f"sandbox refused: cannot load {sys.argv[1]}"})
        return
    safe_exec = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(safe_exec)

    # Pre-import: once NOFILE=3 is set nothing can be loaded from disk, so an allow-listed
    # `import json` inside the untrusted code must be a sys.modules hit.
    for mod in sorted(safe_exec._ALLOWED_MODULES):
        with contextlib.suppress(ImportError):
            importlib.import_module(mod)
    bound = {}
    for name, target in payload.get("bindings", {}).items():
        mod_name, _, attr = target.partition(":")
        obj = importlib.import_module(mod_name)
        bound[name] = getattr(obj, attr) if attr else obj

    roots = {m.partition(".")[0] for m in sys.modules} & (
        set(safe_exec._ALLOWED_MODULES)
        | {t.partition(":")[0].partition(".")[0] for t in payload.get("bindings", {}).values()}
    )
    sys.meta_path.insert(0, _PreloadedSourceFinder(roots))

    try:
        _apply_limits(int(payload["cpu_s"]), int(payload["mem_bytes"]))
    except (OSError, ValueError) as exc:
        _emit({"ok": False, "error": f"sandbox refused: rlimit not applied ({exc})"})
        return

    captured = io.StringIO()
    sys.stdout = sys.stderr = captured
    try:
        # ONE namespace: with a separate locals dict, names bound at top level (imports, classes)
        # are invisible inside functions the code defines, whose globals are `g`.
        g = safe_exec.safe_exec_globals(**bound)
        preset = set(g)
        # Registered so tracebacks show the untrusted source lines (linecache cannot open files
        # under NOFILE=3, and "<untrusted>" is not a file anyway).
        src_lines = payload["code"].splitlines(keepends=True)
        linecache.cache["<untrusted>"] = (len(payload["code"]), None, src_lines, "<untrusted>")
        exec(compile(payload["code"], "<untrusted>", "exec"), g)  # noqa: S102 — the sandboxed exec itself
        value = None
        if payload.get("call"):
            fn = g.get(payload["call"])
            if not callable(fn):
                raise NameError(f"{payload['call']!r} not defined by untrusted code")
            value = _jsonable(fn(*payload.get("args", [])))
        elif payload.get("collect"):
            value = {
                k: _jsonable(v)
                for k, v in g.items()
                if k not in preset
                and not k.startswith("_")
                and not callable(v)
                and not isinstance(v, type(sys))
            }
        result = {"ok": True, "value": value}
    except BaseException as exc:
        result = {
            "ok": False,
            "error": f"{type(exc).__name__}: {exc}"[:2000],
            "traceback": traceback.format_exc()[-4000:],
        }
    result["stdout"] = captured.getvalue()[-4000:]
    _emit(result)


if __name__ == "__main__":
    main()
