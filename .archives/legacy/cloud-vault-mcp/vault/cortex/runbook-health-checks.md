---
title: "Patterns/Runbook Health Checks"
date: 2026-02-19
tags: [concept]
aspect: knower
neural:
  activation: 0.9
  stage: mature
  synapse_in: 18
  synapse_out: 11
---
## Definition

Health checks are automated probes that verify the operational status of services, infrastructure, and data pipelines in the Cohezion stack. A health check answers a simple question: "Is this component working right now?" Health checks run proactively (on a schedule or at startup) rather than reactively (after a user reports a failure). They form the first line of defense in the observability stack, catching problems before they impact agent operations.

Health checks range from simple liveness probes (is the process running?) to deep checks (can the service serve a real query end-to-end?). The pattern is widely established in production systems and formalized in Kubernetes's three-probe model (liveness, readiness, startup), which Cohezion adapts for its MCP server infrastructure.

## Key Properties

- **Liveness vs. readiness**: Liveness confirms the process exists and is not deadlocked; readiness confirms it can serve traffic. A service can be live but not ready (e.g., still loading a model). In Kubernetes, failing liveness triggers a container restart; failing readiness removes the pod from traffic rotation.
- **Startup probes**: For services with variable initialization times (e.g., Ollama loading a model), startup probes disable liveness/readiness checks until the initial load completes, preventing premature restarts.
- **Dependency awareness**: Health checks should test downstream dependencies (database, embedding service) not just the local process. A liveness check should be lightweight and dependency-free; a readiness check should verify all dependencies.
- **Fast execution**: Individual health checks should complete in under 5 seconds to avoid blocking startup or monitoring loops.
- **Actionable output**: Report specific failure reasons, not just "unhealthy". Include which dependency failed and why.
- **Idempotency**: Health checks must not modify state -- they observe and report only.
- **Separate endpoints**: Use dedicated endpoints (`/livez`, `/readyz`, `/healthz`) rather than reusing application endpoints, keeping health checking isolated from business logic.

## Health Check Targets

| Component | Check | Command |
|-----------|-------|---------|
| Cloud Vault MCP | HTTP health endpoint | `curl http://127.0.0.1:8360/health` |
| Ollama | API version endpoint | `curl http://localhost:11434/api/version` |
| SurrealDB | Connection test | `surreal isready --conn <url>` |
| Git repository | Size and pack status | `git count-objects -vH` |
| Log rotation | Log file size check | `du -sh /var/log/cohezion/` |
| Disk space | Available space | `df -h /home/` |

## Related Papers

- [[2026-02-10-debug-log-bloat-analysis]]
- [[2026-02-10-claude-log-mining-architecture]]
- [[2026-02-10-phase-a-implementation-complete]]
- [[2026-02-10-telemetry-corruption-fix]]
- [[log-rotation-and-monitoring]]
- [[mcp-infrastructure-architecture]]
- [[runbook-ci-cd-pipeline]]
- [[runbook-ollama-mcp-operations]]
- [[troubleshooting-mcp-infrastructure]]

## Related Concepts

- [[troubleshooting-mcp-infrastructure]] -- the troubleshooting guide used when health checks detect failures
- [[runbook-ollama-mcp-operations]] -- Ollama-specific operations including health checking
- [[runbook-ci-cd-pipeline]] -- CI pipelines that run health checks as pre-deployment gates
- [[non-blocking-observability]] -- observability pattern that health checks contribute to
- [[cerebellum/runbook-health-checks|Runbook: Health Checks (Operational)]] -- full step-by-step health check procedures with cron monitoring, systemd timer setup, and per-service troubleshooting

## Primary Sources

- Kubernetes Documentation. *Configure Liveness, Readiness and Startup Probes*. [https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- Google Cloud Blog. *Kubernetes best practices: Setting up health checks with readiness and liveness probes*. [https://cloud.google.com/blog/products/containers-kubernetes/kubernetes-best-practices-setting-up-health-checks-with-readiness-and-liveness-probes](https://cloud.google.com/blog/products/containers-kubernetes/kubernetes-best-practices-setting-up-health-checks-with-readiness-and-liveness-probes)

## Relevance to Cohezion

Health checks ensure the Cohezion infrastructure is operational before agents begin work. A session that starts with failing MCP servers wastes context tokens on errors and retries. Running health checks at session startup (or via a scheduled cron job) catches failures early and allows operators to restore services before agents need them.

The [[cloud-vault-mcp]] server exposes a `/health` endpoint that verifies both the web server and its downstream connections (SurrealDB, file system access). The Ollama MCP wrapper's health check verifies both the Ollama API and model availability, accounting for the cold-start latency documented in [[runbook-ollama-mcp-operations]]. These health checks integrate with the [[runbook-ci-cd-pipeline|CI/CD pipeline]] as pre-deployment gates.
