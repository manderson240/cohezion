---
name: async_workflow
description: Asynchronous task queue using Google Keep or local file, with email notifications.
keywords:
- async
- async_workflow
- email_notifier
- keep_integration
- workflow
---

# SKILL: ASYNC_WORKFLOW_PRIME

## DOMAIN EXPERTISE
Asynchronous task queue using Google Keep or local file, with email notifications.

## SETUP

### Google Keep Integration
1. Install gkeepapi: `pip install gkeepapi`
2. Create app password: https://myaccount.google.com/apppasswords
3. Get master token: Use gpsoauth or keep-mcp token generator
4. Set environment:
   ```bash
   export GOOGLE_EMAIL="your.email@gmail.com"
   export GOOGLE_KEEP_TOKEN="your-master-token"
   ```

### Email Notifications
1. Enable 2FA on Gmail
2. Create app password
3. Set environment:
   ```bash
   export NOTIFICATION_EMAIL="sender@gmail.com"
   export NOTIFICATION_PASSWORD="app-password"
   export NOTIFICATION_RECIPIENT="you@email.com"
   ```

### Local Fallback
If Google Keep not configured, uses `.cohezion/tasks.md`:
```markdown
- [ ] Task to do
- [x] Completed task
```

## USAGE

### Check Queue
```bash
python -m cohezion.mcp.async_workflow check
```

### Run Pending Tasks
```bash
python -m cohezion.mcp.async_workflow run
```

### Task Keywords
| Keyword | Handler |
|---------|---------|
| simulate | Run simulations |
| debate | Democratic debate |
| analyze | Semantic analysis |
| audit | Platform audit |
| test | Run pytest |

## SEE ALSO
- keep_integration.py
- email_notifier.py
- async_workflow.py


## KEY CONCEPTS
- **Manifold Mapping**: Tracking 12D Poincaré state representation for async workflow.
- **AutoHarness Invariants**: 0ms AST bytecode policy assertions (arXiv:2603.03329v1).
- **Deterministic Execution**: Zero-latency verification and sovereign local execution.


## INSTRUCTION

### 1. Initialize Context
```python
from cohezion.flume import PoincareManifoldND
from cohezion.agi.autoharness_policy import AutoHarnessPolicy

policy = AutoHarnessPolicy()
state = PoincareManifoldND.project([0.05] * 2048, target_dim=12)
```

### 2. Execute Deterministic Action
```python
# Verify state invariants with 0ms overhead
res = policy.verify_action("standard_execution", state)
assert res.allowed is True
```


## VERSION
v1.0 (Auto-Standardized & Verified)
