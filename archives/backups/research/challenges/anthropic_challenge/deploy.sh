#!/bin/bash
set -e

PROJECT_ID="cohezion-447915"
SERVICE_NAME="anthropic-challenge"
REGION="us-central1"

gcloud builds submit --tag gcr.io/$PROJECT_ID/$SERVICE_NAME

gcloud run deploy $SERVICE_NAME \
  --image gcr.io/$PROJECT_ID/$SERVICE_NAME \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --project $PROJECT_ID
