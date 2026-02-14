# Decision Analysis UI Guide

## Overview

The Decision Analysis feature extends the 3D Graph visualization with interactive exploration of decision reasoning, cascades, and contradictions. Users can drill down from high-level paper relationships to understand **why** decisions were made and **how** they impact other decisions.

## Getting Started

### 1. Open Decision Explorer

In the plugin UI, look for the **Decision Explorer** panel in the sidebar. It appears as a collapsible section below the 3D graph controls.

### 2. Search for a Decision

Type in the search box to find decisions by:
- **Title**: "Phase 2 Complete"
- **Chosen Option**: "Microservices"
- **Decision ID**: "2026-02-14-phase-2-complete"

Search results appear in real-time (<50ms response) with matching decisions highlighted.

### 3. View Decision Details

When you select a decision, the panel shows:
- **Chosen Option**: What was ultimately selected
- **Reasoning Type**: How the decision was made (research, pattern, intuition, convention, hybrid)
- **Confidence Score**: 0-100% confidence in the decision
- **Status**: Active, Archived, or Revisited
- **Rationale**: Full explanation of the decision
- **Alternatives Rejected**: Why other options weren't chosen

### 4. Explore Reasoning Chain

Click **🔗 View Reasoning Chain** to open a flowchart showing:
- Each logical step that led to the decision
- Confidence level for each step
- Type of reasoning used (research, pattern, etc.)
- Key assumptions

**Color Coding**:
- Blue: Research-based reasoning
- Green: Pattern-based reasoning
- Amber: Intuition-based reasoning
- Purple: Convention-based reasoning
- Indigo: Hybrid reasoning

### 5. Analyze Cascades

Click **📊 View Cascades** to see downstream impacts:
- Decisions that are **enabled** by this decision
- Decisions that are **blocked** if this is reversed
- Decisions that are **influenced** indirectly
- Decisions that **conflict** with this one

**Impact Levels**:
- 🔴 Critical: Would require major redesign if reversed
- 🟠 Significant: Would require moderate changes
- ⚪ Minor: Minimal impact if reversed

### 6. Check for Contradictions

Click **⚠️ View Contradictions** to identify:
- Lessons learned that contradict this decision
- Operational evidence that conflicts with it
- Items that require review based on new data

**Severity Levels**:
- Critical: Decision is fundamentally challenged
- High: Significant conflict, needs investigation
- Medium: Some evidence against the decision
- Low: Minor inconsistency

### 7. Open in Vault

Click **📝 Open in Vault** to view the original decision note with full context and discussion.

## Common Workflows

### Trace a Decision Impact

1. Search for your decision
2. Click "View Cascades"
3. See all downstream decisions
4. Click a cascaded decision to view its reasoning
5. Use breadcrumbs to navigate back

### Validate Decision Quality

1. Select a decision
2. Check confidence score (>80% is high confidence)
3. Click "View Reasoning Chain"
4. Review assumptions
5. Check "View Contradictions" for conflicting evidence

### Find Similar Decisions

1. Open a decision
2. Note the reasoning type
3. Search for other decisions with that type
4. Compare their confidence scores and outcomes

### Investigate a Contradiction

1. Click "View Contradictions"
2. Select a high-severity contradiction
3. Click the lesson ID to view the conflicting evidence
4. Compare with the decision's rationale
5. Decide if decision needs revisiting

## UI Components

### Search Bar

- **Fuzzy matching**: "phase complete" matches "Phase 2 Complete"
- **Real-time results**: <50ms response
- **Recent list**: Quick access to 5 most recent decisions
- **Character limit**: Search after 2+ characters

### Metadata Display

- **Confidence bar**: Visual indicator of decision strength
- **Status badge**: Shows current decision status
- **Reasoning badge**: Shows how decision was made
- **Expandable rationale**: Click to see full explanation

### Flowchart

- **Nodes**: One per reasoning step
- **Arrows**: Show progression from step to step
- **Colors**: Indicate type of reasoning
- **Confidence bars**: Show strength of each step
- **Expandable details**: Click step for full content

### Cascade Graph

- **Nodes**: Represent decisions
- **Edges**: Show dependencies
- **Node colors**: Indicate impact level
- **Force layout**: Positions nodes based on relationships
- **Click nodes**: View details in explorer

### Contradiction Table

- **Sortable columns**: Click headers to sort
- **Severity colors**: Instant visual scan of issue importance
- **Expandable rows**: Click to see full details
- **Filter by severity**: Future enhancement

## Settings

Access plugin settings to customize:

- **Decision overlay**: Show/hide decision nodes in 3D graph
- **Reasoning chain colors**: Customize color scheme
- **Cascade depth**: How many levels to show (1-5)
- **Confidence threshold**: Only show decisions above threshold
- **Default reasoning type filter**: Filter by reasoning method

## Performance

- **Search**: <50ms for 88 decisions
- **Reasoning flowchart**: <500ms to render
- **Cascade graph**: <200ms with force layout
- **Contradiction table**: <100ms to sort
- **SurrealDB queries**: <200ms (with caching)

## Troubleshooting

### "No decisions found"

- Check vault has decisions in `/decisions/` folder
- Verify decision notes have `tags: [decision]` in frontmatter
- Run "Reload decisions" from settings

### "SurrealDB connection failed"

- Verify SurrealDB is running: `curl http://localhost:8000/health`
- Check network connectivity
- Plugin gracefully falls back to vault-only mode
- Cached data remains available

### "Flowchart doesn't render"

- Check decision has reasoning_chain in frontmatter
- Verify decision has at least 1 reasoning step
- Clear browser cache: Settings → Advanced → Clear cache

### "Cascades show no results"

- Decision may not have downstream impacts recorded
- Check vault for links from other decisions to this one
- SurrealDB may need reindexing (see admin guide)

### "Slow performance with many decisions"

- Clear cache: Settings → Performance → Clear decision cache
- Reduce cascade depth: Settings → Visualization → Cascade depth
- Close unused visualizations to free memory

## Keyboard Shortcuts

- `Ctrl/Cmd + K`: Open decision search
- `Enter`: Select highlighted decision
- `Esc`: Close modal
- `→`: Next contradiction
- `←`: Previous contradiction

## Accessibility

- Full keyboard navigation support
- Color-blind friendly badges (shapes + colors)
- Screen reader support (ARIA labels)
- High contrast mode available in settings

## Advanced Usage

### Export Decisions

Click the export icon to download decision data as:
- CSV (for spreadsheet analysis)
- JSON (for programmatic processing)
- Markdown (for reports)

### Create Decision Reports

1. Select decisions you want to report on
2. Click "Generate Report"
3. Choose report type:
   - Summary: High-level overview
   - Detail: Full reasoning chains
   - Impact: Cascade analysis
   - Quality: Contradiction analysis

### Link Decisions to Projects

In decision notes, add:
```yaml
related_projects:
  - project-name-1
  - project-name-2
```

Then filter explorer by project.

## Integration with 3D Graph

Decision nodes appear in the 3D graph when enabled:

- **Color**: By reasoning type (same as flowchart)
- **Size**: By confidence score
- **Glow**: High-confidence decisions glow
- **Edges**: Connect to related papers
- **Click**: Opens in Decision Explorer

Toggle decision visibility in 3D graph settings.

## See Also

- [Reasoning Chains Explained](./REASONING_CHAINS_EXPLAINED.md)
- [SurrealDB Integration](./SURREALDB_INTEGRATION.md)
- [API Reference](./API_REFERENCE.md)
