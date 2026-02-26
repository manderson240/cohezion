---
title: Ollama Context Management
date: 2026-02-23
tags: [infrastructure, ollama, performance]
status: stub
---

# Ollama Context Management

Strategies for managing context windows in Ollama-served models — truncation, summarization, and context budget tracking.

## Related
- [[lesson-06-ollama-latency]]
- [[mcp-infrastructure-architecture]]
- [[2026-02-09-ollama-context-management]] — the decision record that defined the Model Wrangler extension strategy for Ollama context window management
- [[2026-02-09-ollama-mcp-server]] — decision to elevate Ollama management to infrastructure via a dedicated MCP server with auto context chunking and model selection
- [[context-management]] — parent concept; Ollama context management is a concrete implementation of the broader context management framework for LLMs
