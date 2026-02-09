# Democratic Swarm Debate: Project Management Approach for Cohezion

## Debate Topic
**Which project management approach should Cohezion adopt for tracking outstanding tasks?**

Options:
A) Integrate with GitHub MCP Server (issues/PRs)
B) Build custom task tracker in Cohezion
C) Integrate with Notion MCP Server
D) Use existing `.cohezion/tasks.md` with enhanced tooling

---

## Round 1: Opening Statements

### 🏗️ Architect Agent
**Proposal: Option D - Enhanced tasks.md**

> The existing `.cohezion/tasks.md` structure is already in place and Git-native. Rather than introducing external dependencies, we should enhance the current system with:
> - JSON schema validation for task entries
> - Automated parsing and status tracking
> - Integration with our existing MCP Knowledge Server
> 
> This maintains Cohezion's "self-contained" principle and avoids vendor lock-in.

### 🔧 Pragmatist Agent
**Proposal: Option A - GitHub MCP Integration**

> GitHub is already our code repository. The GitHub MCP Server is mature and widely supported. Benefits:
> - Native issue tracking with labels, milestones
> - PR integration for code-linked tasks
> - Mobile access via GitHub app
> - Community familiarity
> 
> The infrastructure exists - we just need to connect it.

### 🛡️ Guardian Agent
**Proposal: Option B - Custom Task Tracker**

> Building our own ensures security and complete control. We can:
> - Store task data locally (no external API calls)
> - Implement R-Zero methodology natively
> - Add Cohezion-specific features (skill linkage, simulation tracking)
> - Maintain full audit trail
> 
> External services create dependency risks.

### 💡 Innovator Agent
**Proposal: Option C - Notion MCP**

> Notion offers rich block-based editing, databases, and views. The Notion MCP enables:
> - Kanban boards, calendars, Gantt charts
> - Team collaboration features
> - AI-native integration
> - Beautiful documentation
> 
> However, requires Notion account and API key.

---

## Round 2: Critique & Counter-Proposals

### Architect → Pragmatist
> GitHub issues are designed for code bugs, not research project management. The UX is developer-focused, not researcher-focused.

### Pragmatist → Architect
> Enhanced tasks.md requires building tooling from scratch. Why reinvent when GitHub exists?

### Guardian → Innovator
> Notion is a third-party service with data residency concerns. What if Notion changes their API?

### Innovator → Guardian
> A custom tracker is significant engineering effort that distracts from Cohezion's core mission.

---

## Round 3: Synthesis & Vote

### Voting Results
| Option | Architect | Pragmatist | Guardian | Innovator | Total |
|--------|-----------|------------|----------|-----------|-------|
| A. GitHub MCP | 0 | 1 | 0 | 1 | **2** |
| B. Custom | 1 | 0 | 1 | 0 | **2** |
| C. Notion | 0 | 0 | 0 | 1 | 1 |
| D. Enhanced tasks.md | 1 | 1 | 1 | 0 | **3** ✓ |

### Consensus: **Option D - Enhanced tasks.md with tooling**

---

## Final Recommendation

**Hybrid Approach:**
1. **Primary:** Enhance `.cohezion/tasks.md` with:
   - JSON schema validation
   - Auto-parsing to Prometheus metrics
   - Skill/simulation linkage
   
2. **Secondary:** Mirror critical issues to GitHub using GitHub MCP for external visibility

3. **Future:** Consider Notion MCP when team collaboration grows

---

## Implementation Plan

```python
# Task schema for enhanced tasks.md
{
    "id": "TASK-001",
    "title": "Implement R-Zero metrics",
    "status": "in_progress",  # todo, in_progress, done
    "priority": "high",
    "linked_skills": ["R_ZERO_CHALLENGER_PRIME.md"],
    "assigned_agent": "pragmatist",
    "created": "2026-01-17",
    "due": "2026-01-20"
}
```

### Next Steps
1. Create `src/cohezion/tasks/task_parser.py`
2. Add JSON schema to `.cohezion/tasks.schema.json`
3. Integrate with Knowledge MCP Server
4. Optional: GitHub MCP sync for public visibility
