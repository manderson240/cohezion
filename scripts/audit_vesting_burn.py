#!/usr/bin/env python3
import urllib.request, json
from pathlib import Path

base_dir = Path("/home/mike-anderson/.gemini/antigravity-cli/brain/9d0f94a0-a1ab-464c-92ab-9bab8612583a/scratch/1win-token-solana-programs")
vesting_claim = (base_dir / "programs/vesting/src/instructions/claim.rs").read_text()
vesting_close = (base_dir / "programs/vesting/src/instructions/close.rs").read_text()
vesting_create = (base_dir / "programs/vesting/src/instructions/create.rs").read_text()
vesting_math = (base_dir / "programs/vesting/src/math.rs").read_text()
burn_burn = (base_dir / "programs/burn/src/instructions/burn.rs").read_text()
burn_period = (base_dir / "programs/burn/src/period.rs").read_text()

prompt = f"""You are a Principal Solana Security Researcher conducting a zero-day audit on 1win Solana programs.
Analyze the source code of Vesting and Burn:

--- VESTING: claim.rs ---
{vesting_claim[:2000]}

--- VESTING: close.rs ---
{vesting_close[:2000]}

--- VESTING: math.rs ---
{vesting_math[:2000]}

--- BURN: burn.rs ---
{burn_burn[:2000]}

--- BURN: period.rs ---
{burn_period[:1500]}

Audit for:
1. Schedule and vesting math edge cases: Does `vested()` truncate monthly tranches in a way that allows early excess claims, or does it leave tokens locked?
2. Activity ID indexing: In `create_vesting`, seeds = [b"vesting", config.activity_count.to_le_bytes().as_ref()]. When an activity is cancelled (`cancel_vesting`), does `activity_count` decrement? If not, does cancelling leave an unrecoverable gap or allow re-creation collision?
3. In `burn.rs`, period calculation `now / SECONDS_PER_WEEK`: Is there any period index drift or race condition on Sunday/Thursday rollover?
4. In `close_vesting`, what happens if `claimed >= reference_amount` is satisfied but unvested tokens were withdrawn?

Report any confirmed, high-signal security vulnerabilities.
"""

data = {"model": "deepseek-v4.1-flash:cloud", "prompt": prompt, "stream": True}
req = urllib.request.Request("http://localhost:11434/api/generate", data=json.dumps(data).encode(), headers={"Content-Type": "application/json"})

with urllib.request.urlopen(req, timeout=120) as r:
    for line in r:
        if line:
            chunk = json.loads(line.decode())
            if chunk.get("response"):
                print(chunk["response"], end="", flush=True)
print()
