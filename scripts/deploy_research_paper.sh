#!/bin/bash
# Cohezion: Living Research Paper Deployment Script
# -------------------------------------------------
# This script builds and deploys the Living Research Paper Marimo notebook
# to Google Cloud Run.

set -e

PROJECT_ID="cohezion-platform"
SERVICE_NAME="living-research-paper"
REGION="us-central1"
DOMAIN="cohezion.duckdns.org"

echo "🚀 Starting Deployment of Cohezion Living Research Paper..."

# 1. Build the container using Cloud Build (No local Docker required)
echo "🏗️ Building container on GCP..."
gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME . --project $PROJECT_ID

# 2. Deploy to Cloud Run
echo "📦 Deploying to Cloud Run (Free Tier Optimized)..."
gcloud run deploy $SERVICE_NAME \
    --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 512Mi \
    --cpu 1 \
    --min-instances 0 \
    --max-instances 1 \
    --project $PROJECT_ID

# 3. Finalize
echo "✅ Deployment Successful!"
echo "🌐 URL: \$(gcloud run services describe \$SERVICE_NAME --platform managed --region \$REGION --format 'value(status.url)' --project \$PROJECT_ID)"
echo "🔗 Domain mapped to: https://\$DOMAIN/research"
