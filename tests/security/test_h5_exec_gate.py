"""H5 gate: builtins-reaching LLM code is refused; allowed code still runs.

Asserts the exact strings from the H5 adjudication brief against the out-of-process path
(``run_untrusted``) and the in-process gate (``safe_exec_globals``). NOTE the honest split:
the ``__subclasses__()`` enumeration is NOT refused (it is a pure attribute walk the allow-list
cannot see) -- the claim is that the *payload* is contained, so that half asserts containment.
"""

from __future__ import annotations

import pytest

from cohezion.compound.safe_exec import safe_exec_globals
from cohezion.compound.sandboxed_exec import run_untrusted


def test_dunder_import_os_refused_in_process():
    with pytest.raises((NameError, ImportError)):
        exec("__import__('os').system('true')", safe_exec_globals())  # noqa: S102


def test_dunder_import_os_refused_out_of_process():
    r = run_untrusted("__import__('os').system('true')", collect=True)
    assert not r.ok
    assert "not permitted in safe_exec" in r.error or "NameError" in r.error


def test_enum_hop_refused_out_of_process():
    r = run_untrusted("import enum\nenum.bltns.open('/etc/passwd')", collect=True)
    assert not r.ok
    assert "import of 'enum' is not permitted in safe_exec" in r.error  # SafeExecImportRefusedError


def test_subclasses_walk_is_not_refused_but_payload_contained(tmp_path):
    marker = tmp_path / "pwned"
    code = (
        "n = len([c for c in ().__class__.__bases__[0].__subclasses__()])\n"
        "t = [c for c in ().__class__.__bases__[0].__subclasses__()"
        " if c.__module__ == 'os' and 'system' in c.__init__.__globals__][0]\n"
        f"t.__init__.__globals__['system']('echo x > {marker}')\n"
    )
    r = run_untrusted(code, collect=True)
    assert r.value is None or r.value.get("n", 0) > 0 or not r.ok  # walk ran or child died
    assert not marker.exists()


def test_allowed_expression_still_evaluates():
    r = run_untrusted("import math\nv = sum(range(5)) + int(math.sqrt(16))\n", collect=True)
    assert r.ok, r.error
    assert r.value["v"] == 14
    g = safe_exec_globals()
    exec("x = sum(range(5))", g)  # noqa: S102
    assert g["x"] == 10
