# Active OmA Rule Packs

**Session ID**: `80835800-7087-42b0-ae2a-5573c6be7538`  
**Profile**: `balanced`  
**Mode**: `full-auto`  
**Last Updated**: 2026-09-19T00:55:00Z  

| Rule Pack | Status | Trigger | Primary Lane | Fail Policy |
| --- | --- | --- | --- | --- |
| `hardware-safety` | **ACTIVE** | `alwaysApply: true` | P0-safety | Fail-Closed |
| `kaggle-discipline` | **ACTIVE** | `alwaysApply: true` | P0-safety | Fail-Closed |
| `dual-store-persistence` | **ACTIVE** | `alwaysApply: true` | P1-quality | Fail-Warn |
| `tests-required` | **CONDITIONAL** | Code edits in `src/cohezion/**` | P1-quality | Fail-Warn |
| `migration-safety` | **CONDITIONAL** | DB schema or contract modifications | P0-safety | Fail-Closed |
| `security-review` | **CONDITIONAL** | Auth, tokens, credentials | P0-safety | Fail-Closed |
