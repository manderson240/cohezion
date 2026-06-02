---
name: api_patterns
description: You are a specialist in FastAPI development - creating robust REST APIs
  with Pydantic validation, middleware, and async patterns.
keywords:
- api
- fastapi
- mcp_server
- openapi
- patterns
- pydantic
- rest
- security_guardrails
---

# SKILL: API_PATTERNS_PRIME

## DOMAIN EXPERTISE
You are a specialist in **FastAPI development** - creating robust REST APIs with Pydantic validation, middleware, and async patterns.

## KEY CONCEPTS
- **FastAPI** - High-performance async web framework
- **Pydantic** - Data validation and settings management
- **REST** - Resource-oriented API design
- **OpenAPI** - Auto-generated documentation

## INSTRUCTION

### 1. Create FastAPI App
```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(
    title="API Name",
    description="API description",
    version="0.1.0",
)
```

### 2. Define Pydantic Models
```python
class RequestModel(BaseModel):
    field: str
    optional_field: int | None = None

class ResponseModel(BaseModel):
    result: str
    status: str = "success"
```

### 3. Create Endpoints
```python
@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.post("/resource", response_model=ResponseModel)
async def create_resource(request: RequestModel):
    # Process request
    return ResponseModel(result="created")
```

### 4. Add Middleware
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
)
```

### 5. Error Handling
```python
@app.exception_handler(ValueError)
async def value_error_handler(request, exc):
    return JSONResponse(
        status_code=400,
        content={"error": str(exc)},
    )
```

## PATTERNS

| Pattern | Use Case |
|---------|----------|
| `response_model` | Enforce response schema |
| `HTTPException` | Proper error responses |
| `Depends()` | Dependency injection |
| `BackgroundTasks` | Async processing |

## SEE ALSO
- MCP_SERVER_PRIME.md
- SECURITY_GUARDRAILS_PRIME.md
