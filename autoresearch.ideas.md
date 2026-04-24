# Autoresearch Ideas & Active Paths

**Status (Apr 23, 2026)**: Product brief complete. Competitions active. Prioritizing by deadline and EV/hour.

---

## Priority 1: Gemma Hackathon ($200K, May 18 — 25 days) ✅ Kernel Running

**Status**: Kernel v6 pushed and completed on Kaggle. Results generated:
- Phase 1: 90.8% effectiveness, 75% alignment (5 scenarios, 6 actions)
- Phase 2: 0.77→0.92 effectiveness (+15%), 0.617→0.745 alignment (+12.8%) over 8 episodes
- Mode: CPU_Simulation (no GPU on Kaggle free tier)
- Refined skills with 4 self-improvement events

**Completed**: Kernel, writeup, video script, blog post, demo, dashboard
**Remaining for submission**:
- [ ] Record 60-sec demo video (screen capture + voiceover)
- [ ] Create cover image (1280×720: hurricane + hospital + radio + Gemma logo)
- [ ] Final review of kernel output for correctness
- [ ] Submit via Kaggle competition page

**Action**: Next human session should record video + create cover. Code is ready.

## Priority 2: Nemotron Reasoning Challenge ($106K, June 15) — 0.49 ON LEADERBOARD

**Leaderboard score**: 0.49 (49%) from March 26 LoRA submission. Pure symbolic v29 pushed but CSV submissions error out.
**Training accuracy**: 64.9% (numeral 100%, encryption 98.7%, gravity 80.1%, unit_conversion 78.6%, bit_manip 31.1%, equations 0%)
**Equations analysis**: 1555 problems, ALL per-puzzle rule induction. No same-length character mappings exist — character substitution doesn't transfer (0.1%). Numeric rule induction captures 4.2% of numeric subset. This puzzle type requires LLM-scale reasoning from 3-5 examples. Given leaderboard top at 87%, top teams likely use large models.
**Submission format issue**: Kaggle API returns 400 for CSV uploads. The v20 (0.49) was a model submission format. The current solver needs to be submitted through the Kaggle web UI as a kernel-based entry.

**Highest ROI next step**: Get the kernel scored properly on the hidden test set. The 3-row output from our kernel is just the public sample — Kaggle should score it on the hidden set automatically. If that works, we're at ~50-65%. Then try Kag GPU for equations.

### Remaining Nemotron Ideas (Pruned by ROI)
1. ✅ PUSH 67.5% TO KAGGLE — DONE (v29 pushed, v28 on leaderboard, but ERROR on CSV submission, need code competition approach)
2. **Equations: Per-puzzle rule induction** — 1555 problems, ALL character-based rule induction, not math. Per-puzzle consistent rules solve 4.2% of numeric subset. The remaining 60%+ are multi-digit transformations (concat+transform, digit manipulation). The encryption solver could handle the character-only subset if extended.
3. **Bit-manip: exhaustive nonlinear compositions** — potential +2-3% (currently 31.1%)
4. ~~Unit_conversion: RANSAC/Theil-Sen~~ — PRUNED
5. ~~Gravity: outlier rejection~~ — PRUNED
6. ~~Encryption: context disambiguation~~ — PRUNED
7. ~~Cloud model fallback~~ — PRUNED

### Key Issue: Kaggle Submission Format
- Competition requires code submission via kernel, not CSV upload
- Both v28 and our direct CSV submissions errored
- Need to figure out the correct submission method (likely via Kaggle web UI)

## Priority 3: ARC Prize Paper Track ($450K, Nov 9)

**Current**: Draft v2 complete (3.4% solve rate on ARC-AGI-2). Paper written.
**Action**: Improve solve rate before submission deadline. Aligns with product brief's "published research" success criterion.

## Priority 4: Wiring Completeness Audit

**Goal from product brief**: Zero orphan modules across 1,068 source files.
**Current**: 56.4% wired (602/1068), 43.6% orphan (466/1068).
**Method**: Text-based import scanning (crude — many orphans may be transitively connected).

**Orphan categories (first 30)**:
- Agent modules: adk_swarm/aimo_specialists, generated agents, specialists (ollama, platform_coordinator)
- API modules: routes (agui, fleet), services (brand), main, fail_hook
- CLI, audio, benchmarks, cache, cli, deployment, gateway, models, reporting, sandboxing, storage, tools, validation, vibe, worldviews

**Next**: A more precise audit using import graph tracing (module is truly orphan only if no import chain reaches it from any entry point). The text-based scan overcounts orphans by flagging modules that import wiring systems indirectly.

---

## Pruned / Achieved / Abandoned
- ✅ Encryption dictionary + ambiguous tie-breaking (+8pp overall)
- ✅ XOR-linear GF(2) for bit_manip (+2pp overall)
- ✅ Removed partial mapping fallback (prevents wrong answers)
- ✅ Gravity grid search (+4pp)
- ✅ Gravity precision fix (+0.48pp)
- ✅ Partial bit-manip mapping (+1.4pp)
- ❌ Cloud model for equations (too slow locally, needs Kaggle GPU)
- ❌ Unit conversion non-linear models (REGRESSION — not worth it at +0.5pp)
- ❌ Operator-filtered equations (REGRESSION — not worth it)
- ❌ RANSAC/Theil-Sen for unit_conversion (marginal +0.5-1%, not worth engineering time)
- ❌ Gravity outlier rejection (marginal +0.5-1%, not worth engineering time)
- ❌ Encryption context disambiguation (marginal +0.2%, not worth engineering time)

## Competition Portfolio Summary
| Prize Track | Deadline | EV | Current Status | Next Action |
|---|---|---|---|---|
| Gemma Hackathon | May 18 (25d) | $1,321 | 57% ready | Finish submission |
| Nemotron | June 15 (53d) | ~$3K at 67.5% | Pure symbolic ready | Push to Kaggle, then iterate |
| ARC Paper Track | Nov 9 (190d) | $3,317 | 3.4% solve rate, draft v2 | Improve solve rate |
| SEI Accelathon | TBD | $350 | Not started | Assess when deadline announced |

---

## Session Summary (Apr 23, 2026)

### Nemotron Findings
- **Training accuracy**: 64.9% (not 67.5% as previously claimed — the 67.5% figure was from an older solver version)
- **Equations (0%)**: ALL 1555 are per-puzzle rule induction, not math. Character-level mapping doesn't transfer (0.1%). Numeric rule induction gets 4.2%. Requires LLM inference.
- **Bit_manip (31.1%)**: XOR2/XOR3/MAJ3 patterns add 0 additional solves. Remaining 68.9% need LLM-scale reasoning.
- **Kaggle submission**: API returns 400 for code competitions. Need to submit via Kaggle web UI or fix submission format.
- **Verdict**: Nemotron is at a local maximum for symbolic solving. Further progress requires LLM inference on GPU.

### Gemma Findings
- **Kernel v6**: Complete and running on Kaggle (90.8% effectiveness, +15% skill improvement)
- **Needs**: Video + cover image for submission (human action required)

### Pruned Ideas
- ~~Bit_manip XOR/NL compositions~~ — 0 additional solves from exhaustive simple patterns
- ~~Equations character mapping~~ — 0.1% accuracy, fundamentally different from encryption
- ~~Equations numeric rule induction~~ — 4.2%, not viable for significant improvement
- ~~RANSAC for unit_conversion~~ — marginal, pruned
- ~~Gravity outlier rejection~~ — marginal, pruned
- ~~Encryption context disambiguation~~ — marginal, pruned
