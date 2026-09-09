#!/usr/bin/env python3
"""Demonstration: Card-Aligned Hyperparameter Dispatch per Model Architecture."""

from cohezion.inference.model_card_profiles import MODEL_CARD_REGISTRY, get_aligned_profile

def main():
    print("\n" + "=" * 115)
    print("🎯 CARD-ALIGNED HYPERPARAMETER & TOKEN DISPATCH PER MODEL ARCHITECTURE")
    print("=" * 115)

    for model_id, p in MODEL_CARD_REGISTRY.items():
        print(f"\n[Model: {p.model_id}] (Tier: {p.tier})")
        print(f"  ├─ Purpose           : {p.purpose}")
        print(f"  ├─ Context Window    : {p.context_window:,} tokens")
        print(f"  ├─ Max Output Tokens : {p.max_output_tokens:,} tokens")
        print(f"  ├─ Timeout Ceiling   : {p.timeout_seconds:.1f}s ({p.timeout_seconds/60:.1f} min)")
        print(f"  ├─ Sampling Params   : temp={p.temperature}, top_p={p.top_p}")
        print(f"  └─ Thinking Engine   : {'🧠 Deep CoT Thinking' if p.thinking_model else '⚡ Direct Fast Emission'}")

    print("\n" + "=" * 115)
    print("🎉 ZERO BLANKET OVERRIDES: Every model has its exact hardware-calibrated envelope.")
    print("=" * 115 + "\n")

if __name__ == "__main__":
    main()
