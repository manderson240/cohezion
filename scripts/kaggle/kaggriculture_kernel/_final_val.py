import time, statistics, importlib.util
from kaggle_environments import make

def load(p):
    s=importlib.util.spec_from_file_location("m"+str(abs(hash(p))),p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m.agent

PL=load("main_PLANNER.py"); LV=load("main_LIVESTOCK.py")

def h2h(a,b,seeds,tag):
    aw=bw=t=0; ba=[]; bb=[]; errs=0
    for sd in seeds:
        env=make('kaggriculture',configuration={'seed':sd},debug=True)
        env.run([a,b]); last=env.steps[-1]
        for s in last:
            if s.status not in ("DONE","ACTIVE","INACTIVE"): errs+=1
        ra,rb=last[0].reward,last[1].reward; ba.append(ra); bb.append(rb)
        if ra>rb: aw+=1
        elif rb>ra: bw+=1
        else: t+=1
    print(f"[{tag}] {aw}W-{bw}L-{t}T  meanA={statistics.mean(ba):.0f} meanB={statistics.mean(bb):.0f} errs={errs}")
    return aw,bw,t,errs

seeds=list(range(6))
print("=== HEAD-TO-HEAD (PLANNER is the oracle) ===")
h2h(PL,LV,seeds,"PLANNER(s0) vs LIVESTOCK(s1)")
h2h(LV,PL,seeds,"LIVESTOCK(s0) vs PLANNER(s1)")
h2h(PL,"starter",seeds,"PLANNER(s0) vs starter")
print("=== SELF-PLAY (error check) ===")
h2h(PL,PL,[0,1,2],"PLANNER vs PLANNER")

print("=== PER-TURN TIMING (worst case incl. planning turn) ===")
base=PL; times=[]
def wrapped(obs):
    t=time.time(); r=base(obs); times.append(time.time()-t); return r
env=make('kaggriculture',configuration={'seed':0},debug=True); env.run([wrapped,"starter"])
ts=sorted(times,reverse=True)
print(f"PLANNER per-turn: max={ts[0]*1000:.1f}ms 2nd={ts[1]*1000:.1f}ms 3rd={ts[2]*1000:.1f}ms mean={statistics.mean(times)*1000:.3f}ms n={len(times)} budget=1000ms")
