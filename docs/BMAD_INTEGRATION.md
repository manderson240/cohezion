# BMAD-Cohezion Integration Layer

## Current State Analysis

### BMAD System Components

```
_bmad/
├── core/                    # BMAD Core (Master Agent)
├── bmm/                     # Business Management Module
│   ├── agents/              # Business agents (PM, Architect, Dev, etc.)
│   ├── workflows/           # Business workflows
│   └── config.yaml          # BMM Configuration
├── bmb/                     # Builder Module  
│   ├── agents/              # Builder agents (Agent Builder, Module Builder, etc.)
│   └── workflows/           # Building workflows
├── cis/                     # Creative Intelligence Suite
├── gds/                     # Game Development Studio
├── tea/                     # Test Architecture Enterprise
└── _config/
    ├── manifest.yaml        # System manifest
    └── agent-manifest.csv   # All registered agents (includes our 3 new ones!)
```

### Our Agents Status

✅ **Registered in BMAD**: Lines 29-31 of `agent-manifest.csv`
```csv
29: security-monitor,Sentinel,_bmad/bmm/agents/security-monitor.md,operations,True
30: documentation-curator,Archivist,_bmad/bmm/agents/documentation-curator.md,documentation,True
31: code-review-assistant,Inspector,_bmad/bmm/agents/code-review-assistant.md,code-review,False
```

⚠️ **Missing Integration**: Not yet wired into BMAD workflows

---

## Integration Strategy

### 1. Workflow Integration

**Goal**: Trigger our agents from BMAD workflows

**Implementation**:

#### A. Auto-trigger on Workflow Completion

```yaml
# _bmad/bmm/workflows/4-implementation/code-review/workflow.yaml
name: Code Review with Security
trigger: pr.created
steps:
  - bmad-master: load-inspector
    agent: code-review-assistant
    action: review-pr
    
  - inspector: security-review
    input: "{{pr.number}}"
    output: security-report
    
  - bmad-master: conditional
    if: "{{security-report.critical}} > 0"
    then:
      - action: block-merge
      - action: notify-team
    else:
      - action: approve-review
```

#### B. Scheduled Workflows

```yaml
# _bmad/bmm/workflows/security-monitoring/workflow.yaml
name: Daily Security Monitoring
schedule: "0 8 * * *"
steps:
  - sentinel: daily-check
    action: security-scan
    
  - archivist: doc-maintenance
    action: check-health
    parallel: true
    
  - bmad-master: report-generation
    action: compile-report
    input: [sentinel.results, archivist.results]
```

### 2. Task Integration

**Goal**: Cohezion agents appear in BMAD task system

**Implementation**:

```python
# orchestrator/bmad_integration/task_adapter.py


class CohezionTaskAdapter:
    """Adapter to register Cohezion tasks in BMAD."""

    def register_tasks(self):
        """Register Cohezion tasks with BMAD task system."""
        tasks = [
            {
                "id": "cohezion-security-check",
                "name": "Security Check",
                "agent": "security-monitor",
                "command": "/security-check",
                "schedule": "0 8 * * *",
                "priority": "high",
                "category": "security",
            },
            {
                "id": "cohezion-doc-update",
                "name": "Documentation Update",
                "agent": "documentation-curator",
                "command": "/update-docs",
                "schedule": "0 10 * * *",
                "priority": "medium",
                "category": "documentation",
            },
            {
                "id": "cohezion-pr-review",
                "name": "PR Security Review",
                "agent": "code-review-assistant",
                "command": "/review-pr",
                "trigger": "pr.created",
                "priority": "high",
                "category": "code-review",
            },
        ]

        # Write to BMAD task manifest
        self._update_task_manifest(tasks)
```

### 3. Knowledge Integration

**Goal**: Share knowledge between BMAD sidecars and Cohezion intelligence

**Implementation**:

```
_bmad/_memory/
├── security-monitor-sidecar/          # Our sidecar
│   └── alert-history.md
├── documentation-curator-sidecar/     # Our sidecar
│   └── doc-changes.md
├── code-review-assistant-sidecar/     # Our sidecar
│   └── review-history.md
├── tech-writer-sidecar/              # BMAD sidecar
│   └── documentation-standards.md
└── cohezion-integration/             # NEW: Shared knowledge
    ├── security-patterns-index.md
    ├── doc-health-index.md
    └── learned-patterns.md
```

**Knowledge Sync**:

```python
# Sync BMAD patterns to Cohezion
bmad_patterns = load_bmad_patterns("_bmad/_memory/tech-writer-sidecar/")
for pattern in bmad_patterns:
    intelligence.learn_doc_pattern(
        doc_type=pattern.type, template=pattern.template, example=pattern.example
    )

# Sync Cohezion findings to BMAD
security_patterns = intelligence.get_security_patterns()
append_to_sidecar("_bmad/_memory/cohezion-integration/learned-patterns.md", security_patterns)
```

### 4. Agent-to-Agent Communication

**Goal**: Our agents can call BMAD agents and vice versa

**Implementation**:

```python
# Cohezion agent calling BMAD agent
async def sentinel_call_architect(alert):
    """Sentinel calls BMAD Architect for architectural review."""
    event = Event.create(
        type="agent.request",
        source="security-monitor",
        data={
            "target_agent": "architect",
            "action": "review_security_implications",
            "input": alert,
        },
    )
    await event_bus.emit(event)


# BMAD agent calling Cohezion agent
async def dev_call_inspector(code):
    """BMAD Dev calls Inspector for code review."""
    event = Event.create(
        type="agent.request",
        source="bmm-dev",
        data={"target_agent": "code-review-assistant", "action": "security-review", "input": code},
    )
    await event_bus.emit(event)
```

### 5. Configuration Alignment

**Goal**: Use BMAD config for Cohezion settings

**Implementation**:

```yaml
# _bmad/bmm/config.yaml (existing)
project_name: cohezion
user_skill_level: intermediate
user_name: Mike

# Add Cohezion section
cohezion:
  enabled: true
  agents:
    sentinel:
      autonomous: true
      schedule: "0 8 * * *"
      severity_threshold: medium
    archivist:
      autonomous: true
      schedule: "0 10 * * *"
      freshness_threshold: 90
    inspector:
      autonomous: false
      trigger: on-demand
  
  notifications:
    slack:
      webhook: "${SLACK_WEBHOOK_URL}"
      channel: "#security-alerts"
    email:
      enabled: true
      recipients: ["${NOTIFICATION_EMAIL}"]
  
  integration:
    bmad_events: true
    github_webhooks: true
    auto_pr_review: true
```

---

## Implementation Plan

### Phase 1: Basic Integration (This Session)

1. ✅ **Register agents** in manifest (DONE)
2. **Create BMAD workflow triggers**
3. **Sync configurations**
4. **Test agent-to-agent communication**

### Phase 2: Workflow Integration (Next)

1. **Create Cohezion-specific workflows**
2. **Add workflow hooks to existing BMAD workflows**
3. **Implement task adapter**
4. **Test end-to-end flows**

### Phase 3: Knowledge Integration (Future)

1. **Create shared knowledge space**
2. **Implement bidirectional sync**
3. **Pattern learning from BMAD data**
4. **Cross-agent memory sharing**

---

## Files to Create

### 1. BMAD Workflow Integration

```
_bmad/bmm/workflows/cohezion/
├── security-monitoring/
│   └── workflow.yaml
├── documentation-maintenance/
│   └── workflow.yaml
└── code-review-integration/
    └── workflow.yaml
```

### 2. Task Integration

```
orchestrator/bmad_integration/
├── __init__.py
├── task_adapter.py
├── workflow_hooks.py
└── config_sync.py
```

### 3. Shared Knowledge

```
_bmad/_memory/cohezion-integration/
├── README.md
├── security-patterns-index.md
├── doc-health-index.md
└── learned-patterns.md
```

### 4. Configuration Updates

```
_bmad/bmm/config.yaml  # Add cohezion section
```

---

## Usage Examples

### Example 1: PR Created

```
1. Developer creates PR
2. BMAD workflow triggers
3. Inspector auto-reviews for security
4. Sentinel monitors for critical issues
5. Archivist checks if docs need updates
6. Report compiled
7. Human reviews consolidated report
```

### Example 2: Security Alert

```
1. Sentinel detects critical alert
2. Event Bus notifies Inspector
3. Inspector generates fix
4. BMAD Dev reviews fix
5. Archivist documents pattern
6. Knowledge graph updated
7. Future similar alerts auto-resolved
```

### Example 3: Documentation Update

```
1. Code merged to main
2. Archivist detects impact
3. BMAD Tech Writer notified
4. Cohezion + BMAD collaborate on update
5. PR created with doc changes
6. Inspector reviews for accuracy
7. Docs stay in sync with code
```

---

## Success Metrics

**Integration Complete When**:
- [ ] Cohezion agents appear in BMAD agent list
- [ ] BMAD workflows can trigger Cohezion agents
- [ ] Cohezion agents can call BMAD agents
- [ ] Shared knowledge space operational
- [ ] Configuration unified
- [ ] End-to-end workflows tested

**Measured By**:
- Agent handoff time < 1 second
- Knowledge sync < 5 seconds
- Workflow completion time reduced by 30%
- Cross-agent collaboration visible in logs

---

**Next**: Implement Phase 1 - Basic Integration
