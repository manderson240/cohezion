"""Reply relay — forwards session REPLY messages to the Telegram operator exactly once (SCP4).

Single-instance via flock; claim-before-send so a crashed send is retried by the next
run but a sent reply is never double-delivered.

    .venv/bin/python scripts/sessions/reply_relay.py [--once]
"""

from __future__ import annotations

import argparse
import asyncio
import fcntl
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from cohezion.sessions.session_bus import SessionBus, _sql  # noqa: E402

_LOCK = Path.home() / ".cohezion" / "reply_relay.lock"
_RELAY_SID = "relay"


def _pending_replies() -> list[dict]:
    return _sql(
        "SELECT * FROM session_bus WHERE kind = 'REPLY' AND to_session = 'operator' "
        "AND array::len(claimed_by) = 0 ORDER BY created_at ASC LIMIT 20;"
    )


def relay_once(bus: SessionBus) -> int:
    from cohezion.compound.telegram_hub import TelegramHub

    hub = TelegramHub()
    sent = 0
    for row in _pending_replies():
        rid = str(row.get("id"))
        # claim BEFORE send (exactly-once): if another relay claimed it first, skip.
        if not bus.claim(_RELAY_SID, rid):
            continue
        body = f"[{row.get('from_session', '?')}] {row.get('body', '')}"
        asyncio.run(hub.notify(body))
        sent += 1
    return sent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--interval", type=int, default=30)
    a = ap.parse_args()

    _LOCK.parent.mkdir(parents=True, exist_ok=True)
    lock = open(_LOCK, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print("relay already running", file=sys.stderr)
        return 0

    bus = SessionBus()
    while True:
        n = relay_once(bus)
        if n:
            print(f"relayed {n} reply(ies)")
        if a.once:
            return 0
        time.sleep(a.interval)


if __name__ == "__main__":
    raise SystemExit(main())
