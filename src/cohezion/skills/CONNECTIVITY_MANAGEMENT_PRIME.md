---
name: connectivity-management-prime
description: "Autonomous service discovery, multi-protocol handshake (HTTP/WS), and reliability orchestration within the Cohezion swarm."
metadata:
  version: "1.0.0"
  concepts: ["Truth Anchors", "Failover Logic", "Circuit Breakers", "State Interpolation"]
  source: "src/cohezion/skills/CONNECTIVITY_MANAGEMENT_PRIME.md"
---

# SKILL: CONNECTIVITY_MANAGEMENT_PRIME

## DOMAIN EXPERTISE
Autonomous service discovery, multi-protocol handshake (HTTP/WS), and reliability orchestration within the Cohezion swarm.

## KEY CONCEPTS
- **Truth Anchors**: Using `lsof` or `netstat` to confirm port bindings rather than relying on static configs.
- **Failover Logic**: Failover from premium cloud endpoints to local Ollama fallback (Learning 20/104).
- **Circuit Breakers**: Using `cohezion.reliability.get_circuit()` to prevent cascading failures during service downtime.
- **State Interpolation**: Projecting connectivity health into the 12D manifold for 'Logic Drift' detection.

## INSTRUCTION
1. **Discover**: Query the system state (`lsof -i -P -n | grep LISTEN`) to find active service ports.
2. **Classify**: Map port numbers to services:
   - 8000: SurrealDB (WebSocket/RPC)
   - 8360: Cloud Vault MCP (HTTP/SSE)
   - 11434: Ollama (HTTP/Rest)
   - 22360: Obsidian/Claude Code (Plugin/API)
3. **Verify**: Perform a health check on each identified port (e.g., `/health` for SurrealDB, `/api/tags` for Ollama).
4. **Persist**: Update the local `ConnectivityRegistry` or knowledge graph with the new 'Truth Anchors'.
5. **Monitor**: Attach a `ResourceMonitor` pulse to any service with >0.5 dilation factor.

## ANTI-PATTERNS
- **Static Coupling**: Hardcoding IP/Port addresses in agent tools.
- **Zombie Connections**: Failing to close WebSocket sessions on task completion.
- **VRAM Starvation**: Attempting to connect to Ollama without checking `GTT` availability.

## VERSION
1.0.0
