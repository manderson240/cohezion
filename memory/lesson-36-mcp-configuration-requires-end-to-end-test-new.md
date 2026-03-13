---
title: MCP Configuration Requires End-to-End Test: Unit Tests Miss Protocol Negotiation Failures
date: 2026-02-23
severity: HIGH
category: testing
cost_of_forgetting: "MCP servers appear working in unit tests but fail in production due to protocol negotiation issues"
tags: [mcp, testing, configuration, integration, protocol]
status: validated
aspect: knower
neural:
  activation: 0.79
  stage: growing
  synapse_in: 12
  synapse_out: 9
---

# Lesson: MCP Configuration Requires End-to-End Test: Unit Tests Miss Protocol Negotiation Failures

## Context

During cloud-vault-mcp configuration in February 2026, the MCP server had full unit test coverage for all tool logic. All tests passed. However, when Claude Code attempted to connect to the server, the connection failed with protocol negotiation errors. The server was listening, the health endpoint returned 200, but the MCP protocol handshake (transport initialization, session creation, capability negotiation, tool registration) was failing at the session layer.

## Problem

MCP server configuration involves multiple layers, and unit tests only cover one of them:

1. **Transport layer**: HTTP server starts and listens -- unit tests may verify this
2. **Session initialization**: MCP client and server exchange protocol version and capabilities -- mocked in unit tests
3. **Capability negotiation**: Client requests tool list, server responds with available tools -- mocked in unit tests
4. **Tool registration**: Tools are registered with correct schemas and callable -- unit tests verify logic but not registration

Unit tests mock the transport and session layers to test tool logic in isolation. This means protocol negotiation failures -- wrong transport configuration, missing capability responses, tool registration format errors -- are invisible to the unit test suite. The server "works" in isolation but fails when a real MCP client connects.

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

## Solution

MCP server testing now follows a two-tier approach:

1. **Unit tests**: Validate tool logic, input parsing, output formatting. These run fast and catch regressions in business logic.
2. **End-to-end tests**: Use the MCP Inspector (`npx @modelcontextprotocol/inspector`) to connect as a real client, negotiate the protocol, list tools, and invoke at least one tool. This catches configuration, transport, and protocol issues.

The end-to-end test is run after every configuration change, not just after tool logic changes. This catches the subtle failure where "only the config changed" but the protocol handshake breaks.

## Prevention

- **Always run MCP Inspector after config changes**: Even if "only the port number changed"
- **Check health endpoint AND client connection**: Health returning 200 does not mean MCP protocol works
- **Include E2E test in CI**: If the MCP server is deployed, the CI pipeline must include a real client connection test
- **Test after dependency updates**: FastMCP version changes can alter protocol behavior

## Cost of Forgetting

- **Silent server failures**: Server appears healthy (HTTP 200) but refuses MCP connections
- **Wasted debugging time**: Protocol errors are cryptic and point to transport/session code, not configuration
- **False confidence**: Unit tests pass, giving the illusion the server is working
- **Production outages**: Claude Code or other MCP clients fail to connect in production despite passing CI

## Recommendations

### Do
- Always test MCP servers with a real client connection after configuration changes
- Check server health endpoint before declaring configuration complete

### Don't
- Declare MCP server "working" based on unit tests alone
- Skip client connection test when "only the tool logic changed"

## Related Concepts

- [[cloud-vault-mcp]] - the cloud-vault-mcp server requires end-to-end client tests after every configuration change
- [[mcp-model-context-protocol]] - protocol negotiation failures only surface in end-to-end tests
- [[testing-agent-skills-with-evals]] - The evals framework's end-to-end testing philosophy applies directly to MCP
- [[circleci-ai-cicd-validation]] - CircleCI Chunk's autonomous CI/CD validation must include MCP end-to-end tests
- [[api-design]] - configuration validation requires end-to-end tests beyond unit tests
- [[concept-isolation]] - MCP protocol testing cannot be isolated to unit tests alone
- [[concept-validation]] - MCP configuration must be validated with real client connections
- [[tool-use]] - tool integration via MCP requires end-to-end validation before declaring tools callable
- [[lesson-18-mock-live-services-in-tests]] - complementary lesson: mock in unit tests, but MCP needs real E2E tests alongside

## Validation

**Discovered**: Feb 2026 during cloud-vault-mcp configuration
**Impact**: Caught protocol negotiation failures invisible to unit tests
**Status**: Validated -- MCP Inspector now part of post-configuration checklist
