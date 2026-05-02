# SKILL: SANDBOX_ISOLATION_PRIME

## DOMAIN EXPERTISE
Providing hardware-enforced isolation for agentic code execution, ensuring system safety and resource predictability during autonomous research missions. Supports multiple isolation backends (Docker, systemd-run, subprocess), typed resource profiles, divergence detection, and ResourceMonitor integration.

## KEY TEXTS & CONCEPTS
- **Containerized Universe**: The pattern of wrapping an agent's entire execution context in a container.
- **Resource Hardening**: Applying strict limits on CPU (shares/quota) and Memory (swappiness/limit) to prevent OOM lockups.
- **Stateless Precipitation**: Executing code that produces output files in a transient volume, which are then harvested and the environment destroyed.
- **Sandbox Profiles**: Typed resource envelopes (LIGHT/MEDIUM/HEAVY/CUSTOM) that define memory, CPU, timeout, network, GPU, and divergence thresholds per simulation.
- **Multi-Backend Isolation**: Docker (strongest), systemd-run (native cgroups, near-zero overhead), subprocess with rlimits (always available).
- **Divergence Detection**: Per-sandbox monitoring for NaN/Inf, statistical outliers (Nσ), and HIHO coherence drift from the 0.5 target.
- **Backpressure Integration**: SandboxManager queries ResourceMonitor dilation_factor to delay launches under system pressure.

## INSTRUCTION

1. **Select a Profile**: Choose a `SandboxTier` (LIGHT/MEDIUM/HEAVY) or construct a `SandboxProfile` for CUSTOM workloads.
2. **Initialize via SandboxManager**: Call `SandboxManager.run_simulation(script, tier, profile, files, env)` — the manager selects the best available backend automatically.
3. **Backend Selection**: `select_backend()` probes Docker > systemd-run > subprocess and returns the strongest available option.
4. **Apply Constraints**: The backend translates the profile into enforcement primitives:
   - Docker: `mem_limit`, `cpu_quota`, `network_mode: none`
   - systemd-run: `--scope -p MemoryMax= -p CPUQuota=`
   - subprocess: `resource.setrlimit(RLIMIT_AS)`, `resource.setrlimit(RLIMIT_CPU)`
5. **Inject Payload**: Stream script content and input files into the sandbox (tar archive for Docker, filesystem for process-based).
6. **Monitor Execution**: `DivergenceDetector` tracks per-sandbox coherence, numerical stability, and statistical outliers at the profile's `coherence_check_interval`.
7. **Harvest & Purge**: Extract precipitated artifacts, deregister from ResourceMonitor, and destroy the sandbox.

## VERSION
v1.0

## SEE ALSO
- SIMULATION_PROFILES_PRIME
- SECURITY_GUARDRAILS_PRIME
- ADVERSARIAL_TESTING_PRIME
