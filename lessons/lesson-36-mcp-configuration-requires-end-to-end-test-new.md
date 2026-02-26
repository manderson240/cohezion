---
title: MCP Configuration Requires End-to-End Test: Unit Tests Miss Protocol Negotiation Failures
date: 2026-02-23
severity: HIGH
category: testing
tags: [mcp, testing, configuration, integration, protocol]
status: validated
---

# Lesson: MCP Configuration Requires End-to-End Test: Unit Tests Miss Protocol Negotiation Failures

## Context

MCP server configuration involves multiple layers: transport, session initialization, capability negotiation, and tool registration. Unit tests that mock the transport layer miss failures in protocol negotiation.

## Core Learning

**MCP servers must be tested end-to-end with a real client connection, not just unit tested in isolation.**

### Pattern
```bash
# Unit test (necessary but insufficient)
pytest tests/test_tools.py

# End-to-end validation (required)
# MCP Inspector
npx @modelcontextprotocol/inspector http://localhost:8360/mcp

# Health check
curl -s http://127.0.0.1:8360/health
```

## Recommendations

### Do
- Always test MCP servers with a real client connection after configuration changes
- Check server health endpoint before declaring configuration complete

### Don't
- Declare MCP server "working" based on unit tests alone
- Skip client connection test when "only the tool logic changed"

## Related Concepts

- [[mcp-infrastructure-architecture]] - MCP is core Cohezion infrastructure
- [[testing-agent-skills-with-evals]] - The evals framework's end-to-end testing philosophy applies directly to MCP: unit tests of tool logic are insufficient; protocol negotiation must be validated with a real client
- [[circleci-ai-cicd-validation]] - CircleCI Chunk's autonomous CI/CD validation must include MCP end-to-end tests to catch protocol configuration failures that unit tests miss
- [[cloud-vault-mcp]] - the cloud-vault-mcp server requires end-to-end client tests after every configuration change
- [[api-design]] - configuration validation requires end-to-end tests beyond unit tests
- [[concept-isolation]] - MCP protocol testing cannot be isolated to unit tests alone
- [[mcp-model-context-protocol]] - protocol negotiation failures only surface in end-to-end tests
- [[concept-validation]] - MCP configuration must be validated with real client connections
- [[tool-use]] - tool integration via MCP requires end-to-end validation before declaring tools callable

## Validation

**Discovered**: Feb 2026 during cloud-vault-mcp configuration
**Status**: Validated
