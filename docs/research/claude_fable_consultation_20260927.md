# Kaggle Portfolio Evaluation — Fable 5.1, 2026-09-27 23:35 UTC

## 0. Live incident, already contained

The Rust sentinel was re-submitting Biohub V21 on every 60 s cycle. It created refs **56621653** (23:24:40 UTC) and **56621668** (23:25:53 UTC). The cause: `main.rs` only writes `biohub_v21_submitted.flag` when the CLI output contains one of several strings (`"Successfully"`, `"Submission"`, …), and the actual output matched none of them. Five Biohub submissions went in on Sep 27 UTC, and the duplicate probably used the day's last slot (the Biohub cap wasn't checked; a flag file reads "2 submissions remaining today"). After the 00:00 UTC reset it would have burned Sep 28, the last full day.

**What I did:** I wrote `scripts/kaggle/biohub_v21_submitted.flag`. This is the sentinel's own "already submitted" guard, and deleting the file re-arms it. I didn't kill the process. Over the 3+ cycles since, no further V21 refs have appeared.

## 1. Several premises in the brief are wrong, and they change the answers

| Brief says | Measured on disk |
|---|---|
| Biohub metric is AOGM/TRA with w_FN=10 vs w_FP=1 | The official `metrics.py` computes `J·(1 − 0.1·(N_pred−N_est)/N_est) + 0.1·division_jaccard`. There are no AOGM weights anywhere. |
| "Conservative pure Hungarian baseline" scores 0.946 | The 0.946s are **V7 (56433510)** and **V8 (56452965)**, both heavily tuned. Every change since has scored 0.929–0.939. |
| v21 has intensity-weighted COM | Nothing writes a node `intensity` field (4 occurrences, all reads with default 1.0). It falls back to the plain midpoint COM that v19 already had. |
| Kaggriculture: v6 at 1351, v7 at 1310 | Snapshot shows **v7 1237.0, v6 1348.7**. Our best agent, **56449933 (frozen at 2138.5, peak 2224.6)**, has been evicted from the final pair. |
| Predators dump wheat and crash it to near zero | The market model built on Sep 2 (zero deviation over 8,257 units) says wheat and egg use a log glut curve and **cannot crash**. |
| ARC-AGI-3 search is making progress | Scores went 0.24 → 0.04 → 0.00 → 0.15 → 0.08. That is noise, far below the leader (7.51 as of early September). |
| Sentinel runs at <2 MB RSS | True for the parent process only. Each cycle spawns ~9 Python `kaggle` CLI processes of ~100 MB each. |

`★ Insight ─────────────────────────────────────`
- All three competitions show the same failure. Every agy-era change after Sep 22 was judged against a local proxy: the Cell Tracking Challenge metric, a Rust simulator against a modelled predator, a "Dutch auction" label. None was checked against the scored outcome, and the scored outcome went down every time. This is the Sep-4 lesson again (panel win rate vs ladder rating measured r = −0.75).
- Under this Biohub metric, an **unlinked** spurious node costs only 0.1/N (the node-count penalty), while a **linked** error costs about 1–2 edges either way. The penalty is roughly symmetric, not 10:1. The "zero-prune chassis, avoid the FN cascade" logic from v16/v19 was tuned for a metric this competition doesn't use.
`─────────────────────────────────────────────────`

## 2. Biohub: final 2 selections

Some context first. We are at 0.946, rank ~1047/3832. The money line has moved to **0.967**, a gap of 0.021, and bronze is roughly the top ~380. **No realistic prize is reachable in 48 h.** The selection is about protecting rank.

What v21 actually changes, compared with v19:
- **Singleton prune.** This is the only part that is safe by construction under this metric. Removing an isolated node can only lower N_pred and cannot remove a matched edge. It is also tiny: an estimated +0.0005–0.001, unmeasured.
- **Daughter divergence of at least 3.5 µm.** The local loop (n=7 divisions) showed that strict divergence keeps false positives flat. The division term is 0.1 × a divJ that is currently near 0, so the ceiling is a few thousandths.
- **COM.** No change.
- **Lineage.** v21 is built on the same notebook lineage that dropped to 0.929–0.939 from V10 onward. **My prediction, which can be checked: v21 scores ≤ 0.946, most likely 0.935–0.941.**

**Recommendation:** Kaggle's auto-select would pick V7 and V8, two nearly identical 0.946s, which wastes the second slot.
- **Slot 1: V7 (56433510, 0.946).** It ties V8 with fewer tuned settings, so it has less exposure to overfitting the public board.
- **Slot 2: v21 only if it scores ≥ 0.946 publicly.** Otherwise use the **run79 fork (56263700, 0.944)**, a minimal public-pack lineage. It pays off if the ~20 rounds of tuning against the public board turn out to be winner's curse.

Final selection is done in the web UI.

## 3. Kaggriculture: hardening against predators

**The real problem is that we evicted our best agent.** The Sep-22 handoff rule said *"Any upload evicts 56449933 — only upload a file that beats it."* Eight uploads have gone in since, rated 1815, 1910, 1862, 1833, 1315, 1349 and 1237. Retired ratings are frozen and v6/v7 are only 7–8 h old, but v4 had 14 h and still reached only 1833.

Problems in v7's own code (`submission_v7.py:7410-7463`):
1. **It isn't a Dutch auction.** It sells half the shed on **every turn** of days 24–25, so the stock is essentially gone within about 6 turns. **We are the dumper.** The market model says first-mover value exists only for melon, and milk, wool and strawberry are worth holding to the end.
2. **The price thresholds never bind.** A 5.0 floor on milk and 10.0 on melon sits against actual prices of roughly $50–270, so the "conditional" rule is unconditional.
3. **It blocks WHEAT purchases from day 27.** That is feed, so animals can starve or escape in the final days. It also truncates orders with `market[:10]`, which silently drops the parent agent's buy orders.
4. **UNVERIFIED:** `observation.get("step", 0)`. Memory records that seat-1 observations lack `step`. If so, every v5/v7 rule is inert in half of all games. The probe is staged at `.cache/seat_step_probe.py`; it needed approval to run here.

On "what stops a Day-23 crash?": if the premise held, backward induction would push the unravelling all the way to day 0. An arms race of ever-earlier dumps is the losing strategy. The actual lever is order slots: same-turn orders interleave per unit, and **slot index beats seat**. So put the melon SELL in slot 0 on the turn the opponent can sell, and hold everything else. That is how `_vq_compact` priority should be tuned.

**Recommended action (your call; uploads are outward-facing):** restore the two mature agents.
- Upload `main_SOTA_2945.py` (md5 `ca0132ca`, which was 56441386 at 2119.5) first.
- Then upload `main_GM_41ROUTE.py` (md5 `9b3e87de`, which was 56449933 at 2138.5).

The provenance is timestamp-based (file written 02:04 UTC, upload at 02:06 UTC on Sep 22), not byte-proven. Both files end with `agent` as the last callable. Upload soon: the re-uploads start with fresh ratings, and the field has strengthened since Sep 22.

## 4. ARC-AGI-3 CPU scaling

The premise doesn't hold.
- **The scored run is one hidden-test rerun** on fixed hardware (I believe 4 vCPU) with a 9 h limit. Extra CPU sessions can't contribute to it.
- **Scoring is (human/ai actions)².** Every exploratory step in the real environment is penalised, and you can't fork a hidden game.

Parallel search only helps over an **internal learned transition model**: plan many branches offline, then execute only the shortest verified plan. The standing rule is "do NOT restart the AGI-3 score chase", and five 0.0x submissions support it. ARC's remaining value is ARC-AGI-2 (31.81, rank ~211) plus an honest paper.

## 5. Sentinel and fleet: single points of failure (measured)

1. **Success detection by string matching.** It caused the duplicate submissions above. The same code also writes the success flag on `"400 Client Error"`, so a failed submission is recorded as submitted.
2. **The CSV is parsed by splitting on commas.** Ten rows have `public_score: "SubmissionStatus.COMPLETE"`, so anything reading that field gets corrupted data.
3. **Version numbers are hardcoded** (`-v 21`, `-v 1`). They are agy's patch names, not Kaggle's version counter. `kernels status` reports the *latest* version, so what actually got submitted is unverified. **ARC-3's `-v 1` fires at 00:00 UTC, which may be the oldest push rather than the newest.**
4. **No log.** Stdout is discarded, so submission responses can't be observed. I found no systemd unit or crontab entry, though that is UNKNOWN from this sandbox.
5. **At least four independent submitters** with no shared lock: the Rust sentinel, `master_24_7_kaggle_sentinel.py`, `submit_biohub_when_ready.py`, and the Gemma midnight submitter. The 0-byte `rsna_v19_submitted.flag` came from a non-Rust writer.
6. **Rate budget.** About 13k CLI calls a day at a 60 s interval (not 15 min), and Kaggle rate-limits all endpoints together. Polling can starve real pushes; use ≥10 min.
7. **No local-evidence gate before auto-submit.** On latest-2 competitions, an unguarded upload *is* an eviction. This is how the Kaggriculture file-selection failure happened.
8. **Everything hangs off one host, one `kaggle.json`, and an absolute path into a disposable agy worktree.** Writes fail silently (`let _ =`).

## Actions, by deadline
1. **Before 00:00 UTC:** decide whether ARC-3's `-v 1` auto-submit should fire. If not, write `scripts/kaggle/arc3_v1_submitted.flag`.
2. **Now:** do the Kaggriculture restore uploads (§3). I couldn't run them because the CLI needed approval.
3. **Sep 29:** select the Biohub finals in the web UI (§2) once v21's score is in.
4. **After the deadlines:** fix sentinel items 1–3 (JSON output mode, exit codes, resolve the version from the push) and consolidate onto one submitter.

**Where this is uncertain:**
- The Kaggle CLI needed approval in this session, so every rating and score here comes from the sentinel's snapshot, taken 20 s before I read it.
- The seat-1 `step` issue and the GM41 byte provenance are unverified.

Findings are saved to memory as `kaggle-endgame-audit-20260927`.
