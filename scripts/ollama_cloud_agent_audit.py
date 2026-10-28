#!/usr/bin/env python3
"""Stateless Ollama Cloud Agent Swarm for Solana Smart Contract Auditing.

Dispatches specialized stateless Ollama Cloud models as agents:
- Agent 1: Deep Reasoning & Economic Invariants Agent (deepseek-v4-pro:cloud)
- Agent 2: Solana Anchor Security & Exploit Specialist (kimi-k2.7-code:cloud)
- Agent 3: System Architecture & PoC Synthesis Agent (glm-5.3:cloud)
"""

import json
import os
import sys
import time
import urllib.request
from pathlib import Path

OLLAMA_URL = "http://localhost:11434/api/generate"

def query_agent(model: str, role: str, prompt: str, timeout: int = 180) -> str:
    print(f"\n[>>>] Invoking Stateless Cloud Agent: {role} ({model})...")
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "top_p": 0.9,
            "num_predict": 4096,
        }
    }
    req = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            res_json = json.loads(response.read().decode("utf-8"))
            elapsed = time.time() - t0
            output = res_json.get("response", "").strip()
            print(f"[<<<] {role} responded in {elapsed:.2f}s ({len(output)} chars).")
            return output
    except Exception as e:
        print(f"[!] Error querying {model}: {e}", file=sys.stderr)
        return f"ERROR: {e}"

def read_file_safe(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""

def main():
    base_dir = Path("/home/mike-anderson/.gemini/antigravity-cli/brain/9d0f94a0-a1ab-464c-92ab-9bab8612583a/scratch/1win-token-solana-programs")
    sale_activate_claim = read_file_safe(base_dir / "programs/sale/src/instructions/activate_claim.rs")
    sale_purchase = read_file_safe(base_dir / "programs/sale/src/instructions/purchase.rs")
    sale_claim = read_file_safe(base_dir / "programs/sale/src/instructions/claim.rs")
    sale_refund = read_file_safe(base_dir / "programs/sale/src/instructions/refund.rs")
    sale_math = read_file_safe(base_dir / "programs/sale/src/math.rs")
    vesting_claim = read_file_safe(base_dir / "programs/vesting/src/instructions/claim.rs")
    vesting_withdrawal = read_file_safe(base_dir / "programs/vesting/src/instructions/withdrawal.rs")
    burn_burn = read_file_safe(base_dir / "programs/burn/src/instructions/burn.rs")

    # Step 1: Agent 1 (deepseek-v4-pro:cloud) - Economic & Invariant Analysis
    prompt_agent1 = f"""You are the Deep Reasoning & Economic Invariants Security Agent for Solana smart contracts.
Analyze the following source code from 1win Token Solana Programs (specifically `sale/activate_claim.rs`, `sale/purchase.rs`, `sale/claim.rs`, `sale/refund.rs`, and `sale/math.rs`).

Focus on:
1. Invariant breakdowns: Does `participants` increment without decrement? In `init_aggregate`, `state.participants` is incremented, but what happens if `aggregate` is initialized with 0 deposits, or if deposits are refunded?
2. In `activate_claim.rs`:
   ```rust
   let proceeds = soft_cap_usdc(emission, price_usdc, TOKEN_UNITS)?.saturating_sub(participants);
   let refund = pool.checked_sub(proceeds).ok_or(SaleError::MathOverflow)?;
   ```
   What is the consequence if a malicious user creates 1,000,000 empty aggregates? Does this artificially inflate `participants`, reducing `proceeds` and locking tokens/funds in `refund_vault`?
3. Rounding errors, oversubscription math, and edge cases in `allocate()` when net_usdc_contributed is tiny or huge.
4. Account closure vulnerabilities: `claim` closes `aggregate = wallet`. Can a closed aggregate be re-initialized?

Code context:
--- sale/activate_claim.rs ---
{sale_activate_claim[:4000]}

--- sale/purchase.rs ---
{sale_purchase[:4000]}

--- sale/math.rs ---
{sale_math[:4000]}

Provide a precise, rigorous vulnerability analysis with Severity, Impact, Root Cause, and Attack Scenario.
"""

    report_agent1 = query_agent("deepseek-v4-pro:cloud", "Invariants & Economic Threat Modeler", prompt_agent1)

    # Step 2: Agent 2 (kimi-k2.7-code:cloud) - Solana Anchor Implementation & Vulnerability Specialist
    prompt_agent2 = f"""You are the Solana Anchor Security & Exploit Specialist Agent.
Review the Solana Anchor program files for 1win:
- `programs/sale/src/instructions/claim.rs`
- `programs/sale/src/instructions/refund.rs`
- `programs/vesting/src/instructions/claim.rs`
- `programs/vesting/src/instructions/withdrawal.rs`
- `programs/burn/src/instructions/burn.rs`

Audit these specific attack vectors:
1. Reentrancy / Account reuse / Initialization replay: Does closing `aggregate` in `claim.rs` allow a user to re-initialize an aggregate or trick instructions if not guarded?
2. Missing signer or authority checks in vesting withdrawal or recipient management.
3. Burn program: Daily/weekly quota bypass or period calculation flaws.
4. CPI token transfer verification: Are account mints, owners, and bumps strictly checked?

Code context:
--- sale/claim.rs ---
{sale_claim[:4000]}

--- sale/refund.rs ---
{sale_refund[:4000]}

--- vesting/claim.rs ---
{vesting_claim[:4000]}

--- vesting/withdrawal.rs ---
{vesting_withdrawal[:4000]}

--- burn/burn.rs ---
{burn_burn[:4000]}

Deliver high-impact findings with exact line references, exploit mechanics, and severity ranking.
"""

    report_agent2 = query_agent("kimi-k2.7-code:cloud", "Solana Anchor Exploit Specialist", prompt_agent2)

    # Step 3: Agent 3 (glm-5.3:cloud) - System Architect & PoC Validator
    prompt_agent3 = f"""You are the System Architect & PoC Synthesis Agent.
You have the analyses from two specialized agents:
[Agent 1: Invariants & Economic Threat Modeler (deepseek-v4-pro:cloud)]:
{report_agent1}

[Agent 2: Solana Anchor Security Specialist (kimi-k2.7-code:cloud)]:
{report_agent2}

Synthesize these findings into:
1. Executive Summary of confirmed vulnerabilities.
2. The #1 Critical/High Vulnerability suitable for submission to HackerOne (with estimated reward under 1win's $1,000–$10,000 scale).
3. Step-by-step Reproduction Steps / Exploit Proof-of-Concept logic.
4. Exact Remediation Diff in Rust.
"""

    report_agent3 = query_agent("glm-5.3:cloud", "System Architect & PoC Validator", prompt_agent3)

    output_path = Path("/home/mike-anderson/.gemini/antigravity-cli/brain/9d0f94a0-a1ab-464c-92ab-9bab8612583a/stateless_ollama_cloud_audit_report.md")
    full_report = f"""# Stateless Ollama Cloud Multi-Agent Audit: 1win Solana Smart Contracts

## Agent Swarm Roster
- **Agent 1 (Invariants & Economic Threat Modeler)**: `deepseek-v4-pro:cloud` (1.65T)
- **Agent 2 (Solana Anchor Exploit Specialist)**: `kimi-k2.7-code:cloud` (1.04T)
- **Agent 3 (System Architect & PoC Validator)**: `glm-5.3:cloud` (753B)

---

## 1. Findings from Agent 1 (`deepseek-v4-pro:cloud`)
{report_agent1}

---

## 2. Findings from Agent 2 (`kimi-k2.7-code:cloud`)
{report_agent2}

---

## 3. Synthesis & Proof-of-Concept from Agent 3 (`glm-5.3:cloud`)
{report_agent3}
"""
    output_path.write_text(full_report, encoding="utf-8")
    print(f"\n[+] Full multi-agent audit saved to: {output_path}")

if __name__ == "__main__":
    main()
