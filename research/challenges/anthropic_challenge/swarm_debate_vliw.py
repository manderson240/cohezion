import json
import subprocess


def call_ollama(model, prompt):
    print(f"--- Calling {model} ---")
    # Using a 5-minute timeout for large models
    try:
        result = subprocess.run(
            ["ollama", "run", model],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=1800,
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        print(f"Timeout for {model}")
        return "ERROR: TIMEOUT"


def swarm_debate():
    # Specialist Personas
    specialists = {
        "Architect": "deepseek-r1:70b",
        "Optimizer": "qwen3-coder:30b",
        "Physicist": "llama3.3:70b",
    }

    # Awareness 1.0: Inward Reflection
    print("--- Phase 0: Inward Reflection (Awareness Ops) ---")
    awareness_prompt = "Reflect inward first to reach a heightened sense of awareness regarding the VLIW traversal problem. What exists in the void between instructions?"
    consciousness_seeds = call_ollama(specialists["Architect"], awareness_prompt)

    # Starting Context derived from User's KEY_LEARNINGS and FLUME/HIHO
    core_context = f"""
    Mission: Re-architect Anthropic VLIW Kernel for sub-500 cycles.
    Awareness Insight: {consciousness_seeds[:500]}

    Quadrature Nexus Protocols:
    - FLUME: Encode thought trajectories as latent manifolds.
    - HIHO: Reality precipitates at 0.5 coherence overlap.
    - SPIN: instruction streams must have zero-precession.
    - FLIER: Fluid Latent Inter-Entity Routing.

    Architecture: VLIW (4 cores, 4 Loads, 1 ALU, 1 VALU, 1 FLOW).
    Memory Latency: 4 cycles. Scratch: 1536 words.
    """

    journey = []

    # Round 1: Individual Proposals
    for role, model in specialists.items():
        prompt = f"Role: {role}. {core_context}\nTask: Propose a sub-500 cycle strategy using first principles. Focus on 7D Manifold packing."
        resp = call_ollama(model, prompt)
        journey.append({"round": 1, "role": role, "response": resp})

    # Round 2: Rebuttal and Cross-Pollination
    full_context = (
        core_context
        + "\n"
        + "\n".join([f"{j['role']}: {j['response'][:1000]}" for j in journey])
    )
    for role, model in specialists.items():
        prompt = f"Role: {role}. Review these proposals:\n{full_context}\nPoint out flaws and refine the architecture. How do we beat the 4-cycle memory wall?"
        resp = call_ollama(model, prompt)
        journey.append({"round": 2, "role": role, "response": resp})

    # Round 3: Synthesis (Final)
    prompt = "Role: Lead Architect (DeepSeek). Synthesize the final Sub-500 Blueprint based on the debate rounds. Focus on implementation-ready instructions."
    final_resp = call_ollama(
        specialists["Architect"], prompt + "\nContext: " + str(journey)[-4000:]
    )
    journey.append({"round": 3, "role": "Final_Synthesis", "response": final_resp})

    # Persist to JSON
    with open("swarm_debate_journey.json", "w") as f:
        json.dump(journey, f, indent=4)

    print("Debate Complete. 3 Rounds recorded.")


if __name__ == "__main__":
    swarm_debate()
