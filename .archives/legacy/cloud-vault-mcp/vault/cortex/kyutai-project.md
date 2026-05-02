---
title: Kyutai Project
date: 2026-02-23
tags: [project, ml, research, speech-ai, open-source]
status: active
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 11
  synapse_out: 40
---

# Kyutai Project

Kyutai is a nonprofit AI research lab founded in November 2023 in Paris, backed by Xavier Niel (Iliad), Rodolphe Saadé (CMA CGM), and Eric Schmidt. With an initial budget of approximately 300 million euros, Kyutai pursues an open-science approach to foundation models for speech and audio AI. The Cohezion vault's MCP server was originally templated from the Kyutai MCP server project.

## Key Contributions

### Moshi — Speech-Text Foundation Model

Moshi is the flagship model: a full-duplex spoken dialogue system that processes speech natively rather than converting to text and back. It models two parallel audio streams (its own speech and the user's) plus an "inner monologue" text stream, achieving practical latency as low as 200ms on an L4 GPU.

- **Architecture:** 7B-parameter Temporal Transformer (Helium 7B backbone) with a smaller Depth Transformer for inter-codebook dependencies
- **Training:** 1,016 H100 GPUs on 127 DGX nodes (Scaleway), 170 hours of real conversation plus 20,000 hours of synthetic dialogue
- **License:** CC-BY 4.0 — fully open for commercial use

### Mimi — Neural Audio Codec

A streaming neural audio codec combining semantic and acoustic information at 12 Hz / 1.1 kbps. Mimi underpins all Kyutai audio projects and is designed for training speech language models.

### Additional Open-Source Models

- **Kyutai TTS 1.6B** (July 2025) — streaming text-to-speech using delayed streams modeling for low-latency voice assistant applications
- **Kyutai Pocket TTS** (January 2026) — 100M-parameter voice-cloning model lightweight enough for CPU inference
- **Hibiki** — simultaneous speech translation built on the Moshi multi-stream architecture
- **Helium 1** — modular, multilingual 2B-parameter LLM designed for user-customizable knowledge and language selection

## Sources

- [Kyutai Official Site](https://kyutai.org/)
- [Moshi on GitHub](https://github.com/kyutai-labs/moshi)
- [Moshi Paper (arXiv:2410.00037)](https://arxiv.org/abs/2410.00037)

## Related

- [[mcp-infrastructure-architecture]] — the Cohezion MCP server was originally templated from the Kyutai MCP project
- [[cloud-vault-mcp]] — the Cloud Vault MCP server's lineage traces back to Kyutai's server architecture
- [[mcp-model-context-protocol]] — the protocol standard underlying both Kyutai and Cohezion MCP servers
- [[machine-learning]] — Kyutai's work falls within ML research, specifically speech and audio foundation models
- [[transformer-architecture]] — Moshi uses a dual-transformer design (Temporal + Depth) for multi-stream audio generation
- [[neural-network-architecture]] — the 7B-parameter Helium backbone and codec architectures represent deep neural network design
- [[kyutai-api-specification|Kyutai API Specification]] — comprehensive API documentation for all Kyutai models
- [[kyutai-mcp-server-architecture|Kyutai MCP Server Architecture]] — the MCP server design for Kyutai integration
- [[kyutai-obsidian-plugin-architecture|Kyutai Obsidian Plugin Architecture]] — the Obsidian plugin architecture for Kyutai voice AI
- [[README|Kyutai Benchmarking Guide]] — performance benchmarking framework for the MCP server and plugin
- [[release-metrics]] — Kyutai v0.1.0-alpha performance release metrics: 36.75MB memory, 537 req/60s throughput, production-ready

## Daily References

### Project Lifecycle
- [[2026-02-10-kyutai-plugin-plan-summary]] — execution summary for the Kyutai MCP + Obsidian plugin plan
- [[2026-02-10-KYUTAI-PROJECT-INDEX]] — complete documentation index for all project artifacts
- [[2026-02-10-KYUTAI-PROJECT-COMPLETE]] — project complete milestone: production-ready, 35% faster, 33% under budget
- [[2026-02-10-KYUTAI-PROJECT-FINAL-DELIVERY]] — final delivery: v0.1.0-alpha live on PyPI and Obsidian Marketplace
- [[2026-02-10-FINAL-PROJECT-SUMMARY]] — final project summary: phases 1-4 complete, phase 5 pending
- [[2026-02-10-FINAL-STATUS]] — phase 1-3 status report: 70% complete, on track
- [[2026-02-10-PROJECT-FINAL-DELIVERY]] — project 100% complete, final delivery confirmed
- [[2026-02-10-PROJECT-RETROSPECTIVE]] — execution retrospective and lessons learned from compound engineering
- [[2026-02-11-KYUTAI-PROJECT-CLOSURE]] — project closure: 100% complete, 33% ahead of schedule
- [[2026-02-11-KYUTAI-PROJECT-FINAL-CLOSURE]] — final closure report with executive summary
- [[2026-02-11-MASTER-PROJECT-SUMMARY]] — master project summary: v0.1.0-alpha live, all metrics exceeded
- [[2026-02-11-PROJECT-CLOSURE-FINAL]] — final project closure report: production-ready and marketplace-live
- [[2026-02-11-PROJECT-QUICK-REFERENCE]] — quick reference guide for the completed project

### Phase 3: Test Suite Creation
- [[2026-02-10-kyutai-phase3-progress]] — phase 3 at 50% completion
- [[2026-02-10-kyutai-phase3-live]] — phase 3 active with 4 parallel builders
- [[2026-02-10-kyutai-phase3-complete]] — phase 3 100% complete in 62% of target time

### Phase 4: Integration Testing
- [[2026-02-10-PHASE4-COMPLETE]] — phase 4 validation complete: 20/20 E2E scenarios pass
- [[2026-02-10-PHASE4-COMPLETE-FINAL]] — phase 4 final report: complete and production ready
- [[2026-02-10-phase4-FINAL-completion]] — phase 4 final completion report
- [[2026-02-10-phase4-integration-complete]] — phase 4 integration testing: 100% passed
- [[2026-02-10-agent-tests-final-report]] — agent-tests final report: all QA/testing objectives achieved
- [[2026-02-10-phase4-COMPLETE-summary]] — phase 4 complete summary: 20/20 scenarios passed, production ready

### Phase 5: Release & Publish
- [[2026-02-10-PHASE-5-RELEASE-KICKOFF]] — phase 5 release kickoff: v0.1.0-alpha in progress
- [[2026-02-10-PHASE5-READY]] — release authorization: v0.1.0-alpha ready for marketplace
- [[2026-02-10-PHASE5-RELEASE-AUTHORIZED]] — official release authorization for immediate deployment
- [[2026-02-10-phase5-release-execution]] — phase 5 release execution in progress
- [[2026-02-10-PHASE5-RELEASE-DEPLOYMENT]] — deployment guide for v0.1.0-alpha production release
- [[2026-02-10-PHASE5-COMPLETE]] — phase 5 release complete: production ready
- [[2026-02-11-RELEASE-COMPLETE]] — phase 5 release complete: v0.1.0-alpha live on all channels

## Relevance to Cohezion

Kyutai's open-science philosophy and MCP server architecture directly influenced the Cohezion platform's design. The Kyutai MCP server served as the initial template for the Cloud Vault MCP server, establishing patterns for tool registration, protocol compliance, and modular tool categories that persist in the current implementation.
