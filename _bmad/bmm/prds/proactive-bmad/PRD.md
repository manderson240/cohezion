---
name: proactive-bmad
version: 1.0
status: approved
created: 2026-04-08
owner: Mike-anderson
stakeholders: BMad Master, Winston (Architect), Wendy (Workflow Builder)
---

# Proactive BMad - Product Requirements Document

## 1. Executive Summary

### 1.1 Product Vision

Transform BMad from a reactive tool (waiting for user commands) into a proactive partner that anticipates needs, detects alignment gaps, and suggests concrete actions with one-click execution.

### 1.2 Problem Statement

**Current State (Reactive BMad):**
- Users must manually discover alignment gaps
- No automatic detection of missing workflows, tasks, or quality gates
- High cognitive load - users must remember everything
- Reactive workflow - BMad waits for explicit commands

**Desired State (Proactive BMad):**
- Automatic codebase scanning for alignment issues
- Intelligent suggestions prioritized by impact
- One-click execution with safety confirmation
- Proactive workflow - BMad suggests next best actions

### 1.3 Success Metrics

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Time to detect gaps | Manual (hours) | <2 seconds | Scan duration |
| Alignment visibility | 0% (undetected) | 100% | Suggestions found |
| User cognitive load | High | 50% reduction | User feedback |
| BMad engagement | Reactive | 2x proactive | Tool usage |
| Alignment completion | Low | 80%+ | Execution rate |

---

## 2. User Personas

### 2.1 Primary: BMad Power User (Mike-anderson)

**Characteristics:**
- Deep technical expertise
- Building complex systems (repository layer, compound engineering)
- Values efficiency and automation
- Wants BMad to be a thought partner, not just a tool

**Goals:**
- Maintain BMad alignment across all layers
- Detect gaps before they become problems
- Execute alignment fixes quickly
- Focus on high-value work, not manual discovery

**Pain Points:**
- Manual scanning for alignment gaps is time-consuming
- Easy to miss gaps when focused on implementation
- Context switching between discovery and execution
- Cognitive load of remembering all BMad requirements

### 2.2 Secondary: BMad Casual User

**Characteristics:**
- Uses BMad occasionally for specific tasks
- Less familiar with BMad methodology
- Needs guidance on best practices
- Values simplicity and clarity

**Goals:**
- Learn BMad best practices
- Avoid common mistakes
- Get clear, actionable suggestions
- Build confidence with BMad

**Pain Points:**
- Overwhelmed by BMad complexity
- Doesn't know what they don't know
- Afraid of making mistakes
- Needs hand-holding

---

## 3. User Stories

### 3.1 Core Stories

**US-1: Automatic Codebase Scanning**
```
As a BMad user
I want BMad to scan my codebase automatically
So that I can see alignment gaps without manual discovery

Acceptance Criteria:
- Scan completes in <2 seconds
- Suggestions sorted by priority (critical, high, medium, low)
- Each suggestion has confidence score (0.0-1.0)
- Summary shows totals by priority and category
```

**US-2: One-Click Execution**
```
As a BMad user
I want to execute suggestions with one click
So that I can fix alignment gaps quickly

Acceptance Criteria:
- Auto-executable suggestions clearly marked
- Confirmation required before execution (safety)
- Execution results reported (success/failure)
- Rollback information provided
```

**US-3: Pattern Management**
```
As a BMad power user
I want to enable/disable detection patterns
So that I can customize proactive monitoring

Acceptance Criteria:
- List all available patterns
- Enable/disable individual patterns
- Pattern state persisted across sessions
- Disabled patterns skip detection
```

**US-4: Party Mode Integration**
```
As a Party Mode participant
I want proactive suggestions discussed by agents
So that we can collaborate on alignment decisions

Acceptance Criteria:
- Auto-scan on party mode start
- Suggestions become discussion topics
- Agents provide diverse perspectives
- User can approve execution collaboratively
```

### 3.2 Advanced Stories (Future)

**US-5: Learning from Feedback**
```
As a BMad product manager
I want to track which suggestions users accept/reject
So that we can improve pattern confidence

Acceptance Criteria:
- Track acceptance rate per pattern
- Adjust confidence scores automatically
- Report patterns with low acceptance
- A/B testing framework
```

**US-6: Real-Time Monitoring**
```
As a BMad user
I want real-time file watching
So that I get instant feedback on changes

Acceptance Criteria:
- Watch file system for changes
- Trigger scan on relevant changes
- Debounce rapid changes
- Background execution
```

---

## 4. Functional Requirements

### 4.1 Proactive Monitoring Engine

**FR-1: Pattern Detection**
- System SHALL detect alignment gaps using pattern matching
- System SHALL support 5+ detection patterns initially
- System SHALL be extensible for new patterns
- System SHALL evaluate patterns in <100ms each

**FR-2: Suggestion Generation**
- System SHALL generate suggestions with title, description, priority
- System SHALL assign confidence scores (0.0-1.0)
- System SHALL categorize suggestions (alignment, integration, quality, maintenance)
- System SHALL mark suggestions as auto-executable or manual

**FR-3: Priority Sorting**
- System SHALL sort suggestions by priority (critical > high > medium > low)
- System SHALL secondary sort by confidence (high to low)
- System SHALL group suggestions by category

**FR-4: Metrics Collection**
- System SHALL collect metrics for all detections
- System SHALL track scan duration, suggestions found, execution success
- System SHALL provide summary statistics
- System SHALL log all operations

### 4.2 Auto-Execution Engine

**FR-5: Execution Safety**
- System SHALL require confirmation before execution (default)
- System SHALL check auto_executable flag
- System SHALL skip non-auto-executable suggestions
- System SHALL provide rollback information

**FR-6: Execution Handlers**
- System SHALL support multiple execution handlers
- System SHALL map suggestion IDs to handlers
- System SHALL handle execution errors gracefully
- System SHALL report execution results

**FR-7: Handler Implementations**
- System SHALL create BMad workflows for repository operations
- System SHALL integrate metrics with observability
- System SHALL add tasks to task-manifest.csv
- System SHALL create quality gates

### 4.3 MCP Integration

**FR-8: MCP Tools**
- System SHALL expose 5 MCP tools:
  - bmad_proactive_scan
  - bmad_proactive_execute
  - bmad_proactive_summary
  - bmad_proactive_list_patterns
  - bmad_proactive_enable_pattern

**FR-9: HTTP Endpoints**
- System SHALL provide REST endpoints:
  - POST /proactive/scan
  - POST /proactive/execute
  - GET /proactive/summary
  - GET /proactive/patterns
  - POST /proactive/pattern/{id}/enable

**FR-10: Authentication**
- System SHALL integrate with BMad MCP authentication
- System SHALL validate API keys
- System SHALL handle authentication errors

### 4.4 Pattern Management

**FR-11: Pattern Registration**
- System SHALL register patterns at initialization
- System SHALL support enabling/disabling patterns
- System SHALL persist pattern state
- System SHALL load pattern state on startup

**FR-12: Pattern Detection**
- System SHALL run enabled patterns only
- System SHALL skip disabled patterns
- System SHALL log pattern evaluation
- System SHALL handle detection errors gracefully

---

## 5. Non-Functional Requirements

### 5.1 Performance

**NFR-1: Scan Duration**
- Full codebase scan SHALL complete in <2 seconds
- Individual pattern evaluation SHALL complete in <100ms
- MCP endpoint response time SHALL be <500ms

**NFR-2: Resource Usage**
- Memory usage SHALL not exceed 50MB during scan
- CPU usage SHALL not exceed 10% during scan
- No persistent background processes

**NFR-3: Scalability**
- System SHALL handle codebases with 10,000+ files
- System SHALL support 50+ detection patterns
- System SHALL handle 100+ concurrent MCP requests

### 5.2 Reliability

**NFR-4: Error Handling**
- System SHALL handle all errors gracefully
- System SHALL log errors with full context
- System SHALL not crash on invalid input
- System SHALL provide meaningful error messages

**NFR-5: Data Integrity**
- System SHALL not modify files without confirmation
- System SHALL validate all file operations
- System SHALL provide rollback information
- System SHALL not corrupt existing files

### 5.3 Usability

**NFR-6: Clarity**
- Suggestions SHALL be clear and actionable
- Priority levels SHALL be self-explanatory
- Confidence scores SHALL be explained
- Execution results SHALL be detailed

**NFR-7: Safety**
- Confirmation REQUIRED for all executions
- Rollback information PROVIDED for all executions
- Non-auto-executable suggestions CLEARLY marked
- Errors REPORTED with remediation steps

### 5.4 Maintainability

**NFR-8: Code Quality**
- Code SHALL follow BMad standards
- Tests SHALL achieve 95%+ coverage
- Documentation SHALL be comprehensive
- Patterns SHALL be easy to add

**NFR-9: Extensibility**
- New patterns SHALL be addable in <30 minutes
- New handlers SHALL be addable in <1 hour
- System SHALL support plugin architecture
- System SHALL have clear extension points

---

## 6. Technical Architecture

### 6.1 Components

```
┌─────────────────────────────────────────┐
│  BMad MCP Server (Port 8361)            │
│  ┌─────────────────────────────────┐   │
│  │ Proactive Routes                 │   │
│  │ - /proactive/scan                │   │
│  │ - /proactive/execute             │   │
│  │ - /proactive/summary             │   │
│  │ - /proactive/patterns            │   │
│  └─────────────────────────────────┘   │
│  ┌─────────────────────────────────┐   │
│  │ ProactiveMonitor                 │   │
│  │ - PatternMatch[]                 │   │
│  │ - ProactiveSuggestion[]          │   │
│  │ - execute_suggestion()           │   │
│  └─────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### 6.2 Data Models

**ProactiveSuggestion:**
```python
@dataclass
class ProactiveSuggestion:
    id: str
    title: str
    description: str
    priority: str  # critical, high, medium, low
    category: str  # alignment, integration, quality, maintenance
    suggested_action: str
    auto_executable: bool
    confidence: float  # 0.0-1.0
    timestamp: str
    metadata: dict[str, Any]
```

**PatternMatch:**
```python
@dataclass
class PatternMatch:
    name: str
    description: str
    detection_fn: Callable[[Path], bool]
    suggestion_fn: Callable[[Path], ProactiveSuggestion]
    enabled: bool
```

### 6.3 File Structure

```
src/cohezion/mcp/servers/bmad/
├── proactive_monitor.py      # Detection engine
├── routes_proactive.py       # MCP route handlers
└── server.py                 # BMad MCP server (updated)

_bmad/core/proactive/
└── README.md                 # Documentation

_bmad/bmm/epics/proactive-bmad/
├── EPICS.md                  # Epic definition
└── PRD.md                    # This file

_bmad/tea/stories/proactive-bmad/
└── TDD_STORIES.md            # Test stories
```

---

## 7. Detection Patterns

### 7.1 Repository Layer Patterns

**Pattern 1: repository-workflow-gap**
- **Description:** New repository without BMad workflow
- **Detection:** >4 repository files + no workflow in manifest
- **Suggestion:** Create BMad workflows for repository operations
- **Priority:** High
- **Auto-executable:** Yes
- **Confidence:** 0.9

**Pattern 2: metrics-observability-gap**
- **Description:** RepositoryMetrics not integrated with BMad observability
- **Detection:** base.py exists + no observability directory
- **Suggestion:** Create observability integration
- **Priority:** Medium
- **Auto-executable:** Yes
- **Confidence:** 0.85

**Pattern 3: batch-tasks-missing**
- **Description:** Batch operations not in task-manifest.csv
- **Detection:** task-manifest exists + no batch tasks
- **Suggestion:** Add batch_create, batch_get to manifest
- **Priority:** High
- **Auto-executable:** Yes
- **Confidence:** 0.95

### 7.2 Quality Patterns

**Pattern 4: adversarial-quality-gap**
- **Description:** Adversarial review without BMad quality gate
- **Detection:** adversarial tests exist + no quality-gates directory
- **Suggestion:** Create BMad quality gate
- **Priority:** Medium
- **Auto-executable:** Yes
- **Confidence:** 0.8

**Pattern 5: low-test-coverage**
- **Description:** Test coverage below 80% threshold
- **Detection:** coverage.json exists + coverage < 80%
- **Suggestion:** Run coverage analysis and identify gaps
- **Priority:** High
- **Auto-executable:** No (requires user action)
- **Confidence:** 1.0

---

## 8. User Interface

### 8.1 MCP Tool Response

**Scan Response:**
```json
{
  "suggestions": [
    {
      "id": "repo-workflow-missing",
      "title": "Repository Operations Missing BMad Workflows",
      "description": "Detected repository layer without formal BMad workflow definitions",
      "priority": "high",
      "category": "alignment",
      "suggested_action": "Create BMad workflows for repository batch operations",
      "auto_executable": true,
      "confidence": 0.9
    }
  ],
  "summary": {
    "total_patterns": 5,
    "enabled_patterns": 5,
    "active_suggestions": 3,
    "by_priority": {
      "critical": 0,
      "high": 2,
      "medium": 1,
      "low": 0
    },
    "by_category": {
      "alignment": 2,
      "integration": 1,
      "quality": 0,
      "maintenance": 0
    }
  }
}
```

### 8.2 Execution Confirmation

**Confirmation Prompt:**
```
🤖 BMad Proactive Suggestion:
   Repository Operations Missing BMad Workflows
   Action: Create BMad workflows for repository batch operations
   Priority: High
   Confidence: 90%

   Execute? (y/n): _
```

**Execution Result:**
```json
{
  "success": true,
  "suggestion_id": "repo-workflow-missing",
  "message": "Executed: Create BMad workflows for repository batch operations",
  "actions_taken": [
    "Created workflow at _bmad/core/workflows/repository-operations/workflow.md"
  ]
}
```

---

## 9. Acceptance Criteria

### 9.1 Must Have (P0)

- [x] ProactiveMonitor class implemented
- [x] 5 detection patterns working
- [x] Auto-execution with confirmation
- [x] 5 MCP tools registered
- [x] Documentation complete

### 9.2 Should Have (P1)

- [ ] Party mode integration
- [ ] Unit tests (95%+ coverage)
- [ ] Integration tests passing
- [ ] Manual testing completed

### 9.3 Nice to Have (P2)

- [ ] Learning from feedback
- [ ] Real-time file watching
- [ ] Custom pattern definitions
- [ ] Pattern marketplace

---

## 10. Risks and Mitigations

### 10.1 Technical Risks

**Risk: False Positives**
- **Probability:** Medium
- **Impact:** High (user trust loss)
- **Mitigation:** High confidence thresholds, user feedback tracking

**Risk: Auto-Execution Damage**
- **Probability:** Low
- **Impact:** High (codebase corruption)
- **Mitigation:** Confirmation required, rollback info, version control

**Risk: Performance Impact**
- **Probability:** Low
- **Impact:** Medium (poor UX)
- **Mitigation:** Async scanning, caching, background execution

### 10.2 Product Risks

**Risk: Low Adoption**
- **Probability:** Medium
- **Impact:** High (feature unused)
- **Mitigation:** User education, clear value proposition

**Risk: Over-Automation**
- **Probability:** Medium
- **Impact:** Medium (user frustration)
- **Mitigation:** Confirmation required, opt-out available

---

## 11. Timeline

| Phase | Start | End | Status |
|-------|-------|-----|--------|
| Phase 1: Foundation | 2026-04-08 | 2026-04-08 | ✅ Complete |
| Phase 2: MCP Integration | 2026-04-08 | 2026-04-08 | ✅ Complete |
| Phase 3: Documentation | 2026-04-08 | 2026-04-08 | ✅ Complete |
| Phase 4: Party Mode | 2026-04-09 | 2026-04-15 | 🔄 In Progress |
| Phase 5: Learning | 2026-04-16 | 2026-04-30 | 📋 Backlog |
| Phase 6: Advanced | 2026-05-01 | 2026-05-15 | 📋 Backlog |

---

## 12. Stakeholder Sign-Off

| Role | Name | Status | Date |
|------|------|--------|------|
| Product Owner | Mike-anderson | ✅ Approved | 2026-04-08 |
| BMad Master | 🧙 | ✅ Approved | 2026-04-08 |
| Architect | Winston | ✅ Approved | 2026-04-08 |
| Developer | Amelia | ✅ Approved | 2026-04-08 |
| QA | Quinn | ✅ Approved | 2026-04-08 |

---

**Document Status:** ✅ Approved  
**Version:** 1.0  
**Last Updated:** 2026-04-08  
**Next Review:** 2026-04-15
