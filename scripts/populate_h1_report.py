#!/usr/bin/env python3
import urllib.request, json, asyncio
import websockets

title = "Unit Mismatch in activate_claim: Participant Count Subtracted from Micro-USDC Proceeds"

vuln_info = """## Summary
In the 1win Solana Token Sale program (`GWvQinGBRa7ZUzhXY23MrLjdsx3KfRGxH8yXURBwrz1R`), there is an accounting unit mismatch in `activate_claim.rs` where the participant count is directly subtracted from `soft_cap_usdc`:

```rust
let (proceeds, refund) = if oversubscribed {
    let proceeds =
        soft_cap_usdc(emission, price_usdc, TOKEN_UNITS)?.saturating_sub(participants);
    let refund = pool.checked_sub(proceeds).ok_or(SaleError::MathOverflow)?;
    (proceeds, refund)
} else {
    (pool, 0)
};
```

Simultaneously, `init_aggregate` in `purchase.rs` is permissionless and allows any curve keypair to initialize a `WalletAggregate` without depositing any funds, unconditionally incrementing `state.participants += 1`:

```rust
pub fn init_aggregate(ctx: Context<InitAggregate>) -> Result<()> {
    ...
    state.participants = state
        .participants
        .checked_add(1)
        .ok_or(SaleError::MathOverflow)?;
    ...
}
```

## Technical Analysis & Unit Mismatch
1. `participants` is an integer count of initialized aggregate accounts.
2. `soft_cap_usdc` is denominated in atomic micro-USDC (6 decimals, $0.000001).
3. The codebase comments indicate the author assumed rounding in `claim()` could cost up to 1 minimal unit per participant:
   `// Rounding at claim time can cost up to 1 minimal USDC unit per participant - we subtract participants as headroom and keep it in refund_vault.`
4. However, in `programs/sale/src/math.rs` (`allocate()`), the spent amount is already rounded UP via `ceil_bias = token_units - 1`:
   ```rust
   let spent_wide = u128::from(tokens)
       .checked_mul(u128::from(price_usdc))?
       .checked_add(ceil_bias)?
       .checked_div(u128::from(token_units))?;
   let spent = u64::try_from(spent_wide)?;
   let refund = net.saturating_sub(spent);
   ```
   Because `spent` is rounded up, `refund` is rounded DOWN, strictly favoring protocol solvency. Real claim refunds can never exceed `pool - soft_cap`.
5. Consequently, subtracting `participants` from `soft_cap_usdc` transfers extra micro-USDC into `refund_vault` that honest claimants will never claim, permanently stranding those funds in `refund_vault` until `ClaimClosed`.

## Proof of Concept
We verified this deterministically in the program test suite (`programs/sale/src/math/tests.rs`):
```rust
#[test]
fn exploit_sybil_participants_freezes_proceeds() {
    let emission: u64 = 100_000_000_000;
    let price_usdc: u64 = 30_000;
    let token_units: u64 = 100_000_000;
    let soft_cap = soft_cap_usdc(emission, price_usdc, token_units).unwrap();
    assert_eq!(soft_cap, 30_000_000);

    let honest_nets = [20_000_000u64, 20_000_000u64];
    let pool: u64 = honest_nets.iter().sum();
    assert!(is_oversubscribed(pool, emission, price_usdc, token_units).unwrap());

    let sybil_participants = 10_000;
    let total_participants = 2 + sybil_participants;

    let proceeds = soft_cap.saturating_sub(total_participants);
    let refund = pool.checked_sub(proceeds).unwrap();

    let mut total_honest_refund_claimed = 0u64;
    for &net in &honest_nets {
        let alloc = allocate(net, pool, emission, price_usdc, token_units).unwrap();
        total_honest_refund_claimed += alloc.refund;
    }

    let stranded_funds = refund - total_honest_refund_claimed;
    assert_eq!(stranded_funds, total_participants);
}
```

## Remediation
Remove the participant subtraction from `soft_cap_usdc` in `activate_claim.rs`:

```diff
--- a/programs/sale/src/instructions/activate_claim.rs
+++ b/programs/sale/src/instructions/activate_claim.rs
@@ -107,10 +107,8 @@ pub fn activate_claim(ctx: Context<ActivateClaim>) -> Result<()> {
     let (proceeds, refund) = if oversubscribed {
-        let proceeds =
-            soft_cap_usdc(emission, price_usdc, TOKEN_UNITS)?.saturating_sub(participants);
+        let soft_cap = soft_cap_usdc(emission, price_usdc, TOKEN_UNITS)?;
+        let proceeds = std::cmp::min(pool, soft_cap);
         let refund = pool.checked_sub(proceeds).ok_or(SaleError::MathOverflow)?;
         (proceeds, refund)
     } else {
         (pool, 0)
     };
```

Additionally, increment `state.participants` only upon a confirmed non-zero deposit in `purchase.rs` rather than on empty `init_aggregate` creation."""

impact = """1. State Counter Pollution: Any user can inflate the participant count at minimal cost without contributing to the sale.
2. Stranded Protocol Funds: Because allocate() rounds down refunds in favor of the protocol, the participant headroom subtracted from soft_cap_usdc is never claimable by users and remains stranded in refund_vault until ClaimClosed.
3. Accounting Inconsistency: Unit mismatch between an integer count of accounts and atomic micro-USDC balances."""

async def populate():
    res = urllib.request.urlopen("http://localhost:9222/json").read()
    tabs = json.loads(res.decode())
    target_tab = next(t for t in tabs if "1win" in t.get("title", "") or "Report" in t.get("title", ""))
    ws_url = target_tab["webSocketDebuggerUrl"]
    async with websockets.connect(ws_url) as ws:
        expr = f"""
        (() => {{
            function setNativeValue(element, value) {{
                const valueSetter = Object.getOwnPropertyDescriptor(element, 'value').set;
                const prototype = Object.getPrototypeOf(element);
                const prototypeValueSetter = Object.getOwnPropertyDescriptor(prototype, 'value').set;
                if (prototypeValueSetter && valueSetter !== prototypeValueSetter) {{
                    prototypeValueSetter.call(element, value);
                }} else {{
                    valueSetter.call(element, value);
                }}
                element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                element.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}

            const titleEl = document.getElementById('report_title');
            if (titleEl) setNativeValue(titleEl, {json.dumps(title)});

            const vulnEl = document.getElementById('report_vulnerability_information');
            if (vulnEl) setNativeValue(vulnEl, {json.dumps(vuln_info)});

            const impactEl = document.getElementById('report_impact');
            if (impactEl) setNativeValue(impactEl, {json.dumps(impact)});

            return 'populated successfully';
        }})()
        """
        msg = {"id": 1, "method": "Runtime.evaluate", "params": {"expression": expr, "returnByValue": True}}
        await ws.send(json.dumps(msg))
        resp = await ws.recv()
        print("Result:", json.loads(resp).get("result", {}).get("result", {}).get("value"))

if __name__ == "__main__":
    asyncio.run(populate())
