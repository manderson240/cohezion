import time, statistics, importlib.util
from kaggle_environments import make
def load(p):
    s=importlib.util.spec_from_file_location("m"+str(abs(hash(p))),p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m.agent
V2=load("main_PLANNER_v2.py"); LV=load("main_LIVESTOCK.py")
def h2h(a,b,seeds,tag):
    aw=bw=t=0; ba=[]; bb=[]; errs=0
    for sd in seeds:
        env=make('kaggriculture',configuration={'seed':sd},debug=True); env.run([a,b]); last=env.steps[-1]
        for s in last:
            if s.status not in ("DONE","ACTIVE","INACTIVE"): errs+=1
        ra,rb=last[0].reward,last[1].reward; ba.append(ra); bb.append(rb)
        if ra>rb: aw+=1
        elif rb>ra: bw+=1
        else: t+=1
    print(f"[{tag}] {aw}W-{bw}L-{t}T meanA={statistics.mean(ba):.0f} meanB={statistics.mean(bb):.0f} errs={errs} minA={min(ba):.0f}")
seeds=list(range(12))
h2h(V2,LV,seeds,"v2(s0) vs LIVESTOCK")
h2h(LV,V2,seeds,"LIVESTOCK(s0) vs v2")
h2h(V2,V2,[0,1,2],"v2 self-play (errors)")
times=[]
def w(obs):
    t=time.time(); r=V2(obs); times.append(time.time()-t); return r
env=make('kaggriculture',configuration={'seed':0},debug=True); env.run([w,"starter"])
ts=sorted(times,reverse=True)
print(f"v2 per-turn: max={ts[0]*1000:.1f}ms 2nd={ts[1]*1000:.1f}ms mean={statistics.mean(times)*1000:.3f}ms n={len(times)} (plans ONCE now)")
