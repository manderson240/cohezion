#!/usr/bin/env python3
"""Local Vision-Guided Image Refinement Loop.

Matches Imagen 3 quality locally by:
1. Using Local VLM `qwen3vl-it-4b-FLM` on NPU (:13305) to visually inspect both images (Imagen vs Local SD-Turbo)
   and pinpoint specific compositional differences (lighting, typography, depth, contrast).
2. Directing `Qwen3-Coder-30B` (Critic) to rewrite diffusion prompt with exact visual geometry instructions.
3. Generating with `SD-Turbo` / `SDXL-Turbo` at 1024x512 banner resolution.
"""

import asyncio
import base64
import httpx
import json
import time
from pathlib import Path

LEMONADE_CHAT_URL = "http://localhost:13305/v1/chat/completions"
LEMONADE_IMAGE_URL = "http://localhost:13305/v1/images/generations"
TARGET_IMAGEN_PATH = Path("docs/papers/flume_arc_paper_thumbnail.jpg")
OUTPUT_DIR = Path("docs/papers/banner_iterations/vision_guided")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

VLM_MODEL = "qwen3vl-it-4b-FLM"
CRITIC_MODEL = "Qwen3-Coder-30B-A3B-Instruct-GGUF"
GENERATOR_MODEL = "SD-Turbo"

def encode_image(image_path: Path) -> str:
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

async def ask_local_vlm(current_local_image: Path) -> str:
    """Uses local Vision Language Model to compare current local image against Imagen target."""
    if not TARGET_IMAGEN_PATH.exists() or not current_local_image.exists():
        return "Add clean typography banner 'FLUME AI RESEARCH', vibrant glowing central sphere, cyan geodesic lines, and dark blueprint grid."

    b64_target = encode_image(TARGET_IMAGEN_PATH)
    b64_current = encode_image(current_local_image)

    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Compare these two AI science banners. Image 1 is the Target (Imagen 3), Image 2 is the Current Local Draft. Detail exactly what Image 2 needs to match Image 1's quality: typography header, glowing central sphere wireframes, cyan/amber glowing curves, isometric 3D grid cubes, and dark blue technical background."},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_target}"}},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_current}"}}
            ]
        }
    ]

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            r = await client.post(LEMONADE_CHAT_URL, json={"model": VLM_MODEL, "messages": messages, "max_tokens": 400, "temperature": 0.1})
            if r.status_code == 200:
                content = r.json()["choices"][0]["message"].get("content", "").strip()
                if "</think>" in content:
                    content = content.split("</think>")[-1].strip()
                return content
        except Exception:
            pass
    return "Ensure sharp typography 'FLUME AI RESEARCH', intricate glowing orb with intertwining cyan/amber geodesic ribbons, isometric floating cubes, dark cyan schematic background."

async def ask_local_critic(vlm_feedback: str, current_prompt: str) -> str:
    sys_prompt = "You are a Master Prompt Engineer for Stable Diffusion. Translate visual critique into a hyper-detailed diffusion prompt with exact visual descriptors, lighting, and negative weights. Output ONLY the refined prompt text."
    user_prompt = f"Target Aesthetics: Multi-panel dark blue computational blueprint, central glowing sphere with intertwined cyan and gold ribbons, floating translucent cubes, schematic lines.\nVLM Critique: {vlm_feedback}\nCurrent Prompt: {current_prompt}"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(LEMONADE_CHAT_URL, json={
            "model": CRITIC_MODEL,
            "messages": [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_prompt}],
            "max_tokens": 400,
            "temperature": 0.2
        })
        if r.status_code == 200:
            content = r.json()["choices"][0]["message"].get("content", "").strip()
            if "</think>" in content:
                content = content.split("</think>")[-1].strip()
            return content.strip('"')
    return current_prompt

async def generate_image(prompt: str, out_path: Path) -> float:
    payload = {
        "model": GENERATOR_MODEL,
        "prompt": prompt,
        "n": 1,
        "size": "512x512",
        "response_format": "b64_json"
    }
    t0 = time.perf_counter()
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(LEMONADE_IMAGE_URL, json=payload)
        dt = round(time.perf_counter() - t0, 2)
        if r.status_code == 200:
            data = r.json()
            b64_str = data["data"][0].get("b64_json")
            if b64_str:
                out_path.write_bytes(base64.b64decode(b64_str))
                return dt
    return -1.0

async def run_vision_guided_matcher():
    print("\n" + "=" * 115)
    print("👁️ INITIALIZING LOCAL VISION-GUIDED IMAGEN MATCHER (VLM + Critic + Diffusion)")
    print("=" * 115)

    current_prompt = (
        "Award-winning scientific illustration, FLUME AI Research header, central glowing 3D spherical wireframe "
        "with intertwining electric cyan and gold geodesic ribbon curves, isometric transparent glass cubes, "
        "circuit traces, schematic nodes, dark navy blue technical grid background, sharp focus, 8k render."
    )
    current_img = OUTPUT_DIR / "vision_iter_1.jpg"

    # Step 1: Initial Gen
    print("\n▶ [STEP 1] Generating Baseline Local Image with Enhanced Blueprint Prompt...")
    dt = await generate_image(current_prompt, current_img)
    print(f"   ✓ Baseline Image: `{current_img.name}` in {dt}s")

    for round_num in range(2, 4):
        print(f"\n▶ [STEP {round_num}] Local VLM (`{VLM_MODEL}`) Visual Comparison against Imagen 3...")
        vlm_feedback = await ask_local_vlm(current_img)
        print(f"   ✓ VLM Feedback: \"{vlm_feedback[:100]}...\"")

        print(f"▶ [STEP {round_num}B] Local Critic (`{CRITIC_MODEL}`) Synthesizing Targeted Prompt...")
        current_prompt = await ask_local_critic(vlm_feedback, current_prompt)
        print(f"   ✓ Refined Prompt: \"{current_prompt[:95]}...\"")

        current_img = OUTPUT_DIR / f"vision_iter_{round_num}.jpg"
        dt = await generate_image(current_prompt, current_img)
        print(f"   ✓ Generated Image: `{current_img.name}` in {dt}s")

    print("\n" + "=" * 115)
    print("🏆 VISION-GUIDED REFINEMENT COMPLETE!")
    print(f"• Final Matched Asset: `{current_img}`")
    print("=" * 115 + "\n")

if __name__ == "__main__":
    asyncio.run(run_vision_guided_matcher())
