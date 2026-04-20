Deploy Cohezion to Cloud Run.

IMPORTANT: Free Tier only (min-instances=0, max-instances=1, ephemeral storage).

Prerequisites check:
1. Verify Docker is running: `docker ps`
2. Verify GCP auth: `gcloud auth list`

Steps:
1. Build: `docker build -t cohezion:latest .`
2. Tag: `docker tag cohezion:latest gcr.io/PROJECT_ID/cohezion:latest`
3. Push: `docker push gcr.io/PROJECT_ID/cohezion:latest`
4. Deploy: `gcloud run deploy cohezion --image gcr.io/PROJECT_ID/cohezion:latest --platform managed --region us-central1 --allow-unauthenticated --memory 2Gi --cpu 2 --port 8080 --min-instances 0 --max-instances 1`
5. Verify: health check the deployed URL

Ask user for PROJECT_ID before proceeding if not known.
