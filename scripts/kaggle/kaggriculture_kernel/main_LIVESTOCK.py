"""Kaggriculture agent — carrot base + near-shed COW ranch (LIVESTOCK).

Extends the validated `main_IMPROVED.py` parallel near-shed carrot economy by
adding a small, robust cow ranch. Milk (base 160) is ~4.5x the value of carrot
(base 35) and cows produce indefinitely once fed, so a handful of well-fed cows
compounds far past one-time crops.

Grounded in the actual kaggle-environments `kaggriculture` engine
(kaggriculture.py / AGENTS.md). Exact livestock mechanics used here:

* COW: cost 400, needs a PASTURE tile, first milk on (placed_day + 8), then
  every interval=2 days, max_held=6 milk on the tile. Product MILK.
* Flow: unit on empty tile -> BUILD_PASTURE (free); market ["BUY_ANIMAL","COW",n]
  -> cow lands in the shed; unit shed-adjacent -> ["PICKUP","COW",k]; unit on the
  pasture tile -> ["PLACE","COW"]; DAILY the unit stands on the animal tile with
  WHEAT in ITS OWN inventory -> FEED; HARVEST moves milk into inventory, which
  auto-drops to the shed at end of day; SELL reads the shed.
* ESCAPE: two consecutive end-of-days with fed_today=False -> the cow escapes
  permanently (structure remains, -400 sunk). The placement day counts as unfed
  unless fed that same day. => we FEED every day, deterministically.
* Only (4,4) is shed-adjacent at the start (the other three shed-access tiles are
  in LOCKED quadrants), and the farmer respawns at (4,4) every morning — so the
  FARMER is the rancher: it always begins the day shed-adjacent, picks up wheat
  (and cows during setup), and services the near-shed pastures. The hired hands
  keep running the proven carrot loop.

Design decisions (verified against the engine, tuned by local A/B episodes):
* Wheat for feed is BOUGHT (BUY_PRODUCT WHEAT ~25 ea into the shed, then PICKUP)
  — deterministic and simple; one pickup per day covers every cow. A wheat buffer
  of 2x the herd is kept in the shed so a feed is never missed.
* Milk market is thin (T=122): dumping the whole herd's milk in one turn sags the
  price, but town-center + dairy shops (pizza/ice-cream/smoothie) consume milk
  daily, so metered selling keeps it near base. We sell the shed's milk every
  turn — measured to stay well above carrot value.
* $150 cash floor on every discretionary spend (hire, seed, wheat, cow) so the
  agent never spends itself below the do-nothing baseline.
* Wrapped in try/except -> PASS so a malformed observation never errors an episode.

Ranch sizing (NUM_COWS / PASTURE_TILES) was chosen by head-to-head episodes vs
`main_IMPROVED.py` and `starter`; see the validation block committed alongside.
"""

CARROT_SEED = 20
CASH_FLOOR = 150
SHED = (4, 4)  # only shed-adjacent tile unlocked at start (NW quadrant)

# Near-shed pasture tiles (all NW, adjacent/near (4,4) to minimise rancher walk).
# A 5th (more distant) pasture was measured to break feeding coverage -> cows
# escape and the agent LOSES; 4 near-shed cows is the tuned sweet spot (higher
# banks than 3, 0 escapes across all tested seeds, well clear of the 5-cow cliff).
PASTURE_TILES = [(3, 4), (4, 3), (3, 3), (2, 4)]
NUM_COWS = 4                      # herd size (<= len(PASTURE_TILES))
COW_COST = 400
COW_FIRST_YIELD = 8              # milk starts placed_day + 8
WHEAT_BUFFER_MULT = 2            # keep 2x herd wheat in the shed


def _active_pastures():
    return PASTURE_TILES[:max(0, NUM_COWS)]


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


def _carrot_homes(board):
    """NW tiles by distance from (4,4), EXCLUDING pasture tiles (reserved)."""
    half = board // 2
    cx = cy = half - 1
    reserved = set(_active_pastures())
    cells = [(x, y) for y in range(half) for x in range(half) if (x, y) not in reserved]
    cells.sort(key=lambda c: (abs(c[0] - cx) + abs(c[1] - cy), c[1], c[0]))
    return cells


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
    shed = dict(private.get("shed", {}))
    inventories = private.get("inventories", [{}])
    farmer_inv = inventories[0] if inventories else {}

    hands = list(me.get("hands", []))
    active = _active_pastures()
    ranch_on = NUM_COWS > 0

    # ---------------- market plan (processed AFTER unit actions) ----------------
    # Only maxMarketOrdersPerTurn (=10) orders survive per turn; extras are
    # silently dropped. So we build priority buckets and concatenate livestock
    # buys FIRST — a truncated cow/wheat order would starve the ranch (a cow that
    # never gets fed escapes, -400), which is far costlier than a dropped hire or
    # seed order that simply retries next turn.
    livestock_orders = []
    sell_orders = []
    hire_orders = []
    seed_orders = []

    if ranch_on:
        # Buy the herd once, early: only if we have no cows anywhere yet.
        cows_owned = sum(
            1 for (x, y) in active
            if isinstance(tiles[y][x], dict) and "animal" in tiles[y][x]
        )
        cows_pending = shed.get("COW", 0) + farmer_inv.get("COW", 0)
        want_cows = len(active) - cows_owned - cows_pending
        if want_cows > 0 and day == 0:
            n = 0
            while n < want_cows and (money - COW_COST * (n + 1)) >= CASH_FLOOR:
                n += 1
            if n > 0:
                livestock_orders.append(["BUY_ANIMAL", "COW", n])

        # Keep a wheat buffer in the shed for feeding (buy a day ahead).
        need_wheat = len(active) * WHEAT_BUFFER_MULT
        have_wheat = shed.get("WHEAT", 0) + farmer_inv.get("WHEAT", 0)
        want_wheat = need_wheat - have_wheat
        if want_wheat > 0 and hour <= 2:
            wprice = obs.get("market", {}).get("prices", {}).get("WHEAT", 25)
            wprice = max(1, int(wprice))
            n = 0
            while n < want_wheat and (money - wprice * (n + 1)) >= CASH_FLOOR:
                n += 1
            if n > 0:
                livestock_orders.append(["BUY_PRODUCT", "WHEAT", n])

    # Sell every harvested product sitting in the shed (carrots, milk, etc.).
    for item, cnt in list(shed.items()):
        if cnt > 0 and item not in ("COW", "SHEEP", "GOOSE", "FERTILIZER"):
            sell_orders.append(["SELL", item, cnt])

    # Hire hands early each day (they respawn at the shed and are re-hired daily).
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
            hire_orders.append(["HIRE"])

    # Replenish carrot seeds up to one per carrot-working hand.
    n_carrot_workers = len(hands)  # farmer is the rancher; hands farm carrots
    have_seed = seeds.get("CARROT", 0)
    want_seed = max(0, min(n_carrot_workers, 6) - have_seed)
    buy_n = 0
    while buy_n < want_seed and (money - CARROT_SEED * (buy_n + 1)) >= CASH_FLOOR and buy_n < 6:
        buy_n += 1
    if buy_n > 0:
        seed_orders.append(["BUY_SEED", "CARROT", buy_n])

    market = (livestock_orders + sell_orders + hire_orders + seed_orders)[:10]

    # ---------------- farmer = rancher ----------------
    if ranch_on:
        farmer_op = _rancher_op(me, tiles, farmer_inv, shed, active)
    else:
        # No ranch: farmer falls back to a carrot tile (home[0]).
        farmer_op = _carrot_op(tiles, me["farmer"], _carrot_homes(board)[0], day, seeds.get("CARROT", 0))[0]

    # ---------------- hands = carrot workers ----------------
    homes = _carrot_homes(board)
    seed_budget = seeds.get("CARROT", 0)
    hand_ops = []
    for i, (px, py) in enumerate(hands):
        hx, hy = homes[i] if i < len(homes) else homes[-1]
        op, seed_budget = _carrot_op(tiles, (px, py), (hx, hy), day, seed_budget)
        hand_ops.append(op)

    return {"farmer": farmer_op, "hands": hand_ops, "market": market}


def _carrot_op(tiles, pos, home, day, seed_budget):
    """Proven carrot loop for one unit. Returns (op, remaining_seed_budget)."""
    px, py = pos
    hx, hy = home
    if (px, py) != (hx, hy):
        mv = _step_toward(px, py, hx, hy)
        return ([mv] if mv else ["PASS"], seed_budget)
    tile = tiles[py][px]
    if tile is None:
        if seed_budget > 0:
            return (["PLANT", "CARROT"], seed_budget - 1)
        return (["PASS"], seed_budget)
    if isinstance(tile, dict):
        kind = tile.get("kind")
        if kind == "PLANT":
            age = day - tile.get("planted_day", day)
            if tile.get("yield_units", 0) > 0 and age >= 3:  # CARROT max_yield_day=3
                return (["HARVEST"], seed_budget)
            if not tile.get("watered_today", False):
                return (["WATER"], seed_budget)
            return (["PASS"], seed_budget)
        if kind == "WEED":
            return (["DIG"], seed_budget)
    return (["PASS"], seed_budget)


def _rancher_op(me, tiles, inv, shed, active):
    """One rancher action. Priorities: act on current tile, else fetch/travel.

    The farmer starts each day at (4,4) (shed-adjacent). It:
      - builds any missing pastures,
      - picks up cows from the shed and places them,
      - picks up wheat and feeds every cow daily (escape guard),
      - harvests milk (auto-drops to shed at end of day for selling).
    """
    fx, fy = me["farmer"]
    wheat = inv.get("WHEAT", 0)
    cows_inv = inv.get("COW", 0)

    def tile_at(t):
        return tiles[t[1]][t[0]]

    # Classify pasture tiles.
    to_build = [t for t in active if tile_at(t) is None]
    to_clear = [t for t in active
                if isinstance(tile_at(t), dict) and tile_at(t).get("kind") == "WEED"]
    empty_pastures = [t for t in active
                      if isinstance(tile_at(t), dict)
                      and tile_at(t).get("kind") == "PASTURE" and "animal" not in tile_at(t)]
    animals = [t for t in active
               if isinstance(tile_at(t), dict) and "animal" in tile_at(t)]
    to_harvest = [t for t in animals if tile_at(t).get("yield_units", 0) > 0]
    to_feed = [t for t in animals if not tile_at(t).get("fed_today", False)]

    # ---- 1. act on the CURRENT tile if it needs it ----
    cur = (fx, fy)
    ct = tile_at(cur) if cur in active else None
    if cur in active:
        if ct is None:
            return ["BUILD_PASTURE"]
        if isinstance(ct, dict):
            if ct.get("kind") == "WEED":
                return ["DIG"]
            if ct.get("kind") == "PASTURE" and "animal" not in ct and cows_inv > 0:
                return ["PLACE", "COW"]
            if "animal" in ct:
                if ct.get("yield_units", 0) > 0:
                    return ["HARVEST"]
                if not ct.get("fed_today", False) and wheat > 0:
                    return ["FEED"]

    # ---- 2. shed pickups when standing at (4,4) ----
    if cur == SHED:
        need_cows = len(empty_pastures)
        if cows_inv < need_cows and shed.get("COW", 0) > 0:
            take = min(need_cows - cows_inv, shed.get("COW", 0))
            if take > 0:
                return ["PICKUP", "COW", take]
        need_wheat = len(to_feed) - wheat
        if need_wheat > 0 and shed.get("WHEAT", 0) > 0:
            take = min(need_wheat, shed.get("WHEAT", 0))
            if take > 0:
                return ["PICKUP", "WHEAT", take]

    # ---- 3. choose a travel target ----
    # Building needs nothing in hand; clear weeds; place needs a cow in inv (else shed);
    # feed needs wheat in inv (else shed); harvest needs nothing.
    target = None
    if to_build:
        target = _nearest((fx, fy), to_build)
    elif to_clear:
        target = _nearest((fx, fy), to_clear)
    elif empty_pastures:
        if cows_inv > 0:
            target = _nearest((fx, fy), empty_pastures)
        elif shed.get("COW", 0) > 0:
            target = SHED
    elif to_harvest:
        target = _nearest((fx, fy), to_harvest)
    elif to_feed:
        if wheat > 0:
            target = _nearest((fx, fy), to_feed)
        elif shed.get("WHEAT", 0) > 0:
            target = SHED
    # Nothing to do -> park at shed (ready for tomorrow's pickup).
    if target is None:
        target = SHED

    if (fx, fy) == target:
        return ["PASS"]
    mv = _step_toward(fx, fy, target[0], target[1])
    return [mv] if mv else ["PASS"]


def _nearest(pos, tiles):
    px, py = pos
    return min(tiles, key=lambda t: (abs(t[0] - px) + abs(t[1] - py), t[1], t[0]))
