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
