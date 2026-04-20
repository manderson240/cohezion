---
name: graph-engine-correctness
description: |
  Common correctness bugs in DAG/graph execution engines. Use when: (1) building
  or reviewing a graph execution engine, (2) nodes receive empty inputs unexpectedly,
  (3) a bridge/wrapper method creates an engine but all nodes behave as passthrough,
  (4) multi-root workflows silently drop initial data. Two distinct bugs covered:
  (a) seeding only one root node instead of all roots, (b) bridge methods that
  create a registration-pattern engine but never register implementations.
author: Claude Code
version: 1.0.0
---

# Graph Execution Engine Correctness Patterns

## Problem 1: Only Seeding the Entry Node

### Symptom
Multi-root DAG workflows receive empty inputs `{}` on nodes that have no incoming
edges (other than the declared `entry_node_id`). Execution appears to work but
produces wrong results — root nodes start with no data.

### Root Cause
Graph engines often have a declared `entry_node_id` in the spec, but a DAG can
have **multiple root nodes** (nodes with in-degree 0). Only seeding the declared
entry node leaves other roots with empty inputs.

### Fix
Seed ALL nodes whose predecessor list is empty, not just the designated entry node.

```python
# BAD — only seeds one node even in multi-root DAGs
node_data[workflow.entry_node_id] = dict(initial_input)
predecessors = self._build_predecessors(workflow)

# GOOD — seed all roots (nodes with no incoming edges)
predecessors = self._build_predecessors(workflow)
for node in workflow.nodes:
    if not predecessors.get(node.id):
        node_data[node.id] = dict(initial_input)
```

**Key insight:** Build the predecessor map first, then use it for root detection.
This reuses an already-necessary structure rather than adding a separate pass.

---

## Problem 2: Bridge Method Creates Empty Engine

### Symptom
A wrapper/bridge method (`execute_graph()`, `run_workflow()`, etc.) creates
a `WorkflowEngine` and calls `execute()`. Every node returns its inputs unchanged
(passthrough behavior). Node implementations are never actually called.

### Root Cause
The engine uses a **registration pattern** (`register_node(impl)`) to decouple
node specs from implementations. Bridge methods that only create the engine but
never register implementations cause `_dispatch_node()` to hit the "no impl"
branch and passthrough every node.

### Fix
Iterate the `WorkflowSpec.nodes` and register a concrete node implementation for
each, using `node_type` to select the right class.

```python
# BAD — engine created but empty; all nodes passthrough
engine = WorkflowEngine()
result = await engine.execute(workflow, initial_input or {})

# GOOD — populate engine from spec before executing
node_type_map = {
    "agent": AgentNode,
    "tool": ToolNode,
    "logic_switch": LogicSwitchNode,
    "custom": CustomNode,
}
engine = WorkflowEngine()
for node_spec in workflow.nodes:
    node_cls = node_type_map.get(node_spec.node_type, CustomNode)
    engine.register_node(node_cls(node_spec))

result = await engine.execute(workflow, initial_input or {})
```

**Key insight:** Any method that bridges into a registration-pattern engine is
responsible for populating it. This is easy to miss because the engine will happily
execute in passthrough mode without errors.

---

## Checklist for Graph Engine Review

When auditing a graph execution engine, verify:

- [ ] **Root seeding:** All nodes with no predecessors receive `initial_input`
- [ ] **Bridge methods:** Every method that creates an engine also registers nodes
- [ ] **Context leak:** Internal metadata keys (e.g. `_flux_context`) are stripped
      from node outputs before edge propagation
- [ ] **Type imports:** Any `Any` annotation without import will fail type checkers
      even if `from __future__ import annotations` prevents runtime errors

## Example: Cohezion WorkflowEngine

- Root seeding fix: `src/cohezion/graph/engine.py` (predecessors-based seeding)
- Bridge fix: `src/cohezion/swarm/execution_orchestrator.py` (`execute_graph()`)
- Context leak fix: `src/cohezion/graph/nodes.py` (`AgentNode.forward()`)
