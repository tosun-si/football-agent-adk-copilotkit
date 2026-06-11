#!/bin/bash
set -euo pipefail

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-gb-poc-373711}"
REGION="${LOCATION:-europe-west1}"
DISPLAY_NAME="football-stats-agent-copilotkit"
DESCRIPTION="Football stats agent using ADK and BigQuery MCP via Agent Registry"
AGENT_DIR="football_stats_agent"
REQUIREMENTS_FILE="${AGENT_DIR}/requirements.txt"

# Generate requirements.txt from the workspace member's pyproject so
# adk deploy ships the exact versions we use locally (extras included).
# `--package football-stats-agent` scopes the resolution to that member,
# dropping dev tooling and the proxy member from the export. Without
# this, `adk deploy` derives a stripped-down requirements.txt from
# imports and drops the extras → import errors at runtime on Agent Engine.
trap 'rm -f "${REQUIREMENTS_FILE}"' EXIT

echo "--- Generating ${REQUIREMENTS_FILE} from pyproject.toml ---"
uv export --no-dev --no-hashes --no-emit-project --package football-stats-agent -o "${REQUIREMENTS_FILE}"

echo "--- Deploying to Vertex AI Agent Engine ---"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Agent: ${AGENT_DIR}"

uv run adk deploy agent_engine \
    --project "${PROJECT_ID}" \
    --region "${REGION}" \
    --display_name "${DISPLAY_NAME}" \
    --description "${DESCRIPTION}" \
    "$(pwd)/${AGENT_DIR}"

echo "--- Done ---"
