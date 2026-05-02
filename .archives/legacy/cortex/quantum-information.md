---
title: Quantum Information
date: 2026-02-23
tags: [domain, physics, quantum-computing]
status: active
aspect: knower
neural:
  activation: 0.96
  stage: mature
  synapse_in: 14
  synapse_out: 13
---

## Definition

Quantum information science (QIS) studies how information is encoded, processed, transmitted, and measured using quantum mechanical systems. Unlike classical information theory (where bits are 0 or 1), QIS operates with qubits that exploit superposition (existing in multiple states simultaneously), entanglement (non-local correlations between particles), and interference (constructive/destructive combination of probability amplitudes) to perform computations and communications that are provably impossible in classical systems.

The field spans three major branches: quantum computing (using quantum gates and circuits to solve computational problems exponentially faster than classical algorithms for specific problem classes), quantum communication (using entanglement and quantum key distribution for provably secure information transfer), and quantum sensing (exploiting quantum coherence for measurements beyond classical precision limits). A unifying theme is that quantum systems process information in fundamentally different ways from classical systems — the no-cloning theorem forbids copying unknown quantum states, entanglement enables correlations without classical analog, and measurement irreversibly collapses superpositions.

## Key Properties

- **Qubit as fundamental unit**: A qubit can exist in a superposition of |0> and |1> states, described by a point on the Bloch sphere — this exponentially increases the information capacity of quantum registers
- **Entanglement as a resource**: Entangled qubit pairs enable quantum teleportation (transferring quantum states without moving particles), superdense coding (sending 2 classical bits per qubit), and distributed quantum computing
- **Quantum error correction (QEC)**: Logical qubits are encoded across multiple physical qubits to protect against decoherence; in 2025, Google demonstrated below-threshold surface codes and new qLDPC codes scaled to hundreds of thousands of qubits
- **No-cloning theorem**: It is impossible to create an identical copy of an arbitrary unknown quantum state — this fundamental constraint enables quantum cryptography but complicates error correction and communication
- **Decoherence as the central challenge**: Quantum information is fragile — environmental interactions destroy superposition and entanglement on timescales from microseconds to seconds depending on the physical platform

## Examples

- **Shor's algorithm**: Factors large integers in polynomial time using quantum Fourier transforms — breaks RSA encryption but requires error-corrected logical qubits not yet available at scale
- **Quantum key distribution (QKD)**: The BB84 protocol uses quantum states to establish cryptographic keys with security guaranteed by physics, not computational assumptions — any eavesdropping attempt measurably disturbs the quantum channel
- **Quantum simulation**: Simulating molecular Hamiltonians on quantum hardware provides exponential speedup over classical methods for drug discovery, catalyst design, and materials property prediction
- **Quantum sensing**: Entangled atomic sensors achieve measurement precision beyond the standard quantum limit, with applications in gravitational wave detection, navigation, and medical imaging

## Primary Sources

- Nielsen, M.A. & Chuang, I.L. (2010). *Quantum Computation and Quantum Information*, 10th Anniversary ed. Cambridge University Press. (The standard reference text)
- Google Quantum AI (2024). *Quantum error correction below the surface code threshold*. Nature. [https://www.nature.com/articles/s41586-024-08449-y](https://www.nature.com/articles/s41586-024-08449-y)
- Riverlane (2025). *Quantum Error Correction: 2025 Trends and 2026 Predictions*. [https://www.riverlane.com/blog/quantum-error-correction-our-2025-trends-and-2026-predictions](https://www.riverlane.com/blog/quantum-error-correction-our-2025-trends-and-2026-predictions)

## Related Papers

- [[quantum-teleportation-logic-gates]] — implements quantum teleportation as a primitive for fault-tolerant logic gates, demonstrating a core quantum information protocol
- [[quantum-entangled-atomic-sensors]] — entangled sensor networks achieve precision beyond classical limits, a direct application of quantum information resources
- [[silicon-quantum-computing-platform]] — silicon-based qubit platforms pursue the scalability needed for practical quantum information processing
- [[mit-quantum-computing-progress]] — tracks academic progress toward error-corrected quantum computation
- [[quantum-entanglement-speed-measurement]] — probes the fundamental speed of entanglement distribution, a key parameter for quantum networks
- [[international-year-quantum-2025]] — global recognition of quantum information science's transformative potential

## Related Concepts

- [[quantum-error-correction]] — the error mitigation framework that makes large-scale quantum information processing viable
- [[quantum-computing]] — the applied computational paradigm within quantum information science
- [[quantum-mechanics]] — provides the theoretical foundation for quantum information processing
- [[quantum-entanglement]] — entanglement is the key quantum resource enabling quantum information protocols
- [[quantum-sensors]] — quantum sensing exploits the same entanglement and coherence resources for precision measurement
- [[quantum-materials]] — quantum materials exhibit entanglement and coherence properties relevant to quantum information hardware
- [[cosmology]] — quantum information concepts (no-cloning, entanglement entropy) apply to black hole physics and cosmological horizons

## Relevance to Cohezion

Quantum information connects to Cohezion's research mission through two pathways. First, the vault tracks the rapid progression of quantum hardware and error correction — from Google's below-threshold surface codes to qLDPC scaling breakthroughs — as a research domain with implications for computational problem-solving at scale. Second, several information-theoretic concepts from QIS have analogs in agentic AI design: the no-cloning theorem parallels the challenge of context preservation across agent sessions, entanglement resources parallel shared state in multi-agent systems, and error correction codes parallel the redundancy patterns used in fault-tolerant agent architectures.
