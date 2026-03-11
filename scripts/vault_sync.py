#!/usr/bin/env python3
"""SurrealDB Sync Daemon — keeps SurrealDB in sync with vault file changes."""

import hashlib, json, re, signal, sys, time, urllib.request, base64
from datetime import datetime
from pathlib import Path

VAULT_ROOT = Path(__file__).resolve().parent.parent
CHECKPOINT = VAULT_ROOT / ".vault-journal" / "checkpoint.json"
SURREAL_URL = "http://localhost:8001/sql"
HDRS = {"Content-Type": "text/plain", "surreal-ns": "cohezion", "surreal-db": "vault",
        "Authorization": "Basic " + base64.b64encode(b"root:root").decode()}
POLL = 30
CONTENT_DIRS = ["cortex","sensory","memory","genome","prefrontal","laboratory","cerebellum",
    "benchmarks","motor","hippocampus","thalamus","missions","retrospectives","dreaming",
    "songlines","subconscious","metabolism","visual-cortex","Agents","docs","teleport",
    "assessments","canvas","meta","skills_index"]
D2A = {"cortex":"knower","sensory":"knower","memory":"knower","genome":"knower",
    "prefrontal":"thinker","laboratory":"thinker","cerebellum":"thinker","benchmarks":"thinker",
    "motor":"doer","hippocampus":"doer","thalamus":"doer","missions":"doer",
    "retrospectives":"doer","Agents":"doer","docs":"doer","teleport":"doer",
    "assessments":"thinker","canvas":"connective","meta":"connective","skills_index":"knower",
    "dreaming":"connective","songlines":"connective",
    "subconscious":"connective","metabolism":"connective","visual-cortex":"connective"}
WL = re.compile(r"\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]")
alive = True

def stop(s,f):
    global alive; alive = False; print("\nStopping...", file=sys.stderr)
signal.signal(signal.SIGINT, stop); signal.signal(signal.SIGTERM, stop)

def q(sql):
    req = urllib.request.Request(SURREAL_URL, data=sql.encode("utf-8"), headers=HDRS, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r: return json.loads(r.read())
    except Exception as e:
        print(f"  HTTP error: {e}", file=sys.stderr)
        return []

def gr(data, i=0):
    if not data or i>=len(data): return []
    e=data[i]; return e.get("result",[]) if e.get("status")=="OK" else []

def load_ckpt():
    if CHECKPOINT.exists():
        try: return json.loads(CHECKPOINT.read_text())
        except: pass
    return {}

def save_ckpt(s):
    CHECKPOINT.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT.write_text(json.dumps(s))

def parse_fm(content):
    lines=content.split("\n")
    if not lines or lines[0].strip()!="---": return {}
    fm=[]
    for l in lines[1:]:
        if l.strip()=="---": break
        fm.append(l)
    r={}
    for l in fm:
        if ":" in l and not l.startswith(" ") and not l.startswith("\t"):
            k,_,v=l.partition(":"); k=k.strip(); v=v.strip().strip('"').strip("'")
            if v.startswith("[") and v.endswith("]"):
                v=[x.strip().strip('"').strip("'") for x in v[1:-1].split(",") if x.strip()]
            r[k]=v
    return r

def pid(rp):
    return "neuron:"+rp.replace("/","_").replace("-","_").replace(".","_").replace(" ","_")

def changed(ckpt, full=False):
    out=[]
    for d in CONTENT_DIRS:
        dp=VAULT_ROOT/d
        if not dp.is_dir(): continue
        for f in dp.rglob("*.md"):
            if f.name.startswith("_"): continue
            rp=str(f.relative_to(VAULT_ROOT)); mt=f.stat().st_mtime
            if full or ckpt.get(rp,0)<mt: out.append(f)
    return out

def sync_note(f, ckpt):
    rp=str(f.relative_to(VAULT_ROOT))
    try: content=f.read_text(encoding="utf-8")
    except: return False
    fm=parse_fm(content); links=list(set(WL.findall(content)))
    h=hashlib.sha256(content.encode()).hexdigest()[:16]
    wc=len(content.split()); td=rp.split("/")[0]; asp=D2A.get(td,"unknown")
    title=fm.get("title",f.stem); tags=fm.get("tags",[])
    if isinstance(tags,str): tags=[tags]
    tl=", ".join(f'"{t}"' for t in tags)

    # Find existing neuron by path
    ex=gr(q(f'SELECT id, activation, content_hash FROM neuron WHERE path = {json.dumps(rp, ensure_ascii=False)} LIMIT 1;'))
    if ex:
        nid=str(ex[0]["id"]); ca=ex[0].get("activation"); oh=ex[0].get("content_hash")
        if oh==h: ckpt[rp]=f.stat().st_mtime; return True  # unchanged
        na=min(1.0,(ca or 0.5)+0.05)
    else:
        nid=pid(rp); na=0.6

    sql=f'''UPSERT {nid} SET path={json.dumps(rp, ensure_ascii=False)}, title={json.dumps(title, ensure_ascii=False)}, aspect="{asp}",
        activation={na:.3f}, stage="growing", last_fired=time::now(), cluster_id={json.dumps(td, ensure_ascii=False)},
        synapse_out={len(links)}, word_count={wc}, tags=[{tl}], content_hash="{h}", modified=time::now();'''
    r=q(sql)
    if not r or r[0].get("status")!="OK":
        err=r[0].get("result","?") if r else "no resp"
        print(f"  FAIL {rp}: {str(err)[:120]}", file=sys.stderr)
        if not r: print(f"    SQL: {sql[:200]}", file=sys.stderr)
        return False

    # Akashic log
    q(f'CREATE neuron_history CONTENT {{ neuron: {nid}, event_type: "edited", timestamp: time::now(), detail: "sync {len(links)} links {wc}w" }};')

    # Re-sync outbound synapses
    q(f'DELETE synapse WHERE in = {nid};')
    for lt in links:
        tr=gr(q(f'SELECT id FROM neuron WHERE path CONTAINS {json.dumps(lt, ensure_ascii=False)} LIMIT 1;'))
        if tr:
            q(f'CREATE synapse CONTENT {{ in: {nid}, out: {tr[0]["id"]}, weight: 1.0, link_type: "explicit", created: time::now() }};')

    # Update inbound count
    ib=gr(q(f'SELECT count() FROM synapse WHERE out = {nid} GROUP ALL;'))
    ic=ib[0]["count"] if ib else 0
    q(f'UPDATE {nid} SET synapse_in = {ic};')

    ckpt[rp]=f.stat().st_mtime; return True

def cycle(ckpt, full=False):
    ch=changed(ckpt,full)
    if not ch: return 0
    s=sum(1 for f in ch if sync_note(f,ckpt))
    if s>0: save_ckpt(ckpt)
    print(f"  Synced {s}/{len(ch)}", file=sys.stderr); return s

def main():
    watch="--watch" in sys.argv; full="--full-import" in sys.argv
    if not q("INFO FOR DB;"): print("ERROR: SurrealDB down", file=sys.stderr); sys.exit(1)
    ckpt=load_ckpt() if not full else {}
    print(f"Vault Sync — {len(ckpt)} in checkpoint", file=sys.stderr)
    s=cycle(ckpt,full); print(f"Initial: {s} notes", file=sys.stderr)
    if watch:
        print(f"Watching every {POLL}s...", file=sys.stderr)
        while alive:
            time.sleep(POLL)
            if not alive: break
            s=cycle(ckpt)
            if s>0: print(f"[{datetime.now():%H:%M:%S}] {s} notes", file=sys.stderr)
    print(f"Done. {len(ckpt)} files.", file=sys.stderr)

if __name__=="__main__": main()
