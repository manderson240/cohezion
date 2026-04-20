---
description: Run capability matrix assessment, gap analysis, or fine-tuning evaluation
arguments:
  - name: subcommand
    description: "What to assess: (empty)=full report, model <id>, gaps, finetune, onboard <model>"
    required: false
---

Run the Cohezion Capability Matrix assessment.

## What This Does

The capability matrix unifies tracking across models, skills, and agents to provide:
- **Full report** (`/assess`): Matrix of all entities with quality, speed, success rates
- **Model assessment** (`/assess model <id>`): Detailed assessment of a specific model
- **Gap analysis** (`/assess gaps`): Identify missing or weak capabilities
- **Fine-tuning** (`/assess finetune`): Show fine-tuning opportunities with ROI estimates
- **Model onboarding** (`/assess onboard <model>`): Generate router entries for a new model

## Steps

1. Import and instantiate the CapabilityMatrix and WorkflowManager:
   ```python
   from cohezion.compound.capability_matrix import CapabilityMatrix
   from cohezion.compound.workflow_manager import WorkflowManager
   matrix = CapabilityMatrix()
   wm = WorkflowManager(matrix)
   ```

2. Based on the subcommand argument (`$ARGUMENTS`):

   - **No argument or "report"**: Run `matrix.export_report()` and display the full matrix
   - **"model <id>"**: Run `matrix.assess_model("<id>")` and show detailed entry
   - **"gaps"**: Run `wm.export_gap_report()` and display gap analysis
   - **"finetune"**: Run `matrix.suggest_finetune_targets()` and show opportunities
   - **"onboard <model>"**: Run `wm.run_model_onboarding("<model>")` then `wm.generate_router_entries("<model>")` and show the generated code snippets

3. Display results as formatted markdown tables

4. If gaps are found, suggest next actions:
   - For "scout" gaps: Suggest running `/scout` with specific criteria
   - For "finetune" gaps: Show the fine-tuning command and data requirements
