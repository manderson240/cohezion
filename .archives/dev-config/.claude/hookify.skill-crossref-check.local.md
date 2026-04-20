---
name: skill-crossref-check
enabled: true
event: file
conditions:
  - field: file_path
    operator: regex_match
    pattern: skills/(amd-gemm|amd-moe|amd-mla|competitive-kernel)/SKILL\.md$
---

## Kernel Skill Modified — Cross-Reference Check

You just edited a kernel optimization skill. Ensure consistency across the skill ecosystem:

### If you added a new dead end:
- [ ] Also listed in `competitive-kernel-optimization-ceiling` → "Dead End Summary" section?
- [ ] Also listed in the active plan's "Dead Ends" section?

### If you updated performance numbers:
- [ ] Also updated in `competitive-kernel-optimization-ceiling` → "Current Leaderboard" table?
- [ ] Also updated in the plan's "Current Leaderboard" table?
- [ ] COORDINATION.md Session Registry updated?

### If you added a new API signature or calling convention:
- [ ] Cross-referenced in `aiter-kernel-parameter-semantics` if it's a parameter finding?
- [ ] Cross-referenced in `aiter-mxfp4-api-limitations` if it's a limitation?

### Skill cross-reference map:
```
competitive-kernel-optimization-ceiling (hub)
├── amd-gemm-mxfp4-optimization
├── amd-moe-mxfp4-optimization
├── amd-mla-decode-optimization
├── aiter-kernel-parameter-semantics (companion)
└── aiter-mxfp4-api-limitations (companion)
```

**Keep all 6 skills consistent.** Stale data in one skill causes future sessions to retry dead ends.
