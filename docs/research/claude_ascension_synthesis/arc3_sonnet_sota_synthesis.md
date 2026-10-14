I wrote the explorer and tested it on a toy maze. It solved 20/20 seeds at both scales, but the maze is far simpler than ARC-AGI-3 and I haven't run it on the real environment, so I can't promise any leaderboard movement.

The code is at `/tmp/claude-1000/go_explore/affordance_explorer.py`, with a test in `toy_test.py` alongside it. `/tmp` is ephemeral, so the full source is below too.

The toy maze has a key, a door, a goal, and a HUD counter that changes every step. I ran it at 1× and 2× scale, the second with a 2×2 agent that moves 2 cells per step:

| | solved | median steps |
|---|---|---|
| Explorer, 1× | 20/20 | 170 |
| Explorer, 2× | 20/20 | 163 |
| Random walk | 19/20 | 938 |

The first version solved only 15/20 seeds. Picking up the key happens under the agent's footprint, so the frame diff never saw the world change and the "door is solid" memory went stale. The fix is the `hidden_event` rule explained further down.

## Check these before spending a submission

- **The API may not match the one in your prompt.** I coded to `game.step(a) -> grid | (grid, …, done)` as you described. As I recall, the real ARC-AGI-3 uses 64×64 frames with 16 colours, `ACTION1`–`ACTION5` plus a coordinate-click `ACTION6`, and `RESET`. I haven't checked this against the docs. Adapt `_unpack` and the action map accordingly. Click-driven games have no position-space BFS and need a different target generator.
- **Scoring probably rewards action efficiency, not just solving.** Our own memory notes say so (`arc-agi3-scoring-efficiency-pivot`), though I haven't re-read them. Macro-actions help only if they don't add steps, and the cycle penalty and early-abort rules exist for that reason.
- **The scores don't line up.** "0.25" and "Rank 1 = 19.45%" are in different units, so I can't tell the real gap to the top from your brief.

## Mathematical formulation

**1. State hash.** Frame `s` is a set of `(i, v)` cell/colour pairs, and `M` is the masked set (HUD rows, timers).

- `Z(i,v) = SM64(seed ⊕ (i≪8 | v))` and `h(s) = ⊕_{(i,v)∈s, i∉M} Z(i,v)`.
- Updating after a step costs `O(|Δ|)`: `h' = h ⊕ ⊕_{c∈Δ}[Z(c,old) ⊕ Z(c,new)]`.
- Collision probability for `n` distinct states is about `n²/2⁶⁵`.
- Novelty is `h ∉ Seen`, a set lookup.
- Masking matters. Without it, a step counter makes every state "novel" and `Seen` never fills.

**2. Objective.** Treat the game as a semi-MDP whose options are macros `g = (node, a)`.

- Maximise discovery per action: `max_π E[Σ_k 1[h_k ∉ Seen] + R_goal] / E[Σ_k |m_k|]`, where `|m_k|` is the macro length.
- Macro choice: `π(g|s) = softmax(U(g)/T_t)`.
- `U(g) = β·(1+n(p))^(-1/2) + ν·1[p+δ(a) unvisited] − c·(d_BFS(s,p)+1) − λ·C(g)` for frontier targets.
- `U(obj) = κ/(1+touch(obj)) − c·d_BFS − λ·C(obj)` for affordance targets.
- `n(p)` is the visit count at node `p`, and `δ(a)` is the learned displacement for action `a`.
- Cycle penalty: `C(g) = Σ_j ρ^{age_j}·1[g_j = g]`, over the last 32 chosen targets.

**3. Temperature (annealing plus re-heating).**

`T_t = [T_min + (T₀−T_min)·e^{−t/τ}] · [1 + η(4·P_cyc + min(stall/S, 4))]`

- `stall` is the number of steps since the last new hash.
- `P_cyc` is the fraction of the last 16 states visited at least 3 times.
- Exploration cools on a schedule. It re-heats when the agent loops or stops finding new states.

**4. Learned transition model.** Positions are the agent's bounding-box top-left, so the BFS works for any stride and footprint.

- **Agent colour:** the colour whose same-size mask translates along the action direction, found by centroid shift.
- **Displacement:** `δ(a)` is the modal observed shift per action.
- **Blocked edges:** `(p,a)` is blocked if the agent didn't move.
- **Solid colours:** a colour is solid if a move into it had no effect at all and the colour was never walked on. Unknown colours are treated as passable, which is optimism under uncertainty and drives exploration.
- **BFS:** it runs over this model. The chosen macro is the path to the target, executed in one decision and capped at 32 steps.

**5. Go-Explore archive.** `Archive[h] = (shortest action prefix, expansions)`. When stalled past 200 steps, it picks the least-expanded entry, sends `RESET`, and replays the prefix.

## Failure modes and the guard for each

| Failure | Guard |
|---|---|
| Walking into walls forever | Blocked edges go into the BFS, and a failed move aborts the macro and replans. |
| A→B→A oscillation | The cycle penalty `C(g)`, plus re-heating via `P_cyc`. |
| HUD/timer pixels make every state look new | `masked_rows` in the hash and in the event detector. |
| Door blocked earlier opens after a key pickup | An event clears the blocked edges, tried set and solid votes. Events come from changes outside the agent footprint, or from stepping onto a never-seen colour (`hidden_event`). |
| Big frame change on a level transition | If more than 40% of cells change, per-level memory resets. Agent colour, displacement and walkable colours are kept. |
| Dead end, nothing left to explore | Fall back to `ACTION`, then archive replay after `RESET`, then a random step. |
| Stale macro after the world changes | Every primitive step checks the predicted outcome and aborts on mismatch. |
| Hash collisions | 64-bit Zobrist makes them negligible at this scale. |

## Known limits

- `RESET` may cost real progress in ARC-AGI-3. I'd tune `reset_after` upward.
- Target scoring scans every reachable node, so it's roughly 20 ms per decision at 64×64. That's fine for a few thousand steps.
- Object targets use a simple size filter (`max_obj_area`). Real games will need a better notion of "interesting object", for example colours that appear or disappear on interaction.

## Full source

```python
"""Go-Explore Affordance Explorer for grid games (pure standard library)."""
from __future__ import annotations

import math
import random
from collections import Counter, deque

M64 = (1 << 64) - 1
DIRS = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}
ACTION, RESET = 5, 6


def splitmix64(x: int) -> int:
    x = (x + 0x9E3779B97F4A7C15) & M64
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & M64
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & M64
    return x ^ (x >> 31)


class Zobrist:
    """h(s) = XOR_{(i,v) in s, i not masked} Z(i,v), Z(i,v) = SM64(seed ^ (i<<8 | v))."""

    def __init__(self, seed: int = 0xC0DE, masked_rows=()):
        self.seed, self.masked_rows, self._k = seed, frozenset(masked_rows), {}

    def key(self, i: int, v: int) -> int:
        k = self._k.get((i, v))
        if k is None:
            k = self._k[(i, v)] = splitmix64(self.seed ^ (i << 8 | (v & 0xFF)))
        return k

    def full(self, grid) -> int:
        h, W = 0, len(grid[0])
        for r, row in enumerate(grid):
            if r in self.masked_rows:
                continue
            for c, v in enumerate(row):
                h ^= self.key(r * W + c, v)
        return h

    def diff(self, prev, prev_h: int, grid):
        h, W, changed = prev_h, len(grid[0]), []
        for r, (a, b) in enumerate(zip(prev, grid)):
            if r in self.masked_rows or a == b:
                continue
            for c, (o, n) in enumerate(zip(a, b)):
                if o != n:
                    h ^= self.key(r * W + c, o) ^ self.key(r * W + c, n)
                    changed.append((r, c, o, n))
        return h, changed


def _unpack(out):
    done, grid = False, out
    if isinstance(out, tuple):
        grid = out[0]
        done = any(x is True for x in out[1:])
    elif hasattr(out, "frame") or hasattr(out, "grid"):
        grid = out.frame if hasattr(out, "frame") else out.grid
        done = bool(getattr(out, "done", False))
    if grid and isinstance(grid[0][0], (list, tuple)):  # [layers][H][W] -> last layer
        grid = grid[-1]
    return [list(r) for r in grid], done


class AffordanceExplorer:
    def __init__(self, seed=0, beta=1.0, unknown_bonus=1.0, kappa=3.0, step_cost=0.05, lam=1.5,
                 rho=0.8, T0=1.0, Tmin=0.12, tau=500.0, eta=0.6, stall_scale=20.0,
                 reset_after=200, max_macro=32, max_obj_area=40, masked_rows=(), max_nodes=6000):
        self.rng, self.z = random.Random(seed), Zobrist(masked_rows=masked_rows)
        self.p = dict(beta=beta, ub=unknown_bonus, kappa=kappa, c=step_cost, lam=lam, rho=rho,
                      T0=T0, Tmin=Tmin, tau=tau, eta=eta, S=stall_scale, reset_after=reset_after,
                      max_macro=max_macro, max_obj=max_obj_area, max_nodes=max_nodes)
        self.steps, self.done, self.levels = 0, False, 0
        self.agent_color, self.votes = None, Counter()
        self.disp = {a: Counter() for a in DIRS}
        self.walkable, self.solid_votes = set(), Counter()
        self._new_level_state()

    def _new_level_state(self):
        self.visits, self.tried, self.blocked = Counter(), set(), set()
        self.touched, self.seen, self.rev = Counter(), set(), Counter()
        self.archive, self.trace = {}, []
        self.recent_targets, self.recent_hashes = deque(maxlen=32), deque(maxlen=16)
        self.stall = 0
        self.solid_votes.clear()

    def _stats(self, grid, colors):
        st = {k: [0, 0, 0, 10**9, 10**9, -1, -1] for k in colors}  # n, sum_r, sum_c, minr, minc, maxr, maxc
        for r, row in enumerate(grid):
            for c, v in enumerate(row):
                s = st.get(v)
                if s:
                    s[0] += 1; s[1] += r; s[2] += c
                    s[3] = min(s[3], r); s[4] = min(s[4], c)
                    s[5] = max(s[5], r); s[6] = max(s[6], c)
        return st

    def _locate(self, grid):
        if self.agent_color is None:
            return None, None
        s = self._stats(grid, [self.agent_color])[self.agent_color]
        if s[0] == 0:
            return None, None
        return (s[3], s[4]), (s[5] - s[3] + 1, s[6] - s[4] + 1)

    def _learn_agent(self, prev, grid, a, changed):
        """Agent = the colour whose same-size mask translates along the action direction."""
        colors = {o for *_, o, _n in changed} | {n for *_, n in changed}
        before, after = self._stats(prev, colors), self._stats(grid, colors)
        dr, dc = DIRS[a]
        for k in colors:
            b, f = before[k], after[k]
            if b[0] == 0 or b[0] != f[0]:
                continue
            mr, mc = (f[1] - b[1]) / b[0], (f[2] - b[2]) / b[0]
            proj = mr * dr + mc * dc
            if proj >= 0.5 and abs(mr * dc - mc * dr) < 0.5 * proj:
                self.votes[k] += 1
        if self.votes:
            self.agent_color = self.votes.most_common(1)[0][0]

    def _step_vec(self, a):
        return self.disp[a].most_common(1)[0][0] if self.disp[a] else DIRS[a]

    @staticmethod
    def _rect(pos, fp, off=(0, 0)):
        if pos is None:
            return []
        return [(pos[0] + off[0] + i, pos[1] + off[1] + j)
                for i in range(fp[0]) for j in range(fp[1])]

    def _primitive(self, game, a, trusted_big_change=False):
        prev, prev_h = self.cur, self.h
        prev_pos, fp = self.pos, self.fp
        grid, done = _unpack(game.step(a))
        self.steps += 1
        h, changed = self.z.diff(prev, prev_h, grid)
        info = dict(moved=False, event=False, new=False, level=False)
        hidden_event = False
        area = max(1, len(grid) * len(grid[0]))
        if done or (len(changed) / area > 0.4 and not trusted_big_change):
            info["level"] = True
            self.levels += 1 if not done else 0
            self.done = done
            self.cur, self.h = grid, self.z.full(grid)
            self._new_level_state()
            self.pos, self.fp = self._locate(grid)
            self.seen.add(self.h)
            self.archive[self.h] = [[], 0]
            return info
        if a in DIRS and self.agent_color is None and changed:
            self._learn_agent(prev, grid, a, changed)
        self.cur, self.h = grid, h
        self.pos, self.fp = self._locate(grid)
        if a in DIRS and prev_pos is not None and self.pos is not None:
            info["moved"] = self.pos != prev_pos
            off = ((self.pos[0] - prev_pos[0], self.pos[1] - prev_pos[1])
                   if info["moved"] else self._step_vec(a))
            dest = self._rect(prev_pos, fp, off)
            cols = {prev[r][c] for r, c in dest
                    if 0 <= r < len(prev) and 0 <= c < len(prev[0])} - {self.agent_color}
            if info["moved"]:
                self.disp[a][off] += 1
                # stepping onto a never-seen colour changes the world under the agent's footprint
                # (key pickup, door opening) where the frame diff cannot see it -> force an event
                hidden_event = bool(self.walkable) and bool(cols - self.walkable)
                self.walkable |= cols
            else:
                self.blocked.add((prev_pos, a))
                if h == prev_h:  # no effect at all -> wall-like colour
                    for k in cols:
                        self.solid_votes[k] += 1
        if prev_pos is not None:  # event = change outside agent's old/new footprint
            own = set(self._rect(prev_pos, fp)) | set(self._rect(self.pos, self.fp))
            if hidden_event or any((r, c) not in own for r, c, *_ in changed):
                info["event"] = True
                self.blocked.clear(); self.tried.clear(); self.solid_votes.clear()
            self.tried.add((prev_pos, a))
        if self.pos is not None:
            self.visits[self.pos] += 1
        self.trace.append(a)
        self.rev[h] += 1
        self.recent_hashes.append(h)
        if h not in self.seen:
            self.seen.add(h); info["new"] = True; self.stall = 0
            self.archive[h] = [list(self.trace), 0]
        else:
            self.stall += 1
        self.done = done
        return info

    def _passable(self, pos, solid):
        g, H, W = self.cur, len(self.cur), len(self.cur[0])
        for r, c in self._rect(pos, self.fp):
            if not (0 <= r < H and 0 <= c < W) or g[r][c] in solid or r in self.z.masked_rows:
                return False
        return True

    def _bfs(self):
        solid = {k for k, v in self.solid_votes.items() if v > 0 and k not in self.walkable}
        parent, dist, q = {self.pos: None}, {self.pos: 0}, deque([self.pos])
        while q and len(dist) < self.p["max_nodes"]:
            u = q.popleft()
            for a in DIRS:
                if (u, a) in self.blocked:
                    continue
                dr, dc = self._step_vec(a)
                v = (u[0] + dr, u[1] + dc)
                if v in dist or not self._passable(v, solid):
                    continue
                dist[v], parent[v] = dist[u] + 1, (u, a)
                q.append(v)
        return dist, parent

    @staticmethod
    def _path(parent, node):
        acts = []
        while parent[node] is not None:
            node, a = parent[node]
            acts.append(a)
        return acts[::-1]

    def _objects(self):
        g, skip = self.cur, {self.agent_color} | self.walkable
        H, W = len(g), len(g[0])
        seen, out = set(), []
        for r0 in range(H):
            for c0 in range(W):
                k = g[r0][c0]
                if (r0, c0) in seen or k in skip or r0 in self.z.masked_rows:
                    continue
                stack, cells = [(r0, c0)], []
                seen.add((r0, c0))
                while stack:
                    r, c = stack.pop(); cells.append((r, c))
                    for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        n = (r + dr, c + dc)
                        if 0 <= n[0] < H and 0 <= n[1] < W and n not in seen and g[n[0]][n[1]] == k:
                            seen.add(n); stack.append(n)
                if len(cells) <= self.p["max_obj"]:
                    out.append((k, min(cells), set(cells)))
        return out

    def _temperature(self):
        p = self.p
        base = p["Tmin"] + (p["T0"] - p["Tmin"]) * math.exp(-self.steps / p["tau"])
        rh = list(self.recent_hashes)
        pressure = sum(self.rev[x] >= 3 for x in rh) / len(rh) if rh else 0.0
        return base * (1.0 + p["eta"] * (4.0 * pressure + min(self.stall / p["S"], 4.0)))

    def _cycle_pen(self, key):
        w, pen = 1.0, 0.0
        for t in reversed(self.recent_targets):
            w *= self.p["rho"]
            if t == key:
                pen += w
        return pen

    def _decide(self):
        if self.pos is None:
            return None
        p = self.p
        dist, parent = self._bfs()
        cands = []  # (utility, (node, tail_actions), key)
        for node, d in dist.items():
            for a in DIRS:
                if (node, a) in self.tried or (node, a) in self.blocked:
                    continue
                dr, dc = self._step_vec(a)
                unknown = (node[0] + dr, node[1] + dc) not in self.visits
                u = p["beta"] / math.sqrt(1 + self.visits[node]) + (p["ub"] if unknown else 0.0)
                key = (node, a)
                cands.append((u - p["c"] * (d + 1) - p["lam"] * self._cycle_pen(key), (node, [a]), key))
        for k, tl, cells in self._objects():
            reach = [n for n in dist if any(c in cells for c in self._rect(n, self.fp))]
            if not reach:
                continue
            node = min(reach, key=dist.__getitem__)
            key = ("obj", k, tl)
            u = p["kappa"] / (1 + self.touched[key]) - p["c"] * dist[node] - p["lam"] * self._cycle_pen(key)
            tail = [ACTION] if (node, ACTION) not in self.tried else []
            cands.append((u, (node, tail), key))
        if not cands:
            return None
        T = max(self._temperature(), 1e-6)
        m = max(c[0] for c in cands)
        w = [math.exp((c[0] - m) / T) for c in cands]
        _, (node, tail), key = self.rng.choices(cands, weights=w)[0]
        if key[0] == "obj":
            self.touched[key] += 1
        self.recent_targets.append(key)
        return (self._path(parent, node) + tail)[: p["max_macro"]]

    def _fallback(self):
        """No frontier/affordance left: poke ACTION, then Go-Explore return, then random walk."""
        if self.pos is not None and (self.pos, ACTION) not in self.tried:
            return [ACTION]
        if self.stall >= self.p["reset_after"] and self.archive:
            h = min(self.archive, key=lambda k: (self.archive[k][1], len(self.archive[k][0])))
            self.archive[h][1] += 1
            self.stall = 0
            return [RESET] + list(self.archive[h][0])
        return [self.rng.choice(list(DIRS))]

    def run(self, game, first_grid, max_steps=2000):
        self.cur, _ = _unpack(first_grid)
        self.h = self.z.full(self.cur)
        self.pos, self.fp = None, None
        self.seen.add(self.h); self.archive[self.h] = [[], 0]
        for a in (1, 2, 3, 4) * 2:  # bootstrap: identify the agent colour
            if self.agent_color is not None or self.done:
                break
            self._primitive(game, a)
        self.pos, self.fp = self._locate(self.cur)
        while self.steps < max_steps and not self.done:
            plan = self._decide() or self._fallback()
            for a in plan:
                before = self.pos
                info = self._primitive(game, a, trusted_big_change=(plan[0] == RESET))
                if self.done or info["level"] or info["event"]:
                    break
                if a in DIRS and not info["moved"] and before is not None:
                    break  # prediction failed -> replan with the new blocked edge
                if self.steps >= max_steps:
                    break
        return dict(steps=self.steps, done=self.done, levels=self.levels,
                    states=len(self.seen), agent_color=self.agent_color)
```

**Usage:**

```python
ex = AffordanceExplorer(seed=0, masked_rows=[hud_row_indices])
stats = ex.run(game, game.reset(), max_steps=2000)
```

## Next steps

- Wire `_unpack` and the action map to the real ARC-AGI-3 API.
- Replay one recorded game offline to check agent-colour detection on real frames. That is the step most likely to fail.
- Calibrate `masked_rows` and `max_obj_area` per game, not globally.

I haven't registered this in the repo or run the real environment, so there is no score evidence yet.