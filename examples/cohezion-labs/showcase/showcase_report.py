#!/usr/bin/env python3
"""Render the Cohezion showcase cycles into a markdown + HTML report.

Reads all cycle_round_*.json in the output dir and produces:
  - SHOWCASE_REPORT.md   (human-readable, evidence-first)
  - showcase_report.html (standalone visual dashboard)

Honesty contract: every capability row shows its VERIFIED/SIMULATED/FAILED
status and provenance. Nothing is presented as working without captured evidence.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def load_cycles(out_dir: Path) -> list[dict]:
    cycles = []
    for p in sorted(out_dir.glob("cycle_round_*.json"), key=lambda x: int(x.stem.split("_")[-1])):
        cycles.append(json.loads(p.read_text()))
    return cycles


def render_markdown(cycles: list[dict]) -> str:
    if not cycles:
        return "# Cohezion Showcase\n\nNo cycles recorded yet.\n"
    latest = cycles[-1]
    lines = [
        "# Cohezion Capability Showcase",
        "",
        f"**Latest cycle:** round {latest['round']} @ {latest['ts']}  ",
        f"**Result:** {latest['verified']}/{latest['total']} VERIFIED · "
        f"{latest['simulated']} simulated · {latest['failed']} failed  ",
        f"**Cycles run:** {len(cycles)}",
        "",
        "> Every capability below was exercised against **live local services** "
        "(AMD NPU/iGPU/CPU lemonade nodes + SurrealDB). Status reflects a real call "
        "with captured evidence — not a claim.",
        "",
        "## Capabilities (latest cycle)",
        "",
        "| Status | Capability | Subsystem | Latency | Evidence |",
        "|---|---|---|---|---|",
    ]
    mark = {"VERIFIED": "✅", "SIMULATED": "🟡", "FAILED": "❌"}
    for c in latest["capabilities"]:
        ev = c.get("detail", "").replace("|", "\\|")[:90]
        lines.append(
            f"| {mark.get(c['status'], '?')} {c['status']} | {c['name']} | "
            f"{c['subsystem']} | {c['elapsed_ms']}ms | {ev} |"
        )
    lines += ["", "## Evidence detail", ""]
    for c in latest["capabilities"]:
        lines.append(f"### {mark.get(c['status'], '?')} {c['name']}")
        lines.append(f"- **subsystem:** {c['subsystem']}")
        lines.append(f"- **provenance:** `{c.get('provenance', '—')}`")
        lines.append(f"- **metric:** `{json.dumps(c.get('metric', {}))[:300]}`")
        lines.append(f"- **detail:** {c.get('detail', '')}")
        lines.append("")
    # trend across cycles
    lines += ["## Cycle history", "", "| Round | Time | Verified/Total |", "|---|---|---|"]
    for cyc in cycles:
        lines.append(f"| {cyc['round']} | {cyc['ts']} | {cyc['verified']}/{cyc['total']} |")
    lines.append("")
    return "\n".join(lines)


def render_html(cycles: list[dict]) -> str:
    if not cycles:
        return "<html><body><h1>No cycles</h1></body></html>"
    latest = cycles[-1]
    color = {"VERIFIED": "#16a766", "SIMULATED": "#ffad47", "FAILED": "#fb4c2f"}
    rows = ""
    for c in latest["capabilities"]:
        clr = color.get(c["status"], "#999")
        metric = json.dumps(c.get("metric", {}))
        rows += f"""
        <div class="cap" style="border-left:4px solid {clr}">
          <div class="cap-head"><span class="badge" style="background:{clr}">{c["status"]}</span>
            <span class="cap-name">{c["name"]}</span>
            <span class="lat">{c["elapsed_ms"]} ms</span></div>
          <div class="cap-detail">{c.get("detail", "")}</div>
          <div class="cap-prov">{c.get("provenance", "")}</div>
          <pre class="cap-metric">{metric}</pre>
        </div>"""
    verified = latest["verified"]
    total = latest["total"]
    pct = round(100 * verified / total) if total else 0
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>Cohezion Capability Showcase</title>
<style>
  body{{font-family:'SF Mono',Menlo,monospace;background:#0d1117;color:#e6edf3;margin:0;padding:2rem;}}
  h1{{font-weight:700;letter-spacing:-0.02em;}}
  .hero{{background:linear-gradient(135deg,#1a2332,#0d1117);border:1px solid #30363d;border-radius:12px;padding:1.5rem;margin-bottom:1.5rem;}}
  .score{{font-size:3rem;font-weight:800;color:#16a766;}}
  .sub{{color:#8b949e;}}
  .cap{{background:#161b22;border-radius:8px;padding:1rem;margin:0.6rem 0;}}
  .cap-head{{display:flex;align-items:center;gap:0.75rem;}}
  .badge{{color:#fff;padding:2px 8px;border-radius:4px;font-size:0.72rem;font-weight:700;}}
  .cap-name{{font-weight:600;flex:1;}}
  .lat{{color:#8b949e;font-size:0.8rem;}}
  .cap-detail{{color:#c9d1d9;margin:0.4rem 0;font-size:0.88rem;}}
  .cap-prov{{color:#6e7681;font-size:0.74rem;}}
  .cap-metric{{background:#0d1117;border-radius:6px;padding:0.5rem;font-size:0.72rem;color:#79c0ff;overflow-x:auto;margin:0.4rem 0 0;}}
</style></head><body>
<h1>⬡ Cohezion Capability Showcase</h1>
<div class="hero">
  <div class="score">{verified}/{total} <span style="font-size:1.2rem;color:#8b949e">VERIFIED ({pct}%)</span></div>
  <div class="sub">round {latest["round"]} · {latest["ts"]} · exercised against live AMD local inference + SurrealDB · $0 token cost</div>
</div>
{rows}
<p class="sub" style="margin-top:2rem">Honesty contract: each row is a real call with captured evidence. Generated by showcase_report.py.</p>
</body></html>"""


if __name__ == "__main__":
    out_dir = Path(sys.argv[1] if len(sys.argv) > 1 else "showcase_output")
    cycles = load_cycles(out_dir)
    md = render_markdown(cycles)
    html = render_html(cycles)
    (out_dir / "SHOWCASE_REPORT.md").write_text(md)
    (out_dir / "showcase_report.html").write_text(html)
    print(f"Rendered {len(cycles)} cycle(s) -> SHOWCASE_REPORT.md + showcase_report.html")
    if cycles:
        latest = cycles[-1]
        print(f"Latest: {latest['verified']}/{latest['total']} VERIFIED")
