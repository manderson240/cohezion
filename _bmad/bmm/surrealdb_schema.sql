---
db: surrealdb
table: mcp_infrastructure
type: schema
description: SurrealDB schema for MCP infrastructure metadata and state tracking
version: 1.0.0
date: 2026-03-05
---

# SurrealDB Schema: MCP Infrastructure

## Tables

### mcp_servers
Store MCP server registrations and metadata.

```sql
DEFINE TABLE mcp_servers SCHEMAFULL;

DEFINE FIELD name ON mcp_servers TYPE string;
DEFINE FIELD port ON mcp_servers TYPE int;
DEFINE FIELD entry_point ON mcp_servers TYPE string;
DEFINE FIELD auto_restart ON mcp_servers TYPE bool DEFAULT true;
DEFINE FIELD status ON mcp_servers TYPE string DEFAULT 'stopped';
DEFINE FIELD created_at ON mcp_servers TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON mcp_servers TYPE datetime DEFAULT time::now();
DEFINE FIELD restart_count ON mcp_servers TYPE int DEFAULT 0;
DEFINE FIELD last_health_check ON mcp_servers TYPE option<datetime>;

DEFINE INDEX idx_port ON mcp_servers COLUMNS port UNIQUE;
DEFINE INDEX idx_name ON mcp_servers COLUMNS name UNIQUE;
DEFINE INDEX idx_status ON mcp_servers COLUMNS status;
```

### mcp_sessions
Store user sessions across all servers.

```sql
DEFINE TABLE mcp_sessions SCHEMAFULL;

DEFINE FIELD session_id ON mcp_sessions TYPE string;
DEFINE FIELD server ON mcp_sessions TYPE record<mcp_servers>;
DEFINE FIELD user_id ON mcp_sessions TYPE option<string>;
DEFINE FIELD data ON mcp_sessions TYPE object DEFAULT {};
DEFINE FIELD created_at ON mcp_sessions TYPE datetime DEFAULT time::now();
DEFINE FIELD expires_at ON mcp_sessions TYPE datetime;
DEFINE FIELD last_activity ON mcp_sessions TYPE datetime DEFAULT time::now();

DEFINE INDEX idx_session_id ON mcp_sessions COLUMNS session_id UNIQUE;
DEFINE INDEX idx_expires ON mcp_sessions COLUMNS expires_at;
DEFINE INDEX idx_server ON mcp_sessions COLUMNS server;
```

### mcp_logs
Store unified logs from all servers.

```sql
DEFINE TABLE mcp_logs SCHEMAFULL;

DEFINE FIELD timestamp ON mcp_logs TYPE datetime DEFAULT time::now();
DEFINE FIELD server ON mcp_logs TYPE record<mcp_servers>;
DEFINE FIELD level ON mcp_logs TYPE string;
DEFINE FIELD message ON mcp_logs TYPE string;
DEFINE FIELD source ON mcp_logs TYPE string;
DEFINE FIELD metadata ON mcp_logs TYPE option<object>;

DEFINE INDEX idx_timestamp ON mcp_logs COLUMNS timestamp;
DEFINE INDEX idx_server ON mcp_logs COLUMNS server;
DEFINE INDEX idx_level ON mcp_logs COLUMNS level;
```

### mcp_metrics
Store performance metrics.

```sql
DEFINE TABLE mcp_metrics SCHEMAFULL;

DEFINE TABLE mcp_metrics CHANGEFEED 1d;

DEFINE FIELD timestamp ON mcp_metrics TYPE datetime DEFAULT time::now();
DEFINE FIELD server ON mcp_metrics TYPE record<mcp_servers>;
DEFINE FIELD metric_type ON mcp_metrics TYPE string;
DEFINE FIELD value ON mcp_metrics TYPE number;
DEFINE FIELD unit ON mcp_metrics TYPE option<string>;

DEFINE INDEX idx_timestamp ON mcp_metrics COLUMNS timestamp;
DEFINE INDEX idx_server ON mcp_metrics COLUMNS server;
DEFINE INDEX idx_type ON mcp_metrics COLUMNS metric_type;
```

### skills_cache
Store cached skills metadata.

```sql
DEFINE TABLE skills_cache SCHEMAFULL;

DEFINE FIELD skill_id ON skills_cache TYPE string;
DEFINE FIELD owner ON skills_cache TYPE string;
DEFINE FIELD repo ON skills_cache TYPE string;
DEFINE FIELD name ON skills_cache TYPE string;
DEFINE FIELD description ON skills_cache TYPE option<string>;
DEFINE FIELD installs ON skills_cache TYPE int DEFAULT 0;
DEFINE FIELD category ON skills_cache TYPE option<string>;
DEFINE FIELD tags ON skills_cache TYPE array<string> DEFAULT [];
DEFINE FIELD cached_at ON skills_cache TYPE datetime DEFAULT time::now();
DEFINE FIELD expires_at ON skills_cache TYPE datetime;
DEFINE FIELD content_hash ON skills_cache TYPE option<string>;

DEFINE INDEX idx_skill_id ON skills_cache COLUMNS skill_id UNIQUE;
DEFINE INDEX idx_owner_repo ON skills_cache COLUMNS owner, repo;
DEFINE INDEX idx_expires ON skills_cache COLUMNS expires_at;
DEFINE INDEX idx_category ON skills_cache COLUMNS category;
```

### skills_content
Store cached skill file content.

```sql
DEFINE TABLE skills_content SCHEMAFULL;

DEFINE FIELD skill_id ON skills_content TYPE string;
DEFINE FIELD content ON skills_content TYPE string;
DEFINE FIELD cached_at ON skills_content TYPE datetime DEFAULT time::now();
DEFINE FIELD expires_at ON skills_content TYPE datetime;
DEFINE FIELD size_bytes ON skills_content TYPE int;

DEFINE INDEX idx_skill_id ON skills_content COLUMNS skill_id UNIQUE;
DEFINE INDEX idx_expires ON skills_content COLUMNS expires_at;
```

### bmad_workflows
Store workflow execution metadata.

```sql
DEFINE TABLE bmad_workflows SCHEMAFULL;

DEFINE FIELD workflow_id ON bmad_workflows TYPE string;
DEFINE FIELD module ON bmad_workflows TYPE string;
DEFINE FIELD path ON bmad_workflows TYPE string;
DEFINE FIELD name ON bmad_workflows TYPE string;
DEFINE FIELD execution_count ON bmad_workflows TYPE int DEFAULT 0;
DEFINE FIELD last_executed ON bmad_workflows TYPE option<datetime>;
DEFINE FIELD avg_duration_ms ON bmad_workflows TYPE option<int>;

DEFINE INDEX idx_workflow_id ON bmad_workflows COLUMNS workflow_id UNIQUE;
DEFINE INDEX idx_module ON bmad_workflows COLUMNS module;
```

### bmad_agents
Store agent activation metadata.

```sql
DEFINE TABLE bmad_agents SCHEMAFULL;

DEFINE FIELD agent_id ON bmad_agents TYPE string;
DEFINE FIELD module ON bmad_agents TYPE string;
DEFINE FIELD name ON bmad_agents TYPE string;
DEFINE FIELD activation_count ON bmad_agents TYPE int DEFAULT 0;
DEFINE FIELD last_activated ON bmad_agents TYPE option<datetime>;

DEFINE INDEX idx_agent_id ON bmad_agents COLUMNS agent_id UNIQUE;
DEFINE INDEX idx_module ON bmad_agents COLUMNS module;
```

## Events

### Auto-cleanup expired sessions
```sql
DEFINE EVENT cleanup_expired_sessions ON mcp_sessions WHEN $event = "CREATE" THEN {
    DELETE FROM mcp_sessions WHERE expires_at < time::now();
};
```

### Update server status on heartbeat
```sql
DEFINE EVENT server_heartbeat ON mcp_servers WHEN $event = "UPDATE" THEN {
    UPDATE mcp_servers SET updated_at = time::now() WHERE id = $after.id;
};
```

## Functions

### Get server health status
```sql
DEFINE FUNCTION fn::get_server_health($server_id: record) {
    LET $server = SELECT * FROM $server_id;
    LET $last_check = $server.last_health_check;
    LET $healthy = $last_check > (time::now() - 60s);
    
    RETURN {
        server: $server_id,
        status: $server.status,
        healthy: $healthy,
        last_check: $last_check,
        restart_count: $server.restart_count
    };
};
```

### Get cache statistics
```sql
DEFINE FUNCTION fn::get_cache_stats() {
    LET $total = COUNT(SELECT * FROM skills_cache);
    LET $expired = COUNT(SELECT * FROM skills_cache WHERE expires_at < time::now());
    LET $by_category = SELECT category, COUNT(*) as count FROM skills_cache GROUP BY category;
    
    RETURN {
        total_cached: $total,
        expired: $expired,
        active: $total - $expired,
        by_category: $by_category
    };
};
```

### Log cleanup
```sql
DEFINE FUNCTION fn::cleanup_old_logs($days: int) {
    LET $cutoff = time::now() - ($days * 1d);
    LET $deleted = DELETE FROM mcp_logs WHERE timestamp < $cutoff;
    RETURN { cleaned: count($deleted) };
};
```

## Queries

### Get active servers
```sql
SELECT * FROM mcp_servers WHERE status = 'running' ORDER BY created_at DESC;
```

### Get recent logs
```sql
SELECT * FROM mcp_logs WHERE timestamp > (time::now() - 1h) ORDER BY timestamp DESC LIMIT 100;
```

### Get popular skills
```sql
SELECT * FROM skills_cache ORDER BY installs DESC LIMIT 20;
```

### Get most used workflows
```sql
SELECT * FROM bmad_workflows ORDER BY execution_count DESC LIMIT 10;
```

### Get session metrics
```sql
SELECT 
    count() as total_sessions,
    server,
    count() / (time::now() - min(created_at)) as sessions_per_hour
FROM mcp_sessions
GROUP BY server;
```

## Integration with Redis

While Redis handles real-time session state, SurrealDB serves as:

1. **Persistent metadata** - Server configurations, workflow stats
2. **Historical data** - Logs, metrics over time
3. **Analytics** - Querying patterns, popular skills
4. **Audit trail** - All changes tracked
5. **Multi-server coordination** - When scaling horizontally

### Data Flow
```
Real-time: Client → Redis → MCP Server
Persistent: MCP Server → SurrealDB (async)
Analytics: SurrealDB ← Queries
```

---

**Schema Version**: 1.0.0
**Last Updated**: 2026-03-05
**Status**: Production Ready
