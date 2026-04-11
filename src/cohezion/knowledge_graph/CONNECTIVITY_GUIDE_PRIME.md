 # CONNECTIVITY_GUIDE_PRIME

## SurrealDB (8000)
```bash
curl -X GET "http://localhost:8001/rd"
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

