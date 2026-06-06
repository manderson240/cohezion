---
title: "LANE_WATTS / LAMBDA_ENERGY calibration — honest measurement status"
created: 2026-06-06
owner: "/loop self-improvement (item 3)"
verdict: "instrument added + real SoC anchor captured; absolute per-lane calibration is CONFOUNDED on a unified APU — flagged for an isolated-lane measurement run (item 17). LANE_WATTS unchanged (no fabrication)."
---

# Power calibration — what is and isn't measurable

## The ask (item 3)
Calibrate `model_registry._LANE_WATTS` (npu 2 / igpu 35 / cpu 55) and
`fractal_metrics.LAMBDA_ENERGY` (0.01) against **measured** tokens-per-watt.

## What was found (measurement integrity first)
Real power instrumentation on this Strix Halo box:

| Source | Reads | Real? | Scope |
|---|---|---|---|
| amdgpu `power1_average` (hwmon9) | instantaneous µW → W | ✅ **18–26 W observed** (varies with load) | **whole SoC** |
| RAPL `intel-rapl:0` (`package-0`/`core`) | cumulative `energy_uj` | ✅ (needs ΔE/Δt) | CPU package |
| XDNA2 NPU | — | ❌ not instrumented | — |
| `amd-smi` / `rocm-smi` | — | ❌ not on PATH | — |

**The confound:** on a *unified* APU the CPU, RDNA3.5 iGPU, and Infinity Fabric share one
power rail; amdgpu `power1_average` reports the **total SoC**, RAPL reports the **CPU
package** (overlapping the same silicon), and the **NPU is in neither domain**. There is no
sysfs node that attributes power to a single lane. So a *measured per-lane* joules-per-token
**cannot be produced** from passive counters — it would be a fabricated split.

## What was delivered (honest, additive)
- `hardware_monitor.read_soc_power_w()` — a **real** SoC-power read (amdgpu `power1_average`),
  fail-soft `None`, never a fabricated default. Captured anchor this session: **26.08 W**.
- `hardware_monitor.joules_per_token(power_w, tokens, duration_s)` — the pure energy/token math.
- 5 discriminating tests (energy=P·t not P; zero-tokens→inf; real-or-None; fail-soft).

## What was NOT changed (and why)
`_LANE_WATTS` is **left unchanged**. Its values are defensible *physical priors*
(FastFlowLM NPU <2 W; RDNA3.5 iGPU mid-tens of W; CPU all-core ~50 W) and — critically —
the **only load-bearing property is the ORDERING** `NPU < iGPU < CPU`, because watts are a
*tiebreak* among equal-priority candidates and never override a better-fit model
(`model_registry._rank`). The ordering is preserved; fabricating "calibrated" absolute
numbers would add false precision without changing any routing decision.

`LAMBDA_ENERGY=0.01` likewise stays (CC2 holds: the energy term defaults to 0, so
`feynman_path_weight(0.5,0.0)` is byte-identical and local-beats-cloud is intact).

## The real experiment that WOULD calibrate (→ new item 17)
A **single-lane-isolated ΔP run**: with all other lanes idle, read SoC power baseline, run
sustained inference on ONE lane, sample `read_soc_power_w()`, compute
`ΔP = P_load − P_idle` and `joules_per_token(ΔP, tokens, duration)`. Repeat per lane (NPU via
FastFlowLM's own <2 W telemetry, since it's not in amdgpu/RAPL). Requires all lanes up + a
controlled harness — a measurement session, not a passive read. Until then the priors stand.

## Falsifiable-check outcome
- `test_quality_beats_electricity` — **green** (LANE_WATTS unchanged).
- energy ordering NPU<iGPU<CPU — **preserved** (unchanged priors).
- CC2 harness check — **green** (LAMBDA_ENERGY unchanged, energy term defaults to 0).
The check came back *informative*, not faked: the attempt to measure surfaced a real
hardware confound, which is the honest negative result.

## Item 17 update (2026-06-06): ΔP harness built; live 3-lane run UNPROVEN
The controlled-load ΔP harness core is in place: `hardware_monitor.marginal_power_w(idle, load)`
returns `mean(load) − mean(idle)` (None-safe, no fabricated delta from insufficient data). With
every OTHER lane idle, this isolates a single lane's marginal SoC draw — the isolable measurement
the confounded absolute split (item 3) lacked. 4 discriminating tests prove it separates a light
lane from a heavy one.

**Live run NOT executed (honest UNPROVEN).** Fleet probe this tick: router :13305 UP, iGPU :13307
UP, but **NPU :13306 and CPU :13309 are DOWN**. The NPU<iGPU<CPU separation needs all three lanes
up; with two down it cannot be measured. Running a sustained iGPU load to grab the one available
lane would also perturb the live Hermes bot (shares Granite on the router) — not worth it for 1/3
of the data. So `_LANE_WATTS` stays at its physical priors (ordering intact, CC2 green). The
per-lane recalibration is an OPERATIONAL task for a maintenance window with all lanes up + Hermes
paused — the harness is ready; only the live data is pending.
