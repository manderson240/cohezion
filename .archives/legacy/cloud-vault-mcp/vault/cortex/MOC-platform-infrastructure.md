---
title: "MOC — Platform Infrastructure"
date: 2026-03-04
tags: [moc, navigation, infrastructure, mcp, surrealdb]
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 15
  synapse_out: 39
---

# Map of Content — Platform Infrastructure

## Overview

The platform infrastructure layer powers Cohezion's ability to persist knowledge, serve agent context, and connect AI systems to external tools. This spans the MCP protocol that standardizes tool integration, the SurrealDB graph database that stores agent context, the Ollama embedding service for semantic search, and the CI/CD pipelines that keep it all running reliably. Understanding this layer is essential for anyone extending Cohezion's capabilities or debugging operational issues.

## Core Concepts

- [[mcp-model-context-protocol]] — Open standard for connecting AI systems to external tools and data sources
- [[cloud-vault-mcp]] — The Cloud Vault MCP server providing programmatic access to the Cohezion vault
- [[huggingface]] — HuggingFace ecosystem integration (Hub API, Inference, MTEB, smolagents, TGI, Spaces) → remaining work tracked in [[2026-03-05-huggingface-integration-remaining-work]]
- [[mcp-infrastructure-architecture]] — System overview of how MCP servers bridge Claude Code to local services
- [[surrealdb]] — Multi-model database combining graph, document, and relational capabilities for agent context
- [[graph-databases]] — Node-and-edge data model that makes relationship traversal natural and efficient
- [[knowledge-graph-systems]] — Information networks that enable multi-hop reasoning across concepts
- [[graphrag-knowledge-graph-with-surrealdb]] — Graph-augmented RAG using typed relationships instead of flat vector indices
- [[semantic-search]] — Meaning-based retrieval that complements keyword search and wiki-link traversal
- [[api-design]] — Interface design discipline underpinning MCP, tool contracts, and service boundaries
- [[tool-use]] — Agent capability to invoke external functions, APIs, and services during reasoning
- [[non-blocking-observability]] — Telemetry patterns that never interrupt the primary agent workflow

## Key Decisions

- [[2026-02-13-next-10-phases-graphrag-roadmap]] — 10-phase roadmap for GraphRAG implementation with SurrealDB
- [[2026-02-12-cloudflare-tunnel-for-persistent-mcp-remote-access]] — Persistent remote access to MCP servers via Cloudflare Tunnel
- [[2026-02-10-claude-log-mining-architecture]] — Systematic log mining for alignment patterns and token waste signals
- [[docs/plans/2026-03-12-compound-graph-context]] — Implementation plan to make SurrealDB graph active: cron briefing + UserPromptSubmit hook for ~50% token savings

## Patterns

- [[pattern-compound-engineering]] — Execute-observe-extract-index-inject meta-pattern for knowledge compounding
- [[role-based-multi-agent-coordination]] — Assigning specialist roles to agents for parallel infrastructure work
- [[extraction-pipeline-spec]] — 12D extraction pipeline: SurrealDB neuron vectors → FLUME VAE training data using unified physics forces (gravity/EM/strong/weak)

## Research Papers

- [[agentic-ai-foundation-mcp-linux-foundation]] — MCP donated to Linux Foundation for community governance
- [[anthropic-mcp-apps-claude-integrations]] — Anthropic embedding Slack, Figma, Asana inside Claude via MCP
- [[surrealdb-graph-databases]] — SurrealDB as a graph-native multi-model database
- [[knowledge-graph-semantic-relationships]] — Semantic relationship modeling in knowledge graphs
- [[knowledge-graphs-semantic-web]] — Knowledge graphs and the Semantic Web (RDF, OWL, SPARQL)
- [[schema-design-relational]] — Relational schema design principles for data modeling
- [[service-layer-architecture]] — Service layer patterns for separation of concerns
- [[circleci-ai-cicd-validation]] — CI/CD for AI developers with autonomous validation agents
- [[operational-data-ai-agents]] — Operational data quality as the foundation for agentic AI
- [[data-engineering-ai-era-2026]] — Data engineering evolution from ETL to agent-serving pipelines

## Lessons Learned

- [[lesson-openclaw-node24-setup]] — OpenClaw requires Node 24; nvm setup for Playwright MCP compatibility
- [[lesson-surrealdb-schema-design]] — Record-centric schema outperforms table-centric for agent context graphs
- [[lesson-36-mcp-configuration-requires-end-to-end-test-new]] — MCP unit tests miss protocol negotiation failures; e2e tests required
- [[lesson-10-gitlab-ci-runner]] — Local test pass does not guarantee CI pass; environment parity matters
- [[lesson-35-non-blocking-observability-pattern-new]] — Synchronous telemetry caused 100+ second latency; must be async

## Runbooks & Troubleshooting

- [[SETUP_GUIDE|MCP Tunnel Deployment Guide]] — Expose local vault via public HTTPS URL with Cloudflare tunnel, systemd persistence, and API key auth
- [[runbook-ci-cd-pipeline]] — CI/CD pipeline for linting, testing, and deploying vault tooling
- [[runbook-ollama-mcp-operations]] — Operational procedures for the Ollama embedding MCP server
- [[runbook-health-checks]] — Automated probes verifying service health across the Cohezion stack
- [[runbook-benchmarking-validation]] — Performance benchmarking framework for optimization validation
- [[troubleshooting-mcp-infrastructure]] — Diagnostic procedures for MCP server failures: connectivity, auth, upstream dependencies

## Experiments

- [[2026-02-12-graphrag-phase-1-sql-syntax-errors-block-imports]] — First GraphRAG import attempt; SurrealQL syntax issues discovered

## Platform Scale

- [[2026-03-08-platform-inventory-441-modules]] — March 2026 inventory: 441 Python modules, 90K LOC, 3,200+ tests, 12+ MCP servers, 7 epics — full platform scale snapshot

## Start Here

- **New to this topic?** Start with [[mcp-model-context-protocol]]
- **Looking for patterns?** See [[pattern-compound-engineering]]
- **Recent work:** [[cloud-vault-mcp]]

## Related Maps

- [[MOC-compound-engineering]]
- [[MOC-safety-alignment]]
- [[MOC-astrophysics]]
