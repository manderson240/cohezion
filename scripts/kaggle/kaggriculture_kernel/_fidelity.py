"""Fidelity validator: embedded FarmSim vs real kaggriculture engine, step-for-step.

Drives the REAL engine (controller at seat0, PASS at seat1 so the shared market moves
only by seat0 sells + town consumption). Replays each recorded (state_t, action_t) into
the embedded FarmSim and asserts farm0 / private0 / market next-state matches obs_{t+1}.
Reports the per-step mismatch rate over >=50 states across several seeds.
"""
import sys, copy, importlib.util
from kaggle_environments import make
import _embed_model as em

KDIR = "/home/mike-anderson/dev/cohezion/scripts/kaggle/kaggriculture_kernel"


def load_agent(path):
    spec = importlib.util.spec_from_file_location("ctrl", path)
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod.agent


def _canon_market(m):
    return {"inventory": dict(m["inventory"]), "prices": dict(m["prices"])}


def _diff(embedded, real, ctx):
    """Return list of mismatch descriptions between embedded state and real obs."""
    out = []
    ef, rf = embedded.farm, real["farms"][0]
    if abs(ef["money"] - rf["money"]) > 1e-6:
        out.append(f"{ctx} money emb={ef['money']} real={rf['money']}")
    if ef["tiles"] != rf["tiles"]:
        # find first differing cell
        for y in range(len(ef["tiles"])):
            for x in range(len(ef["tiles"][0])):
                if ef["tiles"][y][x] != rf["tiles"][y][x]:
                    out.append(f"{ctx} tile[{y}][{x}] emb={ef['tiles'][y][x]} real={rf['tiles'][y][x]}")
                    break
            if out and out[-1].startswith(f"{ctx} tile"):
                break
    if [list(p) for p in ef["farmer"]] if False else list(ef["farmer"]) != list(rf["farmer"]):
        out.append(f"{ctx} farmer emb={ef['farmer']} real={rf['farmer']}")
    if len(ef["hands"]) != len(rf["hands"]) or [list(h) for h in ef["hands"]] != [list(h) for h in rf["hands"]]:
        out.append(f"{ctx} hands emb={ef['hands']} real={rf['hands']}")
    if ef.get("unlocked_quadrants") != rf.get("unlocked_quadrants"):
        out.append(f"{ctx} quads emb={ef.get('unlocked_quadrants')} real={rf.get('unlocked_quadrants')}")
    # private shed + seeds
    ep, rp = embedded.private, real["private_0"]
    esh = {k: v for k, v in ep["shed"].items() if v != 0}
    rsh = {k: v for k, v in rp["shed"].items() if v != 0}
    if esh != rsh:
        out.append(f"{ctx} shed emb={esh} real={rsh}")
    esd = {k: v for k, v in ep["seeds"].items() if v != 0}
    rsd = {k: v for k, v in rp["seeds"].items() if v != 0}
    if esd != rsd:
        out.append(f"{ctx} seeds emb={esd} real={rsd}")
    # market inventory
    if dict(embedded.market["inventory"]) != dict(real["market"]["inventory"]):
        for it in em.PRODUCTS:
            if embedded.market["inventory"][it] != real["market"]["inventory"][it]:
                out.append(f"{ctx} mkt_inv[{it}] emb={embedded.market['inventory'][it]} real={real['market']['inventory'][it]}")
                break
    return out


def run_fidelity(controller_path, seeds, verbose=False):
    ctrl = load_agent(controller_path)
    total_steps = 0
    mismatches = 0
    mism_detail = []
    for sd in seeds:
        env = make("kaggriculture", configuration={"seed": sd}, debug=True)
        env.run([ctrl, "pass"])
        real_seed = env.info.get("seed", sd)
        cfg = env.configuration
        tpd = int(cfg.turnsPerDay); bs = int(cfg.boardSize)
        # snapshots: env.steps[t][0].observation holds obs at time t; state[0].action = action taken at t
        steps = env.steps
        # Rebuild an embedded sim from step t and drive with action_t, compare to t+1.
        for t in range(len(steps) - 1):
            st = steps[t][0]
            obs_t = st["observation"] if isinstance(st, dict) else st.observation
            # action is recorded WITH the resulting state: obs_t + action_{t+1} -> obs_{t+1}
            nst = steps[t + 1][0]
            act_t = nst["action"] if isinstance(nst, dict) else nst.action
            farms_t = obs_t["farms"] if isinstance(obs_t, dict) else obs_t.farms
            if not farms_t:
                continue
            priv_t = (steps[t][0]["observation"]["private"] if isinstance(steps[t][0], dict)
                      else steps[t][0].observation.private)
            market_t = obs_t["market"] if isinstance(obs_t, dict) else obs_t.market
            town_t = obs_t["town"] if isinstance(obs_t, dict) else obs_t.town
            step_t = obs_t["step"] if isinstance(obs_t, dict) else getattr(obs_t, "step", t)

            sim = em.FarmSim(
                farm=copy.deepcopy(farms_t[0]),
                private=copy.deepcopy(priv_t),
                market=copy.deepcopy(market_t),
                town=copy.deepcopy(town_t),
                step=step_t, seed=real_seed,
                board_size=bs, turns_per_day=tpd,
                shed_capacity=int(cfg.shedCapacity),
                weed_chance=float(cfg.weedSpawnChance),
                shop_unlock_interval=int(cfg.townShopUnlockInterval),
                shop_sell_interval=int(cfg.townShopSellInterval),
                center_interval=int(cfg.townCenterSellInterval),
                hire_mult=int(cfg.farmHandCostMult),
                max_orders=int(cfg.maxMarketOrdersPerTurn),
            )
            sim.step_once(act_t if isinstance(act_t, dict) else {})

            nxt = steps[t + 1][0]
            nobs = nxt["observation"] if isinstance(nxt, dict) else nxt.observation
            real_next = {
                "farms": nobs["farms"] if isinstance(nobs, dict) else nobs.farms,
                "private_0": (steps[t + 1][0]["observation"]["private"] if isinstance(steps[t + 1][0], dict)
                             else steps[t + 1][0].observation.private),
                "market": nobs["market"] if isinstance(nobs, dict) else nobs.market,
            }
            total_steps += 1
            d = _diff(sim, real_next, f"seed{sd}.step{step_t}")
            if d:
                mismatches += 1
                if len(mism_detail) < 25:
                    mism_detail.extend(d[:2])
    print(f"FIDELITY: {total_steps} step-transitions checked across {len(seeds)} seeds; "
          f"{mismatches} mismatched ({100.0*mismatches/max(1,total_steps):.3f}%)")
    if mism_detail:
        print("First mismatches:")
        for m in mism_detail[:25]:
            print("  ", m)
    return total_steps, mismatches, mism_detail


if __name__ == "__main__":
    ctrl = sys.argv[1] if len(sys.argv) > 1 else f"{KDIR}/main_LIVESTOCK.py"
    seeds = [int(x) for x in sys.argv[2:]] or [0, 1, 2]
    run_fidelity(ctrl, seeds)
