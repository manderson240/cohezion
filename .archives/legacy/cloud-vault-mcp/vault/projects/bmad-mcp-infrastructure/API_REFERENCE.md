# BMAD MCP API Reference

Complete API reference for the BMAD MCP server infrastructure.

## Base URLs

| Server | Port | URL |
|--------|------|-----|
| BMAD MCP | 8361 | `http://localhost:8361` |
| Skills.sh MCP | 8362 | `http://localhost:8362` |
| MCP Manager | 8370 | `http://localhost:8370` |

## BMAD MCP Server (Port 8361)

### Health Check
```bash
GET /health
```
Returns server health status.

**Response:**
```json
{
  "status": "healthy",
  "server": "bmad",
  "port": 8361
}
```

### Server Info
```bash
GET /
```
Returns server information.

**Response:**
```json
{
  "name": "BMAD MCP Server",
  "version": "6.0.4",
  "port": 8361,
  "modules": 6,
  "workflows": 696,
  "agents": 28
}
```

---

## BMAD Tools

### Core Tools

#### bmad_help
Get interactive help and recommendations.

```bash
POST /tools/bmad_help
Content-Type: application/json

{
  "query": "create a prd",
  "context": "Starting a new product",
  "session_id": "optional-session-id"
}
```

**Response:**
```json
{
  "tool": "bmad_help",
  "query": "create a prd",
  "suggestions": [
    {"command": "bmad_bmm_create_prd", "description": "Create a Product Requirements Document"},
    {"command": "bmad_bmm_create_story", "description": "Create user stories"}
  ],
  "available_modules": ["bmm", "gds", "cis", "tea", "bmb", "core"]
}
```

#### bmad_status
Get server and session status.

```bash
POST /tools/bmad_status
Content-Type: application/json

{
  "session_id": "optional-session-id"
}
```

**Response:**
```json
{
  "tool": "bmad_status",
  "version": "6.0.4",
  "modules": ["bmm", "gds", "cis", "tea", "bmb", "core"],
  "workflows_available": 696,
  "agents_available": 28,
  "redis_connected": true
}
```

### BMM Tools (Business Method Module)

#### bmad_bmm_create_prd
Create a Product Requirements Document.

```bash
POST /tools/bmad_bmm_create_prd
Content-Type: application/json

{
  "product_idea": "A mobile app for tracking daily habits",
  "target_users": "Productivity enthusiasts aged 25-45",
  "key_features": ["Daily streaks", "Reminders", "Analytics"],
  "session_id": "optional"
}
```

**Response:**
```json
{
  "tool": "bmad_bmm_create_prd",
  "workflow": "bmm/2-plan-workflows/create-prd.md",
  "next_steps": [
    "Review and refine the PRD",
    "Use bmad_bmm_validate_prd to validate",
    "Use bmad_bmm_create_architecture"
  ],
  "session_id": "uuid"
}
```

#### bmad_bmm_create_story
Create a user story.

```bash
POST /tools/bmad_bmm_create_story
Content-Type: application/json

{
  "story_title": "As a user, I want to track my daily water intake",
  "acceptance_criteria": [
    "User can log water intake",
    "Daily goal is displayed",
    "Streak counter works"
  ],
  "priority": "high",
  "points": 5
}
```

#### bmad_bmm_sprint_planning
Plan a sprint.

```bash
POST /tools/bmad_bmm_sprint_planning
Content-Type: application/json

{
  "stories": [
    {"title": "Story 1", "points": 3},
    {"title": "Story 2", "points": 5}
  ],
  "sprint_goal": "Complete authentication feature",
  "capacity": 40
}
```

**Response:**
```json
{
  "tool": "bmad_bmm_sprint_planning",
  "sprint_plan": {...},
  "capacity_utilization": "60.0%"
}
```

#### bmad_bmm_dev_story
Develop a user story.

```bash
POST /tools/bmad_bmm_dev_story
Content-Type: application/json

{
  "story_id": "story-123",
  "tech_stack": "Python/FastAPI",
  "existing_code": "reference to codebase"
}
```

#### bmad_bmm_code_review
Review code changes.

```bash
POST /tools/bmad_bmm_code_review
Content-Type: application/json

{
  "code_changes": "diff or file content",
  "review_type": "general",
  "focus_areas": ["security", "performance"]
}
```

### GDS Tools (Game Dev Studio)

#### bmad_gds_create_game_brief
Create a game design brief.

```bash
POST /tools/bmad_gds_create_game_brief
Content-Type: application/json

{
  "game_concept": "A puzzle game with time manipulation mechanics",
  "target_platform": "PC/Steam",
  "genre": "Puzzle"
}
```

**Response:**
```json
{
  "tool": "bmad_gds_create_game_brief",
  "game_brief": {...},
  "brief_sections": [
    "Game Concept",
    "Target Audience",
    "Core Mechanics",
    "Art Style",
    "Platform Requirements"
  ]
}
```

#### bmad_gds_game_architecture
Design game architecture.

```bash
POST /tools/bmad_gds_game_architecture
Content-Type: application/json

{
  "game_brief_id": "brief-123",
  "engine_choice": "Unity",
  "multiplayer": false
}
```

### CIS Tools (Creative Intelligence Suite)

#### bmad_cis_brainstorming
Facilitate brainstorming.

```bash
POST /tools/bmad_cis_brainstorming
Content-Type: application/json

{
  "topic": "New features for our product",
  "participants": 4,
  "timebox_minutes": 30,
  "techniques": ["mind-mapping", "crazy-8s"]
}
```

**Response:**
```json
{
  "tool": "bmad_cis_brainstorming",
  "brainstorming_session": {...},
  "techniques_suggested": [
    "Mind Mapping",
    "Rapid Ideation",
    "Yes, And...",
    "Crazy 8s",
    "SCAMPER"
  ]
}
```

### TEA Tools (Test Architecture Enterprise)

#### bmad_tea_test_design
Design tests for a feature.

```bash
POST /tools/bmad_tea_test_design
Content-Type: application/json

{
  "feature_description": "User authentication system",
  "risk_level": "high",
  "test_types": ["unit", "integration", "e2e"]
}
```

### BMB Tools (BMAD Builder)

#### bmad_bmb_create_agent
Create a custom BMAD agent.

```bash
POST /tools/bmad_bmb_create_agent
Content-Type: application/json

{
  "agent_name": "custom-dev",
  "role": "Senior Developer",
  "capabilities": ["Python", "FastAPI", "Redis"],
  "communication_style": "professional"
}
```

#### bmad_party_mode
Multi-agent collaboration.

```bash
POST /tools/bmad_bmad_party_mode
Content-Type: application/json

{
  "objective": "Design a new feature",
  "agents": ["bmm-pm", "bmm-architect", "bmm-dev"],
  "duration_minutes": 60
}
```

### Utility Tools

#### bmad_list_workflows
List available workflows.

```bash
POST /tools/bmad_list_workflows
Content-Type: application/json

{
  "module": "bmm"  // Optional: filter by module
}
```

**Response:**
```json
{
  "tool": "bmad_list_workflows",
  "count": 30,
  "workflows": [
    {"id": "bmm/create-prd", "module": "bmm", "name": "create-prd"},
    {"id": "bmm/sprint-planning", "module": "bmm", "name": "sprint-planning"}
  ],
  "modules": ["bmm", "gds", "cis", "tea", "bmb", "core"]
}
```

#### bmad_list_agents
List available agents.

```bash
POST /tools/bmad_list_agents
Content-Type: application/json

{
  "module": "bmm"  // Optional: filter by module
}
```

#### bmad_index_docs
Index project documentation.

```bash
POST /tools/bmad_index_docs
Content-Type: application/json

{
  "project_path": ".",
  "include_patterns": ["*.md", "*.py", "*.js"]
}
```

---

## Resources API

### Get Workflow
```bash
GET /resources/workflows/{module}/{path}
```

Example:
```bash
GET /resources/workflows/bmm/2-plan-workflows/create-prd/workflow-create-prd
```

**Response:**
```json
{
  "id": "bmm/2-plan-workflows/create-prd",
  "content": "# Create PRD Workflow\n\n## Steps...",
  "module": "bmm"
}
```

### Get Agent
```bash
GET /resources/agents/{agent_id}
```

Example:
```bash
GET /resources/agents/bmm-pm
```

**Response:**
```json
{
  "id": "bmm-pm",
  "module": "bmm",
  "name": "pm",
  "content": "# Product Manager Agent\n\nYou are a product manager..."
}
```

### List Modules
```bash
GET /resources/modules
```

---

## Skills.sh MCP Server (Port 8362)

### Health Check
```bash
GET /health
```

### Server Info
```bash
GET /
```

### Tools

#### skills_search
Search for skills.

```bash
POST /tools/skills_search
Content-Type: application/json

{
  "query": "docker",
  "category": "DevOps",
  "limit": 20
}
```

**Response:**
```json
{
  "tool": "skills_search",
  "query": "docker",
  "count": 20,
  "skills": [
    {
      "id": "docker-setup",
      "name": "docker-setup",
      "owner": "example",
      "repo": "docker-skills",
      "full_id": "example/docker-skills",
      "description": "Docker containerization best practices",
      "installs": 15000
    }
  ]
}
```

#### skills_get
Get skill details.

```bash
POST /tools/skills_get
Content-Type: application/json

{
  "skill_id": "vercel-labs/skills"
}
```

#### skills_install
Install a skill locally.

```bash
POST /tools/skills_install
Content-Type: application/json

{
  "skill_id": "vercel-labs/skills"
}
```

**Response:**
```json
{
  "tool": "skills_install",
  "skill_id": "vercel-labs/skills",
  "status": "success",
  "output": "Skill installed successfully"
}
```

#### skills_execute
Execute a skill (fetch content).

```bash
POST /tools/skills_execute
Content-Type: application/json

{
  "skill_id": "vercel-labs/skills"
}
```

**Response:**
```json
{
  "tool": "skills_execute",
  "skill_id": "vercel-labs/skills",
  "source": "cache",
  "content": "---\nname: find-skills...",
  "truncated": false,
  "full_length": 1234
}
```

#### skills_list
List skills.

```bash
POST /tools/skills_list
Content-Type: application/json

{
  "category": "Development",
  "trending": true,
  "limit": 20,
  "installed_only": false
}
```

#### skills_categories
List categories.

```bash
POST /tools/skills_categories
```

#### skills_sync
Sync cache with remote.

```bash
POST /tools/skills_sync
Content-Type: application/json

{
  "force": true
}
```

#### skills_cache_info
Get cache statistics.

```bash
POST /tools/skills_cache_info
```

**Response:**
```json
{
  "tool": "skills_cache_info",
  "stats": {
    "total_cached": 100,
    "max_size": 1000,
    "ttl_hours": 24,
    "cache_full": false
  }
}
```

---

## MCP Manager (Port 8370)

### Health Check
```bash
GET /health
```

### Status
```bash
GET /
```

### Server Management

#### Start Server
```bash
POST /servers/{name}/start
```

#### Stop Server
```bash
POST /servers/{name}/stop
```

#### Restart Server
```bash
POST /servers/{name}/restart
```

#### Check Server Health
```bash
GET /servers/{name}/health
```

---

## Error Responses

All errors return JSON with an `error` field:

```json
{
  "error": "Description of what went wrong"
}
```

Common HTTP status codes:
- `200` - Success
- `400` - Bad request (invalid parameters)
- `404` - Not found (workflow/agent/skill not found)
- `500` - Server error

---

## Usage Examples

### Complete PRD Workflow

```bash
# 1. Get help
curl -X POST http://localhost:8361/tools/bmad_help \
  -H "Content-Type: application/json" \
  -d '{"query": "create a product requirements document"}'

# 2. Create PRD
curl -X POST http://localhost:8361/tools/bmad_bmm_create_prd \
  -H "Content-Type: application/json" \
  -d '{
    "product_idea": "AI-powered code review tool",
    "target_users": "Software developers",
    "key_features": ["Automated reviews", "Security scanning", "Performance tips"]
  }'

# 3. Create user stories
curl -X POST http://localhost:8361/tools/bmad_bmm_create_story \
  -H "Content-Type: application/json" \
  -d '{
    "story_title": "User can submit code for review",
    "acceptance_criteria": ["Upload code", "Select language", "Get results"]
  }'

# 4. Plan sprint
curl -X POST http://localhost:8361/tools/bmad_bmm_sprint_planning \
  -H "Content-Type: application/json" \
  -d '{
    "stories": [
      {"title": "Story 1", "points": 3},
      {"title": "Story 2", "points": 5},
      {"title": "Story 3", "points": 8}
    ],
    "sprint_goal": "MVP launch",
    "capacity": 40
  }'
```

### Skills.sh Search

```bash
# Search for skills
curl -X POST http://localhost:8362/tools/skills_search \
  -H "Content-Type: application/json" \
  -d '{"query": "docker", "limit": 5}'

# Get skill details
curl -X POST http://localhost:8362/tools/skills_get \
  -H "Content-Type: application/json" \
  -d '{"skill_id": "vercel-labs/skills"}'

# Execute skill (get content)
curl -X POST http://localhost:8362/tools/skills_execute \
  -H "Content-Type: application/json" \
  -d '{"skill_id": "anthropics/skills"}'
```

---

## Platform-Specific Usage

### Opencode
```bash
/opencode> bmad-help
/opencode> bmad-create-prd
/opencode> bmad-list-workflows
```

### Zed
Configure in `.zed/mcp.json`:
```json
{
  "mcpServers": {
    "bmad": {
      "type": "streamable-http",
      "url": "http://localhost:8361"
    }
  }
}
```

### VS Code
Configure in `.vscode/mcp.json`.

### Claude Code
Native commands + MCP client available.

---

## Rate Limits

Currently no rate limits enforced locally. For cloud deployments via ngrok, standard ngrok free tier limits apply.

## Authentication

Local servers: No authentication required.
Cloud access: Set `MCP_API_KEY` environment variable and validate in production.

## Session Management

Sessions are stored in Redis with 1-hour TTL. Session IDs can be passed to tools for continuity.

## Caching

- Skills.sh: Cached for 24 hours in Redis
- BMAD workflows: Loaded fresh from disk (auto-reload on file changes)
- Agents: Cached in memory
