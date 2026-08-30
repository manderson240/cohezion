"""Stress controller: exercises land-buy, ongoing crops, extra cows, goose, care,
fertilize, weeds — the dynamics paths the planner will explore. Used only to widen
fidelity-validation coverage beyond the LIVESTOCK carrot+cow subset."""
import random

_SHED = (4, 4)


def _step_toward(px, py, tx, ty):
    if px < tx: return "EAST"
    if px > tx: return "WEST"
    if py < ty: return "SOUTH"
    if py > ty: return "NORTH"
    return None


def agent(obs):
    try:
        return _decide(obs)
    except Exception:
        return {"farmer": ["PASS"], "hands": [], "market": []}


def _decide(obs):
    player = obs["player"]
    me = obs["farms"][player]
    day = obs["day"]; hour = obs["hour"]
    money = me["money"]
    tiles = me["tiles"]
    priv = obs["private"]
    seeds = priv.get("seeds", {})
    shed = dict(priv.get("shed", {}))
    invs = priv.get("inventories", [{}])
    finv = invs[0] if invs else {}
    fx, fy = me["farmer"]
    rng = random.Random(day * 97 + hour * 7 + player)

    market = []
    # Buy land early to exercise unlock path
    if day == 2 and hour == 0 and money > 2500:
        market.append(["BUY_LAND"])
    if day == 6 and hour == 0 and money > 5000:
        market.append(["BUY_LAND"])
    # Buy a goose (COOP) + cows to exercise multi-animal
    if day == 0 and hour == 0:
        market.append(["BUY_ANIMAL", "GOOSE", 1])
        market.append(["BUY_ANIMAL", "COW", 2])
    # Ongoing crops
    for crop in ("TOMATO", "STRAWBERRY"):
        if seeds.get(crop, 0) == 0 and money > 400 and hour <= 2:
            market.append(["BUY_SEED", crop, 1])
    if seeds.get("CARROT", 0) < 3 and money > 200:
        market.append(["BUY_SEED", "CARROT", 2])
    if shed.get("WHEAT", 0) < 6 and money > 200 and hour <= 3:
        market.append(["BUY_PRODUCT", "WHEAT", 4])
    if hour <= 1 and money > 300:
        market.append(["HIRE"])
    for item, cnt in list(shed.items()):
        if cnt > 0 and item not in ("COW", "GOOSE", "SHEEP", "FERTILIZER"):
            market.append(["SELL", item, cnt])

    # farmer: wander a fixed serpentine, build/place/feed/care/harvest opportunistically
    tile = tiles[fy][fx]
    op = ["PASS"]
    if isinstance(tile, dict):
        k = tile.get("kind")
        if "animal" in tile:
            if tile.get("yield_units", 0) > 0:
                op = ["HARVEST"]
            elif not tile.get("fed_today") and finv.get("WHEAT", 0) > 0:
                op = ["FEED"]
            elif not tile.get("cared_today"):
                op = ["CARE"]
            elif tile.get("fertilizer_available"):
                op = ["COLLECT_FERTILIZER"]
        elif k == "PASTURE" and finv.get("COW", 0) > 0:
            op = ["PLACE", "COW"]
        elif k == "COOP" and finv.get("GOOSE", 0) > 0:
            op = ["PLACE", "GOOSE"]
        elif k == "PLANT":
            if tile.get("yield_units", 0) > 0 and (day - tile.get("planted_day", day)) >= 3:
                op = ["HARVEST"]
            elif not tile.get("watered_today"):
                op = ["WATER"]
            elif finv.get("FERTILIZER", 0) > 0 and rng.random() < 0.3:
                op = ["FERTILIZE"]
        elif k == "WEED":
            op = ["DIG"]
    elif tile is None:
        # near shed: build structures; else plant
        if (fx, fy) == _SHED and finv.get("COW", 0) == 0 and shed.get("COW", 0) > 0:
            op = ["PICKUP", "COW", shed.get("COW", 0)]
        elif (fx, fy) == _SHED and shed.get("WHEAT", 0) > 0 and finv.get("WHEAT", 0) == 0:
            op = ["PICKUP", "WHEAT", min(4, shed.get("WHEAT", 0))]
        elif rng.random() < 0.3:
            op = ["BUILD_PASTURE"]
        elif rng.random() < 0.3:
            op = ["BUILD_COOP"]
        elif seeds.get("CARROT", 0) > 0 and rng.random() < 0.5:
            op = ["PLANT", "CARROT"]
        elif seeds.get("TOMATO", 0) > 0:
            op = ["PLANT", "TOMATO"]
        else:
            op = [rng.choice(["NORTH", "SOUTH", "EAST", "WEST"])]
    else:
        op = [rng.choice(["NORTH", "SOUTH", "EAST", "WEST"])]

    hands = me.get("hands", [])
    hand_ops = []
    for (hx, hy) in hands:
        ht = tiles[hy][hx]
        if isinstance(ht, dict) and ht.get("kind") == "PLANT" and not ht.get("watered_today"):
            hand_ops.append(["WATER"])
        elif ht is None and seeds.get("CARROT", 0) > 0 and rng.random() < 0.4:
            hand_ops.append(["PLANT", "CARROT"])
        else:
            hand_ops.append([rng.choice(["NORTH", "SOUTH", "EAST", "WEST", "PASS"])])
    return {"farmer": op, "hands": hand_ops, "market": market[:10]}
