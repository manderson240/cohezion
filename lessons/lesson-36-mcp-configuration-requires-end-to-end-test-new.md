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

## Validation

**Discovered**: Feb 2026 during cloud-vault-mcp configuration
**Status**: Validated
