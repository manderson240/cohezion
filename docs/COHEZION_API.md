# Cohezion API Reference

> **Version:** 0.1.0
> **Base URL:** `http://localhost:8080` (default)
> **Documentation:** Auto-generated at `/docs` (development mode)

---

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Error Responses](#error-responses)
- [Endpoint Categories](#endpoint-categories)
  - [Health & Monitoring](#health--monitoring)
  - [Universe Operations](#universe-operations)
  - [MCP & Knowledge](#mcp--knowledge)
  - [Swarm Operations](#swarm-operations)
  - [Journey Tracking](#journey-tracking)
  - [FLUME VAE](#flume-vae)
  - [RL Policy](#rl-policy)
  - [Skills](#skills)
  - [Observability](#observability)
  - [Compound Engineering](#compound-engineering)
  - [Streaming](#streaming)
  - [Anima](#anima)
  - [Vault](#vault)
- [WebSocket Endpoints](#websocket-endpoints)
- [Data Models](#data-models)

---

## Overview

The Cohezion API provides RESTful endpoints for managing a 12D universe simulation, AI agent orchestration, and neural network operations. The API supports:

- **72+ HTTP endpoints** across 12 categories
- **WebSocket streaming** for real-time pulse data
- **Server-Sent Events (SSE)** for long-running inference
- **Token-efficient routing** with automatic fallback

---

## Authentication

Most endpoints are open by default. The Vault search endpoints require Bearer token authentication.

### Vault Authentication

```bash
curl -H "Authorization: Bearer <token>" \
  "http://localhost:8080/vault/search?q=query"
```

| Header | Value | Required |
|--------|-------|----------|
| `Authorization` | `Bearer <token>` | Yes (Vault only) |

---

## Rate Limiting

The API implements rate limiting via middleware. Limits are configurable per-client IP.

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Maximum requests allowed |
| `X-RateLimit-Remaining` | Remaining requests in window |
| `Retry-After` | Seconds until reset (on 429) |

**Response: 429 Too Many Requests**

```json
{
  "detail": "Rate limit exceeded"
}
```

---

## Error Responses

All errors follow a consistent JSON format:

```json
{
  "detail": "Error message description"
}
```

### HTTP Status Codes

| Code | Meaning | Common Causes |
|------|---------|---------------|
| `200` | Success | Request completed successfully |
| `201` | Created | Resource created (not currently used) |
| `400` | Bad Request | Invalid parameters or malformed request |
| `401` | Unauthorized | Missing or invalid auth token (Vault) |
| `404` | Not Found | Resource doesn't exist |
| `422` | Unprocessable Entity | Validation error (e.g., wrong vector dimensions) |
| `429` | Too Many Requests | Rate limit exceeded |
| `500` | Internal Server Error | Server-side failure |
| `503` | Service Unavailable | Degraded service (search fallback failed) |

---

## Endpoint Categories

### Health & Monitoring

#### GET /health

Basic health check for the API.

**Response:**

```json
{
  "status": "healthy",
  "service": "cohezion"
}
```

---

#### GET /metrics/unified

Comprehensive unified metrics snapshot.

**Response:**

```json
{
  "timestamp": "2026-03-01T12:00:00",
  "metrics": {
    "guardrail_operations": {},
    "cache_performance": {},
    "token_usage": {},
    "session_management": {},
    "resource_utilization": {}
  }
}
```

---

#### GET /metrics/system

System resource metrics including CPU, memory, and Ollama status.

**Response:**

```json
{
  "cpu_percent": 15.2,
  "memory_total_gb": 32.0,
  "memory_available_gb": 24.5,
  "memory_percent": 23.4,
  "ollama_available": true,
  "ollama_models": ["gemma3n", "phi3", "mistral"]
}
```

---

#### GET /metrics/agents

Return registered agent stats from CapabilityRegistry.

**Response:**

```json
{
  "count": 12,
  "agents": [
    {
      "name": "analyst_technical",
      "type": "analyst",
      "description": "Technical analysis agent",
      "metrics": {
        "score": 0.9234,
        "path": "skills/analyst.md"
      }
    }
  ]
}
```

---

#### GET /metrics/training

Training metrics from checkpoint files.

**Response:**

```json
{
  "flume_vae": {
    "status": "trained",
    "epochs": 50,
    "checkpoint": "data/flume/checkpoints/flume_vae_ep50.pt"
  },
  "rl_policy": {
    "status": "trained",
    "episodes": 100,
    "checkpoint": "data/rl/checkpoints/policy_final.pt"
  }
}
```

---

#### GET /metrics/pipeline

Pipeline stage completion status.

**Response:**

```json
{
  "stages": [
    {
      "stage": "mass_sim_export",
      "status": "complete",
      "detail": "5 .npy files"
    },
    {
      "stage": "vae_training",
      "status": "complete",
      "detail": "data/flume/checkpoints/flume_vae_ep50.pt"
    }
  ],
  "complete_count": 4,
  "total_count": 4
}
```

---

#### GET /metrics/tokens

Token efficiency metrics from the compound client.

**Response:**

```json
{
  "cache_hits": 150,
  "cache_misses": 50,
  "cache_hit_rate": 0.75,
  "tokens_saved": 7500,
  "total_calls": 200,
  "model_usage": {
    "gemma3n": 120,
    "phi3": 80
  }
}
```

---

### Universe Operations

#### GET /universe/nodes

Return universe nodes for HologramField visualization.

**Query Parameters:**

| Parameter | Type | Default | Range | Description |
|-----------|------|---------|-------|-------------|
| `limit` | integer | 100 | 1-100,000 | Maximum nodes to return |

**Response:**

```json
{
  "nodes": [
    {
      "id": "node_001",
      "position": [1.2, 3.4, -0.5],
      "axiomatic": [1.2, 3.4, -0.5, 1709347200, 0.52, 0.48, 0.55, 0.51, 0.49, 0.53, 0.50, 0.15],
      "coherence": 0.85,
      "agent_name": "analyst_0",
      "intent": "Analyzing consciousness patterns",
      "node_type": "dream"
    }
  ],
  "source": "surrealdb"
}
```

**Fallback:** Returns synthetic data when SurrealDB is unavailable.

---

#### GET /wallet

Return Ascension Credit wallet state.

**Response:**

```json
{
  "balance": 12500,
  "history": [
    {
      "timestamp": "2026-02-05T00:00:00Z",
      "amount": 500,
      "reason": "Manifold coherence bonus",
      "agent": "orchestrator"
    }
  ]
}
```

---

#### POST /simulate/step

Advance the universe simulation by one tick.

**Response:**

```json
{
  "tick": 42,
  "axiomatic": [0.5, 0.9, 0.2, 1709347200, 0.52, 0.48, 0.55, 0.51, 0.49, 0.53, 0.50, 0.15],
  "coherence": 0.8723,
  "timestamp": 1709347200.123
}
```

---

### MCP & Knowledge

#### GET /mcp/servers

List all available MCP servers.

**Response:**

```json
{
  "servers": [
    {
      "name": "knowledge",
      "type": "knowledge",
      "status": "active"
    },
    {
      "name": "swarm",
      "type": "swarm",
      "status": "active"
    }
  ]
}
```

---

#### GET /mcp/tools

List all available MCP tools.

**Response:**

```json
{
  "tools": ["search", "debate", "analyze"]
}
```

---

#### POST /knowledge/search

Search knowledge base.

**Request Body:**

```json
{
  "query": "consciousness emergence",
  "limit": 5
}
```

**Response:**

```json
{
  "results": [
    {
      "id": "entry_001",
      "content": "Consciousness emerges from...",
      "score": 0.92
    }
  ]
}
```

---

#### GET /knowledge/skills

List all skills.

**Response:**

```json
{
  "skills": ["analyst", "critic", "synthesizer"]
}
```

---

#### GET /knowledge/skills/{skill_name}

Get a specific skill.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `skill_name` | string | Name of the skill |

**Response:**

```json
{
  "name": "analyst",
  "domain_expertise": "Technical analysis",
  "concepts": {},
  "instructions": ["Analyze the input", "Identify patterns"]
}
```

---

#### POST /knowledge/query

Search the knowledge graph for relevant entries.

**Request Body:**

```json
{
  "query": "neural patterns",
  "top_k": 5
}
```

**Response:**

```json
{
  "query": "neural patterns",
  "results": [...],
  "count": 5
}
```

---

### Swarm Operations

#### POST /swarm/debate

Run a multi-perspective debate.

**Request Body:**

```json
{
  "query": "What is consciousness?",
  "perspectives": ["technical", "ethical", "historical"]
}
```

**Response:**

```json
{
  "content": "Synthesized analysis...",
  "confidence": 0.92,
  "model_chain": ["gemma3n", "phi3", "mistral"],
  "processing_time_ms": 1250
}
```

---

#### GET /swarm/perspectives

Get available analyst perspectives.

**Response:**

```json
{
  "perspectives": ["technical", "ethical", "historical", "creative"]
}
```

---

#### GET /swarm/metrics

Get swarm workflow metrics.

**Response:**

```json
{
  "metrics": {
    "total_debates": 42,
    "avg_confidence": 0.85
  }
}
```

---

#### POST /swarm/execute

Plan and execute a swarm from a natural language intent.

**Request Body:**

```json
{
  "intent": "Analyze the latest research on quantum computing",
  "max_agents": 4
}
```

**Response:**

```json
{
  "report_id": "rpt_001",
  "plan_name": "research_analysis",
  "intent": "Analyze the latest research on quantum computing",
  "status": "completed",
  "total_tokens": 1250,
  "total_duration_ms": 3400,
  "tasks": [
    {
      "task_id": "task_001",
      "subject": "Research collection",
      "status": "completed",
      "duration_ms": 800,
      "tokens": 400
    }
  ]
}
```

---

### Journey Tracking

#### GET /journeys

List recent agent journeys.

**Response:**

```json
{
  "journeys": [
    {
      "id": "journey_abc123",
      "query": "What is the meaning of consciousn...",
      "steps": 5
    }
  ]
}
```

---

#### GET /journeys/{journey_id}

Get a specific journey with full trajectory.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `journey_id` | string | Journey identifier |

**Response:**

```json
{
  "journey_id": "journey_abc123",
  "query": "What is consciousness?",
  "steps": [
    {
      "agent_type": "analyst",
      "agent_name": "analyst_technical",
      "perspective": "technical",
      "physics_state": {
        "x": 0.1,
        "y": 0.3,
        "z": 0.5,
        "coherence": 0.85
      }
    }
  ]
}
```

---

#### GET /journeys/{journey_id}/trajectory

Get physics trajectory for visualization.

**Response:**

```json
{
  "trajectory": [
    [0.1, 0.3, 0.5, 0.7, 0.85],
    [0.2, 0.4, 0.6, 0.8, 0.88]
  ]
}
```

---

#### POST /journeys/demo

Create a demo journey to showcase visualization.

**Response:**

```json
{
  "journey_id": "demo_123",
  "steps": 5
}
```

---

#### GET /journeys/{journey_id}/visualize

Render an animated visualization of the journey trajectory.

**Response:** GIF image (`image/gif`)

---

#### GET /journeys/{journey_id}/plot

Render a multi-panel 12D physics visualization.

**Response:** PNG image (`image/png`)

---

#### GET /compare/calm-vs-llm/{journey_id}

Compare CALM continuous trajectory vs standard LLM discrete steps.

**Response:** PNG image (`image/png`)

---

### FLUME VAE

FLUME (Flowing Latent Unified Manifold Encoder) provides 256D vector encoding/decoding using a Variational Autoencoder.

#### POST /flume/train

Trigger FLUME VAE training on synthetic data.

**Request Body:**

```json
{
  "epochs": 50,
  "batch_size": 128,
  "lr": 0.001,
  "z_dim": 256,
  "kl_weight": 0.01,
  "coherence_weight": 0.05,
  "n_samples": 10000
}
```

**Response:**

```json
{
  "epochs_completed": 50,
  "final_mse": 0.0234,
  "final_kl": 0.0156,
  "final_total": 0.0390,
  "checkpoint_path": "data/flume/checkpoints/flume_vae_ep50.pt"
}
```

---

#### GET /flume/status

Check FLUME VAE training status and latest checkpoint.

**Response:**

```json
{
  "trained": true,
  "checkpoint_path": "data/flume/checkpoints/flume_vae_ep50.pt",
  "last_metrics": {
    "epoch": 50,
    "mse": 0.0234,
    "kl": 0.0156
  }
}
```

---

#### POST /flume/encode

Encode a 256D vector through the trained VAE.

**Request Body:**

```json
{
  "vector": [0.5, 0.3, 0.8, ...]  // 256 floats
}
```

**Response:**

```json
{
  "mu": [0.52, 0.31, 0.79, ...],  // Latent mean
  "log_var": [-0.1, -0.2, -0.15, ...],  // Log variance
  "coherence": 0.85
}
```

**Error: 422** - Vector must be exactly 256D

---

#### POST /flume/decode

Decode a latent vector through the VAE.

**Request Body:**

```json
{
  "latent": [0.52, 0.31, 0.79, ...]
}
```

**Response:**

```json
{
  "reconstruction": [0.5, 0.3, 0.8, ...],
  "coherence": 0.85
}
```

---

#### POST /flume/interpolate

Interpolate between two 256D vectors in latent space.

**Request Body:**

```json
{
  "vector_a": [0.1, 0.2, 0.3, ...],  // 256D
  "vector_b": [0.8, 0.7, 0.6, ...],  // 256D
  "ratio": 0.5  // 0.0 = vector_a, 1.0 = vector_b
}
```

**Response:**

```json
{
  "result": [0.45, 0.45, 0.45, ...],
  "coherence": 0.82,
  "mu_a": [0.12, 0.22, 0.32, ...],
  "mu_b": [0.78, 0.68, 0.58, ...]
}
```

**Validation:**
- Both vectors must be 256D
- Ratio must be between 0.0 and 1.0

---

### RL Policy

Reinforcement Learning policy endpoints for navigation in the FLUME environment.

#### POST /rl/train

Trigger RL policy training on FlumeNav-v0.

**Request Body:**

```json
{
  "n_episodes": 100,
  "max_steps": 200,
  "lr": 0.0003,
  "gamma": 0.99
}
```

**Response:**

```json
{
  "episodes_completed": 100,
  "final_reward": 45.6,
  "final_coherence": 0.88,
  "mean_reward": 42.3,
  "checkpoint_path": "data/rl/checkpoints/policy_final.pt"
}
```

---

#### GET /rl/policy/{agent_id}

Inspect a trained RL policy checkpoint.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `agent_id` | string | Agent identifier or "final" |

**Response:**

```json
{
  "exists": true,
  "checkpoint_path": "data/rl/checkpoints/policy_final.pt",
  "parameters": 134000,
  "state_dim": 256,
  "action_dim": 256
}
```

---

#### POST /rl/step

Run a single RL step: state -> policy -> action + coherence.

**Request Body:**

```json
{
  "state": [0.1, 0.2, 0.3, ...]  // 256D state vector
}
```

**Response:**

```json
{
  "action": [0.01, -0.02, 0.03, ...],  // 256D action vector
  "coherence": 0.87
}
```

**Error: 422** - State must be exactly 256D

---

#### POST /rl/episode

Run a full RL episode (up to 200 steps) with the trained policy.

**Response:**

```json
{
  "steps": 150,
  "total_reward": 45.6,
  "mean_coherence": 0.85,
  "final_coherence": 0.88,
  "trajectory": [
    {
      "state_mean": 0.5,
      "state_std": 0.1,
      "action_norm": 0.8,
      "reward": 0.3,
      "coherence": 0.85
    }
  ]
}
```

---

#### GET /rl/policy-info

Return policy metadata: architecture, parameters, training metrics.

**Response:**

```json
{
  "loaded": true,
  "architecture": "PolicyNetwork(shared=[Linear+ReLU x2], mean_head=Linear, log_std=Parameter)",
  "state_dim": 256,
  "action_dim": 256,
  "hidden_dim": 128,
  "parameters": 134000,
  "checkpoint_path": "data/rl/checkpoints/policy_final.pt",
  "training_metrics": [...]
}
```

---

### Skills

#### GET /skills/list

List all available PRIME skills.

**Response:**

```json
{
  "count": 15,
  "skills": [
    "analyst",
    "critic",
    "synthesizer",
    "researcher"
  ]
}
```

---

#### POST /skills/{skill_name}/execute

Parse skill, expand instructions into a plan, and execute via PlanExecutor.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `skill_name` | string | Name of the PRIME skill |

**Request Body:**

```json
{
  "input_text": "Analyze the input data",
  "config": {}
}
```

**Response:**

```json
{
  "skill_name": "analyst",
  "agent_class": "analystAgent",
  "result": "Analysis complete...",
  "status": "executed",
  "plan_steps": [
    {
      "step_index": 0,
      "operation": "analyze",
      "description": "Analyze input patterns",
      "output": "Found 3 patterns",
      "tokens_used": 150,
      "duration_ms": 450
    }
  ],
  "total_tokens": 150,
  "total_duration_ms": 450
}
```

---

#### POST /query/find-capable-agent

Use CapabilityRegistry to find best agents for a query.

**Request Body:**

```json
{
  "query": "technical analysis of neural networks",
  "top_k": 5
}
```

**Response:**

```json
{
  "query": "technical analysis of neural networks",
  "agents": [
    {
      "name": "analyst_technical",
      "type": "analyst",
      "description": "Technical analysis agent",
      "score": 0.9234,
      "path": "skills/analyst.md"
    }
  ]
}
```

---

#### POST /templates/parse

Parse a PRIME skill definition and return structured spec + generated code.

**Request Body:**

```json
{
  "skill_name": "analyst"
}
```

**Response:**

```json
{
  "name": "analyst",
  "domain_expertise": "Technical analysis",
  "concepts": {
    "pattern": "Recurring structure in data"
  },
  "instructions": ["Analyze the input", "Identify patterns"],
  "version": "1.0",
  "see_also": ["critic", "synthesizer"],
  "agent_stub": "...generated code...",
  "config_class": "...generated config..."
}
```

---

### Observability

#### GET /metrics/cache

Get cache performance analytics.

**Response:**

```json
{
  "timestamp": "2026-03-01T12:00:00",
  "cache_performance": {
    "l1_hit_rate": 0.85,
    "l2_hit_rate": 0.72,
    "l3_hit_rate": 0.45
  }
}
```

---

#### GET /metrics/efficiency

Get token efficiency metrics.

**Response:**

```json
{
  "timestamp": "2026-03-01T12:00:00",
  "token_efficiency": {
    "tokens_per_second": 45.5,
    "avg_duration_ms": 1200
  }
}
```

---

#### GET /metrics/guardrails

Get guardrail performance metrics.

**Response:**

```json
{
  "timestamp": "2026-03-01T12:00:00",
  "guardrail_performance": {
    "block_rate": 0.02,
    "check_count": 500
  }
}
```

---

#### GET /metrics/resources

Get resource utilization metrics.

**Response:**

```json
{
  "timestamp": "2026-03-01T12:00:00",
  "resource_performance": {
    "memory_usage_mb": 512,
    "concurrency_waits": 3
  }
}
```

---

#### GET /metrics/health

Get system health score and recommendations.

**Response:**

```json
{
  "timestamp": "2026-03-01T12:00:00",
  "health_score": 0.92,
  "status": "excellent",
  "recommendations": []
}
```

**Status Levels:**
- `excellent` >= 0.90
- `good` >= 0.75
- `fair` >= 0.60
- `poor` < 0.60

---

#### GET /metrics/trends/{metric_name}

Get trend for a specific metric.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `metric_name` | string | Metric to track (e.g., `total_cache_hit_rate`) |

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `window` | integer | 10 | Number of historical records to analyze |

**Response:**

```json
{
  "timestamp": "2026-03-01T12:00:00",
  "metric": "total_cache_hit_rate",
  "trend": {
    "current_value": 0.75,
    "previous_value": 0.72,
    "change_percent": 4.17,
    "direction": "increasing",
    "anomaly_detected": false,
    "anomaly_reason": null
  }
}
```

---

#### GET /metrics/dashboard

Get comprehensive dashboard report.

**Response:**

```json
{
  "timestamp": "2026-03-01T12:00:00",
  "system_status": {
    "overall_health_score": 0.92,
    "health_status": "excellent"
  },
  "metrics": {
    "cache": {...},
    "token_efficiency": {...},
    "guardrails": {...},
    "resources": {...}
  },
  "aggregate_statistics": {
    "total_operations": 1000,
    "aggregate_tokens": 50000,
    "avg_tokens_per_operation": 50.0
  },
  "trends": {...},
  "recommendations": [...]
}
```

---

#### POST /metrics/reset

Reset current metrics (archive to history).

**Response:**

```json
{
  "status": "success",
  "message": "Metrics reset and archived to history",
  "timestamp": "2026-03-01T12:00:00"
}
```

---

### Compound Engineering

#### GET /metrics/compound

Return compound engineering metrics from retrospection analysis.

**Response:**

```json
{
  "total_learnings": 42,
  "top_compound_scores": [
    {"name": "analyst", "score": 0.95}
  ],
  "suggested_refinements": [
    {
      "skill_name": "analyst",
      "reason": "Add error handling patterns",
      "learning_count": 3
    }
  ],
  "total_executions": 156
}
```

---

#### POST /compound/execute

Execute a PRIME skill with live Ollama models via CompoundExecutor.

**Request Body:**

```json
{
  "skill_name": "analyst",
  "input_text": "Analyze the data",
  "model": "gemma3n"
}
```

**Response:**

```json
{
  "skill_name": "analyst",
  "final_output": "Analysis complete...",
  "steps": [
    {
      "step_index": 0,
      "operation": "analyze",
      "description": "Analyze input",
      "output": "Found patterns",
      "tokens_used": 100,
      "duration_ms": 400,
      "model": "gemma3n"
    }
  ],
  "total_tokens": 100,
  "total_duration_ms": 400,
  "model_usage": {"gemma3n": 100}
}
```

---

#### POST /compound/feedback

Run a compound feedback cycle: execute -> analyze -> refine.

**Request Body:**

```json
{
  "skill_name": "analyst",
  "input_text": "Analyze the data",
  "model": "gemma3n",
  "cycles": 1
}
```

**Response:**

```json
{
  "skill_name": "analyst",
  "cycles_completed": 1,
  "total_tokens": 150,
  "total_duration_ms": 600,
  "total_refinements": 2,
  "compound_score_delta": 0.05,
  "patterns": ["error_handling", "pattern_recognition"]
}
```

---

#### GET /compound/health

Return compound system health from the metrics collector.

**Response:**

```json
{
  "total_executions": 156,
  "total_refinements": 23,
  "total_cycles": 45,
  "success_rate": 0.98,
  "total_tokens": 7800,
  "model_usage": {"gemma3n": 5000, "phi3": 2800},
  "top_refined_skills": [...],
  "compound_score_trend": [...]
}
```

---

#### GET /compound/history/{skill_name}

Return compound execution history for a specific skill.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `skill_name` | string | Name of the skill |

**Response:**

```json
{
  "skill_name": "analyst",
  "executions": 50,
  "refinements": 10,
  "cycles": 20,
  "total_tokens": 2500,
  "success_rate": 0.96,
  "latest_execution": 1709347200,
  "latest_refinement": 1709347500
}
```

---

### Streaming

#### POST /inference/stream

Start long-running inference with SSE streaming.

**Request Body:**

```json
{
  "skill_name": "analyst",
  "input_text": "Analyze this large dataset",
  "model": "gemma3n",
  "checkpoint_interval": 5,
  "max_duration_sec": 7200
}
```

**Response:** Server-Sent Events stream

```
data: {"type": "start", "session_id": "sess_123"}

data: {"type": "step", "step_index": 0, "output": "..."}

data: {"type": "checkpoint", "step": 5}

data: {"type": "complete", "result": "..."}
```

**Headers:**
- `X-Session-ID`: Session identifier
- `Content-Type`: `text/event-stream`

---

#### POST /inference/resume/{session_id}

Resume inference from checkpoint.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | string | Session to resume |

**Response:** Server-Sent Events stream (same as `/inference/stream`)

---

#### DELETE /inference/cancel/{session_id}

Request graceful session cancellation.

**Response:**

```json
{
  "message": "Cancellation requested for sess_123"
}
```

---

#### GET /inference/sessions

List all active sessions.

**Response:**

```json
{
  "sessions": ["sess_123", "sess_456"]
}
```

---

#### GET /inference/status/{session_id}

Get session status.

**Response:**

```json
{
  "session_id": "sess_123",
  "active": true,
  "state": {
    "current_step": 5,
    "total_steps": 10,
    "intermediate_results_count": 5,
    "model_usage": {"gemma3n": 500}
  }
}
```

---

#### POST /inference/close/{session_id}

Close and clean up session.

**Response:**

```json
{
  "message": "Session sess_123 closed"
}
```

---

### Anima

#### GET /anima/narration

Generate narration for current system state.

**Response:**

```json
{
  "narration": "The system hums with coherent patterns...",
  "source": "ollama",
  "generation_time_ms": 450
}
```

---

#### GET /anima/health

Check Anima health status.

**Response:**

```json
{
  "status": "healthy",
  "ollama": {
    "available": true,
    "target_available": true
  },
  "model": "gemma3n",
  "model_available": true
}
```

---

#### POST /anima/narration

Generate narration for provided system state.

**Request Body:**

```json
{
  "coherence_value": 0.85,
  "active_agent_count": 3,
  "recent_events": ["step_completed", "checkpoint_saved"],
  "skill_count": 5,
  "session_depth": 2
}
```

**Response:** Same as GET /anima/narration

---

### Vault

#### POST /vault/search

Search the vault using natural language (requires auth).

**Headers:**

| Header | Value |
|--------|-------|
| `Authorization` | `Bearer <token>` |

**Request Body:**

```json
{
  "query": "neural network patterns",
  "limit": 10
}
```

**Response:**

```json
{
  "results": [
    {
      "id": "record_001",
      "content": "Neural patterns emerge...",
      "similarity": 0.92
    }
  ],
  "status": "healthy",
  "empty": false,
  "refinement_suggestion": null,
  "latency_ms": 45.2
}
```

---

#### GET /vault/search

Search the vault using GET request (requires auth).

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `q` | string | required | Search query |
| `limit` | integer | 10 | Max results (1-10) |

**Response:** Same as POST /vault/search

---

#### GET /vault/stats

Get vault search engine stats.

**Response:**

```json
{
  "record_count": 150,
  "index_status": "healthy",
  "last_updated": "2026-03-01T12:00:00",
  "keyword_cache_size": 150,
  "stats": {
    "hnsw_indexed": true,
    "fallback_used": false
  }
}
```

---

## WebSocket Endpoints

### WS /pulse

Stream 12D state pulses to the frontend.

**Connection:**

```javascript
const ws = new WebSocket('ws://localhost:8080/pulse');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // data.type === 'pulse'
  // data.payload.brane = [physics, biology, logic, quantum, field, control, novelty, precipitation]
};
```

**Message Format:**

```json
{
  "type": "pulse",
  "payload": {
    "brane": [0.85, 0.52, 0.51, 0.53, 0.30, 1.0, 0.03, 0.75]
  }
}
```

**Dimensions:**
1. **physics** - System energy (1 - CPU norm)
2. **biology** - Organic complexity
3. **logic** - Reasoning coherence
4. **quantum** - Uncertainty measure
5. **field** - GPU pressure (VRAM norm)
6. **control** - Stability (dilation factor)
7. **novelty** - Entropy (0.02-0.05)
8. **precipitation** - Output coherence

**Interval:** ~500ms

---

## Data Models

### Common Types

#### PhysicsState

```typescript
{
  x: number;              // Spatial X (-1 to 1)
  y: number;              // Spatial Y (-1 to 1)
  z: number;              // Spatial Z (0 to 1, synthesis progress)
  time: number;           // Temporal dimension (0 to 1)
  mass: number;           // Information density (0 to 1)
  sentiment: number;      // Emotional valence (0 to 1)
  complexity: number;     // Cognitive complexity (0 to 1)
  factuality: number;     // Groundedness (0 to 1)
  connectivity: number;   // Network connections (0 to 1)
  stability: number;      // System stability (0 to 1)
  novelty: number;        // Innovation factor (0 to 1)
  coherence: number;        // Overall coherence (0 to 1)
}
```

#### Journey

```typescript
{
  journey_id: string;
  query: string;
  steps: JourneyStep[];
  final_response?: string;
  final_confidence?: number;
}
```

#### JourneyStep

```typescript
{
  agent_type: "analyst" | "critic" | "synthesizer";
  agent_name: string;
  perspective?: string;
  input_text: string;
  output_text: string;
  physics_state: PhysicsState;
  duration_ms: number;
  confidence: number;
}
```

### Enumerations

#### AgentType

- `analyst` - Analysis and pattern recognition
- `critic` - Evaluation and contradiction detection
- `synthesizer` - Integration and final output

#### HealthStatus

- `excellent` - Score >= 0.90
- `good` - Score >= 0.75
- `fair` - Score >= 0.60
- `poor` - Score < 0.60

---

## Pagination

Pagination is not currently implemented. Most list endpoints support a `limit` parameter for basic result restriction.

---

## Versioning

Current API version: **0.1.0**

Version is included in the OpenAPI schema at `/docs` (development mode).

---

## Additional Resources

- **OpenAPI Spec:** `/docs` (development mode)
- **ReDoc:** `/redoc` (development mode)
- **Source:** `src/cohezion/api/`

---

## Changelog

### v0.1.0 (2026-03-01)
- Initial API release
- 72+ endpoints across 12 categories
- WebSocket streaming support
- SSE long-running inference
- FLUME VAE integration
- RL policy management
- Compound engineering feedback loops
