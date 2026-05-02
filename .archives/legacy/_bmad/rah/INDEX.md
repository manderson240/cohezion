---
name: rah-module-index
description: Master index for Resilience & Autonomic Healing (RAH) module
type: index
project: rah-module
status: in-progress
date: 2026-03-08
---

# RAH Module - Resilience & Autonomic Healing

## 🎯 Quick Navigation

### Development Workflow Artifacts

| Phase | Artifact | Status | Location |
|-------|----------|--------|----------|
| **PRD** | Product Requirements | ✅ Complete | [[_bmad/rah/prds/PRD\|PRD.md]] |
| **ARCH** | Architecture | ✅ Complete | [[_bmad/rah/architecture/ARCHITECTURE\|ARCHITECTURE.md]] |
| **EPICS** | Agile Epics | ✅ Complete | [[_bmad/rah/epics/EPICS\|EPICS.md]] |
| **CODE** | Implementation | 🟡 Phase 2 | `src/cohezion/resilience/` |
| **WORKFLOW** | Module Creation | ✅ Complete | [[_bmad/rah/workflows/implement-module\|implement-module.md]] |

---

## 📁 File Locations

### BMAD Directory Structure
```
_bmad/
├── rah/
│   ├── prds/
│   │   └── PRD.md              ⭐ Requirements
│   ├── architecture/
│   │   └── ARCHITECTURE.md      ⭐ Architecture
│   ├── epics/
│   │   └── EPICS.md            ⭐ Epics
│   ├── agents/
│   │   └── rah-specialist.md    ⭐ Agent persona
│   └── workflows/
│       └── implement-module.md  ⭐ The Master Workflow
```

### Source Code
```
src/cohezion/resilience/
├── __init__.py
├── manager.py                 ⭐ Autonomic Manager
├── strategies.py              ⭐ Healing Strategies
└── monitors/                  ⭐ Specialized Monitors
```
