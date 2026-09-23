#!/usr/bin/env python3
"""Prototype and test NE Quadrant Expansion for Kaggriculture.

Verifies:
1. BUY_LAND order execution in FarmSim.
2. Unlocked quadrant propagation in obs.
3. Expanded carrot home assignment (42+ tiles).
4. Head-to-head tournament: v6 (with NE expansion) vs v5 SOTA.
"""

from __future__ import annotations
import sys
import copy
from pathlib import Path
import statistics

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

import main_PLANNER_v5_sota as v5

def make_v6_controller(P_override=None):
    base_P = dict(v5.DEFAULT_P)
    base_P.update({
        "expand_land": True,
        "buy_ne_day": 11,
        "hire_tiers": [(1000, 10), (700, 8), (350, 5), (150, 2)],
        "max_hands_seed": 12,
        "cash_floor": 150,
    })
    if P_override:
        base_P.update(P_override)
    P = v5._p_of(base_P)

    def v6_controller(obs):
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
        unlocked_quads = list(me.get("unlocked_quadrants", ["NW"]))

        num_cows = P["num_cows"]
        active = P["pastures"][:num_cows]
        ranch_on = num_cows > 0
        cash_floor = P["cash_floor"]
        cow_cost = P["cow_cost"]

        land_orders = []
        livestock_orders = []
        sell_orders = []
        hire_orders = []
        seed_orders = []

        # 1. Dynamic Land Expansion
        if (
            P.get("expand_land", False)
            and "NE" not in unlocked_quads
            and day >= P.get("buy_ne_day", 11)
            and hour <= 1
            and (money - 1000) >= cash_floor
        ):
            land_orders.append(["BUY_LAND"])

        # 2. Livestock management
        if ranch_on:
            cows_owned = sum(
                1 for (x, y) in active if isinstance(tiles[y][x], dict) and "animal" in tiles[y][x]
            )
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

        # 3. Market Sales & Day 29 Fertilizer Liquidation
        for item, cnt in list(shed.items()):
            if cnt > 0 and item not in ("COW", "SHEEP", "GOOSE", "FERTILIZER"):
                sell_orders.append(["SELL", item, cnt])
            elif day == 29 and item == "FERTILIZER" and cnt > 0:
                sell_orders.append(["SELL", item, cnt])

        # 4. Hires
        if hour <= 1:
            target = 0
            for money_gt, t in P["hire_tiers"]:
                if money > money_gt:
                    target = t
                    break
            already = me.get("hires_today", 0)
            for _ in range(max(0, target - already)):
                hire_orders.append(["HIRE"])

        # 5. Seeds (with Day 27+ seed freeze)
        if day < 27:
            n_carrot_workers = len(hands)
            have_seed = seeds.get("CARROT", 0)
            want_seed = max(0, min(n_carrot_workers, P["max_hands_seed"]) - have_seed)
            buy_n = 0
            cs = P["carrot_seed_cost"]
            while (
                buy_n < want_seed
                and (money - cs * (buy_n + 1)) >= cash_floor
                and buy_n < P["max_hands_seed"]
            ):
                buy_n += 1
            if buy_n > 0:
                seed_orders.append(["BUY_SEED", "CARROT", buy_n])

        market = (land_orders + livestock_orders + sell_orders + hire_orders + seed_orders)[:10]

        # 6. Unit ops
        if ranch_on:
            farmer_op = v5._rancher_op(me, tiles, farmer_inv, shed, active, P.get("care", False))
        else:
            homes0 = _expanded_carrot_homes(board, active, unlocked_quads)
            farmer_op = v5._carrot_op(tiles, me["farmer"], homes0[0], day, seeds.get("CARROT", 0))[0]

        homes = _expanded_carrot_homes(board, active, unlocked_quads)
        seed_budget = seeds.get("CARROT", 0)
        hand_ops = []
        for i, (px, py) in enumerate(hands):
            hx, hy = homes[i] if i < len(homes) else homes[-1]
            op, seed_budget = v5._carrot_op(tiles, (px, py), (hx, hy), day, seed_budget)
            hand_ops.append(op)

        return {"farmer": farmer_op, "hands": hand_ops, "market": market}

    return v6_controller


def _expanded_carrot_homes(board, reserved, unlocked_quads):
    half = board // 2
    shed_tiles = set(v5._shed_access_tiles(board))
    reserved = set(reserved) | shed_tiles
    cells = []

    if "NW" in unlocked_quads:
        for y in range(half):
            for x in range(half):
                if (x, y) not in reserved:
                    cells.append((x, y))

    if "NE" in unlocked_quads:
        for y in range(half):
            for x in range(half, board):
                if (x, y) not in reserved:
                    cells.append((x, y))

    if "SW" in unlocked_quads:
        for y in range(half, board):
            for x in range(half):
                if (x, y) not in reserved:
                    cells.append((x, y))

    if "SE" in unlocked_quads:
        for y in range(half, board):
            for x in range(half, board):
                if (x, y) not in reserved:
                    cells.append((x, y))

    cx, cy = half - 1, half - 1
    cells.sort(key=lambda c: (abs(c[0] - cx) + abs(c[1] - cy), c[1], c[0]))
    return cells


if __name__ == "__main__":
    from kaggle_environments import make

    print("=== Testing Single Game: v6 with NE expansion vs v5 SOTA ===")
    v6_ctrl = make_v6_controller()
    env = make("kaggriculture", configuration={"seed": 0}, debug=False)
    env.run([v6_ctrl, v5.agent])
    last = env.steps[-1]
    r_v6 = last[0].reward
    r_v5 = last[1].reward
    farm_v6 = last[0].observation["farms"][0]
    print(f"Seed 0: v6={r_v6} vs v5={r_v5} | Unlocked: {farm_v6['unlocked_quadrants']} | Hands: {len(farm_v6['hands'])}")
