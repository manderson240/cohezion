#!/usr/bin/env python3
import urllib.request, json

prompt = '''You are the Lead Triager on HackerOne for 1win Token Solana Programs.
Critically evaluate this submitted vulnerability report to determine its validity, realistic exploitability, and exact CVSS/severity classification:

REPORT SUMMARY:
- An attacker can call init_aggregate without depositing, incrementing participants.
- In activate_claim:
  let proceeds = soft_cap_usdc(emission, price_usdc, TOKEN_UNITS)?.saturating_sub(participants);
  let refund = pool.checked_sub(proceeds).ok_or(SaleError::MathOverflow)?;
- The researcher claims an attacker can inflate participants to zero out proceeds or trap funds in refund_vault.

CRITICAL TRIAGE QUESTIONS:
1. Economics on Mainnet:
   In 1win, DEFAULT_EMISSION = 130,000,000 $1WIN (10^8 decimals), PRICE = 30,000 ($0.03 USDC).
   soft_cap_usdc is 3,900,000,000,000 micro-USDC ($3,900,000).
   Since participants subtracts 1 micro-USDC ($0.000001) per participant, how many accounts must an attacker create to zero out $3.9M?
   (Answer: 3.9 trillion accounts! Rent for each account on Solana is ~0.0012 SOL).
2. What is the real impact if an attacker creates e.g. 10,000 or 100,000 aggregates?
   Cost to attacker vs amount of USDC stranded?
3. Is there ANY other place where participants is used?
4. What is the correct HackerOne severity rating under CVSS 3.1: Critical, High, Medium, or Low?
5. How would the 1win team remediate this, and what is the exact payout recommendation?
'''

data = {'model': 'deepseek-v4.1-flash:cloud', 'prompt': prompt, 'stream': True}
req = urllib.request.Request('http://localhost:11434/api/generate', data=json.dumps(data).encode(), headers={'Content-Type': 'application/json'})

with urllib.request.urlopen(req, timeout=120) as r:
    for line in r:
        if line:
            chunk = json.loads(line.decode())
            if chunk.get('response'):
                print(chunk['response'], end='', flush=True)
print()
