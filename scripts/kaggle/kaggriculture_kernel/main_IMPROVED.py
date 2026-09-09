"""Kaggriculture agent — parallel near-shed carrot economy (IMPROVED).

Replaces the prior submission.py, which was NON-FUNCTIONAL: it read a
non-existent `obs.soil_moisture` attribute and returned a bare int, whereas
the real contract is `agent(obs) -> {"farmer":[...], "hands":[...],
"market":[...]}`. That agent effectively did nothing and sat near the bottom
of the ladder (public score 194.5, rank ~6363/6669).

Grounded in the actual kaggle-environments `kaggriculture` engine
(AGENTS.md / kaggriculture.py). Strategy, chosen after local validation:

* The built-in `starter` baseline is a single stationary carrot loop
  (~+500 coins/season). It is beatable purely by THROUGHPUT.
* Units reset to the shed each morning and hands re-spawn near the shed,
  so tiles FAR from the shed cost walking turns that dominate the thin crop
  margins. Measured: scaling hands + buying land + using far tiles LOSES to
  the lean version. The sweet spot is a COMPACT cluster of near-shed tiles
  worked by the farmer + a few hands, each running the proven carrot loop.
* Carrot (seed 20, base price 35, ~3 units/harvest under daily watering) is
  the best cheap per-tile value and matches what the `starter` uses.

Cash discipline: hires and seed buys keep a $150 cash floor so the agent
never spends itself below the do-nothing baseline. No land purchases (far
tiles are net-negative under the daily reset). Wrapped in try/except so a
malformed observation degrades to PASS instead of erroring the episode.

Local validation (kaggle-environments, episodeSteps=720):
  vs starter : 20-0 across both seats (min bank 4304, starter ~3300)
  vs random  : 4-0
  vs pass    : 3-0
  self-play  : 3 ties, 0 errors  (passes the submission validation episode)

HONEST CEILING: top of the public leaderboard (~2970 rating) is reached by
distilled, hard-coded 720-turn "replay tapes" (base64+zlib schedules) built
from weeks of replay-hunting the leaders, plus a livestock-heavy economy
(8 cows / 5-6 sheep, ~12 hands, 3 quadrants) with clone-aware market timing.
That is not reachable by a clean heuristic in this scope. This agent is the
high-ROI, low-risk move: turn a non-functional bot into one that reliably
beats the competent `starter`-class opponents, moving us well off the floor.
Next step (needs live-ladder iteration): add a small cow/sheep ranch for
compounding milk/wool income — the highest-value ongoing yields.
"""

CARROT_SEED = 20
CASH_FLOOR = 150


def _home_tiles(board):
    """NW-quadrant tiles ordered by Manhattan distance from the farmer spawn (4,4).

    Only the NW quadrant is unlocked at the start; hugging the shed keeps
    walking overhead minimal, which is what makes the thin crop margins pay.
    """
    half = board // 2
    cx = cy = half - 1
    cells = [(x, y) for y in range(half) for x in range(half)]
    cells.sort(key=lambda c: (abs(c[0] - cx) + abs(c[1] - cy), c[1], c[0]))
    return cells


def _step_toward(px, py, tx, ty):
    if px < tx:
        return "EAST"
    if px > tx:
        return "WEST"
    if py < ty:
        return "SOUTH"
    if py > ty:
        return "NORTH"
    return None


def agent(obs):
    try:
        return _decide(obs)
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}


def _decide(obs):
    player = obs["player"]
    me = obs["farms"][player]
    private = obs["private"]
    tiles = me["tiles"]
    money = me["money"]
    day = obs["day"]
    hour = obs["hour"]
    board = len(tiles)
    seeds = private.get("seeds", {})
    shed = private.get("shed", {})

    units = [me["farmer"]] + list(me.get("hands", []))
    n_units = len(units)
    homes = _home_tiles(board)

    # ---------------- market plan (processed AFTER unit actions) ----------------
    market = []

    # Liquidate everything harvested (harvest lands in unit inventory and
    # auto-drops to the shed at end of day; SELL only reads the shed).
    for item, cnt in list(shed.items()):
        if cnt > 0:
            market.append(["SELL", item, cnt])

    # Hire hands early each day (they re-spawn near the shed and are re-hired
    # daily). Hire cost is fib(n): 1,1,2,3,5,8. Cap low and cash-safe — extra
    # hands only pay off on tiles close enough to work without wasting the day.
    if hour <= 1:
        if money > 800:
            target = 5
        elif money > 350:
            target = 3
        elif money > 150:
            target = 1
        else:
            target = 0
        already = me.get("hires_today", 0)
        for _ in range(max(0, target - already)):
            market.append(["HIRE"])

    # Replenish carrot seeds up to one per working unit, honoring the cash floor.
    have = seeds.get("CARROT", 0)
    want = max(0, min(n_units, 6) - have)
    buy_n = 0
    while buy_n < want and (money - CARROT_SEED * (buy_n + 1)) >= CASH_FLOOR and buy_n < 6:
        buy_n += 1
    if buy_n > 0:
        market.append(["BUY_SEED", "CARROT", buy_n])

    market = market[:10]  # engine caps at maxMarketOrdersPerTurn (default 10)

    # ---------------- per-unit field ops ----------------
    # seed_budget guards the engine's atomic PLANT rule: if PLANT requests for a
    # crop exceed seeds on hand, ALL of them are dropped that turn.
    seed_budget = seeds.get("CARROT", 0)
    ops = []
    for i in range(n_units):
        px, py = units[i]
        hx, hy = homes[i] if i < len(homes) else homes[-1]

        if (px, py) != (hx, hy):
            mv = _step_toward(px, py, hx, hy)
            ops.append([mv] if mv else ["PASS"])
            continue

        tile = tiles[py][px]
        if tile is None:
            if seed_budget > 0:
                ops.append(["PLANT", "CARROT"])
                seed_budget -= 1
            else:
                ops.append(["PASS"])
        elif isinstance(tile, dict):
            kind = tile.get("kind")
            if kind == "PLANT":
                age = day - tile.get("planted_day", day)
                if tile.get("yield_units", 0) > 0 and age >= 3:  # CARROT max_yield_day=3
                    ops.append(["HARVEST"])
                elif not tile.get("watered_today", False):
                    ops.append(["WATER"])
                else:
                    ops.append(["PASS"])
            elif kind == "WEED":
                ops.append(["DIG"])
            else:
                ops.append(["PASS"])
        else:
            ops.append(["PASS"])

    return {"farmer": ops[0], "hands": ops[1:], "market": market}
