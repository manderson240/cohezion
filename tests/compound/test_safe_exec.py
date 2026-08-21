"""H5 availability-regression tests for safe_exec_globals (security finding F2 re-eval).

The hardening that supplied a restricted ``__builtins__`` accidentally denied ALL imports,
breaking legit LLM solver code (``import numpy`` / ``import math`` / ``from itertools import ...``).
These tests pin the curated safe-import allow-list: math/numpy stdlib imports SUCCEED while
os/subprocess imports still raise ImportError.
"""

from __future__ import annotations

import pytest

from cohezion.compound.safe_exec import safe_exec_globals


def test_import_math_succeeds():
    """A solver body doing `import math` must run under safe_exec_globals."""
    code = "import math\nresult = math.sqrt(16.0)"
    g = safe_exec_globals()
    exec(code, g)
    assert g["result"] == 4.0


def test_import_numpy_succeeds():
    """A solver body doing `import numpy as np` must run under safe_exec_globals."""
    np = pytest.importorskip("numpy")
    code = "import numpy as np\nresult = int(np.array([1, 2, 3]).sum())"
    g = safe_exec_globals()
    exec(code, g)
    assert g["result"] == 6


def test_from_itertools_import_succeeds():
    """`from itertools import ...` must work (common in ARC/AIMO solvers)."""
    code = "from itertools import product\nresult = len(list(product([0, 1], repeat=2)))"
    g = safe_exec_globals()
    exec(code, g)
    assert g["result"] == 4


def test_import_os_still_denied():
    """`import os` must still raise ImportError — the RCE gadget stays blocked."""
    g = safe_exec_globals()
    with pytest.raises(ImportError):
        exec("import os", g)


def test_import_subprocess_still_denied():
    """`import subprocess` must still raise ImportError."""
    g = safe_exec_globals()
    with pytest.raises(ImportError):
        exec("import subprocess", g)


def test_import_sys_still_denied():
    """`import sys` must still raise ImportError (sys.modules is an escape vector)."""
    g = safe_exec_globals()
    with pytest.raises(ImportError):
        exec("import sys", g)


def test_from_os_import_denied():
    """`from os import system` must still raise ImportError."""
    g = safe_exec_globals()
    with pytest.raises(ImportError):
        exec("from os import system", g)


def test_benign_solver_with_numpy_defines_solve():
    """End-to-end: a benign solver body that imports numpy + defines solve runs and is callable."""
    pytest.importorskip("numpy")
    solver_code = (
        "import numpy as np\n"
        "import math\n"
        "def solve(grid):\n"
        "    arr = np.array(grid)\n"
        "    return int(arr.sum()) + math.floor(0.9)\n"
    )
    g = safe_exec_globals()
    exec(solver_code, g)
    assert "solve" in g
    assert g["solve"]([[1, 2], [3, 4]]) == 10


def test_existing_builtins_allowlist_preserved():
    """The existing builtins allow-list still works; dangerous builtins still absent."""
    g = safe_exec_globals()
    exec("result = sum([1, 2, 3]) + len('abc')", g)
    assert g["result"] == 9
    with pytest.raises(NameError):
        exec("open('/etc/passwd')", g)


def test_extra_names_passed_through():
    """Caller-supplied names (e.g. np=np) are still injected."""
    np = pytest.importorskip("numpy")
    g = safe_exec_globals(np=np)
    exec("result = int(np.array([5, 5]).sum())", g)
    assert g["result"] == 10


# --- _class_defs contract (H5 site #4: auto_generator gym.Env synthesis) ---


def test_class_def_fails_without_class_defs_flag():
    """DISCRIMINATING: a `class` statement raises NameError under the DEFAULT gate.

    This pins WHY the flag is needed — the default builtins deliberately omit __build_class__
    and there is no __name__ key. If this ever stops raising, the flag has become a no-op and
    the two paths have silently merged.
    """
    g = safe_exec_globals()
    with pytest.raises(NameError):
        exec("class A:\n    pass", g)  # noqa: S102 — deliberate: testing the exec gate


def test_class_def_succeeds_with_class_defs_flag():
    """AVAILABILITY: `_class_defs=True` lets a class (with super().__init__) define + instantiate."""
    g = safe_exec_globals(_class_defs=True)
    code = (
        "class Base:\n"
        "    def __init__(self):\n"
        "        self.tag = 'base'\n"
        "class Child(Base):\n"
        "    def __init__(self):\n"
        "        super().__init__()\n"
        "        self.n = 42\n"
        "inst = Child()\n"
    )
    exec(code, g)  # noqa: S102 — deliberate: testing the exec gate
    assert g["inst"].n == 42
    assert g["inst"].tag == "base"


def test_class_defs_flag_does_not_reopen_import_hole():
    """DISCRIMINATING: the class-def builtins must NOT smuggle back __import__/open.

    A lazy fix (`__builtins__ = full builtins` when _class_defs=True) would pass the
    availability tests above while re-opening the exact RCE H5 closes. `import os` must still
    raise under the flag.
    """
    g = safe_exec_globals(_class_defs=True)
    with pytest.raises(ImportError):
        exec("import os", g)  # noqa: S102 — deliberate: testing the exec gate
    with pytest.raises(NameError):
        exec("open('/etc/passwd')", g)  # noqa: S102 — deliberate: testing the exec gate


def test_class_defs_reserved_kwarg_not_leaked_as_name():
    """`_class_defs` is a control flag, not a name the exec'd code should see."""
    g = safe_exec_globals(_class_defs=True)
    assert "_class_defs" not in g


def test_enum_not_importable_no_bltns_escape():
    """REGRESSION (CSO 2026-08-21): `enum` re-exports the real builtins as `enum.bltns`, a
    ONE-HOP escape to open/eval/exec/__import__ — strictly worse than the accepted sys->os
    escapes. A prior version briefly allow-listed enum; this pins it OFF the list on BOTH paths.

    Discriminating: an impl that adds enum back (or any module binding `builtins`/`os`) makes
    the `import enum` line succeed and the `enum.bltns.__import__` reach os — this test fails.
    """
    for g in (safe_exec_globals(), safe_exec_globals(_class_defs=True)):
        with pytest.raises(ImportError):
            exec("import enum", g)  # noqa: S102 — deliberate: testing the exec gate


def test_no_allowlisted_module_binds_real_builtins():
    """Structural guard: no module on the import allow-list may expose the real `builtins`
    module as a plain top-level attribute (the enum.bltns class of one-hop escape).

    This is the check that WOULD have caught the enum regression at authoring time — it scans
    every allow-listed module for an attribute that IS the builtins module, independent of any
    single known name.
    """
    import builtins as _b
    import importlib

    from cohezion.compound.safe_exec import _ALLOWED_MODULES

    offenders = []
    for name in _ALLOWED_MODULES:
        try:
            mod = importlib.import_module(name)
        except ImportError:
            continue
        for attr in vars(mod).values():
            if attr is _b:
                offenders.append(name)
                break
    assert not offenders, (
        f"allow-listed modules bind the real builtins (one-hop escape): {offenders}"
    )
