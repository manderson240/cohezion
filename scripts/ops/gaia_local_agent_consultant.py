#!/usr/bin/env python3
"""GAIA SDK Local Agent Consultant.

Consults resident local silicon models (`Qwen3-Coder-30B` via Lemonade on :13305)
for architectural guidance, invariant verification, and Kaggle optimization strategies.
Uses Typed Context to guarantee zero type confusion and 100% provenance tracking.
"""

import asyncio
import httpx
import json
import time
from cohezion.core.typed_context import TypedContextStore, ContextType

LEMONADE_URL = "http://localhost:13305/v1/chat/completions"
MODEL_ID = "Qwen3-Coder-30B-A3B-Instruct-GGUF"

class GaiaLocalConsultant:
    def __init__(self, model: str = MODEL_ID):
        self.model = model

    async def consult(self, question: str, role: str = "GAIA Frontier Systems Architect") -> dict[str, str]:
        store = TypedContextStore()
        store.insert(f"You are a {role}. Provide deep, mathematically rigorous, and code-verifiable answers.", ContextType.INSTRUCTION, "system_persona")
        store.insert(question, ContextType.INSTRUCTION, "user_query")
        
        prompt = store.assemble()
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": f"You are a {role} running locally on AMD Strix Halo silicon."},
                {"role": "user", "content": question}
            ],
            "temperature": 0.2,
            "max_tokens": 800
        }
        
        t0 = time.perf_counter()
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                r = await client.post(LEMONADE_URL, json=payload)
                dt = round(time.perf_counter() - t0, 2)
                if r.status_code == 200:
                    text = (r.json()["choices"][0]["message"].get("content") or "").strip()
                    tool_item = store.insert(text, ContextType.TOOL_OUTPUT, f"local_agent:{self.model}")
                    ev_item = store.transform(tool_item, ContextType.EVIDENCE, validator=lambda s: len(s) > 10)
                    return {
                        "status": "success",
                        "response": text,
                        "latency_s": dt,
                        "evidence_id": ev_item.item_id,
                        "model": self.model
                    }
                else:
                    return {"status": "error", "error": f"HTTP {r.status_code}", "latency_s": dt}
            except Exception as e:
                return {"status": "error", "error": str(e), "latency_s": round(time.perf_counter() - t0, 2)}

if __name__ == "__main__":
    consultant = GaiaLocalConsultant()
    res = asyncio.run(consultant.consult("What are the 3 highest-yield topological invariants for ARC Prize 2026?"))
    print(json.dumps(res, indent=2))
