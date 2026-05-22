#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="gb-poc-373711"
REGION="europe-west1"
SERVICE_NAME="agent-engine-proxy"
REGISTRY="europe-west1-docker.pkg.dev/${PROJECT_ID}/internal-images"
IMAGE="${REGISTRY}/${SERVICE_NAME}:latest"

echo "Building amd64 image and pushing to Artifact Registry..."
docker buildx build --platform linux/amd64 -t "${IMAGE}" ../agent_engine_proxy --push -f ../agent_engine_proxy/Dockerfile

echo "Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "GCP_PROJECT_ID=${PROJECT_ID},LOCATION=${REGION}" \
  --port 8080

echo "Done! Service URL:"
gcloud run services describe "${SERVICE_NAME}" \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --format "value(status.url)"
