---
name: bmad-create-prd
description: Create a Product Requirements Document using BMAD. Use when starting a new product or feature.
---

# Create PRD

Create a Product Requirements Document using BMAD methodology.

## Prerequisites

- You should have a clear product idea
- Know your target users
- Have key features identified

## Usage

```bash
curl -X POST http://localhost:8361/tools/bmad_bmm_create_prd \
  -H "Content-Type: application/json" \
  -d '{
    "product_idea": "A mobile app for tracking daily habits",
    "target_users": "Productivity enthusiasts aged 25-45",
    "key_features": ["Daily streaks", "Reminders", "Analytics", "Social sharing"]
  }'
```

## Workflow

1. **Call the tool** with your product details
2. **Load the workflow**: Read `_bmad/bmm/2-plan-workflows/create-prd/workflow-create-prd.md`
3. **Follow the workflow** instructions exactly
4. **Create the PRD** in the appropriate location

## Next Steps

After creating the PRD:
- Use `bmad_bmm_validate_prd` to validate
- Create user stories with `bmad_bmm_create_story`
- Plan your sprint with `bmad_bmm_sprint_planning`
