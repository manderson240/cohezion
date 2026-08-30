"""Parameterized generalization of the LIVESTOCK controller.

Same proven loop (farmer = rancher servicing near-shed NW cows, hands = carrot
lanes), but NUM_COWS / pasture tile set / hire tiers / cash floor are parameters
so the planner can roll candidates forward in the embedded model and pick the best.
P is a dict; missing keys fall back to the LIVESTOCK defaults.
"""

# Ordered near-shed NW pasture tiles by farmer-walk distance from (4,4).
# The farmer respawns at (4,4); tiles closest to it are cheapest to service.
NW_PASTURES = [(3, 4), (4, 3), (3, 3), (2, 4), (4, 2), (2, 3), (3, 2), (2, 2),
               (1, 4), (4, 1), (1, 3), (3, 1)]

DEFAULT_P = {
    "num_cows": 4,
    "care": False,
    "pastures": [(3, 4), (4, 3), (3, 3), (2, 4)],
    "carrot_seed_cost": 20,
    "cash_floor": 150,
    "cow_cost": 400,
    "wheat_buffer_mult": 2,
    "hire_tiers": [(800, 5), (350, 3), (150, 1)],   # (money_gt, target_hands)
    "max_hands_seed": 6,
}
SHED = (4, 4)


def _step_toward(px, py, tx, ty):
    if px < tx: return "EAST"
    if px > tx: return "WEST"
    if py < ty: return "SOUTH"
    if py > ty: return "NORTH"
    return None


def _nearest(pos, tiles):
    px, py = pos
    return min(tiles, key=lambda t: (abs(t[0] - px) + abs(t[1] - py), t[1], t[0]))


def _carrot_homes(board, reserved):
    half = board // 2
    cx = cy = half - 1
    reserved = set(reserved)
    cells = [(x, y) for y in range(half) for x in range(half) if (x, y) not in reserved]
    cells.sort(key=lambda c: (abs(c[0] - cx) + abs(c[1] - cy), c[1], c[0]))
    return cells


def _carrot_op(tiles, pos, home, day, seed_budget):
    px, py = pos; hx, hy = home
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
            if tile.get("yield_units", 0) > 0 and age >= 3:
                return (["HARVEST"], seed_budget)
            if not tile.get("watered_today", False):
                return (["WATER"], seed_budget)
            return (["PASS"], seed_budget)
        if kind == "WEED":
            return (["DIG"], seed_budget)
    return (["PASS"], seed_budget)


def _rancher_op(me, tiles, inv, shed, active, care=False):
    fx, fy = me["farmer"]
    wheat = inv.get("WHEAT", 0)
    cows_inv = inv.get("COW", 0)

    def tile_at(t):
        return tiles[t[1]][t[0]]

    to_build = [t for t in active if tile_at(t) is None]
    to_clear = [t for t in active if isinstance(tile_at(t), dict) and tile_at(t).get("kind") == "WEED"]
    empty_pastures = [t for t in active if isinstance(tile_at(t), dict)
                      and tile_at(t).get("kind") == "PASTURE" and "animal" not in tile_at(t)]
    animals = [t for t in active if isinstance(tile_at(t), dict) and "animal" in tile_at(t)]
    to_harvest = [t for t in animals if tile_at(t).get("yield_units", 0) > 0]
    to_feed = [t for t in animals if not tile_at(t).get("fed_today", False)]
    # CARE (only after fed): accumulates a milk bonus consumed on production days,
    # ~tripling milk yield. Free labour for the 4-cow ranch (spare farmer turns).
    to_care = [t for t in animals
               if care and tile_at(t).get("fed_today", False) and not tile_at(t).get("cared_today", False)]

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
                if care and ct.get("fed_today", False) and not ct.get("cared_today", False):
                    return ["CARE"]

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
    elif to_care:
        target = _nearest((fx, fy), to_care)
    if target is None:
        target = SHED
    if (fx, fy) == target:
        return ["PASS"]
    mv = _step_toward(fx, fy, target[0], target[1])
    return [mv] if mv else ["PASS"]


def controller(obs, P):
    player = obs["player"]
    me = obs["farms"][player]
    private = obs["private"]
    tiles = me["tiles"]
    money = me["money"]
    day = obs["day"]; hour = obs["hour"]
    board = len(tiles)
    seeds = private.get("seeds", {})
    shed = dict(private.get("shed", {}))
    inventories = private.get("inventories", [{}])
    farmer_inv = inventories[0] if inventories else {}
    hands = list(me.get("hands", []))

    num_cows = P["num_cows"]
    active = P["pastures"][:num_cows]
    ranch_on = num_cows > 0
    cash_floor = P["cash_floor"]
    cow_cost = P["cow_cost"]

    livestock_orders = []; sell_orders = []; hire_orders = []; seed_orders = []

    if ranch_on:
        cows_owned = sum(1 for (x, y) in active
                         if isinstance(tiles[y][x], dict) and "animal" in tiles[y][x])
        cows_pending = shed.get("COW", 0) + farmer_inv.get("COW", 0)
        want_cows = len(active) - cows_owned - cows_pending
        if want_cows > 0 and day == 0:
            n = 0
            while n < want_cows and (money - cow_cost * (n + 1)) >= cash_floor:
                n += 1
            if n > 0:
                livestock_orders.append(["BUY_ANIMAL", "COW", n])
        need_wheat = len(active) * P["wheat_buffer_mult"]
        have_wheat = shed.get("WHEAT", 0) + farmer_inv.get("WHEAT", 0)
        want_wheat = need_wheat - have_wheat
        if want_wheat > 0 and hour <= 2:
            wprice = obs.get("market", {}).get("prices", {}).get("WHEAT", 25)
            wprice = max(1, int(wprice))
            n = 0
            while n < want_wheat and (money - wprice * (n + 1)) >= cash_floor:
                n += 1
            if n > 0:
                livestock_orders.append(["BUY_PRODUCT", "WHEAT", n])

    for item, cnt in list(shed.items()):
        if cnt > 0 and item not in ("COW", "SHEEP", "GOOSE", "FERTILIZER"):
            sell_orders.append(["SELL", item, cnt])

    if hour <= 1:
        target = 0
        for money_gt, t in P["hire_tiers"]:
            if money > money_gt:
                target = t; break
        already = me.get("hires_today", 0)
        for _ in range(max(0, target - already)):
            hire_orders.append(["HIRE"])

    n_carrot_workers = len(hands)
    have_seed = seeds.get("CARROT", 0)
    want_seed = max(0, min(n_carrot_workers, P["max_hands_seed"]) - have_seed)
    buy_n = 0
    cs = P["carrot_seed_cost"]
    while buy_n < want_seed and (money - cs * (buy_n + 1)) >= cash_floor and buy_n < P["max_hands_seed"]:
        buy_n += 1
    if buy_n > 0:
        seed_orders.append(["BUY_SEED", "CARROT", buy_n])

    market = (livestock_orders + sell_orders + hire_orders + seed_orders)[:10]

    if ranch_on:
        farmer_op = _rancher_op(me, tiles, farmer_inv, shed, active, P.get("care", False))
    else:
        homes0 = _carrot_homes(board, active)
        farmer_op = _carrot_op(tiles, me["farmer"], homes0[0], day, seeds.get("CARROT", 0))[0]

    homes = _carrot_homes(board, active)
    seed_budget = seeds.get("CARROT", 0)
    hand_ops = []
    for i, (px, py) in enumerate(hands):
        hx, hy = homes[i] if i < len(homes) else homes[-1]
        op, seed_budget = _carrot_op(tiles, (px, py), (hx, hy), day, seed_budget)
        hand_ops.append(op)

    return {"farmer": farmer_op, "hands": hand_ops, "market": market}
