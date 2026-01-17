# SKILL: CLOUD_DEPLOYMENT_PRIME

## DOMAIN EXPERTISE
You are a specialist in **cloud deployment** - Docker, Cloud Run, CI/CD, and serverless patterns.

## INSTRUCTION

### 1. Docker Compose
```yaml
services:
  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      - DATABASE_URL=...
    depends_on:
      - db
```

### 2. Dockerfile
```dockerfile
FROM python:3.12-slim
WORKDIR /app
RUN pip install uv
COPY . .
RUN uv sync --frozen
EXPOSE 8080
CMD ["uv", "run", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 3. Cloud Run Deploy
```bash
# Build and push
docker build -t gcr.io/PROJECT/app .
docker push gcr.io/PROJECT/app

# Deploy
gcloud run deploy app \
  --image gcr.io/PROJECT/app \
  --region us-central1 \
  --allow-unauthenticated
```

### 4. Health Checks
```python
@app.get("/health")
async def health():
    return {"status": "healthy"}
```

## SEE ALSO
- API_PATTERNS_PRIME.md
