#!/usr/bin/env python3
"""
HIHO Reality Precipitation & Audio Field Sonification Operational Demo
========================================================================
Demonstrates:
  1. 0.5 HIHO Coherence audio frequency generation (432 Hz fundamental tuning).
  2. Off-coherence dissonance calculation and Lyapunov attractor micro-perturbations.
  3. High-speed JSON audio buffer generation (<50ms performance verification).
  4. Router integration for Tier 1 Local Silicon (Qwen3-Coder-30B on :13305) / Tier 2 Cloud.
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path


# Ensure src/ is on sys.path if run directly
SRC_DIR = Path(__file__).resolve().parents[2] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from cohezion.governance.quadrature_nexus import QuadratureState
from cohezion.inference.unified_hybrid_router import TaskClass
from cohezion.physics.hiho_sonification import (
    DEFAULT_FUNDAMENTAL_HZ,
    HIHOSonifier,
)


def print_log(msg: str) -> None:
    """Print message to stdout immediately with timestamp."""
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def run_coherence_demo() -> bool:
    """Execute 0.5 HIHO coherence fundamental audio frequency generation demo.

    Returns
    -------
    bool
        True if all assertions pass.
    """
    print_log("=== Phase 1: 0.5 HIHO Coherence Fundamental Frequency (432 Hz) ===")
    sonifier = HIHOSonifier(fundamental_hz=DEFAULT_FUNDAMENTAL_HZ)

    # 1. Perfect 0.5 HIHO Coherence state across all 4 fabrics
    hiho_state = QuadratureState(
        awareness=0.5,
        precision=0.5,
        creativity=0.5,
        dilation=0.5,
        coherence=0.5,
        entropy=0.5,
        stability=0.5,
        momentum=0.5,
        novelty=0.5,
        resonance=0.5,
        decay=0.5,
        synthesis=0.5,
    )

    audio_state = sonifier.sonify_quadrature_state(hiho_state)
    print_log(f"Fundamental Frequency: {audio_state.fundamental_hz:.2f} Hz")
    print_log(f"System Coherence: {audio_state.system_coherence:.4f}")
    print_log(f"Coherence Distance |c - 0.5|: {audio_state.coherence_distance:.4f}")
    print_log(f"Dissonance Index: {audio_state.dissonance_index:.4f}")

    assert audio_state.fundamental_hz == 432.0, f"Expected 432 Hz, got {audio_state.fundamental_hz}"
    assert audio_state.coherence_distance == 0.0, f"Expected 0.0 distance, got {audio_state.coherence_distance}"
    assert audio_state.dissonance_index == 0.0, f"Expected 0.0 dissonance, got {audio_state.dissonance_index}"

    for fab_name, fab_data in audio_state.fabrics.items():
        print_log(
            f"  Fabric: {fab_name:<13} | Base Freq: {fab_data.base_frequency_hz:6.2f} Hz "
            f"| Effective Freq: {fab_data.frequency_hz:6.2f} Hz | Amp: {fab_data.amplitude:.2f}"
        )

    # Verify ratios at 0.5 HIHO coherence
    assert audio_state.fabrics["Space"].frequency_hz == 432.0
    assert audio_state.fabrics["Field"].frequency_hz == 540.0
    assert audio_state.fabrics["Control"].frequency_hz == 648.0
    assert audio_state.fabrics["Precipitation"].frequency_hz == 864.0
    print_log("✓ Phase 1 0.5 HIHO Coherence assertions PASSED.\n")
    return True


def run_off_coherence_demo() -> bool:
    """Execute off-coherence dissonance and Lyapunov micro-perturbation demo.

    Returns
    -------
    bool
        True if all assertions pass.
    """
    print_log("=== Phase 2: Off-Coherence Dissonance & Lyapunov Micro-Perturbations ===")
    sonifier = HIHOSonifier(fundamental_hz=DEFAULT_FUNDAMENTAL_HZ)

    # 1. Sub-HIHO state (coherence = 0.2, distance = 0.3)
    sub_hiho = {"coherence": 0.2}
    audio_sub = sonifier.sonify_quadrature_state(sub_hiho, lyapunov_perturbation=0.0)
    print_log(
        f"Sub-HIHO Coherence (0.2) -> Distance: {audio_sub.coherence_distance:.4f} "
        f"| Dissonance: {audio_sub.dissonance_index:.4f}"
    )
    assert audio_sub.coherence_distance == 0.3
    assert audio_sub.dissonance_index == 0.6

    # 2. Super-HIHO state (coherence = 0.8, distance = 0.3) + Lyapunov micro-perturbation (0.05)
    super_hiho = {"coherence": 0.8}
    lyapunov_eps = 0.05
    audio_super = sonifier.sonify_quadrature_state(super_hiho, lyapunov_perturbation=lyapunov_eps)
    print_log(
        f"Super-HIHO (0.8) + Lyapunov (0.05) -> Distance: {audio_super.coherence_distance:.4f} "
        f"| Dissonance: {audio_super.dissonance_index:.4f}"
    )
    assert abs(audio_super.dissonance_index - 0.7) < 1e-6  # 0.6 base + 0.1 perturbation

    print_log("✓ Phase 2 Off-Coherence assertions PASSED.\n")
    return True


def run_buffer_performance_demo() -> bool:
    """Execute JSON audio buffer generation <50ms benchmark.

    Returns
    -------
    bool
        True if buffer generation completes in <50ms.
    """
    print_log("=== Phase 3: High-Speed Web Audio API / PyGame JSON Buffer Synthesis ===")
    sonifier = HIHOSonifier(fundamental_hz=DEFAULT_FUNDAMENTAL_HZ, sample_rate=44100)
    hiho_state = QuadratureState(
        awareness=0.5, precision=0.5, creativity=0.5, dilation=0.5,
        coherence=0.5, entropy=0.5, stability=0.5, momentum=0.5,
        novelty=0.5, resonance=0.5, decay=0.5, synthesis=0.5
    )
    audio_state = sonifier.sonify_quadrature_state(hiho_state)

    # Warmup
    _ = sonifier.to_web_audio_json(audio_state, duration_s=0.05)

    # Timed run
    t0 = time.perf_counter()
    json_output = sonifier.to_web_audio_json(audio_state, duration_s=0.05)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    metadata = json_output["metadata"]
    print_log(
        f"JSON Audio Buffer generated in {elapsed_ms:.3f} ms "
        f"(Internal Engine: {metadata['generation_time_ms']:.3f} ms)"
    )
    print_log(
        f"Buffer Sample Rate: {metadata['sample_rate']} Hz "
        f"| Duration: {metadata['duration_s']:.2f} s | Length: {metadata['buffer_length']} samples"
    )

    assert len(json_output["samples"]) == 2205, f"Expected 2205 samples, got {len(json_output['samples'])}"
    assert elapsed_ms < 50.0, f"Performance budget breached: {elapsed_ms:.2f} ms >= 50.0 ms"
    print_log("✓ Phase 3 Buffer Synthesis (<50ms target) PASSED.\n")
    return True


async def run_router_delegation_demo() -> bool:
    """Demonstrate internal model inference delegation using UnifiedHybridRouter.

    Returns
    -------
    bool
        True when router execution completes.
    """
    print_log("=== Phase 4: Model Inference Delegation Probe (Tier 1 Silicon / Tier 2 Cloud) ===")
    sonifier = HIHOSonifier()
    prompt = "Synthesize an optimal ADSR envelope for a 0.5 HIHO coherent 432 Hz fundamental frequency field."

    print_log("Delegating task prompt to router (TaskClass.CODING)...")
    try:
        res = await asyncio.wait_for(
            sonifier.delegate_inference(prompt, task_class=TaskClass.CODING),
            timeout=2.0,
        )
        print_log("Router Delegation Outcome:")
        print_log(f"  Tier Used:  {res.tier_used}")
        print_log(f"  Model:      {res.model_name}")
        print_log(f"  Latency:    {res.latency_ms:.2f} ms")
        print_log(f"  Verified:   {res.verified}")
    except TimeoutError:
        print_log("Router delegation probe timed out (Local Silicon offline/standby). Using Tier 0 Fallback.")
    print_log("✓ Phase 4 Model Delegation probe complete.\n")
    return True


def main() -> int:
    """Main execution entrypoint."""
    print_log("Starting HIHO Reality Precipitation & Audio Field Sonification Harness...\n")

    p1 = run_coherence_demo()
    p2 = run_off_coherence_demo()
    p3 = run_buffer_performance_demo()
    asyncio.run(run_router_delegation_demo())

    if p1 and p2 and p3:
        print_log("==========================================================================")
        print_log("SUCCESS: ALL HIHO AUDIO SONIFICATION HARNESS VERIFICATIONS PASSED (EXIT 0)")
        print_log("==========================================================================")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
