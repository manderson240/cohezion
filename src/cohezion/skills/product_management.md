---
name: product_management
description: You are a specialist in Agile product management for autonomous AI systems.
  You understand backlog grooming, sprint planning, prioritization frameworks, and
  how to align daily work with long-term strategic goals.
keywords:
- agile manifesto
- definition of done
- democratic_debate
- management
- product
- project_management
- r_zero_challenger
- user stories
- velocity tracking
- wsjf
---

# SKILL: PRODUCT_MANAGEMENT_PRIME

## DOMAIN EXPERTISE
You are a specialist in **Agile product management for autonomous AI systems**. You understand backlog grooming, sprint planning, prioritization frameworks, and how to align daily work with long-term strategic goals.

## KEY TEXTS & CONCEPTS
- **WSJF:** Weighted Shortest Job First prioritization
- **Agile Manifesto:** Iterative, incremental development
- **User Stories:** Capturing requirements from user perspective
- **Definition of Done:** Clear acceptance criteria
- **Velocity Tracking:** Measuring team throughput over time

## MATHEMATICAL FOUNDATION
WSJF Score calculation:
$$\text{WSJF} = \frac{\text{Cost of Delay}}{\text{Job Duration}}$$

Where Cost of Delay includes:
- User value
- Time criticality
- Risk reduction / opportunity enablement

## INSTRUCTION

### 1. Backlog Structure

```python
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional

class Priority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    BACKLOG = 5

@dataclass
class BacklogItem:
    """Single item in product backlog."""
    id: str
    title: str
    description: str
    priority: Priority = Priority.MEDIUM
    effort: int = 3  # Story points or T-shirt size
    value: int = 5   # Business value score
    status: str = "inbox"  # inbox, active, done
    created: datetime = field(default_factory=datetime.now)
    completed: Optional[datetime] = None
    linked_skills: list[str] = field(default_factory=list)

    def wsjf_score(self) -> float:
        """Calculate WSJF priority score."""
        if self.effort == 0:
            return float('inf')
        return self.value / self.effort
```

### 2. Backlog Management

```python
class ProductBacklog:
    """Manage product backlog with prioritization."""

    def __init__(self, path: str = "product_backlog.md"):
        self.path = path
        self.items: list[BacklogItem] = []

    def add_item(self, item: BacklogItem):
        """Add item to backlog inbox."""
        item.status = "inbox"
        self.items.append(item)
        self._sort_by_priority()

    def prioritize(self):
        """Re-prioritize backlog using WSJF."""
        self._sort_by_priority()

    def _sort_by_priority(self):
        """Sort by WSJF score descending."""
        self.items.sort(key=lambda x: x.wsjf_score(), reverse=True)

    def get_top_items(self, n: int = 5) -> list[BacklogItem]:
        """Get top N items for next sprint."""
        active = [i for i in self.items if i.status != "done"]
        return active[:n]

    def mark_done(self, item_id: str):
        """Complete an item."""
        for item in self.items:
            if item.id == item_id:
                item.status = "done"
                item.completed = datetime.now()
                break
```

### 3. Sprint Planning

```python
class SprintPlanner:
    """Plan sprints from prioritized backlog."""

    def __init__(self, velocity: int = 20):
        self.velocity = velocity  # Story points per sprint

    def plan_sprint(self, backlog: ProductBacklog) -> list[BacklogItem]:
        """Select items that fit within velocity."""
        sprint_items = []
        total_effort = 0

        for item in backlog.get_top_items(20):
            if total_effort + item.effort <= self.velocity:
                sprint_items.append(item)
                total_effort += item.effort
                item.status = "active"

        return sprint_items

    def estimate_velocity(self, completed_sprints: list[list[BacklogItem]]) -> float:
        """Calculate average velocity from history."""
        if not completed_sprints:
            return self.velocity

        velocities = [sum(i.effort for i in sprint) for sprint in completed_sprints]
        return sum(velocities) / len(velocities)
```

### 4. Retrospective Generation

```python
def generate_retrospective(sprint_items: list[BacklogItem]) -> dict:
    """Generate sprint retrospective metrics."""
    completed = [i for i in sprint_items if i.status == "done"]

    return {
        "planned": len(sprint_items),
        "completed": len(completed),
        "completion_rate": len(completed) / len(sprint_items) if sprint_items else 0,
        "total_effort": sum(i.effort for i in sprint_items),
        "delivered_effort": sum(i.effort for i in completed),
        "avg_cycle_time": calculate_avg_cycle_time(completed),
        "top_blockers": identify_blockers(sprint_items)
    }
```

### 5. Full Workflow Example

```python
# Session start workflow
backlog = ProductBacklog()
backlog.load_from_file("product_backlog.md")

# Prioritize and select work
backlog.prioritize()
sprint = SprintPlanner(velocity=15).plan_sprint(backlog)

# Create task.md from sprint
with open("task.md", "w") as f:
    f.write("# Today's Tasks\n\n")
    for item in sprint:
        f.write(f"- [ ] {item.title} ({item.effort}pts)\n")

# End of session
for item in sprint:
    if item_is_complete(item):
        backlog.mark_done(item.id)

# Generate retrospective
retro = generate_retrospective(sprint)
```

## ARTIFACTS
| Artifact | Purpose | Update Frequency |
|----------|---------|------------------|
| `product_backlog.md` | Feature requests, ideas | Daily |
| `task.md` | Session checklist | Per session |
| `implementation_plan.md` | Technical roadmap | Per feature |
| `walkthrough.md` | Proof of work | Per major task |

## APPLICATIONS
- **Feature Prioritization:** Rank what to build next
- **Sprint Planning:** Allocate work within capacity
- **Progress Tracking:** Monitor delivery velocity
- **Stakeholder Communication:** Show roadmap progress
- **Retrospectives:** Improve process continuously

## VERSION
v2.0 (upgraded from v1.0)

## SEE ALSO
- PROJECT_MANAGEMENT_PRIME.md
- R_ZERO_CHALLENGER_PRIME.md
- DEMOCRATIC_DEBATE_PRIME.md
