---
type: antigravity-artifact
session_id: a62d57fc-4d38-4adb-85a9-90e7977b1b20
date: 2026-03-04
title: "Connectivity Guide Prime"
aspect: doer
neural:
  activation: 0.291
  stage: embryo
  cluster: Agents
---

 # CONNECTIVITY_GUIDE_PRIME

## SurrealDB (8000)
```bash
curl -X GET "http://localhost:8000/rd"
```

## Cloud Vault (8360)
```bash
curl -X GET "http://localhost:8360/api/v1/healthcheck"
```

## Ollama (11434)
```bash
curl -X POST "http://localhost:11434/api/model/completions" \
  -H 'Content-Type: application/json' \
  -d '{ "prompt": "Tell me a joke." }'
```

## Obsidian/Claude Code (22360)
```bash
curl -X GET "http://localhost:22360/docs"
```

