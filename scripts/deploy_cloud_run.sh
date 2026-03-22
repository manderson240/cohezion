#!/bin/bash
set -e

PROJECT_ID="cohezion-477604"
SERVICE_NAME="cohezion"
REGION="us-central1"
IMAGE_URI="us-central1-docker.pkg.dev/$PROJECT_ID/cohezion-repo/$SERVICE_NAME:latest"

# Check for gcloud
if ! command -v gcloud &> /dev/null; then
    echo "gcloud command not found. Checking common locations..."
    if [[ ":$PATH:" != *":/snap/bin:"* ]] && [ -d "/snap/bin" ]; then
        echo "Adding /snap/bin to PATH"
        export PATH=$PATH:/snap/bin
    fi
fi

if ! command -v gcloud &> /dev/null; then
    echo "Error: gcloud SDK is not installed or not in PATH."
    echo "Please install it: https://cloud.google.com/sdk/docs/install"
    echo "Or ensure it is in your PATH."
    exit 1
fi

echo "Using Project ID: $PROJECT_ID"
echo "Deploying Service: $SERVICE_NAME"
echo "Image URI: $IMAGE_URI"

# Build
echo "Building Docker image..."
# Use --platform linux/amd64 to ensure compatibility
docker build --platform linux/amd64 --build-arg CACHEBUST=$(date +%s) -t $SERVICE_NAME:latest .

# Tag
echo "Tagging image..."
docker tag $SERVICE_NAME:latest $IMAGE_URI

# Push
echo "Pushing to GCR..."
docker push $IMAGE_URI

# Deploy
echo "Deploying to Cloud Run..."
# Note: OLLAMA_HOST and SURREAL_URL set to defaults if not provided.
# Warning: localhost in Cloud Run refers to the container, not the host machine.
DEFAULT_OLLAMA="http://localhost:11434"
DEFAULT_SURREAL="ws://localhost:8000/rpc"

echo "Using Environment:"
echo "OLLAMA_HOST: ${OLLAMA_HOST:-$DEFAULT_OLLAMA}"
echo "SURREAL_URL: ${SURREAL_URL:-$DEFAULT_SURREAL}"

gcloud run deploy $SERVICE_NAME \
  --image $IMAGE_URI \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2 \
  --set-env-vars "OLLAMA_HOST=${OLLAMA_HOST:-$DEFAULT_OLLAMA},SURREAL_URL=${SURREAL_URL:-$DEFAULT_SURREAL}" \
  --port 8080 \
  --project $PROJECT_ID

echo "Deployment complete!"
