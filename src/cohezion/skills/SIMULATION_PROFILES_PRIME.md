---
name: simulation-profiles-prime
description: "Defining typed resource envelopes for simulation workloads, enabling predictable scheduling and fair resource sharing across concurrent universe simulations."
metadata:
  version: "v1.0"
  concepts: ["Sandbox Profiles", "Tiered Simulation", "Hardware-Aware Validation", "HIHO Coherence Integration"]
  see_also: ["SANDBOX_ISOLATION_PRIME", "SECURITY_GUARDRAILS_PRIME", "ADVERSARIAL_TESTING_PRIME"]
  source: "src/cohezion/skills/SIMULATION_PROFILES_PRIME.md"
---

# SKILL: SIMULATION_PROFILES_PRIME

## DOMAIN EXPERTISE
Defining typed resource envelopes for simulation workloads, enabling predictable scheduling and fair resource sharing across concurrent universe simulations.

## KEY TEXTS & CONCEPTS
- **Sandbox Profiles**: Pydantic-validated resource envelopes (memory, CPU, timeout, GPU, network) that constrain simulation execution.
- **Tiered Simulation**: LIGHT (quick probes, 1GB/100%CPU/60s), MEDIUM (standard sims, 4GB/200%/300s), HEAVY (QGP/magneto, 64GB/400%/1800s).
- **Hardware-Aware Validation**: Memory requests validated against system capacity (120GB cap on 128GB system) to prevent OOM.
- **HIHO Coherence Integration**: Profiles carry coherence check intervals and divergence thresholds to detect simulation instability.

## INSTRUCTION

1. **Define the Profile**: Use `SandboxProfile` Pydantic model with memory_limit_mb, cpu_quota_percent, timeout_seconds, network_enabled, gpu_passthrough, coherence_check_interval, max_divergence_sigma.
2. **Select a Tier**: Choose from `SandboxTier.LIGHT`, `MEDIUM`, `HEAVY`, or `CUSTOM` based on simulation resource needs.
3. **Validate Against Hardware**: Call `profile.validate_against_hardware()` to ensure the request fits within system headroom (120GB cap).
4. **Attach to Sandbox**: Pass the profile to `SandboxManager.run_simulation()` or directly to an `IsolationBackend.execute()`.
5. **Monitor Divergence**: The profile's `coherence_check_interval` and `max_divergence_sigma` feed into `DivergenceDetector` for per-sandbox stability monitoring.

## VERSION
v1.0

## SEE ALSO
- SANDBOX_ISOLATION_PRIME
- SECURITY_GUARDRAILS_PRIME
- ADVERSARIAL_TESTING_PRIME
