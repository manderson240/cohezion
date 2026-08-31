r"""Consult All Ollama Cloud Models CLI Tool
===========================================
Queries all models in the Ollama Cloud Roster:
  1. `deepseek-v4-pro:cloud` (Deep Reasoning)
  2. `glm-5.2:cloud` (Frontier Science & Architecture)
  3. `qwen3.5:397b-cloud` (Frontier Coding)
  4. `mistral-large-2026:cloud` (Fast Q&A Overflow)
"""

from __future__ import annotations

import json
import logging
import time
import urllib.request


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434/api/generate"

ROSTER = [
    ("deepseek-v4-pro:cloud", "Deep Reasoning", 0.2),
    ("glm-5.2:cloud", "Frontier Science & Architecture", 0.2),
    ("qwen3.5:397b-cloud", "Frontier Coding", 0.1),
    ("mistral-large-2026:cloud", "Fast Q&A Overflow", 0.5),
]


def query_model(model_id: str, category: str, temp: float, prompt: str) -> None:
    logger.info("=== Consulting [%s] `%s` (temp=%.2f) ===", category, model_id, temp)
    payload = {
        "model": model_id,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": temp},
    }

    t0 = time.time()
    try:
        req = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode(),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            res = json.loads(r.read().decode())
            dt = round(time.time() - t0, 2)
            resp = res.get("response", "").strip()
            print(f"\n[{model_id} - {category}] ({dt}s):")
            print(resp[:300] + ("..." if len(resp) > 300 else ""))
    except Exception as e:
        logger.warning("! Failed to query `%s`: %s", model_id, e)


def main() -> None:
    prompt = "Briefly state your core strength and how you assist AGI agent swarms running on 128GB unified memory hardware."

    print("\n" + "=" * 95)
    print("      OLLAMA CLOUD MODEL ROSTER CONSULTATION HARNESS")
    print("=" * 95)

    for model_id, category, temp in ROSTER:
        query_model(model_id, category, temp, prompt)

    print("\n" + "=" * 95)
    print("🎉 All Ollama Cloud Models Successfully Consulted!")


if __name__ == "__main__":
    main()
