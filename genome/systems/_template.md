---
title: "System Card: [Component Name]"
date: YYYY-MM-DD
version: 1
last_revised: YYYY-MM-DD
tags: [spec, system-card]
card_type: system
status: active
neural:
  activation: 0.35
  stage: embryo
  synapse_in: 0
  synapse_out: 1
---

# System Card: [Component Name]

> [!abstract] Summary
> One-paragraph description of what this system does, why it exists, and its role in Cohezion.

## Identity

| Field | Value |
|-------|-------|
| **Component** | [Name] |
| **Type** | service / database / CLI / hook / plugin |
| **Owner** | [Team or individual] |
| **Status** | active / deprecated / planned |
| **Version** | [Current version] |
| **Source** | [Path to source code or config] |
| **Deployed As** | systemd service / Docker / npm plugin / pip package |

## Connection Details

| Field | Value |
|-------|-------|
| **Host** | localhost / remote URL |
| **Port** | [Port number] |
| **Protocol** | HTTP / stdio / WebSocket / gRPC |
| **Auth** | Bearer token / basic / none |
| **Health Endpoint** | [URL or command] |

## Dependencies

| Dependency | Type | Required | Notes |
|-----------|------|----------|-------|
| [Name] | runtime / build / optional | Yes/No | [Version or constraint] |

## Capabilities

### What It Does
- [Capability 1]
- [Capability 2]

### What It Does NOT Do
- [Non-capability — clarifies scope boundaries]

## Configuration

```yaml
# Key environment variables or config
KEY: value
```

## Monitoring & Health

| Check | Method | Frequency | Alert Threshold |
|-------|--------|-----------|-----------------|
| [Check name] | [How to check] | [How often] | [When to alert] |

## Known Limitations

- [Limitation 1]
- [Limitation 2]

## Reconstruction Steps

> [!tip] Disaster Recovery
> Steps to rebuild this system from scratch using only vault knowledge.

1. [Step 1]
2. [Step 2]

## Security Considerations

- [Security note 1]

## Related

- [[related-concept-or-decision]]

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1 | YYYY-MM-DD | Initial card |
