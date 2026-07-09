"""Minimal in-process hardening for ``exec()`` of LLM-synthesized code (security finding H5).

THE BUG: CPython auto-injects the FULL ``builtins`` module into any globals dict that lacks a
``"__builtins__"`` key. So ``exec(llm_code, {"np": np})`` runs with ``__import__``, ``open``,
``eval``, ``compile``, ``os``, ``subprocess`` all reachable — i.e. arbitrary code execution. The
exec'd code is model-generated from a task prompt, so this is a prompt-injection -> RCE chain.

THIS FIX supplies a restricted ``__builtins__`` allow-list plus a curated ``__import__`` that only
names a small set of pure, computational modules (math, numpy, itertools, ...) at the import-statement
level. It is NOT a security boundary. Two independent in-process escapes remain WIDE OPEN:
  1. Transitive module attributes — several allow-listed modules re-export ``sys`` (and from there
     ``os``) as a plain attribute: ``import collections; collections._sys.modules['os'].system(...)``
     reaches os in a SINGLE attribute access (``statistics.sys`` is a second path; ``json.codecs``
     reaches codecs; ``numpy.testing`` imports freely). Directly blocking the literal name ``sys``
     at the import gate does NOT prevent this and is not attempted.
  2. Introspection gadget chains — ``().__class__.__bases__[0].__subclasses__()`` escapes regardless
     of the import gate.
So treat the import allow-list as an AVAILABILITY restore plus a minor speed-bump against the most
naive ``import os`` line — NOT as a sandbox. The DURABLE security boundary is running untrusted/LLM
code OUT OF PROCESS (subprocess + ``resource`` rlimits + seccomp/``bubblewrap``/``nsjail``, or
RestrictedPython). Do not rely on anything in this module to contain hostile code.

AVAILABILITY (finding F2): a previous hardening denied ``__import__`` entirely, which broke legit
LLM-generated ARC/AIMO solver code that does ``import numpy`` / ``import math`` / ``from itertools
import ...`` — ``solve`` was never defined and the fallback solver silently returned None. The
curated allow-list below restores those imports. It does NOT reduce the attack surface to "safe"
(see the transitive/gadget escapes above); it only stops the most naive direct ``import os``.
"""

from __future__ import annotations

import builtins


# Pure, side-effect-free builtins the LLM math/policy code legitimately needs. DELIBERATELY EXCLUDES
# __import__, open, eval, compile, exec, input, globals, locals, vars, getattr, setattr, delattr,
# __build_class__, memoryview, breakpoint, help. (True/False/None are keywords — always available.)
_ALLOWED = (
    "abs",
    "all",
    "any",
    "bin",
    "bool",
    "bytearray",
    "bytes",
    "callable",
    "chr",
    "complex",
    "dict",
    "divmod",
    "enumerate",
    "filter",
    "float",
    "format",
    "frozenset",
    "hash",
    "hex",
    "int",
    "isinstance",
    "issubclass",
    "iter",
    "len",
    "list",
    "map",
    "max",
    "min",
    "next",
    "oct",
    "ord",
    "pow",
    "print",
    "range",
    "repr",
    "reversed",
    "round",
    "set",
    "slice",
    "sorted",
    "str",
    "sum",
    "tuple",
    "zip",
    # exceptions the generated code may raise/catch
    "Exception",
    "ValueError",
    "TypeError",
    "KeyError",
    "IndexError",
    "AttributeError",
    "ZeroDivisionError",
    "ArithmeticError",
    "RuntimeError",
    "StopIteration",
    "OverflowError",
    "NotImplementedError",
)

# Computational modules that LLM solver code legitimately imports. The literal names os, subprocess,
# sys, socket, shutil, importlib, builtins, ctypes, pathlib are not on this list — but that is an
# AVAILABILITY/naive-typo filter, NOT a security guarantee: several entries below transitively
# re-export sys/os (e.g. collections._sys, statistics.sys), so this gate does not contain hostile
# code. See the module docstring; the real boundary is out-of-process.
_ALLOWED_MODULES = frozenset(
    {
        "math",
        "numpy",
        "itertools",
        "functools",
        "collections",
        "statistics",
        "fractions",
        "decimal",
        "re",
        "json",
    }
)


def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    """Restricted ``__import__`` for exec'd LLM code. Permits only top-level imports whose root is in
    the curated list (``import numpy``, ``from itertools import product``); ``numpy.linalg`` is allowed
    iff its root ``numpy`` is. A non-allow-listed root (``import os``) raises ImportError. This is an
    AVAILABILITY/naive-typo gate, NOT a sandbox: allow-listed modules transitively re-export sys/os
    (see module docstring), so this does not contain hostile code."""
    root = name.partition(".")[0]
    if root not in _ALLOWED_MODULES:
        raise ImportError(f"import of {name!r} is not permitted in safe_exec")
    return builtins.__import__(name, globals, locals, fromlist, level)


_SAFE_BUILTINS: dict = {
    name: getattr(builtins, name) for name in _ALLOWED if hasattr(builtins, name)
}
_SAFE_BUILTINS["__import__"] = _safe_import


def safe_exec_globals(**extra) -> dict:
    """Return a globals dict for ``exec()`` of UNTRUSTED / LLM-generated code: a restricted
    ``__builtins__`` allow-list (no import/open/eval) plus the caller's explicit names
    (e.g. ``np=np``, ``sympy=sympy``). Any caller-supplied ``__builtins__`` is dropped so it can't
    re-open the hole. Closes the H5 auto-injection RCE; see module docstring for the durable fix."""
    extra.pop("__builtins__", None)
    return {"__builtins__": _SAFE_BUILTINS, **extra}
