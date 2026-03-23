---
title: "Edge Computing"
date: 2026-03-04
tags: [concept, infrastructure, distributed-systems, iot]
aspect: knower
neural:
  activation: 0.89
  stage: mature
  synapse_in: 11
  synapse_out: 10
---

# Edge Computing

## Definition

Edge computing is a distributed computing paradigm that brings computation and data storage closer to the sources of data generation, rather than relying on centralized cloud data centers. By processing data at or near the network edge -- on devices, local servers, or nearby infrastructure nodes -- edge computing reduces latency, conserves bandwidth, and enables real-time decision-making for latency-sensitive applications. The related concept of fog computing, coined by Cisco in 2012, extends cloud capabilities to the local area network level, occupying an intermediate layer between edge devices and the cloud.

## Key Properties

- **Low-latency processing:** Edge nodes process data locally, reducing round-trip times from tens or hundreds of milliseconds (cloud) to single-digit milliseconds. This is critical for autonomous vehicles, industrial control systems, and real-time health monitoring.
- **Bandwidth conservation:** By processing data locally and sending only essential information to the cloud, edge computing reduces network congestion. This is especially important for IoT deployments generating terabytes of sensor data daily.
- **Three-tier architecture (edge-fog-cloud):** The edge layer handles immediate processing, the fog layer provides intermediate aggregation and analytics, and the cloud layer provides long-term storage, model training, and global coordination. Each tier complements the others based on latency, compute, and storage requirements.
- **AI at the edge:** Inference of [[machine-learning]] models (object detection, anomaly detection, NLP) increasingly runs on edge devices using lightweight architectures (MobileNet, TinyML) and specialized accelerators (NPUs, TPUs). Training typically remains in the cloud.
- **Security and privacy:** Processing sensitive data locally reduces exposure to network-based attacks and supports data residency requirements, as raw data need not leave the device or premises.

## Examples

- Autonomous vehicles process camera, LIDAR, and radar data onboard in real-time using edge compute hardware (NVIDIA DRIVE), making safety-critical driving decisions without cloud round-trips.
- Smart factory IoT sensors run edge inference for predictive maintenance, detecting equipment anomalies within milliseconds and triggering alerts before failures occur.
- Content delivery networks (CDNs) like Cloudflare and Akamai cache and serve content from edge locations worldwide, reducing latency for web applications.

## Primary Sources

- Shi, W. et al. (2016). *Edge Computing: Vision and Challenges*. IEEE Internet of Things Journal. [DOI:10.1109/JIOT.2016.2579198](https://doi.org/10.1109/JIOT.2016.2579198)
- Satyanarayanan, M. (2017). *The Emergence of Edge Computing*. IEEE Computer. [DOI:10.1109/MC.2017.9](https://doi.org/10.1109/MC.2017.9)
- Bonomi, F. et al. (2012). *Fog Computing and Its Role in the Internet of Things*. ACM MCC Workshop.

## Related Concepts

- [[machine-learning]] — ML models deployed at the edge for real-time inference
- [[computer-vision]] — vision models optimized for edge deployment (MobileNet, EfficientNet-Lite)
- [[federated-learning]] — distributed training across edge devices without centralizing data
- [[robotics]] — robots rely on edge computing for onboard perception and control
- [[data-pipelines]] — edge processing forms the first stage of data collection pipelines
- [[non-blocking-observability]] — observability systems must account for edge-deployed services
- [[ondevice_learning]] — on-device training and fine-tuning extend edge computing beyond inference to local adaptation
- [[hw_acceleration]] — edge hardware accelerators (NPUs, Neural Engines) enable practical on-device ML

## Related Papers

- [[silicon-quantum-computing-platform]] — advances in quantum hardware may eventually enable quantum processing at the edge
- [[nvidia-nemotron-3-nano-nemo-gym]] — small language models designed for efficient edge deployment

## Relevance to Cohezion

Edge computing principles inform Cohezion's architecture in two ways. First, the concept of processing data close to its source parallels the agent-local context management strategy, where agents maintain local state and only synchronize essential information with the central knowledge graph. Second, edge-fog-cloud tiering mirrors Cohezion's three-layer memory architecture: agent working memory (edge), session context (fog), and persistent vault storage (cloud).

## Agent Outputs

- REMOTE_ACCESS — Remote access guide (Pixelbook setup)
- recovery_walkthrough — Recovery walkthrough for session continuity
- reboot_handoff — Reboot handoff document for session restart
- retrospective_hardware_stability — Retrospective: hardware stability investigation
