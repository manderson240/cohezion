---
description: Deploy Cohezion to Cloud Run
---
# Cohezion Deployment Workflow

// turbo-all

## Prerequisites
- Google Cloud SDK installed
- Docker installed
- Authenticated to GCP: `gcloud auth login`

## Steps

1. Build Docker image
```bash
cd /home/mike-anderson/dev/cohezion
docker build -t cohezion:latest .
```

2. Tag for Cloud Run
```bash
docker tag cohezion:latest gcr.io/PROJECT_ID/cohezion:latest
```

3. Push to Container Registry
```bash
docker push gcr.io/PROJECT_ID/cohezion:latest
```

4. Deploy to Cloud Run
```bash
gcloud run deploy cohezion \
  --image gcr.io/PROJECT_ID/cohezion:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 2Gi \
  --cpu 2 \
  --port 8080
```

5. Verify deployment
```bash
curl https://cohezion-HASH-uc.a.run.app/health
```

## Environment Variables
Set these in Cloud Run:
- `OLLAMA_HOST` - Ollama server URL
- `SURREAL_URL` - SurrealDB connection
- `COHEZION_SECRET_KEY` - JWT secret

## Local Development
```bash
cd /home/mike-anderson/dev/cohezion
uv run uvicorn cohezion.api:app --reload --port 8080
```
