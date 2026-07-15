"""CLI for the Session Control Plane — the interface the global hooks call.

    python -m cohezion.sessions register <sid> <label> --pid <pid> --mode turn
    python -m cohezion.sessions heartbeat <sid>
    python -m cohezion.sessions inbox <sid> [--cap 20]
    python -m cohezion.sessions send <to-sid|all> <body> [--from <sid>] [--kind MSG|REPLY]
    python -m cohezion.sessions list
"""

from __future__ import annotations

import argparse

from cohezion.sessions.session_bus import MessageKind, SessionBus, SessionRegistry


def main() -> int:
    ap = argparse.ArgumentParser(prog="cohezion.sessions")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("register")
    p.add_argument("sid")
    p.add_argument("label")
    p.add_argument("--pid", type=int, required=True)
    p.add_argument("--mode", default="turn")

    p = sub.add_parser("heartbeat")
    p.add_argument("sid")

    p = sub.add_parser("inbox")
    p.add_argument("sid")
    p.add_argument("--cap", type=int, default=20)

    p = sub.add_parser("send")
    p.add_argument("to")
    p.add_argument("body")
    p.add_argument("--from", dest="from_sid", default="operator")
    p.add_argument("--kind", choices=["MSG", "REPLY"], default="MSG")

    sub.add_parser("list")

    a = ap.parse_args()
    bus, reg = SessionBus(), SessionRegistry()

    if a.cmd == "register":
        reg.register(a.sid, a.label, pid=a.pid, mode=a.mode)
    elif a.cmd == "heartbeat":
        reg.heartbeat(a.sid)
    elif a.cmd == "inbox":
        for m in bus.fetch(a.sid, cap_msgs=a.cap):
            frm = m.get("from_session") or "operator"
            print(f"- [{m.get('created_at', '')}] from {frm}: {m.get('body', '')}")
    elif a.cmd == "send":
        bus.post(a.to, a.body, kind=MessageKind[a.kind], from_session=a.from_sid)
        print(f"sent {a.kind} to {a.to}")
    elif a.cmd == "list":
        for r in reg.list_active():
            print(f"{r.get('session_id')}  pid={r.get('pid')}  mode={r.get('mode')}  {r.get('label')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
