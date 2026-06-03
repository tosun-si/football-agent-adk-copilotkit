#!/usr/bin/env bash
set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-gb-poc-373711}"
REGION="${LOCATION:-europe-west1}"
SERVICE_NAME="agent-engine-proxy-copilotkit"
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/internal-images"
IMAGE="${REGISTRY}/${SERVICE_NAME}:latest"

# PROJECT_NUMBER and ENGINE_ID are required by main.py; sourced from
# .envrc via direnv when running locally.
: "${PROJECT_NUMBER:?PROJECT_NUMBER env var is required (run direnv allow)}"
: "${ENGINE_ID:?ENGINE_ID env var is required (run direnv allow)}"

echo "Building amd64 image and pushing to Artifact Registry..."
docker buildx build --platform linux/amd64 -t "${IMAGE}" ../agent_engine_proxy --push -f ../agent_engine_proxy/Dockerfile

echo "Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --image "${IMAGE}" \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "GCP_PROJECT_ID=${PROJECT_ID},PROJECT_NUMBER=${PROJECT_NUMBER},LOCATION=${REGION},ENGINE_ID=${ENGINE_ID}" \
  --port 8080

echo "Done! Service URL:"
gcloud run services describe "${SERVICE_NAME}" \
  --region "${REGION}" \
  --project "${PROJECT_ID}" \
  --format "value(status.url)"
