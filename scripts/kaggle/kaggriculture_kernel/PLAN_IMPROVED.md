# Kaggriculture — Improved Agent Plan & Gap Analysis

**Status:** improved agent written + locally validated. **Nothing pushed/submitted.**
Competition `kaggriculture` is ACTIVE (deadline 2026-09-30, $50K, we `userHasEntered=True`).
(NB: the portfolio memory note calling Kaggriculture "closed/archived" is WRONG — verified live.)

## 1. What the competition actually is (quoted from the kit)

Turn-based **2-player farming economy**, 30 days × 24 turns = **720 turns**. "The winner is
determined by who has the most money in the bank at the end." Agent contract (AGENTS.md):

```py
def agent(obs) -> {"farmer": [op, ...], "hands": [[op,...],...], "market": [[op,...],...]}
```
`obs` = `{player, step, day, hour, farms[], private{shed,seeds,inventories}, market, town}`;
`farms[i]` = `{money, tiles[y][x], farmer:[x,y], hands:[[x,y]...], unlocked_quadrants, hires_today}`.

**Scoring is NOT coins** — it is a Bradley-Terry **skill rating** from win/loss/tie only:
"The actual coin difference in a match does not affect the rating change—only the win, loss,
or tie outcome matters." So `194.5` vs leader `~2970` is an Elo-like rating, not a coin count.

## 2. Why our score was 194.5 (rank ~6363/6669)

The existing `submission.py` is **non-functional**: it reads `obs.soil_moisture` (a field that
does not exist; `obs` is a dict, not an object) and returns a **bare int**, but the engine
expects an action **dict**. Confirmed locally: that agent stays at the $3000 starting bank and
**loses to every functional opponent**, including the built-in `pass` and `starter`. The
`main.py` in this folder writes a CSV — irrelevant to a simulation competition. The 194.5 is
simply the ladder floor for a bot that never earns.

## 3. Gap analysis — what the leaders (~2970) actually do

Read the top public writeup (`raykkretzschmar/kaggriculture-findings-from-zero-to-top-meta`,
107 votes) and top kernels (boatlee `V16-RC5 8C/4S`, denizeryilmaz `V111 8C4S Economic Core`).
The 14× gap is **NOT a different ML technique** — it is:

1. **A livestock-heavy economy.** Mature farm = **~8 cows / 5-6 sheep / ~5 strawberry / some
   wheat, 12 hands, 3 quadrants (NE+SW)**. Cows(milk 160)/sheep(wool 200) produce *indefinitely*
   once fed → compounding income that dwarfs one-time crops.
2. **Distilled 720-turn "replay tapes."** The elite candidate embedded in the findings notebook
   is a **base64+zlib-compressed hard-coded full-game schedule** ("C92"), produced by weeks of
   downloading leader replays, distilling the repeated field+market moves, and gating them in
   local tournaments. Plus a **clone-aware one-turn market front-run** (sell your premium line one
   turn before the mirror opponent dumps) and a terminal cleanup routine.

The top of the board is an engineering artifact of replay-distillation + live-ladder tuning, not
a clever generalizable heuristic.

## 4. The improved agent (`main_IMPROVED.py`) — what changed and why

A **grounded, robust, parallel near-shed carrot economy** (deliberately lean, not the elite tape):

- Correct contract: real `agent(obs)` returning the `farmer/hands/market` dict; try/except → PASS
  so a bad observation never errors the validation episode.
- Each unit is assigned a **fixed home tile hugging the shed** and runs the proven carrot
  loop (plant → water in window → harvest at age 3 → auto-drop to shed → sell next morning).
- **Lean by measurement:** units reset to the shed daily and hands re-spawn there, so FAR tiles
  waste walking turns that dominate thin crop margins. A scaled version (more hands + NE/SW land +
  far tiles) **lost head-to-head to the lean version 0-6** and even dropped games to `starter`.
  So: ≤5 hands, compact NW tiles, **no land**, $150 cash floor (never spend below the do-nothing
  baseline).

### Local validation (kaggle-environments, episodeSteps=720)
| Matchup | Result |
|---|---|
| vs `starter` (competent single-tile carrot baseline) | **20-0** across both seats, min bank 4304 vs ~3300 |
| vs `random` | 4-0 |
| vs `pass` | 3-0 |
| self-play (the submission Validation Episode) | 3 ties, **0 errors** |

Expected delta: our current bot **loses to `starter`**; this one **beats `starter`-class
opponents decisively and never loses money or errors** → a large rank jump off the ~6363 floor.

## 5. Honest verdict: is ~2968 reachable?

**No — not in this scope, not with a clean heuristic.** The ~2970 tier is distilled hard-coded
replay tapes + a tuned 8c/5s livestock economy, refined over weeks against the live ladder with
replay downloads and local tournaments. This deliverable is the **honest high-ROI move**: convert
a broken, bottom-of-ladder bot into one that reliably beats the competent baseline.

### Next steps (in priority order, each needs live-ladder iteration)
1. **Add a small cow/sheep ranch.** Dedicate a few near-shed tiles to pastures; buy cow → PICKUP
   from shed → PLACE on pasture → FEED daily (needs WHEAT in the feeding unit's inventory, so
   grow/BUY_PRODUCT wheat) → HARVEST milk → sell. Milk (160) / wool (200) are the highest-value
   ongoing yields and compound. **Risk:** an unfed animal escapes (−400) — validate feeding
   coverage locally before trusting it. This is the single biggest score lever.
2. **Clone-aware market front-run** for mirror matches (sell premium one turn early).
3. **Terminal liquidation** in the last 1-2 days (bank unsold inventory).
4. Only after 1-3 pay off locally: consider land expansion + more hands with a movement plan that
   keeps walking overhead bounded.

## 6. Submission mechanics (for when a human decides to submit — NOT done here)
- Single file: `main.py` at root with `agent(obs)`. `kaggle competitions submit kaggriculture -f main.py -m "..."`.
- Up to 5 submissions/day; only the latest 2 are tracked and count for the final Bradley-Terry tournament.
- To submit this agent, a human renames `main_IMPROVED.py` → `main.py` (or bundles it) and submits.
