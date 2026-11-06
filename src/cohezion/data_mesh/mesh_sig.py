"""HMAC verification for signed ``data_product_event`` rows (consumer side).

Byte-compatible with the producer ``~/uap-corpus/pursue/capella_mesh.py`` (canon/sign/check_sig):
``_sig`` = {alg, v, kid, mac} inside the JSON-string ``payload``; the MAC covers
event_type|source|[str(int(priority)) if v>=2]|repr(timestamp)|canon(payload minus _sig).
Key bytes are never logged or returned in messages.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any


KEY_DIR = Path.home() / ".config" / "cohezion" / "mesh_keys"
_KID_PREFIX_TO_FILE = {"uap-capella-": "uap-capella.key"}
_DEFAULT_SOURCE = "uap:capella"  # producer: ``source or SOURCE``


def _num(x: Any) -> Any:
    """Whole floats -> int so 5.0 and 5 canonicalise alike (matches the producer)."""
    if isinstance(x, float) and x.is_integer():
        return int(x)
    if isinstance(x, dict):
        return {k: _num(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_num(v) for v in x]
    return x


def canon(x: Any) -> bytes:
    return json.dumps(
        _num(x), sort_keys=True, separators=(",", ":"), ensure_ascii=False, default=str
    ).encode()


def verify_sig(row: dict[str, Any], key_bytes: bytes) -> str:
    """Return ``"ok"`` | ``"BAD"`` | ``"none"``; malformed input is BAD, never an exception."""
    try:
        payload = json.loads(row["payload"])
    except (KeyError, TypeError, ValueError, RecursionError):
        return "none"
    sig = payload.pop("_sig", None) if isinstance(payload, dict) else None
    if sig is None:
        return "none"
    try:
        if not isinstance(sig, dict) or not isinstance(sig.get("mac"), str):
            return "BAD"
        v = int(sig.get("v", 1))
        parts = [
            str(row["event_type"]).encode(),
            str(row.get("source") or _DEFAULT_SOURCE).encode(),
            repr(row["timestamp"]).encode(),
            canon(payload),
        ]
        if v >= 2:
            parts.insert(2, str(int(row.get("priority", 1))).encode())
        want = hmac.new(key_bytes, b"|".join(parts), hashlib.sha256).hexdigest()
        return "ok" if hmac.compare_digest(want.encode(), sig["mac"].encode()) else "BAD"
    except (KeyError, TypeError, ValueError, OverflowError, RecursionError, UnicodeEncodeError):
        return "BAD"


def known_kid(kid: Any) -> bool:
    return any(str(kid).startswith(p) for p in _KID_PREFIX_TO_FILE)


def load_key(kid: Any, key_dir: Path | None = None) -> bytes | None:
    """Key bytes for ``kid`` or None (unknown kid, absent/unreadable, loose mode, short key)."""
    name = next((f for p, f in _KID_PREFIX_TO_FILE.items() if str(kid).startswith(p)), None)
    if name is None:
        return None
    path = (key_dir or KEY_DIR) / name
    try:
        if path.stat().st_mode & 0o077:
            return None
        key = bytes.fromhex(path.read_text().strip())
    except (OSError, ValueError):
        return None
    return key if len(key) >= 32 else None
