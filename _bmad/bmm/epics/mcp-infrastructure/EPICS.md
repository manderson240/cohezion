---
name: mcp-infrastructure-epics
description: Agile Epics for Universal MCP Server Infrastructure implementation
type: epics
project: mcp-infrastructure
status: active
sprint: current
---

# Epics: Universal MCP Server Infrastructure

## Epic 1: Core Infrastructure ✅ COMPLETE

**Status**: ✅ **COMPLETE**
**Story Points**: 21
**Duration**: 4 days
**Owner**: mike-anderson

### Description
Build the foundational infrastructure including Redis, shared utilities, and MCP server framework.

### User Stories

#### Story 1.1: Redis Infrastructure
**As a** developer, **I want** Redis running locally in Docker, **so that** session state persists across platform switches.

- **AC1**: Redis container starts with Docker
- **AC2**: Redis binds to port 6379
- **AC3**: AOF persistence enabled
- **AC4**: Health check passes
- **Estimate**: 3 points

#### Story 1.2: Session Management
**As a** system, **I want** a Redis-backed session manager, **so that** user sessions survive server restarts.

- **AC1**: Sessions stored with prefix isolation
- **AC2**: 1-hour TTL with refresh
- **AC3**: CRUD operations work
- **AC4**: Connection pooling
- **Estimate**: 5 points

#### Story 1.3: Vault Logging
**As a** developer, **I want** unified logging to the vault, **so that** I can debug across all servers.

- **AC1**: All servers log to vault
- **AC2**: Structured JSON format
- **AC3**: Rotation and cleanup
- **AC4**: Console + vault dual logging
- **Estimate**: 3 points

#### Story 1.4: MCP Server Manager
**As a** system, **I want** a manager to orchestrate MCP servers, **so that** ports don't conflict and servers auto-restart.

- **AC1**: Port allocation (8360-8399)
- **AC2**: Health checks every 30s
- **AC3**: Auto-restart on failure (max 5)
- **AC4**: HTTP API for management
- **Estimate**: 8 points

#### Story 1.5: Shared Utilities
**As a** developer, **I want** shared utilities package, **so that** code is DRY across servers.

- **AC1**: Session manager module
- **AC2**: Logging module
- **AC3**: Common types/interfaces
- **AC4**: Error handling utilities
- **Estimate**: 2 points

### Acceptance Criteria
- [x] All servers can connect to Redis
- [x] Port allocator prevents conflicts
- [x] Health monitoring works
- [x] Logs appear in vault

### Definition of Done
- [x] Code reviewed
- [x] Tests passing
- [x] Documentation complete
- [x] Deployed to local VM

---

## Epic 2: BMAD MCP Server ✅ COMPLETE

**Status**: ✅ **COMPLETE**
**Story Points**: 34
**Duration**: 5 days
**Owner**: mike-anderson

### Description
Build BMAD MCP server with 20+ core tools, workflow loading, and agent management.

### User Stories

#### Story 2.1: Server Skeleton
**As a** developer, **I want** a basic MCP server running on port 8361, **so that** I can add BMAD tools.

- **AC1**: Server starts on port 8361
- **AC2**: Health endpoint responds
- **AC3**: Info endpoint works
- **AC4**: Graceful shutdown
- **Estimate**: 3 points

#### Story 2.2: BMAD Engine
**As a** system, **I want** a BMAD workflow engine, **so that** I can load and execute 696 workflows.

- **AC1**: Load modules from `_bmad/`
- **AC2**: Index workflows
- **AC3**: Index agents
- **AC4**: Execute workflows with params
- **Estimate**: 8 points

#### Story 2.3: Core Tools
**As a** user, **I want** help and status tools, **so that** I can understand the system.

- **AC1**: bmad_help tool works
- **AC2**: bmad_status tool works
- **AC3**: bmad_list_workflows works
- **AC4**: bmad_list_agents works
- **AC5**: bmad_index_docs works
- **Estimate**: 5 points

#### Story 2.4: BMM Tools (Business)
**As a** product manager, **I want** BMM tools, **so that** I can create PRDs and plan sprints.

- **AC1**: bmad_bmm_create_prd
- **AC2**: bmad_bmm_create_story
- **AC3**: bmad_bmm_sprint_planning
- **AC4**: bmad_bmm_dev_story
- **AC5**: bmad_bmm_code_review
- **Estimate**: 8 points

#### Story 2.5: GDS Tools (Game Dev)
**As a** game developer, **I want** GDS tools, **so that** I can create game designs.

- **AC1**: bmad_gds_create_game_brief
- **AC2**: bmad_gds_game_architecture
- **Estimate**: 3 points

#### Story 2.6: CIS & TEA Tools
**As a** creative lead, **I want** CIS and TEA tools, **so that** I can brainstorm and test.

- **AC1**: bmad_cis_brainstorming
- **AC2**: bmad_tea_test_design
- **Estimate**: 3 points

#### Story 2.7: Multi-Agent & Builder
**As a** architect, **I want** party mode and builder tools, **so that** I can extend BMAD.

- **AC1**: bmad_bmb_create_agent
- **AC2**: bmad_party_mode
- **Estimate**: 2 points

#### Story 2.8: Resources API
**As a** developer, **I want** resources endpoints, **so that** I can fetch workflows and agents.

- **AC1**: /resources/workflows/{path}
- **AC2**: /resources/agents/{id}
- **AC3**: /resources/modules
- **Estimate**: 2 points

### Acceptance Criteria
- [x] 20+ tools implemented
- [x] All 696 workflows accessible
- [x] 28 agents loadable
- [x] Session management works

### Definition of Done
- [x] All tools tested
- [x] API documented
- [x] Integration tests pass
- [x] Performance targets met (<100ms)

---

## Epic 3: Skills.sh Integration ✅ COMPLETE

**Status**: ✅ **COMPLETE**
**Story Points**: 21
**Duration**: 3 days
**Owner**: mike-anderson

### Description
Integrate Skills.sh registry with search, install, execute, and caching capabilities.

### User Stories

#### Story 3.1: Skills.sh Client
**As a** system, **I want** an HTTP client for skills.sh, **so that** I can search 85K+ skills.

- **AC1**: Search skills by query
- **AC2**: Filter by category
- **AC3**: Get trending skills
- **AC4**: List categories
- **Estimate**: 5 points

#### Story 3.2: Skill Fetching
**As a** system, **I want** to fetch skill content from GitHub, **so that** I can execute skills.

- **AC1**: Fetch from raw.githubusercontent.com
- **AC2**: Try multiple URL patterns
- **AC3**: Handle 404 gracefully
- **AC4**: Parse SKILL.md format
- **Estimate**: 3 points

#### Story 3.3: Local Cache
**As a** user, **I want** skills cached locally, **so that** I can use them offline and faster.

- **AC1**: Cache 1000 skills max
- **AC2**: 24-hour TTL
- **AC3**: Redis storage
- **AC4**: Cache stats available
- **Estimate**: 5 points

#### Story 3.4: Skills MCP Server
**As a** developer, **I want** a Skills.sh MCP server on port 8362, **so that** tools can access skills.

- **AC1**: Server starts on port 8362
- **AC2**: skills_search tool
- **AC3**: skills_get tool
- **AC4**: skills_install tool
- **AC5**: skills_execute tool
- **Estimate**: 5 points

#### Story 3.5: Cache Management
**As a** user, **I want** cache management tools, **so that** I can control the local cache.

- **AC1**: skills_sync tool
- **AC2**: skills_cache_info tool
- **AC3**: skills_list with installed_only filter
- **AC4**: Clear and invalidate operations
- **Estimate**: 3 points

### Acceptance Criteria
- [x] Can search 85K+ skills
- [x] Install works via npx
- [x] Execute fetches content
- [x] Cache hit rate >90%

### Definition of Done
- [x] All 8 tools work
- [x] Cache performance good
- [x] API documented
- [x] Tests passing

---

## Epic 4: Platform Integrations ✅ COMPLETE

**Status**: ✅ **COMPLETE**
**Story Points**: 13
**Duration**: 2 days
**Owner**: mike-anderson

### Description
Create native commands and MCP configs for all supported IDEs.

### User Stories

#### Story 4.1: Opencode Commands
**As an** opencode user, **I want** 111 BMAD commands, **so that** I can use BMAD natively.

- **AC1**: Copy 111 commands from .claude/
- **AC2**: Transform frontmatter format
- **AC3**: Test command execution
- **AC4**: MCP client config
- **Estimate**: 5 points

#### Story 4.2: Zed IDE Support
**As a** Zed user, **I want** MCP config, **so that** I can use BMAD tools.

- **AC1**: Create .zed/mcp.json
- **AC2**: Test connection
- **AC3**: Document usage
- **Estimate**: 2 points

#### Story 4.3: Antigravity Support
**As an** Antigravity user, **I want** MCP config, **so that** I can use BMAD tools.

- **AC1**: Create .antigravity/mcp.yml
- **AC2**: Test connection
- **AC3**: Document usage
- **Estimate**: 2 points

#### Story 4.4: VS Code Support
**As a** VS Code user, **I want** MCP config, **so that** I can use BMAD tools.

- **AC1**: Create .vscode/mcp.json
- **AC2**: Test connection
- **AC3**: Document usage
- **Estimate**: 2 points

#### Story 4.5: Claude Code Dual Mode
**As a** Claude Code user, **I want** both native and MCP, **so that** I get best of both.

- **AC1**: Keep existing native commands
- **AC2**: Add .claude/mcp.json
- **AC3**: Document dual mode
- **AC4**: Test both paths
- **Estimate**: 2 points

### Acceptance Criteria
- [x] All 5 platforms have configs
- [x] Opencode has 111 commands
- [x] MCP clients connect successfully

### Definition of Done
- [x] Configs tested on each platform
- [x] Documentation complete
- [x] Users can start using immediately

---

## Epic 5: Cloud Access ✅ COMPLETE

**Status**: ✅ **COMPLETE**
**Story Points**: 8
**Duration**: 1 day
**Owner**: mike-anderson

### Description
Enable cloud access via ngrok tunnel for Claude.ai/code and remote usage.

### User Stories

#### Story 5.1: Docker Compose
**As a** developer, **I want** Docker Compose setup, **so that** I can start all services easily.

- **AC1**: Redis service
- **AC2**: BMAD MCP service
- **AC3**: Skills MCP service
- **AC4**: MCP Manager service
- **AC5**: Ngrok service (optional)
- **Estimate**: 3 points

#### Story 5.2: Ngrok Integration
**As a** cloud user, **I want** ngrok tunnel, **so that** I can access BMAD from anywhere.

- **AC1**: Ngrok Docker service
- **AC2**: Configurable domain
- **AC3**: HTTPS endpoint
- **AC4**: Environment variables
- **Estimate**: 2 points

#### Story 5.3: Environment Config
**As a** deployer, **I want** environment configuration, **so that** I can customize deployment.

- **AC1**: .env.mcp template
- **AC2**: Cloud .mcp.json
- **AC3**: Ngrok auth token support
- **AC4**: Documentation
- **Estimate**: 2 points

#### Story 5.4: Startup Script
**As a** developer, **I want** a startup script, **so that** I can start all servers easily.

- **AC1**: start-mcp-servers.sh
- **AC2**: Health checks
- **AC3**: Process management
- **AC4**: Status output
- **Estimate**: 1 point

### Acceptance Criteria
- [x] Docker Compose works
- [x] Ngrok tunnel functional
- [x] Cloud config ready
- [x] Easy startup

### Definition of Done
- [x] Tested end-to-end
- [x] Documentation complete
- [x] Users can access from cloud

---

## Epic 6: Documentation ✅ COMPLETE

**Status**: ✅ **COMPLETE**
**Story Points**: 13
**Duration**: Ongoing
**Owner**: mike-anderson

### Description
Create comprehensive documentation in the Obsidian vault.

### User Stories

#### Story 6.1: PRD Document
**As a** stakeholder, **I want** a PRD, **so that** I understand requirements.

- **AC1**: Problem statement
- **AC2**: Solution overview
- **AC3**: User stories
- **AC4**: Success criteria
- **Estimate**: 3 points

#### Story 6.2: Architecture Document
**As a** developer, **I want** architecture docs, **so that** I understand the system.

- **AC1**: System diagrams
- **AC2**: Component details
- **AC3**: API design
- **AC4**: ADRs
- **Estimate**: 5 points

#### Story 6.3: API Reference
**As an** integrator, **I want** API docs, **so that** I can use the APIs.

- **AC1**: All endpoints documented
- **AC2**: Request/response examples
- **AC3**: Error codes
- **AC4**: Usage examples
- **Estimate**: 3 points

#### Story 6.4: Implementation Status
**As a** manager, **I want** status tracking, **so that** I know what's done.

- **AC1**: Completion summary
- **AC2**: Feature checklist
- **AC3**: Next steps
- **AC4**: File locations
- **Estimate**: 2 points

### Acceptance Criteria
- [x] PRD complete
- [x] Architecture complete
- [x] API reference complete
- [x] Status tracking complete

### Definition of Done
- [x] All docs in vault
- [x] Cross-referenced
- [x] Searchable
- [x] Maintained

---

## Epic 7: Complete BMAD Tools ⏳ PENDING

**Status**: ⏳ **PENDING**
**Story Points**: 55
**Duration**: 3 weeks
**Owner**: TBD

### Description
Implement remaining 88 BMAD tools to reach full 108 command coverage.

### User Stories

#### Story 7.1: BMM Module Completion
**As a** PM, **I want** all 30 BMM tools, **so that** I have full business method coverage.

- Current: 5 tools
- Target: 30 tools
- Remaining: 25 tools
- **Estimate**: 13 points

#### Story 7.2: GDS Module Completion
**As a** game dev, **I want** all 25 GDS tools, **so that** I have full game dev coverage.

- Current: 2 tools
- Target: 25 tools
- Remaining: 23 tools
- **Estimate**: 13 points

#### Story 7.3: CIS Module Completion
**As a** creative lead, **I want** all 10 CIS tools, **so that** I have full creative coverage.

- Current: 1 tool
- Target: 10 tools
- Remaining: 9 tools
- **Estimate**: 5 points

#### Story 7.4: TEA Module Completion
**As a** QA lead, **I want** all 10 TEA tools, **so that** I have full testing coverage.

- Current: 1 tool
- Target: 10 tools
- Remaining: 9 tools
- **Estimate**: 5 points

#### Story 7.5: BMB Module Completion
**As an** architect, **I want** all 15 BMB tools, **so that** I can build custom modules.

- Current: 2 tools (1 shared with Core)
- Target: 15 tools
- Remaining: 13 tools
- **Estimate**: 13 points

#### Story 7.6: Core Module Completion
**As a** user, **I want** all 8 Core tools, **so that** I have full utility coverage.

- Current: 4 tools
- Target: 8 tools
- Remaining: 4 tools
- **Estimate**: 3 points

#### Story 7.7: Agent Prompts
**As a** user, **I want** all 28 agent prompts, **so that** I can activate any agent.

- Current: 0 prompts (engine ready)
- Target: 28 prompts
- **Estimate**: 3 points

### Acceptance Criteria
- [ ] 108 tools total
- [ ] 28 agent prompts
- [ ] All workflows accessible
- [ ] Full API coverage

### Definition of Done
- [ ] All tools tested
- [ ] Documentation updated
- [ ] Performance verified
- [ ] User acceptance passed

---

## Summary

| Epic | Status | Points | Stories | Duration |
|------|--------|--------|---------|----------|
| 1. Core Infrastructure | ✅ Complete | 21 | 5 | 4 days |
| 2. BMAD MCP Server | ✅ Complete | 34 | 8 | 5 days |
| 3. Skills.sh Integration | ✅ Complete | 21 | 5 | 3 days |
| 4. Platform Integrations | ✅ Complete | 13 | 5 | 2 days |
| 5. Cloud Access | ✅ Complete | 8 | 4 | 1 day |
| 6. Documentation | ✅ Complete | 13 | 4 | Ongoing |
| 7. Complete BMAD Tools | ⏳ Pending | 55 | 7 | 3 weeks |
| **Total** | **6/7 Complete** | **165** | **38** | **~6 weeks** |

### Velocity
- **Completed**: 110 points in 15 days = 7.3 points/day
- **Projected**: Remaining 55 points = ~7 days

### Next Sprint
Focus on Epic 7 (Complete BMAD Tools) to reach full 108 command coverage.

---

**Document Version**: 1.0.0
**Last Updated**: 2026-03-05
**Status**: Active
