#!/usr/bin/env python3
"""Local Playwright + lemonade agent — actually DRIVES the marimo notebook to test the AI assist.
Real browser (Playwright/chromium), $0 reasoning (lemonade). No cloud, no Claude.

It loads the notebook, records console + the :13305 network calls + the interactive elements, takes a
screenshot, optionally clicks an AI-looking control + sends a test prompt, then has a local model
JUDGE whether the AI works and, if not, the exact fix. Observes the real thing instead of guessing.

RUN (marimo must be serving; launch it WITHOUT a token so the agent can connect):
  cd ~/dev/cohezion
  uvx marimo edit notebooks/cohezion_local_continuation.py --headless --no-token --port 2718 &
  uv run --with playwright python scripts/marimo_playwright_agent.py http://localhost:2718
"""
from __future__ import annotations

import sys
import time

import httpx
from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:2718"
LEMONADE = "http://localhost:13305/v1/chat/completions"


def judge(observations: str) -> str:
    prompt = ("You are testing a marimo notebook's LOCAL AI assist (it should call a local LLM at "
              ":13305 via /v1/chat/completions). Given these real browser observations, is the AI "
              "working? If not, state the EXACT problem + the fix. Be concise.\n\n" + observations)
    # Bonsai-8B is non-thinking (won't empty its content like the reasoning models); Gemma fallback.
    for model in ("Bonsai-8B-gguf", "Gemma-4-26B-A4B-it-GGUF"):
        try:
            r = httpx.post(LEMONADE, json={"model": model,
                                           "messages": [{"role": "user", "content": prompt}],
                                           "max_tokens": 400, "temperature": 0.2}, timeout=150)
            c = r.json()["choices"][0]["message"]["content"].strip()
            if c:
                return c
        except Exception:
            continue
    return "(judge empty across models — read the observations above directly)"


def main() -> None:
    console: list[str] = []
    network: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("console", lambda m: console.append(f"{m.type}: {m.text[:200]}"))
        page.on("response", lambda r: network.append(f"{r.status} {r.url[:130]}")
                if any(k in r.url for k in ("13305", "/chat/completions", "completions")) else None)
        print(f"-> {URL}")
        page.goto(URL, wait_until="networkidle", timeout=35000)
        time.sleep(3)
        title = page.title()
        # marimo --no-token connects new clients as READ-ONLY; "Take over" to become the editor
        # (the AI-assist controls only exist for the editor connection)
        try:
            page.get_by_text("Take over", exact=False).first.click(timeout=3000)
            time.sleep(2.5)
        except Exception:
            pass
        # dump interactive controls so we can locate the AI trigger WITHOUT guessing selectors
        controls = page.eval_on_selector_all(
            "button, [role=button], [aria-label], [title]",
            "els => Array.from(new Set(els.map(e => (e.getAttribute('aria-label')||e.getAttribute('title')||e.textContent||'').trim()).filter(Boolean))).slice(0,45)")
        # best-effort: click a control that looks like AI/chat, then watch the network for the call
        triggered = "no AI control clicked"
        for label in (controls or []):
            if any(w in label.lower() for w in ("generate with ai", "fix with ai")):
                clicked = False
                for sel in (f"[aria-label='{label}']", f"[title='{label}']"):  # aria/title first
                    try:
                        page.click(sel, timeout=2000)
                        clicked = True
                        break
                    except Exception:
                        pass
                if not clicked:
                    try:
                        page.get_by_text("generate", exact=False).first.click(timeout=2000)  # the inline link
                        clicked = True
                    except Exception:
                        pass
                if clicked:
                    time.sleep(1.5)
                    try:  # type a prompt into whatever input appeared, then submit
                        page.keyboard.type("print('local AI works')")
                        page.keyboard.press("Enter")
                    except Exception:
                        pass
                    time.sleep(4)  # let the :13305 call fire + return
                    triggered = f"clicked + prompted: {label!r}"
                    break
        shot = "/tmp/marimo_agent.png"
        page.screenshot(path=shot)
        browser.close()

    obs = (f"page title: {title}\n"
           f"AI-trigger attempt: {triggered}\n\n"
           f"console (last 15):\n" + "\n".join(console[-15:] or ["(none)"]) +
           "\n\nnetwork to the AI endpoint (:13305 / chat / completions):\n" +
           ("\n".join(network) or "  NONE — the AI was not called, or it hit the wrong endpoint (e.g. 404 /chat/completions)") +
           "\n\ninteractive controls (to find the AI trigger):\n" + ", ".join((controls or [])[:35]))
    print(obs)
    print("\n=== lemonade judgment ===\n" + judge(obs))
    print(f"\nscreenshot: {shot}")


if __name__ == "__main__":
    main()
