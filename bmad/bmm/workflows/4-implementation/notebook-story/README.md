# Notebook Story Workflow

## Overview

Notebook stories are executable Jupyter notebooks that demonstrate, verify, or prototype agent orchestration patterns. They serve as living documentation and verification artifacts for the BMad agentic system.

## When to Use Notebook Stories

Use notebook stories for:

- **Orchestration Pattern Demonstrations** - Show how agents coordinate using specific patterns (loop, threshold, sequential, etc.)
- **Verification & Testing** - Verify that orchestration components (HRM, router, skills) work correctly
- **Prototyping** - Experiment with new orchestration approaches before codifying them
- **ML Experiments** - Document MLE-star style hypothesis testing and metric tracking
- **Integration Testing** - Test multi-agent collaboration patterns

Do NOT use notebook stories for:

- Feature implementation (use regular dev-story workflow)
- Production code (notebooks are for demonstration/verification only)
- Documentation-only content (use markdown files)

## Workflow Steps

### 1. Create Notebook from Template

```bash
# Copy template to stories/notebooks directory
cp bmad/bmm/workflows/4-implementation/notebook-story/notebook-story-template.ipynb \
   docs/stories/notebooks/[story-id]-[descriptive-name].ipynb
```

Naming convention: `[epic].[story]-[descriptive-name].ipynb`

Examples:
- `0-7-sample-orchestration.ipynb`
- `0-8-hrm-verification.ipynb`
- `1-3-challenger-solver-demo.ipynb`

### 2. Fill in Agent Orchestration Metadata

**In the first markdown cell:**

1. Replace `[Story ID]` with epic.story format (e.g., `0.7`)
2. Replace `[Title]` with descriptive title
3. Set **Primary Agent** from [agent-manifest.csv](file:///g:/My%20Drive/agentic_development/cohezion/bmad/_cfg/agent-manifest.csv)
4. Set **Agent Model** (e.g., `gemini-2.0-flash-exp`)
5. Set **Execution Date** (ISO 8601: `YYYY-MM-DD`)
6. Set **Status** to `drafted`
7. List all **Tools & Skills** you plan to use
8. Describe the **Orchestration Pattern**
9. Write the **Purpose** statement

**In the notebook metadata (JSON):**

Update the `agent_orchestration` object with the same information.

### 3. Implement Orchestration Logic

1. **Setup Cell** - Import required modules and tools
2. **Implementation Cells** - Write orchestration code
3. **Verification Cells** - Add assertions to validate behavior

**Best Practices:**

- Add comments explaining orchestration decisions
- Use `print()` statements to show orchestration flow
- Include assertions to verify expected behavior
- Keep cells focused (one concept per cell)
- Add markdown cells to explain complex logic

### 4. Execute and Verify

```bash
# Run notebook (from project root)
jupyter nbconvert --to notebook --execute \
  docs/stories/notebooks/[notebook-name].ipynb \
  --inplace
```

Or execute in VS Code / Jupyter Lab interactively.

**Verification Checklist:**

- [ ] All cells execute without errors
- [ ] All assertions pass
- [ ] Output demonstrates expected orchestration behavior
- [ ] Execution metadata is captured in notebook

### 5. Update Metadata Post-Execution

After successful execution:

1. Update **Status** to `completed`
2. Verify **Execution Date** is current
3. Confirm **Tools & Skills Used** list is complete
4. Review output and add any observations to markdown cells

### 6. Validate Metadata

```bash
# Validate notebook metadata
python bmad/bmm/utils/notebook_metadata_validator.py \
  --path docs/stories/notebooks/[notebook-name].ipynb
```

Fix any validation errors before committing.

### 7. Commit and Reference

```bash
git add docs/stories/notebooks/[notebook-name].ipynb
git commit -m "feat: Add notebook story [story-id] - [title]"
```

If this notebook relates to a markdown story file, add reference:

In `docs/stories/[story-id]-[name].md` under **Dev Agent Record** → **Context Reference**:

```markdown
### Context Reference

- [Notebook: [story-id]-[name].ipynb](file:///g:/My%20Drive/agentic_development/cohezion/docs/stories/notebooks/[story-id]-[name].ipynb)
```

## Multi-Agent Orchestration

For notebooks demonstrating multi-agent collaboration:

1. Set `multi_agent: true` in JSON metadata
2. List all agents in `collaborating_agents` array
3. Add "Collaborating Agents" section to markdown header
4. Document which agent performs which steps in code comments

Example:

```python
# Agent: bmad-master (Orchestrator)
# Coordinates the workflow and routes tasks

task_description = "Design microservices architecture"

# Agent: architect (via HRM Router)
# Handles complex architectural decisions
routing_decision = hrm_router.route(task_description)

# Agent: dev (Implementer)
# Executes the implementation based on architect's design
implementation = dev_agent.execute(routing_decision.output)
```

## Integration with Dev Story Workflow

Notebook stories complement markdown stories:

| Aspect | Markdown Story | Notebook Story |
|--------|---------------|----------------|
| **Purpose** | Requirements & planning | Demonstration & verification |
| **Content** | ACs, tasks, dev notes | Executable code & results |
| **Status** | drafted → review → done | drafted → completed → verified |
| **Agent Record** | Context ref, completion notes | Orchestration metadata, execution results |

**Cross-referencing:**

- Markdown story references notebook in "Context Reference"
- Notebook references markdown story in "Story ID" field
- Both share the same story ID (e.g., `0.7`)

## Notebook Metadata Schema

See [notebook-orchestration-standards.md](file:///g:/My%20Drive/agentic_development/cohezion/bmad/bmm/workflows/4-implementation/notebook-story/notebook-orchestration-standards.md) for complete schema definition.

## Examples

- [notebook-story-template.ipynb](file:///g:/My%20Drive/agentic_development/cohezion/bmad/bmm/workflows/4-implementation/notebook-story/notebook-story-template.ipynb) - Template with all fields
- [0-7-sample-orchestration.ipynb](file:///g:/My%20Drive/agentic_development/cohezion/docs/stories/notebooks/0-7-sample-orchestration.ipynb) - Loop with threshold
- [0-8-hrm-verification.ipynb](file:///g:/My%20Drive/agentic_development/cohezion/docs/stories/notebooks/0-8-hrm-verification.ipynb) - HRM router verification

## Troubleshooting

**Q: Notebook won't execute**
- Check Python path setup in first code cell
- Verify all imports are available
- Check for syntax errors

**Q: Metadata validation fails**
- Run validator with `--verbose` flag
- Check agent names against agent-manifest.csv
- Verify JSON syntax in metadata

**Q: How do I version notebooks?**
- Use git for version control
- For major changes, create new notebook with incremented story ID
- Document relationship in markdown header

## References

- [Notebook Orchestration Standards](file:///g:/My%20Drive/agentic_development/cohezion/bmad/bmm/workflows/4-implementation/notebook-story/notebook-orchestration-standards.md)
- [Agent Manifest](file:///g:/My%20Drive/agentic_development/cohezion/bmad/_cfg/agent-manifest.csv)
- [Dev Story Workflow](file:///g:/My%20Drive/agentic_development/cohezion/bmad/bmm/workflows/4-implementation/dev-story/README.md)
- [Cohezion Method](file:///g:/My%20Drive/agentic_development/cohezion/docs/cohezion-method.md)
