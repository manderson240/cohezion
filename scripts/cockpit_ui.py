#!/usr/bin/env python3
"""Cockpit UI — one live pane of glass over the running compound stack.

WIRE, not build: consumes the existing `cohezion.cockpit.daemon_state` reads
(read_lemonade_health / read_graph_counts / read_task_queue — a data layer that
had no UI = Wire-at-Creation gap) and adds the gauntlet/sweep/vault surfaces
this session created. stdlib only; no deps; $0.

Run:  uv run python scripts/cockpit_ui.py          # serves http://localhost:8378
      uv run python scripts/cockpit_ui.py --port N
Then open the URL. The page auto-refreshes every 10s from /api/state.
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


RUN = Path.home() / ".cohezion" / "npu_gauntlet"
SWEEP_LOG = Path.home() / ".cohezion" / "idle_eviction.log"
VAULT_RESEARCH = Path.home() / "vaults" / "cohezion-vault" / "model-research"
LEDGER = Path.home() / ".cohezion" / "ollama_cloud_usage.jsonl"
LEMONADE = "http://localhost:13305"


# ── state collectors (each fail-soft: a dead source shows as empty, never 500s) ──


def _fleet() -> dict:
    try:
        with urllib.request.urlopen(f"{LEMONADE}/api/v1/health", timeout=5) as r:  # noqa: S310
            d = json.load(r)
        loaded = d.get("all_models_loaded", [])
        avail = 0.0
        try:  # noqa: SIM105 — fail-soft telemetry read; try/except reads clearer than suppress
            avail = round(
                int(Path("/proc/meminfo").read_text().split("MemAvailable:")[1].split()[0])
                / 1048576,
                1,
            )
        except Exception:
            pass
        return {
            "ok": True,
            "version": d.get("version"),
            "ram_gb": avail,
            "models": [
                {"name": m["model_name"], "device": m["device"], "status": m.get("status", "")}
                for m in loaded
            ],
        }
    except Exception:
        return {"ok": False, "models": [], "ram_gb": 0.0}


def _gauntlet() -> dict:
    rounds = RUN / "rounds.jsonl"
    hb = RUN / "heartbeat"
    out: dict = {"alive": False, "lap": None, "leaderboard": []}
    try:
        if hb.exists():
            age_min = (time.time() - hb.stat().st_mtime) / 60
            out["alive"] = age_min < 30
            out["heartbeat_age_min"] = round(age_min, 1)
        rows = [json.loads(x) for x in rounds.read_text().splitlines() if x.strip()][-60:]
        if rows:
            out["lap"] = rows[-1].get("lap")
            agg: dict = {}
            for r in rows:
                a = agg.setdefault(r["model"], {"n": 0, "q": 0.0, "tps": 0.0})
                a["n"] += 1
                a["q"] += r.get("mean_quality", 0)
                a["tps"] += r.get("mean_tps", 0)
            out["leaderboard"] = sorted(
                (
                    {
                        "model": m,
                        "acc": round(a["q"] / a["n"], 3),
                        "tps": round(a["tps"] / a["n"], 1),
                        "rounds": a["n"],
                    }
                    for m, a in agg.items()
                ),
                key=lambda x: -x["acc"],
            )
    except Exception:
        pass
    return out


def _sweep() -> dict:
    try:
        lines = [x for x in SWEEP_LOG.read_text().splitlines() if "evicted" in x]
        return {"evictions_total": len(lines), "last": lines[-1][:120] if lines else None}
    except Exception:
        return {"evictions_total": 0, "last": None}


def _cockpit() -> dict:
    """Wire the existing daemon_state reads (fail-soft if unavailable)."""
    out: dict = {}
    try:
        from cohezion.cockpit import daemon_state as ds

        out["tasks"] = ds.read_task_queue()
        out["graph"] = ds.read_graph_counts()
    except Exception:
        out["tasks"] = {"total": 0, "done": 0}
        out["graph"] = {}
    return out


def _research() -> dict:
    try:
        files = sorted(VAULT_RESEARCH.glob("2026-07-17-*.md"))
        tally: dict = {}
        for f in files:
            m = re.search(r"verdict-([a-z-]+)", f.read_text()[:400])
            v = m.group(1) if m else "other"
            tally[v] = tally.get(v, 0) + 1
        return {"today_count": len(files), "by_verdict": tally}
    except Exception:
        return {"today_count": 0, "by_verdict": {}}


def _cloud_spend() -> dict:
    try:
        rows = [json.loads(x) for x in LEDGER.read_text().splitlines() if x.strip()]
        return {"calls": len(rows), "resp_chars": sum(r.get("response_chars", 0) for r in rows)}
    except Exception:
        return {"calls": 0, "resp_chars": 0}


def collect_state() -> dict:
    return {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "fleet": _fleet(),
        "gauntlet": _gauntlet(),
        "sweep": _sweep(),
        "cockpit": _cockpit(),
        "research": _research(),
        "cloud": _cloud_spend(),
    }


# ── page ─────────────────────────────────────────────────────────────────────

PAGE = """<!doctype html><html><head><meta charset=utf-8>
<title>Cohezion Cockpit</title>
<style>
 body{background:#0b0e14;color:#c9d1d9;font:13px/1.5 ui-monospace,monospace;margin:0;padding:16px}
 h1{font-size:16px;margin:0 0 4px;color:#58a6ff} .ts{color:#6e7681;font-size:11px;margin-bottom:14px}
 .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px}
 .card{background:#11151c;border:1px solid #21262d;border-radius:8px;padding:12px}
 .card h2{font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:#8b949e;margin:0 0 8px}
 table{width:100%;border-collapse:collapse} td,th{text-align:left;padding:2px 6px;border-bottom:1px solid #1b212b}
 th{color:#6e7681;font-weight:400} .g{color:#3fb950} .y{color:#d29922} .r{color:#f85149} .dim{color:#6e7681}
 .big{font-size:20px;font-weight:600} .row{display:flex;justify-content:space-between}
 .pill{display:inline-block;padding:1px 6px;border-radius:10px;background:#1b212b;margin:1px}
</style></head><body>
<h1>◆ Cohezion Cockpit</h1><div class=ts id=ts>loading…</div>
<div class=grid id=grid></div>
<script>
const q=(s)=>document.querySelector(s);
function ramClass(g){return g<8?'r':g<16?'y':'g'}
function card(t,h){return `<div class=card><h2>${t}</h2>${h}</div>`}
async function tick(){
 let s; try{s=await (await fetch('/api/state')).json()}catch(e){q('#ts').textContent='fetch failed';return}
 q('#ts').textContent=s.ts;
 const f=s.fleet, g=s.gauntlet, c=s.cockpit;
 let cards='';
 // fleet
 let fm=(f.models||[]).map(m=>`<tr><td>${m.name}</td><td class=dim>${m.device}</td><td>${m.status}</td></tr>`).join('');
 cards+=card('Fleet · lemonade '+(f.version||'?'),
   `<div class=row><span>RAM available</span><span class="big ${ramClass(f.ram_gb)}">${f.ram_gb} GB</span></div>
    <table><tr><th>model</th><th>dev</th><th>state</th></tr>${fm}</table>`);
 // gauntlet
 let lb=(g.leaderboard||[]).map(m=>`<tr><td>${m.model}</td><td class=g>${m.acc}</td><td>${m.tps}</td><td class=dim>${m.rounds}</td></tr>`).join('');
 cards+=card('NPU Gauntlet '+(g.alive?'<span class=g>●live</span>':'<span class=r>●stale</span>')+' lap '+(g.lap??'?'),
   `<table><tr><th>model</th><th>acc</th><th>tps</th><th>n</th></tr>${lb}</table>`);
 // ops
 cards+=card('Ops',
   `<div class=row><span>Sweep evictions</span><span class=big>${s.sweep.evictions_total}</span></div>
    <div class=dim>${s.sweep.last||'—'}</div>
    <div class=row style=margin-top:8px><span>Tasks</span><span>${(c.tasks.done||0)}/${(c.tasks.total||0)} done</span></div>
    <div class=row><span>Cloud calls</span><span>${s.cloud.calls} <span class=dim>(${s.cloud.resp_chars} ch)</span></span></div>`);
 // knowledge
 let gv=Object.entries(c.graph||{}).map(([k,v])=>`<span class=pill>${k}: ${v}</span>`).join('')||'<span class=dim>—</span>';
 let rv=Object.entries(s.research.by_verdict||{}).map(([k,v])=>`<span class=pill>${k}: ${v}</span>`).join('');
 cards+=card('Knowledge',
   `<div class=row><span>Research verdicts today</span><span class=big>${s.research.today_count}</span></div>
    <div>${rv}</div><div style=margin-top:8px class=dim>graph tables</div><div>${gv}</div>`);
 q('#grid').innerHTML=cards;
}
tick(); setInterval(tick,10000);
</script></body></html>"""


class H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        if self.path.startswith("/api/state"):
            body = json.dumps(collect_state()).encode()
            ctype = "application/json"
        else:
            body = PAGE.encode()
            ctype = "text/html; charset=utf-8"
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--port", type=int, default=8378)
    args = p.parse_args()
    srv = ThreadingHTTPServer(("127.0.0.1", args.port), H)
    print(f"Cohezion Cockpit → http://localhost:{args.port}  (Ctrl-C to stop)")
    srv.serve_forever()


if __name__ == "__main__":
    main()
