import urllib.request
import json
import asyncio
import websockets

prompt = """We updated the report with all of your recommended points:
1. Exact attack flow: oversubscribed condition, sybil aggregate creation, activate_claim execution.
2. Fund lockup duration: time-locked until Phase::ClaimClosed (now >= claim_start_date + claim_duration) before admin can call sweep().
3. Concrete rent math: 57-byte WalletAggregate costs ~0.0012 SOL ($0.18) to freeze 1 micro-USDC ($0.000001); $1.00 freeze requires 1M accounts (~$180,000 in rent).
4. Full formal Rust test and git diff patch provided.

Does this fully address all triage requirements?"""

async def run():
    targets = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json").read().decode())
    h1_tab = next((t for t in targets if "report_assistant/408860" in t.get("url", "")), None)
    if not h1_tab:
        return
    ws_url = h1_tab["webSocketDebuggerUrl"]
    async with websockets.connect(ws_url) as ws:
        async def eval_js(expr):
            await ws.send(json.dumps({"id": 1, "method": "Runtime.evaluate", "params": {"expression": expr, "returnByValue": True}}))
            res = json.loads(await ws.recv())
            return res.get("result", {}).get("result", {}).get("value")

        script = f"""(() => {{
            const ta = document.querySelector('textarea[placeholder="Ask a question..."]');
            const keys = Object.keys(ta);
            const reactPropKey = keys.find(k => k.startsWith('__reactProps'));
            const props = ta[reactPropKey];

            props.onChange({{
                target: {{ value: {json.dumps(prompt)} }},
                currentTarget: {{ value: {json.dumps(prompt)} }},
                preventDefault: () => {{}},
                stopPropagation: () => {{}}
            }});

            setTimeout(() => {{
                const btns = Array.from(document.querySelectorAll('[data-testid="hai-submit-button"]'));
                const activeBtn = btns.find(b => !b.disabled);
                if (activeBtn) activeBtn.click();
            }}, 300);
            return 'Dispatched';
        }})()"""
        await eval_js(script)

        # Wait for reply
        await asyncio.sleep(8)
        aside_text = await eval_js("document.querySelector('aside')?.innerText || ''")
        print("\n=== HAI FINAL VERDICT ===\n")
        print(aside_text[-1200:])

if __name__ == "__main__":
    asyncio.run(run())
