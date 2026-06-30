"""Minimal in-process hardening for ``exec()`` of LLM-synthesized code (security finding H5).

THE BUG: CPython auto-injects the FULL ``builtins`` module into any globals dict that lacks a
``"__builtins__"`` key. So ``exec(llm_code, {"np": np})`` runs with ``__import__``, ``open``,
``eval``, ``compile``, ``os``, ``subprocess`` all reachable — i.e. arbitrary code execution. The
exec'd code is model-generated from a task prompt, so this is a prompt-injection -> RCE chain.

THIS FIX closes the trivial auto-injection hole by supplying a restricted ``__builtins__`` allow-list
(no import/open/eval/compile/exec/input/getattr-family). It is NOT a true sandbox — Python's
introspection (``().__class__.__bases__[0].__subclasses__()`` gadget chains) can still escape an
in-process restriction. The DURABLE fix is to run untrusted/LLM code OUT OF PROCESS (subprocess +
``resource`` rlimits + seccomp/``bubblewrap``/``nsjail``, or RestrictedPython). Treat this as the
stop-gap that denies the trivial ``import os`` RCE the PoC demonstrated.
"""

from __future__ import annotations

import builtins

# Pure, side-effect-free builtins the LLM math/policy code legitimately needs. DELIBERATELY EXCLUDES
# __import__, open, eval, compile, exec, input, globals, locals, vars, getattr, setattr, delattr,
# __build_class__, memoryview, breakpoint, help. (True/False/None are keywords — always available.)
_ALLOWED = (
    "abs", "all", "any", "bin", "bool", "bytearray", "bytes", "callable", "chr", "complex",
    "dict", "divmod", "enumerate", "filter", "float", "format", "frozenset", "hash", "hex",
    "int", "isinstance", "issubclass", "iter", "len", "list", "map", "max", "min", "next",
    "oct", "ord", "pow", "print", "range", "repr", "reversed", "round", "set", "slice",
    "sorted", "str", "sum", "tuple", "zip",
    # exceptions the generated code may raise/catch
    "Exception", "ValueError", "TypeError", "KeyError", "IndexError", "AttributeError",
    "ZeroDivisionError", "ArithmeticError", "RuntimeError", "StopIteration", "OverflowError",
    "NotImplementedError",
)

_SAFE_BUILTINS: dict = {name: getattr(builtins, name) for name in _ALLOWED if hasattr(builtins, name)}


def safe_exec_globals(**extra) -> dict:
    """Return a globals dict for ``exec()`` of UNTRUSTED / LLM-generated code: a restricted
    ``__builtins__`` allow-list (no import/open/eval) plus the caller's explicit names
    (e.g. ``np=np``, ``sympy=sympy``). Any caller-supplied ``__builtins__`` is dropped so it can't
    re-open the hole. Closes the H5 auto-injection RCE; see module docstring for the durable fix."""
    extra.pop("__builtins__", None)
    return {"__builtins__": _SAFE_BUILTINS, **extra}
