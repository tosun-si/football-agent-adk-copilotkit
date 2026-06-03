#!/bin/bash
set -euo pipefail

# Configuration
SERVICE_NAME="football-stats-api-copilotkit"
REGION="europe-west1"
PROJECT_ID="gb-poc-373711"
REGISTRY="europe-west1-docker.pkg.dev/${PROJECT_ID}/internal-images"
IMAGE_NAME="${REGISTRY}/${SERVICE_NAME}:latest"

echo "--- Deploying ADK API Server to Cloud Run ---"
echo "Project: ${PROJECT_ID}"
echo "Service: ${SERVICE_NAME}"
echo "Region: ${REGION}"

# 1. Build amd64 image and push to Artifact Registry
echo "Building amd64 image and pushing to Artifact Registry..."
docker buildx build --platform linux/amd64 -t "${IMAGE_NAME}" . --push

# 3. Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --image "${IMAGE_NAME}" \
    --platform managed \
    --region "${REGION}" \
    --allow-unauthenticated \
    --set-env-vars "GCP_PROJECT_ID=${PROJECT_ID},LOCATION=${REGION},GOOGLE_GENAI_USE_VERTEXAI=True,BIGQUERY_DATASET=qatar_fifa_world_cup,BIGQUERY_TABLE=team_players_stat_raw,PYTHONUNBUFFERED=1" \
    --project "${PROJECT_ID}"

echo "--- Deployment Complete ---"
gcloud run services describe "${SERVICE_NAME}" --platform managed --region "${REGION}" --format 'value(status.url)' --project "${PROJECT_ID}"
