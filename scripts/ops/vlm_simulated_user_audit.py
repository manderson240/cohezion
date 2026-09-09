#!/usr/bin/env python3
"""Simulated User Interaction & Visual Evaluation via Ollama Vision Model (`step3-vl-10b` / `qwen3-vl`)."""

from __future__ import annotations

import base64
import sys

import httpx


# Add src to path
sys.path.insert(0, "/home/mike-anderson/dev/cohezion/src")


def evaluate_screenshot_with_vlm(screenshot_path: str) -> None:
    print("=" * 90)
    print("    👁️ SIMULATED END-USER VLM EVALUATION (Local Ollama Vision Fleet)")
    print("=" * 90)

    with open(screenshot_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")

    prompt = (
        "You are acting as an expert QA and Human-Computer Interaction Evaluator evaluating a Web dashboard screenshot.\n"
        "Inspect this image carefully:\n"
        "1. Is the Marimo WASM application successfully rendered with NO red error banners or internal error messages?\n"
        "2. Are the 3 UI sliders ('HIHO Coherence Target', 'EVO Electrons', 'Relativistic Drift Velocity') visible and accessible at the top?\n"
        "3. Is the 3D Exotic Vacuum Object (EVO) charge soliton torus rendered cleanly with WebGL Viridis colormap in the center?\n"
        "4. Is the 'Live Soliton State & Tensor Telemetry' section displayed below the 3D canvas?\n"
        "Provide a crisp, objective scorecard and overall PASS/FAIL rating."
    )

    try:
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "qwen3-vl:8b",
                    "prompt": prompt,
                    "images": [img_b64],
                    "stream": False,
                },
            )
            if resp.status_code == 200:
                result = resp.json().get("response", "")
                print("\n📋 VLM EVALUATION REPORT:")
                print(result)
            else:
                # Try fallback vision model
                resp2 = client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "llama3.2-vision:latest",
                        "prompt": prompt,
                        "images": [img_b64],
                        "stream": False,
                    },
                )
                if resp2.status_code == 200:
                    print("\n📋 VLM EVALUATION REPORT (llama3.2-vision):")
                    print(resp2.json().get("response", ""))
                else:
                    print(f"Ollama Vision response: {resp.status_code} / {resp2.status_code}")
    except Exception as e:
        print(f"Error querying VLM: {e}")

    print("\n" + "=" * 90)


if __name__ == "__main__":
    evaluate_screenshot_with_vlm("/home/mike-anderson/dev/cohezion/docs/assets/renderings/marimo_wasm_live_screenshot.png")
