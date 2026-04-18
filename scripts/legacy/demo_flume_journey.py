#!/usr/bin/env python3
"""
FLUME Journey Demonstration Script
Shows how to generate and analyze agent journeys through FLUME latent space
"""

import sys

import numpy as np


# Add Cohezion to path
sys.path.insert(0, "/home/mike-anderson/dev/cohezion/src")
sys.path.insert(0, "/home/mike-anderson/dev/cohezion/.venv/lib/python3.13/site-packages")


def demonstrate_flume_journey():
    """Demonstrate FLUME journey capabilities"""
    print("🌀 FLUME Journey Demonstration")
    print("=" * 50)

    # Import FLUME components
    try:
        from cohezion.api.services.flume import compute_coherence, get_vae

        print("✅ Successfully imported Cohezion FLUME components")
    except ImportError as e:
        print(f"⚠️  Could not import Cohezion components: {e}")
        print("🔄 Using simulation mode for demonstration")
        return simulate_journey()

    # Initialize VAE
    try:
        vae = get_vae()
        print("✅ FLUME VAE initialized successfully")
        using_real_vae = True
    except Exception as e:
        print(f"⚠️  Could not load real VAE: {e}")
        print("🔄 Using simulated components")
        using_real_vae = False

    # Generate sample journey
    print("\n📋 Generating Sample Agent Journey...")
    print("-" * 40)

    journey_themes = [
        "Quantum Consciousness Exploration",
        "Biological Intelligence Analysis",
        "Mathematical Pattern Recognition",
        "Logical Reasoning Chain",
        "Creative Problem Solving",
        "Ethical Decision Framework",
        "Strategic Planning Session",
        "Scientific Discovery Process",
    ]

    latents = []
    labels = []
    coherences = []
    concepts = []

    for i, theme in enumerate(journey_themes[:6]):  # 6-step journey
        print(f"Step {i + 1}: Processing '{theme}'...")

        # Simple encoding (in reality would use tokenizer + VAE)
        import hashlib

        seed = int(hashlib.md5(theme.encode()).hexdigest()[:8], 16) % 2**32
        np.random.seed(seed)

        # Generate latent with thematic structure
        t = np.linspace(0, 6 * np.pi, 256)
        if i % 2 == 0:  # Even steps - more structured
            latent = (
                0.4 * np.sin(t) + 0.2 * np.sin(3 * t) * np.exp(-t / 15) + 0.1 * np.random.randn(256)
            )
        else:  # Odd steps - more exploratory
            latent = (
                0.6 * np.sin(t) + 0.3 * np.sin(7 * t) * np.exp(-t / 10) + 0.2 * np.random.randn(256)
            )

        # Normalize
        latent = latent / np.linalg.norm(latent)

        # Calculate coherence (HIHO stability)
        coherence = compute_coherence(latent.tolist())

        # Generate conceptual interpretation
        latent_mean = np.mean(latent)
        latent_std = np.std(latent)

        if latent_mean > 0.2:
            domain = "Quantum/AI Realm"
        elif latent_mean > -0.2:
            domain = "Analytical/Logical Realm"
        else:
            domain = "Mathematical/Structural Realm"

        if latent_std > 0.4:
            complexity = "Complex Dynamics"
        else:
            complexity = "Stable Patterns"

        concept = f"{complexity} in {domain}"

        latents.append(latent)
        labels.append(theme)
        coherences.append(coherence)
        concepts.append(concept)

        print("  → Latent vector: 256D normalized")
        print(f"  → HIHO Coherence: {coherence:.3f}")
        print(f"  → Interpretation: {concept}")
        print()

    # Journey analysis
    print("📊 Journey Analysis Summary")
    print("-" * 40)

    coherences_array = np.array(coherences)
    avg_coherence = np.mean(coherences_array)
    hiho_compliance = (
        np.sum((coherences_array >= 0.4) & (coherences_array <= 0.6)) / len(coherences_array) * 100
    )
    coherence_std = np.std(coherences_array)

    print(f"Average Coherence: {avg_coherence:.3f}")
    print(f"HIHO Band Compliance (0.4-0.6): {hiho_compliance:.0f}%")
    print(f"Coherence Stability (std): {coherence_std:.3f}")

    # Path analysis
    if len(latents) > 1:
        total_path = 0
        for i in range(1, len(latents)):
            step_distance = np.linalg.norm(np.array(latents[i]) - np.array(latents[i - 1]))
            total_path += step_distance

        print(f"Total Path Length: {total_path:.3f}")
        print(f"Average Step Size: {total_path / (len(latents) - 1):.3f}")

    print("\n🎯 Key Insights:")
    print("-" * 40)

    if avg_coherence > 0.7:
        print("🎯 High coherence journey - agent maintained strong HIHO alignment")
    elif avg_coherence > 0.5:
        print("⚖️  Moderate coherence - balanced exploration and stability")
    else:
        print("🔍 Exploratory journey - agent ventured into diverse thought regions")

    if hiho_compliance > 70:
        print("✅ Excellent stability maintenance within HIHO band")
    elif hiho_compliance > 40:
        print("⚠️  Moderate stability - some deviation from optimal coherence")
    else:
        print("🔬 High exploration mode - agent prioritized novelty over stability")

    print("\n💾 Journey data ready for export:")
    print(f"   • {len(latents)} steps × 256D latent vectors")
    print(f"   • {len(labels)} semantic labels")
    print(f"   • {len(coherences)} coherence measurements")
    print(f"   • {len(concepts)} conceptual interpretations")

    return {
        "latents": latents,
        "labels": labels,
        "coherences": coherences,
        "concepts": concepts,
        "metrics": {
            "avg_coherence": avg_coherence,
            "hiho_compliance": hiho_compliance,
            "coherence_std": coherence_std,
            "path_length": total_path if len(latents) > 1 else 0,
        },
    }


def simulate_journey():
    """Fallback simulation when Cohezion not available"""
    print("🔄 Running in simulation mode...")
    # Return simulated data
    latents = [np.random.randn(256) for _ in range(5)]
    latents = [l / np.linalg.norm(l) for l in latents]  # Normalize

    labels = ["Start", "Analysis", "Insight", "Decision", "Action"]
    coherences = [0.3, 0.5, 0.7, 0.6, 0.4]  # Sample coherence values
    concepts = ["Initial State", "Processing", "Breakthrough", "Refinement", "Execution"]

    return {
        "latents": latents,
        "labels": labels,
        "coherences": coherences,
        "concepts": concepts,
        "metrics": {
            "avg_coherence": np.mean(coherences),
            "hiho_compliance": 60.0,  # 3/5 in band
            "coherence_std": np.std(coherences),
            "path_length": 0,  # Simplified
        },
    }


if __name__ == "__main__":
    journey_data = demonstrate_flume_journey()
    print("\n" + "=" * 50)
    print("🎉 Demonstration complete!")
    print("💡 To run the interactive visualizer, use:")
    print("   ./launch_simple_flume.sh")
    print("=" * 50)
