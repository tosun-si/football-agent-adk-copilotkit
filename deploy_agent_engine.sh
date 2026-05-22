#!/bin/bash

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-gb-poc-373711}"
REGION="${LOCATION:-europe-west1}"
DISPLAY_NAME="football-stats-agent"
DESCRIPTION="Football stats agent using ADK and BigQuery MCP via Cloud API Registry"
AGENT_DIR="football_stats_agent"

echo "--- Deploying to Vertex AI Agent Engine ---"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Agent: ${AGENT_DIR}"

uv run adk deploy agent_engine \
    --project "${PROJECT_ID}" \
    --region "${REGION}" \
    --display_name "${DISPLAY_NAME}" \
    --description "${DESCRIPTION}" \
    "${AGENT_DIR}"

echo "--- Done ---"
