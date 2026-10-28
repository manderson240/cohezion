"""checked_statements: the one place HTTP-200-with-ERR becomes an error."""

from __future__ import annotations

import pytest

from cohezion.storage.surreal_http import SurrealQLError, checked_statements


def test_all_ok_passes_through():
    body = [{"status": "OK", "result": [{"id": "x:1"}], "time": "1ms"}]
    assert checked_statements(body) is body


def test_any_err_statement_raises_with_the_db_message():
    body = [
        {"status": "OK", "result": None},
        {"status": "ERR", "result": "Specify a namespace to use"},
    ]
    with pytest.raises(SurrealQLError, match="Specify a namespace") as ei:
        checked_statements(body)
    assert ei.value.failed == [body[1]]


def test_http_error_surfaces_the_body_not_just_the_code():
    with pytest.raises(SurrealQLError, match="Parse error at line 3") as ei:
        checked_statements([], status_code=400, text='{"details":"Parse error at line 3"}')
    assert ei.value.status_code == 400


def test_non_list_body_is_rejected():
    with pytest.raises(SurrealQLError, match="shape"):
        checked_statements({"error": "something"})


def test_allow_partial_returns_but_never_hides():
    body = [{"status": "ERR", "result": "boom"}]
    out = checked_statements(body, allow_partial=True)
    assert out[0]["status"] == "ERR"  # caller must look; nothing is swallowed


def test_reflex_lineage_stdlib_only():
    """Importable without the cohezion package machinery (fresh-interpreter budget)."""
    import subprocess
    import sys
    from pathlib import Path

    src = Path(__file__).resolve().parents[2] / "src" / "cohezion" / "storage" / "surreal_http.py"
    r = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            f"import importlib.util as u,sys;s=u.spec_from_file_location('m','{src}');m=u.module_from_spec(s);sys.modules['m']=m;s.loader.exec_module(m);print(sum(k.startswith('cohezion') for k in sys.modules))",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == "0"
