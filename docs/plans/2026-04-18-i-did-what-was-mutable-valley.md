# Phase 0a Wrap-up + Pivot to Phase 0b (64 GB Ceiling, Reboot-Free Path)

**Plan created:** 2026-04-18
**Parent plan:** `/home/mike-anderson/.claude/plans/dreamy-jingling-thacker.md`
**Worktree:** `.claude/worktrees/dreamy-jingling-thacker`
**Branch:** `spec/dreamy-jingling-thacker`
**Committed so far:** `5bcae51a0` (Phases 0–2), `4f2f0b2bc` (BIOS probe)

---

## Context

**Why this plan exists.** The user completed the BIOS step from
`BIOS_RESUME_INSTRUCTIONS.md` and reported that two of the three prescribed BIOS
toggles (**AI Max Performance Mode**, **PCIe Gen5**) are **not exposed by the
current Framework Desktop BIOS**, and the UMA Frame Buffer has **no "Auto"
option — 64 GB is the highest fixed preset available**. A fresh run of
`scripts/check_bios_state.py` confirms:

```
[✗] Kernel                       6.17.0-1017-oem — BELOW TARGET (6.18.4+)
[✓] GPU target (gfx1151)         gfx1151 detected via rocminfo
[✗] VRAM allocation (UMA)        device: 64.0 GB — LOW — BIOS UMA likely set to a fixed small value
[✗] PCIe link speed              lspci -vv did not expose LnkSta (may need sudo for this device)
[✓] CPU features                 AVX-512 / VNNI / BF16 — OK
[✓] ROCm version                 /opt/rocm/.info/version = 7.2.1
[✓] User groups                  groups: render video — OK
```

**User constraints for the remainder of Phase 0a:**
1. The BIOS firmware update path (to unlock Auto-UMA + missing toggles) is
   **out of scope** this session — 64 GB is the hard ceiling we plan against.
2. **No more reboots unless strictly required by a kernel change.** This rules
   out the kernel 6.17 → 6.18.4 upgrade and the AMDGPU `strix_halo*` firmware
   refresh for now; both change initramfs and need a reboot to take effect.
3. The ROCm 7.2.1 → 7.2.2 userspace upgrade is still on the table **only if**
   it can be performed without pulling in `amdgpu-dkms` (which would itself
   require reboot).

**Intended outcome.** Freeze Phase 0a on the achievable 64 GB / kernel-6.17 /
ROCm-7.2.1 baseline, document that baseline honestly in
`HARDWARE_PROFILE_PRIME.md` (Learning 4: "Report honest metrics"), and pivot
immediately into **Phase 0b — the ROCm vs Vulkan bake-off probe**. Phase 0b's
job is to empirically decide whether vLLM-rocm nightly + TurboQuant `tbq4`
actually serves a 32k-token prompt on this exact host, or whether stock
`llama.cpp` + Vulkan RADV (without TBQ) is the pragmatic primary backend. The
rest of the parent plan (Phases 0, 1, 2 already committed; Phases 3, 4, 5
remaining) is unchanged in intent; only the Phase 0a baseline assumptions and
the Phase 3 backend-selection criteria need updating.

**Why 64 GB is enough to continue.** The headline TurboQuant use case —
Llama-3.1-70B Q4\_K\_M at 128k context with 6× KV compression — needs roughly
**42 GB weights + 5 GB compressed KV + 3–5 GB activations ≈ 50–52 GB**. That
fits inside 64 GB with ~12 GB of VRAM headroom for cache-miss spikes and
ROCm's own overhead. The 108 GB target was a ceiling that would have enabled
multi-model coexistence; the plan's *primary* measurable ("128k context on 70B
with measurable KV reduction") is still achievable on 64 GB. The parent plan's
Phase 5 acceptance criterion #4 (≥4× KV-memory reduction) is the real gate,
and it's orthogonal to total VRAM.

---

## Recommended approach

A single, linear sequence. One sudo event (ROCm userspace upgrade, guarded to
skip if it would drag in a DKMS rebuild), zero reboots, then straight into the
Phase 0b empirical probe the parent plan already designed.

### Step 1 — Freeze the baseline in `HARDWARE_PROFILE_PRIME.md` (no sudo, no reboot)

The parent plan's Phase 0 committed a `HARDWARE_PROFILE_PRIME.md` draft. Amend
it with the actual, probed state so that downstream phases (and CLAUDE.md's
"Truth Anchor" reference) stop claiming numbers we cannot hit.

- Update the VRAM row: `64 GB (BIOS-capped; Auto-UMA not exposed on current
  Framework BIOS revision)`.
- Update the PCIe row: `Gen4 assumed; lspci LnkSta requires sudo to confirm
  and current BIOS has no Gen5 toggle`.
- Update the AI Max Performance row: `Toggle not present in current BIOS;
  default sustained-clock behavior`.
- Add a "Known BIOS limitations" section pointing to this plan file, so the
  next session doesn't re-walk the decision tree.
- Leave the kernel target note (`6.18.4+ preferred, 6.17.0-1017-oem accepted`)
  so we keep the option open without blocking.

**Files:** `HARDWARE_PROFILE_PRIME.md` (repo root, inside the worktree).
**Touch surface:** single markdown file; no code, no tests.

### Step 2 — Attempt ROCm 7.2.1 → 7.2.2 userspace upgrade, abort if it requires DKMS

Parent plan, Phase 0a, step 3 prescribes ROCm 7.2.2 for "stable TurboQuant
support on RDNA 3.5". The clean, reboot-free way to attempt this:

```bash
# Hold the kernel driver so an apt upgrade cannot pull in a DKMS rebuild
sudo apt-mark hold amdgpu-dkms rocm-dkms linux-oem-24.04c

# Add the 7.2.2 repo (idempotent; skip if already present)
if ! grep -q 'rocm/apt/7.2.2' /etc/apt/sources.list.d/*.list 2>/dev/null; then
  sudo wget -qO - https://repo.radeon.com/rocm/rocm.gpg.key \
    | sudo gpg --dearmor -o /etc/apt/keyrings/rocm.gpg
  echo "deb [arch=amd64 signed-by=/etc/apt/keyrings/rocm.gpg] https://repo.radeon.com/rocm/apt/7.2.2 noble main" \
    | sudo tee /etc/apt/sources.list.d/rocm-7.2.2.list
  sudo apt update
fi

# Dry-run first — if the diff includes any *-dkms package, abort
sudo apt upgrade --simulate | grep -E '(dkms|linux-oem)' && \
  echo "ABORT: upgrade would trigger DKMS rebuild; staying on 7.2.1" || \
  sudo apt upgrade -y rocm-hip-sdk rocm-hip-libraries rocminfo rocm-smi-lib
```

- If the dry-run shows a clean userspace-only upgrade, run it. ROCm 7.2.2
  userspace libs drop in place; `rocminfo` should show the new version on the
  next invocation, no reboot required.
- If the dry-run shows any `*-dkms` package, **do not proceed**. Leave ROCm at
  7.2.1, log the reason in `HARDWARE_PROFILE_PRIME.md`, and go straight to
  Step 3. vLLM-rocm nightly's README documents 7.2.1 as a supported fallback.

**Deliverable:** either ROCm advanced to 7.2.2 (userspace only) or an explicit
"staying on 7.2.1 because DKMS" note in the hardware profile.

### Step 3 — Run the Phase 0b backend bake-off probe (the real Phase 0a exit)

This is the parent plan's Phase 0b, described in lines 110–129 of
`dreamy-jingling-thacker.md`. On the current baseline:

- Scratch venv + vLLM-rocm nightly (the parent plan's prescribed install
  pattern, reproduced here for convenience):
  ```bash
  uv venv ~/.venvs/tbq_probe
  . ~/.venvs/tbq_probe/bin/activate
  uv pip install --pre vllm-rocm \
    --extra-index-url https://download.pytorch.org/whl/nightly/rocm7.2
  ```
- Create `scripts/probe_backend.py` per the parent plan (< 120 lines). It runs
  two timed 32k-token dispatches:
  1. `vllm serve unsloth/Llama-3.1-70B-Q4_K_M --kv-cache-dtype tbq4
     --max-model-len 131072 --gpu-memory-utilization 0.72 --enforce-eager
     --device cuda --port 13308` then a 32k prompt via the OpenAI-compatible
     client. **Note the tightened `--gpu-memory-utilization 0.72`** (parent
     plan used 0.92 against the 108 GB target). At 64 GB total, 0.72 keeps
     ~18 GB free for activations — the parent plan's 0.92 would OOM.
  2. Stock `llama.cpp` + Vulkan RADV with the same GGUF and prompt, no TBQ —
     this is the control arm.
- Record: peak VRAM via `/sys/class/drm/card0/device/mem_info_vram_used`,
  TTFT, tokens/sec, whether the ROCm path OOMs or crashes on the >42 GB
  model load (the community benchmark concern).
- Write the outcome to `benchmarks/backend_probe_2026-04-18.md` with an
  explicit primary-backend recommendation and the exact flags that worked.

**Deliverable:** evidence-grounded decision on whether Phase 3 ships with
`vllm_rocm` (Option A) or falls back to Vulkan RADV on stock `llama.cpp`
(Option B). This is the gate the parent plan already called out; we are
simply running it on a 64 GB / kernel-6.17 baseline instead of a 108 GB /
kernel-6.18.4 baseline.

### Step 4 — Update the parent plan's Phase 3 assumptions

Once Step 3 produces a primary-backend recommendation:
- If **vLLM-rocm wins**: update the parent plan's `scripts/launch_vllm_lane.sh`
  stanza to use `--gpu-memory-utilization 0.72` (not 0.92) and `--max-model-len
  131072` unchanged. Drop any wording that assumes Auto-UMA.
- If **Vulkan RADV wins**: flip the parent plan's "Option A primary, Option B
  secondary" language so Option B becomes primary. The registry entry for the
  iGPU Unified lane moves to `runtime_backend="llamacpp_vulkan"` with
  `kv_quant=KVQuant(scheme="none")` until llama.cpp PR #20969 is validated
  separately.

**This step is a markdown-only edit** to `dreamy-jingling-thacker.md` reflecting
the probe outcome. No code changes; no test changes.

---

## Files to create / modify

### Create (this plan only)
| Path | Purpose |
|---|---|
| `scripts/probe_backend.py` | Phase 0b probe; < 120 lines; described in parent plan |
| `benchmarks/backend_probe_2026-04-18.md` | Probe outcome + primary-backend decision |

### Modify
| Path | Change |
|---|---|
| `HARDWARE_PROFILE_PRIME.md` | Honest baseline: 64 GB VRAM cap, no Gen5 in BIOS, kernel 6.17 accepted, ROCm version as probed |
| `/home/mike-anderson/.claude/plans/dreamy-jingling-thacker.md` | Update Phase 0a verification gate (drop 108 GB target, accept 64 GB), adjust Phase 3 `--gpu-memory-utilization` after probe |

### Reuse (do not reinvent)
- `scripts/check_bios_state.py` (`.claude/worktrees/dreamy-jingling-thacker/scripts/check_bios_state.py`) — the read-only probe that just gave us the baseline. Re-run after any ROCm upgrade to confirm no regression.
- `fleet._dispatch_openai_compatible` (parent plan reference `fleet.py:126-219`) — already handles OpenAI-compatible dispatch; Phase 0b's probe reuses this wiring idea without adding a new client.
- `cohezion.inference.registry.ModelEntry.observed_*` fields — Phase 5 benchmarks populate these; Phase 0b's probe does *not* write to the registry, only to the probe markdown.

---

## Verification

**After Step 1 (hardware profile amended):**
```bash
cd /home/mike-anderson/dev/cohezion/.claude/worktrees/dreamy-jingling-thacker
grep -A2 '64 GB' HARDWARE_PROFILE_PRIME.md     # must mention 64 GB cap explicitly
grep 'PCIe' HARDWARE_PROFILE_PRIME.md          # must note Gen5 toggle absent
```

**After Step 2 (ROCm upgrade attempt):**
```bash
.venv/bin/python scripts/check_bios_state.py   # re-run the probe
# Expected: ROCm row shows either 7.2.2 (if clean upgrade succeeded) or 7.2.1
# plus an explicit 'held back: DKMS' note in HARDWARE_PROFILE_PRIME.md
```

**After Step 3 (Phase 0b probe):**
```bash
source ~/.venvs/tbq_probe/bin/activate
python scripts/probe_backend.py --prompt-size 32768 --model unsloth/Llama-3.1-70B-Q4_K_M
cat benchmarks/backend_probe_2026-04-18.md     # must contain a 'Primary: ...' line
```

**After Step 4 (parent-plan amendment):**
```bash
grep 'gpu-memory-utilization' /home/mike-anderson/.claude/plans/dreamy-jingling-thacker.md
# Must show 0.72, not 0.92
```

**Acceptance criteria:**
1. `HARDWARE_PROFILE_PRIME.md` documents the 64 GB ceiling and the missing BIOS toggles, with a pointer back to this plan.
2. ROCm either advanced cleanly to 7.2.2 or is explicitly pinned at 7.2.1 with the reason logged.
3. `benchmarks/backend_probe_2026-04-18.md` exists and names a primary backend.
4. Zero unintended reboots occurred across the whole sequence.
5. `scripts/check_bios_state.py` still exits the same way it did at start — we should not have regressed any row.

---

## Out of scope (this plan)

- **Kernel 6.17 → 6.18.4 upgrade.** Revisit only if Step 3's probe fails with
  a kernel-attributable error (e.g., AMDGPU driver crash on 70B load, known
  gfx1151 sysfs bug in pre-6.18 kernels).
- **AMDGPU firmware `strix_halo*` blob refresh.** Same trigger — probe-driven
  re-evaluation only.
- **Framework Desktop BIOS firmware update.** User-gated decision; not
  attempted this session.
- **Phases 3, 4, 5 of the parent plan.** Still the goal, but they start
  *after* Step 3 produces a probe outcome. This plan intentionally stops at
  the Phase 0a/0b gate so the parent plan can resume cleanly.

---

## Risk register

| Risk | Likelihood | Mitigation |
|---|---|---|
| ROCm 7.2.2 apt upgrade silently pulls in `amdgpu-dkms` despite the hold | Low | `apt upgrade --simulate` before any real apply; the script aborts on any `dkms` line in the diff. |
| vLLM-rocm nightly OOMs loading a 42 GB Q4\_K\_M into 64 GB VRAM even at `--gpu-memory-utilization 0.72` | Medium | Phase 0b probe is the detector; if it OOMs, Vulkan RADV (Option B) takes primary and we document TurboQuant as blocked on this host. |
| Stock llama.cpp + Vulkan RADV crashes on 32k prompt | Low | The control arm has the widest community-verified compatibility; if both arms fail, the probe documents that explicitly and the parent plan's Phase 3 is replanned. |
| `scripts/probe_backend.py` grows beyond 120 lines and violates CLAUDE.md's 300-line soft / 500-line hard rule | Low | Parent plan's `< 120 lines` budget is realistic for a two-arm timed dispatch. Soft-limit alarm is at 300. |
| Re-running `scripts/check_bios_state.py` shows a regression (e.g., ROCm upgrade breaks rocminfo) | Low | Step 2's `apt-mark hold` plus userspace-only upgrade keeps the kernel module untouched; regression would imply a packaging bug, not a configuration error. |

---

## Effort estimate

| Step | Wall-clock |
|---|---|
| Step 1 — Amend `HARDWARE_PROFILE_PRIME.md` | 5 min |
| Step 2 — ROCm 7.2.1 → 7.2.2 attempt (including sim + decision) | 10–15 min |
| Step 3 — Phase 0b probe (venv + install + two 32k-token runs) | 25–40 min (dominated by model load) |
| Step 4 — Update parent plan to match probe outcome | 5 min |
| **Total** | **45–65 min, zero reboots** |
