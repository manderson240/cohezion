---
title: Silicon as the Bedrock of Quantum Computers
date: 2026-02-07
tags: [silicon-quantum-computing-platform, quantum-entanglement, quantum-entangled-atomic-sensors, mit-quantum-computing-progress, axion-dark-matter-quantum-sensors]
connectivity: 0.2
cross_domain: 0.38
completion: 0.67
temporal: 1.0
recency: 1.0
connectivity_summary: ★☆☆☆☆ (3/5 links)
completion_summary: 2/3 sections (66%)
conceptual_depth: 1.0
conceptual_label: Pure Theory
similar_papers:
- mit-quantum-computing-progress
- quantum-teleportation-logic-gates
- quantum-entangled-atomic-sensors
- international-year-quantum-2025
dim_conceptual_depth: 1.0
source: https://physicsworld.com/a/could-silicon-become-the-bedrock-of-quantum-computers/
dimensions:
  connectivity: 0.15
  cross_domain: 0
  completion: 100
  temporal: 0.5
  recency: 0.7
  conceptual_depth: 0.5
  algorithm_complexity: 1
  implementation_difficulty: 1
  interdisciplinary_transfer: 0.5
  impact_score: 0.24
aspect: knower
neural:
  activation: 0.651
  stage: mature
  cluster: papers
---
# Silicon as the Bedrock of Quantum Computers

## Summary

Silicon Quantum Computing (SQC), an Australian company founded in 2017 as a UNSW Sydney spin-off by Professor Michelle Simmons (2018 Australian of the Year), has developed the 14|15 quantum computing platform -- named for silicon (element 14) and phosphorus (element 15) on the periodic table. The platform places individual phosphorus atoms with atomic precision into isotopically pure silicon-28 using scanning tunnelling microscopes (STM), creating spin qubits with exceptionally long coherence times due to the ultra-quiet nuclear-spin-free lattice environment.

In December 2025, SQC demonstrated a breakthrough multi-register processor linking 11 qubits across two phosphorus registers (four and five atoms respectively), achieving fidelities up to 99.99%. Crucially, the architecture demonstrated the opposite of the typical quantum scaling problem: qubit quality *strengthened* as qubit count increased, a critical requirement for fault-tolerant systems. Earlier in February 2025, the team published a Nature paper demonstrating 98.9% fidelity on Grover's algorithm without any error correction.

In February 2026, SQC launched Quantum Twins, a world-first application-specific quantum simulator for molecule and materials discovery. Quantum Twins physically encode direct replicas of the quantum systems customers wish to analyze, using arrays of up to 15,000 qubit registers patterned with 0.13 nanometer (atom-level) accuracy. The company demonstrated patterning 250,000 qubit registers in just eight hours (November 2025), de-risking the manufacturing yields needed for commercial scale.

## Key Findings

- **Atomic precision manufacturing**: SQC patterns phosphorus atoms in silicon-28 with 0.13 nm accuracy using STM, the only private quantum computing company that manufactures its own quantum chips
- **Inverse scaling advantage**: The 11-qubit multi-register processor showed increasing fidelity with higher qubit counts (up to 99.99%), defying the typical degradation seen in other quantum architectures
- **Error-correction-free records**: 98.9% fidelity on Grover's algorithm achieved without running any error correction, published in Nature (February 2025)
- **Quantum Twins product**: Application-specific quantum simulators that physically encode replicas of target quantum systems for materials and chemistry discovery
- **Manufacturing at scale**: 250,000 qubit registers patterned in eight hours; full chip design-to-test cycle completed in under a week

## Methodology

The fabrication process starts with isotopically pure silicon-28, which has no nuclear spin in its lattice, creating an environment with minimal magnetic noise for the qubits. Individual phosphorus atoms are precision-placed using custom-designed STMs. Multiple phosphorus donors placed within nanometers of each other create nuclear spin registers sharing a single electron. Two such registers are linked by electron exchange interaction, enabling non-local connectivity across the processor. The company's 25-year manufacturing process development gives it a unique full-stack capability from qubit design through chip fabrication and testing.

## Implications

SQC's results address the central challenge in quantum computing: whether qubit quality can be maintained as systems scale. The demonstrated inverse scaling behavior -- better fidelity at higher qubit counts -- suggests that silicon spin qubits may offer a uniquely scalable path to fault-tolerant quantum computing. The DARPA Quantum Benchmarking Initiative selected SQC for Stage B, and the company announced a collaboration with NVIDIA to develop NVQlink high-speed GPU-quantum interconnects. SQC's roadmap targets the world's first commercial-scale quantum computer by 2033. Telstra has already reported dramatic reductions in model training time using SQC's quantum machine learning systems, and the Australian Defence Force purchased a rack-mounted system for datacenter deployment.

## Primary Sources

- [Could silicon become the bedrock of quantum computers?](https://physicsworld.com/a/could-silicon-become-the-bedrock-of-quantum-computers/) -- Physics World
- [SQC Launches Quantum Twins](https://www.sqc.com.au/news/sqc-launches-quantum-twins) -- SQC official announcement (February 2026)
- [Silicon atom processor links 11 qubits with more than 99% fidelity](https://phys.org/news/2025-12-silicon-atom-processor-links-qubits.html) -- Phys.org (December 2025)
- [SQC Study Shows Silicon-Based Quantum Processor Can Scale Without Loss of Fidelity](https://thequantuminsider.com/2025/12/17/sqc-study-shows-silicon-based-quantum-processor-can-scale-without-loss-of-fidelity/) -- The Quantum Insider
- [SQC 14|15 Qubits](https://www.sqc.com.au/qubits) -- SQC platform page

## Relevance to Cohezion

Relevant to [[enhanced-simulator]] for quantum simulation modeling. The Quantum Twins approach of using physical qubit arrays to simulate quantum chemistry could inform Cohezion's simulation architecture, particularly for modeling molecular interactions and materials properties. The inverse scaling behavior parallels a key question in multi-agent systems: whether adding more agents improves or degrades system quality. [[quantum-computing]], [[quantum-mechanics]]

## Related Concepts

- [[quantum-teleportation-logic-gates]] — silicon qubit arrays and photonic gate teleportation represent complementary paths to modular quantum computers; silicon provides the qubit registers while photonic interfaces enable inter-module communication
- [[amorphous-materials-3d-atomic-structure]]
- [[quantum-entanglement-speed-measurement]]
- [[axion-dark-matter-quantum-sensors]] — high-purity silicon qubits with long coherence times are directly applicable to quantum sensor networks searching for dark matter; the platform described here could serve as the sensing element
- [[quantum-entangled-atomic-sensors]]
- [[supersolid-quantum-state]]
- [[quantum-sensors]]
- [[dark-matter-detection]]
- [[mit-quantum-computing-progress]] — silicon quantum computing and MIT's error correction work are complementary milestones toward fault-tolerant quantum computing
- [[international-year-quantum-2025]] — silicon quantum computing exemplifies the hardware advances highlighted in the International Year of Quantum Science coverage
- [[quantum-information]] — silicon qubit arrays are hardware platforms for quantum information processing and storage
- [[quantum-computing]] — silicon is proposed as the scalable substrate for fault-tolerant quantum computing
