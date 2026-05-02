---
name: post-submission-learning
enabled: true
event: bash
pattern: popcorn.*(submit|leaderboard|benchmark)
action: warn
---

## Submission Result — Record in Kernel Skill

You just ran a popcorn submission. **Before moving on, record the result.**

### Checklist:
1. **Was it a test, benchmark, or leaderboard submission?**
2. **Did it pass or fail?** If fail — what error?
3. **What was the timing?** Compare to baseline in the kernel skill.
4. **Is this a new dead end?** If so, add to the "Exhausted Paths" table.
5. **Is this an improvement?** If so, update "Current Status" and "Performance History".

### Where to record:
- GEMM results → `~/.claude/skills/amd-gemm-mxfp4-optimization/SKILL.md`
- MoE results → `~/.claude/skills/amd-moe-mxfp4-optimization/SKILL.md`
- MLA results → `~/.claude/skills/amd-mla-decode-optimization/SKILL.md`

### Format for dead ends:
```
| API/approach | Result | Root cause |
```

### Format for improvements:
Update the "Current Status" table at the top of the skill with new timing.

**Do NOT skip this step.** Unrecorded results get retried by future sessions, wasting submissions.
