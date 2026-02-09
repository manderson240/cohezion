---
title: "Quantum Error Correction"
date: 2026-02-07
tags: [concept, quantum-entanglement, quantum-sensors, topological-defects]
---
## Definition

Theory and practice of detecting and correcting errors in quantum computations without destroying quantum information. Foundational work by Alexei Kitaev (toric code, 1997), Freedman & Meyer (planar codes, 2001), and Dennis et al. (threshold analysis, 2002). Surface codes store logical information non-locally in topological features, tolerating error rates below ~1%. Google achieved below-threshold error suppression in 2024 with distance-7 codes on 101 qubits.

## Key Properties

- Stores logical qubits non-locally in ground state degeneracy protected by topological order
- Surface codes use 2D grid with few-body stabilizer measurements (X and Z parity checks)
- Achieves fault tolerance when physical error rate falls below ~0.1-1% threshold
- Requires only local interactions, making it scalable to large systems
- 2024: Google demonstrated logical error rate of 0.143% per cycle with 2.14x improvement per distance increase

## Examples

- Google Quantum AI: distance-7 surface code with 101 qubits achieving 0.143% logical error rate per cycle
- Experimental below-threshold quantum memory validating decades of theoretical predictions

## Primary Sources

- Alexei Kitaev (1997). *Fault-Tolerant Quantum Computation by Anyons*. [https://errorcorrectionzoo.org/c/surface](https://errorcorrectionzoo.org/c/surface)
- Michael Freedman and David Meyer (2001). *Projective Plane and Planar Quantum Codes*. [https://link.springer.com/article/10.1007/s102080010013](https://link.springer.com/article/10.1007/s102080010013)
- Eric Dennis, Alexei Kitaev, Andrew Landahl, John Preskill (2002). *Topological Quantum Memory*. [https://www.nature.com/articles/s41586-024-08449-y](https://www.nature.com/articles/s41586-024-08449-y)

## Related Papers

- [[silicon-quantum-computing-platform]]
- [[mit-quantum-computing-progress]]
- [[beyond-the-quantum-pilot-wave-theory]]

## Related Concepts

- [[quantum-entanglement]]
- [[quantum-sensors]]
- [[topological-defects]]

## Relevance to Cohezion

Quantum error correction represents the kind of specialized knowledge that Cohezion agents extract as patterns and store in the patterns directory for reuse. When agents encounter quantum computing implementation challenges, find_relevant_context surfaces prior error correction explorations, while the Knowledge Graph's topological structure mirrors the topological order concepts underlying surface codes.
