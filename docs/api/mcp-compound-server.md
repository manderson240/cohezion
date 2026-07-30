# MCP Compound Engineering Server - API Documentation

**Version:** 1.0.0  
**Transport:** stdio  
**Server:** cohezion-compound

## Overview

The Compound Engineering MCP Server provides 11 tools for managing multi-session AI workflows with:
- **Session Lifecycle**: Warm-start/clean-shutdown with vault persistence
- **Token Efficiency**: Cache metrics and optimization  
- **Adversarial Review**: Ralph Lopps Red Team + Multiperspective analysis
- **Autoresearch**: Automated optimization identification
- **Experiential Learning**: Capture execution learnings to vault

---

## Tools Reference

### Session Lifecycle Tools

#### `compound_start_session`

Start a compound session with warm-start from vault.

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| max_cache_entries | int | No | 256 | Maximum cache entries to load |
| enable_persistence | bool | No | true | Enable vault persistence |

**Returns:**
```json
{
  "status": "success",
  "session_id": "uuid-string",
  "cache_entries_loaded": 128,
  "persistence_enabled": true
}
```

**Example:**
```python
result = await mcp.call_tool(
    "compound_start_session", {"max_cache_entries": 256, "enable_persistence": True}
)
```

---

#### `compound_check_alignment`

Check request alignment before execution (HIHO threshold).

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| request | string | Yes | - | The request to check |
| threshold | float | No | 0.5 | Coherence threshold (0.0-1.0) |

**Returns:**
```json
{
  "status": "success",
  "coherence": 0.75,
  "should_proceed": true,
  "issues": []
}
```

**Example:**
```python
result = await mcp.call_tool(
    "compound_check_alignment", {"request": "Generate a Python function", "threshold": 0.5}
)
```

---

#### `compound_end_session`

End compound session with clean-shutdown to vault.

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| save_cache | bool | No | true | Save cache to vault |

**Returns:**
```json
{
  "status": "success",
  "session_summary": {
    "session_id": "uuid-string",
    "duration_seconds": 3600,
    "tokens_used": 5000
  }
}
```

---

### Token Cache Tools

#### `cache_get_metrics`

Get token cache efficiency metrics.

**Returns:**
```json
{
  "status": "success",
  "metrics": {
    "overall_hit_rate": 0.82,
    "total_requests": 1000,
    "semantic_cache": {
      "exact_hits": 650,
      "semantic_hits": 120,
      "misses": 230
    }
  }
}
```

---

#### `cache_optimize`

Run cache optimization pass.

**Returns:**
```json
{
  "status": "success",
  "recommendations": {
    "similarity_threshold": 0.65,
    "cache_size": 2048
  }
}
```

---

### Adversarial Review Tools

#### `ralph_lopps_review`

Run Ralph Lopps Red Team adversarial review.

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| code | string | Yes | - | Code to review |
| context | string | No | "" | Optional execution context |

**Returns:**
```json
{
  "status": "success",
  "findings": [
    {
      "severity": "critical",
      "category": "coherence",
      "description": "Missing coherence validation",
      "recommendation": "Add RequestAlignmentAnalyzer.check_alignment()",
      "line_number": 15
    }
  ],
  "total_findings": 1,
  "critical_count": 1
}
```

**Example:**
```python
findings = await mcp.call_tool(
    "ralph_lopps_review",
    {
        "code": "async def execute(req): return await process(req)",
        "context": "Production API endpoint",
    },
)
```

---

#### `multiperspective_review`

Run Blue/Green/Yellow Hat multiperspective review.

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| proposal | string (JSON) | Yes | - | Design proposal as JSON |

**Returns:**
```json
{
  "status": "success",
  "review": {
    "blue_process_optimizations": [...],
    "green_alternatives": [...],
    "yellow_risks": [...],
    "ralph_findings": [...]
  }
}
```

---

### Autoresearch Tools

#### `autoresearch_analyze`

Analyze metrics and identify improvement opportunities.

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| metrics_json | string (JSON) | Yes | - | Metrics to analyze |

**Returns:**
```json
{
  "status": "success",
  "opportunities": [
    {
      "category": "cache",
      "priority": 9,
      "current_value": 0.45,
      "target_value": 0.80,
      "potential_impact": "Reduce token costs by 60%",
      "recommendation": "Increase semantic_cache_size to 4096"
    }
  ]
}
```

---

### Experiential Learning Tools

#### `learning_capture`

Capture execution learning to vault.

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| execution_result_json | string (JSON) | Yes | - | Execution result |

**Returns:**
```json
{
  "status": "success",
  "vault_path": "logs/compound/learning_20260325.json",
  "captured": true
}
```

---

#### `learning_process_execution`

Process execution through full learning loop.

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| execution_result_json | string (JSON) | Yes | - | Execution result |

**Returns:**
```json
{
  "status": "success",
  "results": {
    "learning_captured": true,
    "skill_refinement": {...},
    "research_plan": {...}
  }
}
```

---

#### `skill_refinement_apply`

Apply refinement to a skill.

**Parameters:**
| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| skill_name | string | Yes | - | Skill name (alphanumeric, hyphens, underscores) |
| refinement_type | string | Yes | - | One of: token_optimization, coherence_improvement, cache_optimization |

**Returns:**
```json
{
  "status": "success",
  "skill": "TOKEN_EFFICIENCY_PRIME",
  "refinement_applied": true
}
```

**Validation:**
- `skill_name` must match `^[\w\-]+$`
- `refinement_type` must be in whitelist

---

## Error Handling

All tools return consistent error format:

```json
{
  "status": "error",
  "error": "Human-readable error message"
}
```

Common errors:
- **Session not initialized**: Call `compound_start_session` first
- **Redis unavailable**: Cache persistence disabled, check REDIS_URL
- **Invalid JSON**: Check JSON syntax in *_json parameters
- **Validation failed**: Check parameter constraints

---

## Configuration

**Environment Variables:**
| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| REDIS_URL | No | redis://localhost:6379 | Redis connection string |
| PYTHONPATH | Yes | - | Must include src/ directory |

**Systemd Service:**
```bash
systemctl --user enable cohezion-compound.service
systemctl --user start cohezion-compound.service
```

---

## Examples

### Complete Workflow

```python
# 1. Start session
session = await mcp.call_tool("compound_start_session", {})

# 2. Check alignment
alignment = await mcp.call_tool(
    "compound_check_alignment", {"request": "Complex task description", "threshold": 0.5}
)

if alignment["should_proceed"]:
    # 3. Run adversarial review on code
    review = await mcp.call_tool("ralph_lopps_review", {"code": "async def execute(): ..."})

    # 4. Capture learnings
    await mcp.call_tool(
        "learning_capture",
        {
            "execution_result_json": json.dumps(
                {
                    "request": "Complex task",
                    "success": True,
                    "tokens_used": 5000,
                    "lessons": ["Lesson learned"],
                }
            )
        },
    )

# 5. End session
await mcp.call_tool("compound_end_session", {})
```

### Token Optimization

```python
# Check current metrics
metrics = await mcp.call_tool("cache_get_metrics", {})

if metrics["metrics"]["overall_hit_rate"] < 0.80:
    # Run optimization
    recommendations = await mcp.call_tool("cache_optimize", {})
    
    # Apply recommendations
    print(f"Recommended threshold: {recommendations['recommendations']['similarity_threshold']}")
```

---

## Security Considerations

1. **Input Validation**: All user inputs are validated before processing
2. **Skill Name Sanitization**: Only alphanumeric, hyphens, underscores allowed
3. **Redis Security**: Use localhost-only or authenticated Redis
4. **Vault Access**: Relies on existing vault MCP authentication

---

## Performance Targets

- **Cache Hit Rate**: ≥80%
- **Token Efficiency**: 12x improvement (60K→5K tokens)
- **Vault Latency**: ≤100ms
- **Coherence Threshold**: ≥0.70

---

*Generated: 2026-03-25*  
*Version: 1.0.0*  
*Server: cohezion-compound*
