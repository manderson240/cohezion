# BMAD Traceability Graph

```mermaid
graph TD
    4_implementation -->|invokes| validate_workflow
    4_production -->|invokes| validate_workflow
    gametest -->|chains to| test_framework
```
