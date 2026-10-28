import urllib.request
import json
import asyncio
import websockets

prompt = """This is for Report Intent #408860 on the 1win Solana Token Sale program (GWvQinGBRa7ZUzhXY23MrLjdsx3KfRGxH8yXURBwrz1R).

Vulnerability: In activate_claim.rs, participants count is subtracted directly from soft_cap_usdc (micro-USDC). Anyone can call init_aggregate without depositing funds, incrementing state.participants. Under oversubscribed conditions, if participants >= soft_cap_usdc, proceeds evaluates to 0, trapping the sale proceeds in refund_vault until ClaimClosed.

We populated Description with technical root cause, a formal Rust unit test, and a git diff patch, and calibrated severity to Low / Defense-in-depth due to mainnet account rent costs.

Can you review this and let us know if anything is missing to ensure smooth triage acceptance?"""


async def run():
    targets = json.loads(urllib.request.urlopen("http://127.0.0.1:9222/json").read().decode())
    h1_tab = next((t for t in targets if "report_assistant/408860" in t.get("url", "")), None)
    if not h1_tab:
        print("Tab not found")
        return
    ws_url = h1_tab["webSocketDebuggerUrl"]
    async with websockets.connect(ws_url) as ws:

        async def eval_js(expr):
            await ws.send(
                json.dumps(
                    {
                        "id": 1,
                        "method": "Runtime.evaluate",
                        "params": {"expression": expr, "returnByValue": True},
                    }
                )
            )
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
            return 'Dispatched prompt to Hai';
        }})()"""
        res = await eval_js(script)
        print("Result:", res)

        # Wait and read Hai's response
        for i in range(10):
            await asyncio.sleep(2)
            aside_text = await eval_js("document.querySelector('aside')?.innerText || ''")
            if "Hai for Hackers" in aside_text and (
                "triage" in aside_text.lower() or "report" in aside_text.lower()
            ):
                # Check for new messages from Hai
                pass

        final_text = await eval_js("document.querySelector('aside')?.innerText || ''")
        print("\n=== HAI FULL CONVERSATION ===\n")
        print(final_text)


if __name__ == "__main__":
    asyncio.run(run())
