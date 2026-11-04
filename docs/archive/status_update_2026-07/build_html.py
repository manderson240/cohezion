#!/usr/bin/env python3
"""Assemble the multimodal status HTML from locally-generated content + media assets.

All inputs were produced by LOCAL inference / local tools ($0):
  - content.json  : narrative + 2-host dialogue   (Gemma-4-26B-A4B, thinking-off, :13305)
  - assets/dialogue.mp3 : expressive 2-voice audio (espeak-ng + ffmpeg)
  - assets/status_video.mp4 : narrated slide video (matplotlib + ffmpeg)
Charts (Chart.js) and the diagram (Mermaid) render client-side from CDNs.
"""

from __future__ import annotations

import html
import json
import pathlib

ROOT = pathlib.Path(__file__).parent
content = json.loads((ROOT / "content.json").read_text())
narrative = content["narrative"]
dialogue_raw = content["dialogue"]


def narrative_html(text: str) -> str:
    paras = [p.strip() for p in text.split("\n") if p.strip()]
    return "\n".join(f"<p>{html.escape(p)}</p>" for p in paras)


def dialogue_html(text: str) -> str:
    rows = []
    for ln in text.splitlines():
        if ":" not in ln:
            continue
        spk, _, said = ln.partition(":")
        spk = spk.strip().upper()
        if spk not in ("ARIA", "KAI"):
            continue
        side = "left" if spk == "ARIA" else "right"
        rows.append(
            f'<div class="bubble {side}"><span class="who">{spk}</span>{html.escape(said.strip())}</div>'
        )
    return "\n".join(rows)


HTML = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Cohezion — Local-First AI Status Update</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>
<style>
  :root{{--bg:#0b1020;--panel:#121a2e;--fg:#e6edf3;--muted:#9aa4b2;--ac:#5eead4;--ac2:#a78bfa;--ac3:#f59e0b}}
  *{{box-sizing:border-box}}
  body{{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}}
  .wrap{{max-width:1000px;margin:0 auto;padding:32px 20px 64px}}
  header{{text-align:center;padding:36px 0 12px}}
  header h1{{font-size:54px;margin:0;color:var(--ac);letter-spacing:2px}}
  header .sub{{font-size:20px;color:var(--fg);margin-top:4px}}
  header .meta{{color:var(--ac2);margin-top:10px;font-size:14px}}
  .pill{{display:inline-block;background:var(--panel);border:1px solid #25304a;border-radius:999px;
        padding:4px 12px;margin:4px;font-size:13px;color:var(--muted)}}
  section{{background:var(--panel);border:1px solid #1e2740;border-radius:14px;padding:22px 24px;margin:22px 0}}
  h2{{color:var(--ac);font-size:22px;margin:0 0 14px;border-left:3px solid var(--ac);padding-left:10px}}
  p{{margin:0 0 12px}}
  video,audio{{width:100%;border-radius:10px;outline:none}}
  .grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px}}
  @media(max-width:720px){{.grid{{grid-template-columns:1fr}}}}
  canvas{{background:transparent}}
  .kpi{{display:flex;flex-wrap:wrap;gap:14px;justify-content:center}}
  .kpi div{{background:#0e1626;border:1px solid #25304a;border-radius:12px;padding:14px 18px;text-align:center;min-width:150px}}
  .kpi b{{display:block;font-size:30px;color:var(--ac3)}}
  .kpi span{{font-size:13px;color:var(--muted)}}
  .mermaid{{background:#0e1626;border-radius:10px;padding:16px;text-align:center}}
  .chat{{display:flex;flex-direction:column;gap:10px}}
  .bubble{{max-width:78%;padding:10px 14px;border-radius:14px;position:relative}}
  .bubble .who{{display:block;font-size:11px;letter-spacing:1px;color:var(--muted);margin-bottom:3px}}
  .bubble.left{{align-self:flex-start;background:#13233a;border:1px solid #244}}
  .bubble.right{{align-self:flex-end;background:#231a3a;border:1px solid #423}}
  footer{{text-align:center;color:var(--muted);font-size:13px;margin-top:30px}}
  .note{{color:var(--muted);font-size:13px}}
</style></head>
<body><div class="wrap">
<header>
  <h1>COHEZION</h1>
  <div class="sub">Local-First AI Engineering — Status Update</div>
  <div class="meta">AMD Strix Halo · Ryzen AI MAX+ 395 · gfx1151 iGPU + XDNA2 NPU · 2026-06-07</div>
  <div style="margin-top:10px">
    <span class="pill">🧠 narrative · dialogue → Gemma-4-26B (local)</span>
    <span class="pill">🔊 audio → espeak-ng + ffmpeg</span>
    <span class="pill">🎬 video → matplotlib + ffmpeg</span>
    <span class="pill">📊 charts → Chart.js</span>
    <span class="pill">$0 — generated entirely on local silicon</span>
  </div>
</header>

<section>
  <h2>▶ Status video (narrated)</h2>
  <video controls preload="metadata" poster="assets/frames/01_title.png">
    <source src="assets/status_video.mp4" type="video/mp4">
  </video>
  <p class="note">~2 min · slides rendered from real metrics, narration synthesized locally.</p>
</section>

<section>
  <h2>Executive summary</h2>
  {narrative_html(narrative)}
</section>

<section>
  <h2>By the numbers</h2>
  <div class="kpi">
    <div><b>47</b><span>packages wired · 0 orphans</span></div>
    <div><b>7</b><span>research rounds · all verified</span></div>
    <div><b>$0.00</b><span>per 10k local loop (vs $0.18)</span></div>
    <div><b>29%</b><span>of Claude plan budget</span></div>
    <div><b>0.84</b><span>Kaggle Nemotron banked</span></div>
  </div>
</section>

<section>
  <h2>Fleet model ladder &amp; cost</h2>
  <div class="grid">
    <div><canvas id="ladder"></canvas></div>
    <div><canvas id="cost"></canvas></div>
  </div>
  <p class="note">The new 6.5&nbsp;GB Gemma-4-12B-QAT fills the memory-pressure gap between E4B (4.6&nbsp;GB)
  and the 26B (15.7&nbsp;GB): when the 26B can't fit, code/reasoning stay on the fast local lane instead of
  slow CPU or paid cloud.</p>
</section>

<section>
  <h2>Routing architecture</h2>
  <div class="mermaid">
flowchart LR
  R["request"] --> C{{"classify + capability route"}}
  C -->|cheap/short| NPU["NPU · llama3.2-1B<br/>$0 · 42 t/s"]
  C -->|structured/code| IG["iGPU · Gemma E4B / 12B-QAT / 26B<br/>$0"]
  C -->|deep reasoning| CPU["CPU · 31B / 70B<br/>$0"]
  IG -->|OOM-deferred 26B| MID["12B-QAT 6.5GB<br/>fast local fallback"]
  C -.->|quality gate fails| CL["cloud<br/>last resort · $$"]
  classDef z fill:#13233a,stroke:#244,color:#e6edf3;
  classDef c fill:#231a3a,stroke:#423,color:#e6edf3;
  class NPU,IG,CPU,MID z; class CL c;
  </div>
</section>

<section>
  <h2>🔊 Two-host briefing (expressive dialogue)</h2>
  <audio controls preload="metadata"><source src="assets/dialogue.mp3" type="audio/mpeg"></audio>
  <p class="note">Script written by the local 26B model; voiced locally (ARIA &amp; KAI).</p>
  <div class="chat">
  {dialogue_html(dialogue_raw)}
  </div>
</section>

<footer>
  Generated end-to-end with local inference on AMD Strix Halo — no cloud tokens spent.<br>
  Cohezion · compound engineering · observable · non-destructive · local-first.
</footer>
</div>
<script>
const gridC="#1e2740", fg="#e6edf3";
Chart.defaults.color=fg; Chart.defaults.borderColor=gridC;
new Chart(document.getElementById('ladder'),{{type:'bar',
  data:{{labels:['E2B (NPU)','E4B (iGPU)','12B-QAT (NEW)','26B-A4B'],
    datasets:[{{label:'on-disk size (GB)',data:[2.9,4.6,6.5,15.7],
      backgroundColor:['#5eead4','#5eead4','#f59e0b','#a78bfa']}}]}},
  options:{{plugins:{{legend:{{display:false}},title:{{display:true,text:'Fleet model footprint (GB, measured)'}}}},
    scales:{{y:{{grid:{{color:gridC}}}},x:{{grid:{{display:false}}}}}}}}}});
new Chart(document.getElementById('cost'),{{type:'bar',
  data:{{labels:['Local fleet','Cloud (Sonnet)'],
    datasets:[{{label:'$ per 10k-token compound loop',data:[0.0,0.18],
      backgroundColor:['#5eead4','#f87171']}}]}},
  options:{{plugins:{{legend:{{display:false}},title:{{display:true,text:'Cost per 10k-token loop (USD)'}}}},
    scales:{{y:{{grid:{{color:gridC}},ticks:{{callback:v=>'$'+v.toFixed(2)}}}},x:{{grid:{{display:false}}}}}}}}}});
mermaid.initialize({{startOnLoad:true,theme:'dark',themeVariables:{{background:'#0e1626'}}}});
</script>
</body></html>"""

(ROOT / "index.html").write_text(HTML, encoding="utf-8")
print(f"wrote {ROOT / 'index.html'} ({len(HTML)} bytes)")
