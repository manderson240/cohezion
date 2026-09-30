"""The SDK-import ratchet must detect a removed module, stay quiet on the baseline, and be WIRED."""

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location(
    "sdk_import_scan", ROOT / "scripts/ci/sdk_import_scan.py"
)
sis = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sis)


def test_si1_self_test_plants_a_removed_module_and_a_removed_name():
    assert sis.self_test() == 0


def test_si2_real_tree_has_no_unresolved_sdk_import_beyond_the_baseline():
    import json

    baseline = set(json.loads(sis.BASELINE.read_text()))
    assert sis.scan(sis.SRC) - baseline == set()


def test_si3_a_removed_module_is_flagged_and_a_present_one_is_not(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("from gaia.agents.chat.agent import ChatAgent\n")
    (tmp_path / "src" / "b.py").write_text("from gaia.llm.lemonade_client import LemonadeClient\n")
    found = {k.split("::")[0] for k in sis.scan(tmp_path / "src")}
    assert found == {"src/a.py"}


def test_si4_scanner_is_wired_into_both_gates():
    for gate in ("scripts/ci/automerge_guard.sh", ".github/workflows/ci.yml"):
        text = (ROOT / gate).read_text()
        assert "sdk_import_scan.py --self-test" in text and "sdk_import_scan.py\n" in text, gate


def test_si5_import_as_form_is_scanned_not_just_from_imports(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "a.py").write_text("import gaia.agents.no_such_pkg.agent as Nope\n")
    (tmp_path / "src" / "b.py").write_text("import gaia.llm.lemonade_client as ok\n")
    assert {k.split("::")[0] for k in sis.scan(tmp_path / "src")} == {"src/a.py"}


def test_si6_an_sdk_module_that_exits_at_import_is_reported_not_fatal(monkeypatch):
    def boom(_name):
        raise SystemExit(3)

    monkeypatch.setattr(sis.importlib, "import_module", boom)
    assert sis.unresolved("gaia.whatever", []) == ["gaia.whatever (SystemExit)"]
