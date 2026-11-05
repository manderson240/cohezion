"""mesh_sig + EventConsumer signature gate. Rows are signed by a vendored copy of the
producer's sign() (~/uap-corpus/pursue/capella_mesh.py) so byte-compatibility is tested."""

from __future__ import annotations

import hashlib
import hmac
import json
import subprocess

import pytest

from cohezion.data_mesh import event_consumer as ec
from cohezion.data_mesh import mesh_sig
from cohezion.data_mesh.event_consumer import EventConsumer


KEY = bytes.fromhex("ab" * 32)


def _sign(event_type, ts, payload, source, priority, v):  # vendored producer sign()
    parts = [event_type.encode(), source.encode(), repr(ts).encode(), mesh_sig.canon(payload)]
    if v >= 2:
        parts.insert(2, str(int(priority)).encode())
    mac = hmac.new(KEY, b"|".join(parts), hashlib.sha256).hexdigest()
    return {"alg": "HMAC-SHA256", "v": v, "kid": "uap-capella-2026-11", "mac": mac}


def _row(v=2, event_type="DATA_PRODUCT_UPDATED", payload=None, priority=1):
    payload = payload or {"product_id": "uap-capella-warehouse", "counts": {"a": 5.0}}
    ts = 1762300000.25
    payload = dict(payload, _sig=_sign(event_type, ts, payload, "uap:capella", priority, v))
    return {
        "id": "data_product_event:x1",
        "event_type": event_type,
        "source": "uap:capella",
        "payload": json.dumps(payload),
        "priority": priority,
        "timestamp": ts,
    }


def _consumer(filed, **kw):
    return EventConsumer(
        "t",
        sql_fn=lambda q: [],
        key_fn=kw.pop("key_fn", lambda kid: KEY),
        file_work_item_fn=lambda t, d, dom, pr=1: filed.append((t, pr)) or "wi:1",
        **kw,
    )


@pytest.mark.parametrize("v", [1, 2])
def test_signed_rows_verify_ok(v):
    assert mesh_sig.verify_sig(_row(v=v), KEY) == "ok"


def _tamper(row):
    row = dict(row)
    row["payload"] = row["payload"].replace('"a": 5', '"a": 6')
    assert row["payload"] != _row()["payload"]
    return row


def test_flipped_payload_is_bad_and_missing_sig_is_none():
    assert mesh_sig.verify_sig(_tamper(_row()), KEY) == "BAD"
    assert (
        mesh_sig.verify_sig({"payload": "{}", "event_type": "x", "timestamp": 1.0}, KEY) == "none"
    )


@pytest.mark.parametrize(
    "sig", ["str", 7, {"mac": 5}, {"mac": "zz", "v": "x"}, {"mac": "ab", "v": None}]
)
def test_malformed_sig_is_bad_without_exception(sig):
    row = _row()
    p = json.loads(row["payload"])
    p["_sig"] = sig
    row["payload"] = json.dumps(p)
    assert mesh_sig.verify_sig(row, KEY) == "BAD"


def test_bad_sig_files_item_and_skips_handler(monkeypatch):
    filed = []
    c = _consumer(filed)
    called = []
    monkeypatch.setattr(c, "_dispatch", lambda e: called.append(e) or {"action": "tally"})
    out = c.handle(_tamper(_row()))
    assert out["action"] == "rejected_sig" and out["sig"] == "BAD"
    assert called == [] and filed == [
        ("mesh: BAD signature on DATA_PRODUCT_UPDATED from uap:capella", 2)
    ]


def test_discriminating_real_verifier_rejects_where_ok_stub_would_not(monkeypatch):
    tampered = _tamper(_row())
    assert mesh_sig.verify_sig(tampered, KEY) == "BAD"
    monkeypatch.setattr(mesh_sig, "verify_sig", lambda row, key: "ok")  # neutralized gate
    c = _consumer([])
    monkeypatch.setattr(c, "_run_drift", lambda: 0)
    assert c.handle(tampered)["action"] != "rejected_sig"  # stub lets forgery through


def test_unsigned_from_signing_source_filed_but_handled():
    filed = []
    out = _consumer(filed).handle(
        {"event_type": "custom", "source": "uap:capella", "payload": "{}"}
    )
    assert out["sig"] == "none" and out["action"] == "tally"
    assert filed[0][0] == "mesh: unsigned event from a signing source"


def test_missing_key_unverifiable_once_per_run_not_rejected():
    filed = []
    c = _consumer(filed, key_fn=lambda kid: None)
    row = _row(event_type="CUSTOM")
    assert c.handle(row)["sig"] == "unverifiable"
    assert c.handle(row)["action"] == "tally"
    assert len(filed) == 1


def test_drift_route_records_exit_code(monkeypatch):
    seen = {}
    monkeypatch.setattr(ec.DRIFT_SCRIPT.__class__, "exists", lambda self: True)

    def fake_run(cmd, **kw):
        seen.update(cmd=cmd, **kw)
        return subprocess.CompletedProcess(cmd, 2)

    monkeypatch.setattr(ec.subprocess, "run", fake_run)
    out = _consumer([]).handle(_row())
    assert out["drift"] == 2 and out["sig"] == "ok"
    assert seen["timeout"] == 120 and seen["cmd"][-1] == "drift"
    assert "drift" not in _consumer([]).handle(_row(event_type="LINEAGE_UPDATED"))


def test_drift_script_missing_skips(monkeypatch):
    monkeypatch.setattr(ec, "DRIFT_SCRIPT", ec.Path("/nonexistent/capella_mesh.py"))
    assert _consumer([]).handle(_row())["drift"] == "script-missing"


def test_load_key_enforces_mode_and_length(tmp_path):
    f = tmp_path / "uap-capella.key"
    f.write_text("ab" * 32)
    f.chmod(0o644)
    assert mesh_sig.load_key("uap-capella-2026-11", tmp_path) is None
    f.chmod(0o600)
    assert mesh_sig.load_key("uap-capella-2026-11", tmp_path) == KEY
    assert mesh_sig.load_key("other-1", tmp_path) is None
    f.write_text("ab" * 8)
    assert mesh_sig.load_key("uap-capella-2026-11", tmp_path) is None
    assert mesh_sig.load_key("uap-capella-2026-11", tmp_path / "nope") is None
