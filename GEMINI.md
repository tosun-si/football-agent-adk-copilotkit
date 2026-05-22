# Football Stats Agent Context

## Project Overview
Goal: Create a helpful football stats assistant application using the Google Agent Development Kit (ADK) and the official BigQuery MCP protocol via Cloud API Registry.

## Architecture
- **Framework**: Google ADK (`LlmAgent`)
- **Model**: `gemini-2.5-flash` via Vertex AI
- **Tool Access**: Cloud API Registry (managed MCP server for BigQuery)
- **Deployment**: `adk web` locally / Vertex AI Agent Engine or Cloud Run in production
- **Entry Point**: `football_stats_agent.agent:root_agent` (configured in `agent_config.yaml`)

## Production Deployment

### 1. Vertex AI Agent Engine (Recommended)
Managed path using the `adk deploy agent_engine` CLI command. This handles agent serialization properly (avoids pickling issues with MCP toolsets) and enables the **Playground** in the console.
- **Command**: `./deploy_agent_engine.sh`
- **Resource Name**: `projects/975119474255/locations/europe-west1/reasoningEngines/8813658819973349376`
- **Console**: [Vertex AI Agent Engines Dashboard](https://console.cloud.google.com/vertex-ai/agents/agent-engines?project=gb-poc-373711)
- **How to Test**:
    - Go to the [Agent Engines Dashboard](https://console.cloud.google.com/vertex-ai/agents/agent-engines?project=gb-poc-373711).
    - Select the engine and use the **Playground** tab to interact with the agent.
- **Key Requirement**: The Reasoning Engine service account (`service-{PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com`) needs **both** `roles/mcp.toolUser` (to call MCP tools) and `roles/cloudapiregistry.viewer` (to discover MCP servers in the API Registry). Without `cloudapiregistry.viewer`, the deployment fails with "MCP server not found".
- **Important**: Use `adk deploy agent_engine` instead of a custom Python deploy script. Custom scripts using `ReasoningEngine.create()` with `AdkApp` fail with pickling errors (`cannot pickle '_io.TextIOWrapper'`) due to MCP toolsets. The CLI handles serialization correctly and enables the Playground.

### 2. ADK API Server (Cloud Run)
Standard REST path using FastAPI.
- **Command**: `./deploy_api.sh`
- **How to Test**:
    - **Swagger UI**: Visit `https://football-stats-api-4wtmsxga6q-ew.a.run.app/docs`.
    - **CURL**:
      1. Create a session:
      ```bash
      curl -X POST "https://football-stats-api-4wtmsxga6q-ew.a.run.app/apps/football_stats_agent/users/user123/sessions/session456" \
           -H "Content-Type: application/json" \
           -d '{}'
      ```
      2. Run the agent:
      ```bash
      curl -X POST "https://football-stats-api-4wtmsxga6q-ew.a.run.app/run" \
           -H "Content-Type: application/json" \
           -d '{
             "appName": "football_stats_agent",
             "userId": "user123",
             "sessionId": "session456",
             "newMessage": {
               "parts": [{"text": "Who is the best passer?"}]
             }
           }'
      ```

## Dataset (raw_data/)
- `world_cup_team_players_stats_raw_ndjson.json` — Raw player statistics in NDJSON format
- `create_and_load_team_stats_raw_table.sh` — Loads data into BigQuery via `bq load --autodetect`
- **Env vars**: `PROJECT_ID`, `REGION`, `BUCKET_PATH` (GCS path where the NDJSON file is uploaded)
- **Target table**: `qatar_fifa_world_cup.team_players_stat_raw`

## Data Source
- **GCP Project**: `gb-poc-373711` (Project Number: `975119474255`)
- **BigQuery Dataset**: `qatar_fifa_world_cup`
- **BigQuery Table**: `team_players_stat_raw`
- **Dataset Location**: `europe-west1`
- **API Registry Location**: `global`

## IAM Permissions Required
Roles must be granted to the user AND the **Service Accounts** (`{PROJECT_NUMBER}-compute@developer.gserviceaccount.com` and `service-{PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com`):

| Role | Purpose |
|------|---------|
| `roles/mcp.toolUser` | **Mandatory** for calling MCP tools via Cloud API Registry |
| `roles/cloudapiregistry.viewer` | **Mandatory** for discovering MCP servers in the API Registry |
| `roles/bigquery.dataViewer` | Read access to BigQuery |
| `roles/bigquery.jobUser` | Run BigQuery queries |
| `roles/aiplatform.user` | Access Vertex AI and Agent Engine |
| `roles/storage.objectAdmin` | Manage deployment artifacts |

## Troubleshooting

### McpError: Connection closed
1. **Missing IAM role**: Ensure `roles/mcp.toolUser` is granted to the service account.
2. **Incorrect SQL column names**: The table uses camelCase (`playerName`, `goalsScored`).

### Deployment Failures
1. **cannot pickle '_io.TextIOWrapper'**: Use `adk deploy agent_engine` CLI instead of custom Python deploy scripts. The CLI handles MCP toolset serialization correctly.
2. **MCP server not found**: Ensure the Service Account has `roles/cloudapiregistry.viewer` to discover MCP servers. Also try project **number** as fallback in the MCP resource name.
3. **Cloud Run Port**: Container must listen on port `8080`.
4. **adk api_server args**: Use `adk api_server` without `--app` in Docker to use `agent_config.yaml`.

## Local Development with Docker Compose

All 3 services (ADK agent, Agent Engine proxy, webapp) can run locally via Docker Compose with GCP credentials mounted from the host.

```bash
# Build all images (centralized via Docker Bake)
docker buildx bake

# Set the Agent Engine ID (required by the proxy)
export ENGINE_ID=your-engine-id

# Run all services
docker compose up
```

### Services
| Service | Local URL | Port |
|---------|-----------|------|
| ADK Agent (Cloud Run API) | `http://localhost:8080` | 8080 |
| Agent Engine Proxy | `http://localhost:8081` | 8081 |
| Webapp | `http://localhost:3000` | 3000 |

## Docker Bake (Centralized Builds)

`docker-bake-agentic-apps.hcl` defines build targets for all 3 services with Artifact Registry tags and **registry-based cache**.

```bash
# Build all
docker buildx bake

# Build one target
docker buildx bake adk-agent
docker buildx bake agent-engine-proxy
docker buildx bake webapp
```

### Targets
| Target | Image Tag | Cache Tag |
|--------|-----------|-----------|
| `adk-agent` | `.../football-stats-api:latest` | `.../football-stats-api:cache` |
| `agent-engine-proxy` | `.../agent-engine-proxy:latest` | `.../agent-engine-proxy:cache` |
| `webapp` | `.../football-stats-webapp:latest` | `.../football-stats-webapp:cache` |

All tags prefixed with `europe-west1-docker.pkg.dev/gb-poc-373711/internal-images`.

### Registry cache
Each target uses `cache-from`/`cache-to` with `type=registry` and `mode=max` (caches all layers). CI/CD pipelines reuse layers across runs, speeding up builds when only app code changes.

### Local deploy scripts
`deploy_api.sh` and `agent_engine_proxy/deploy.sh` build for `linux/amd64` with `docker buildx build --platform linux/amd64 --push`, then `gcloud run deploy`. For manual deployments from Apple Silicon machines.

## CI/CD with Cloud Build

`deploy-services-to-cloud-run.yaml` builds all images and deploys all 3 Cloud Run services.

### Pipeline steps
1. **Build & push** (`gcr.io/cloud-builders/docker`) — `docker buildx bake --push` with registry cache
2. **Deploy Agent Engine** (`uv:python3.11-alpine`) — `uv pip install --system google-adk` + `adk deploy agent_engine`
3. **Deploy Cloud Run** (`google-cloud-cli:slim`) — Retrieves the latest Agent Engine ID via Vertex AI REST API, then deploys all 3 services:
   - `football-stats-api` with BigQuery/Vertex AI env vars
   - `agent-engine-proxy` with project/location env vars + `ENGINE_ID` (dynamically retrieved from step 2)
   - `football-stats-webapp` dynamically fetches URLs from deployed services

### Run
```bash
gcloud builds submit --config deploy-services-to-cloud-run.yaml --project gb-poc-373711 --region europe-west1
```

Uses Cloud Build predefined substitutions `$PROJECT_ID` (from `--project`) and `$LOCATION` (from `--region`). The Agent Engine ID is dynamically retrieved via REST API after deployment.

### Source upload filter
`.gcloudignore` excludes `.git`, `.venv`, `node_modules`, `.next`, IDE files, docs, and local config from Cloud Build uploads.

## Dockerfiles (Multi-stage Builds)

All Python services use multi-stage builds with uv (builder -> runtime). The webapp uses a 3-stage Next.js build with `output: "standalone"`.

- **Root `Dockerfile`** (ADK agent): Builder uses `ghcr.io/astral-sh/uv:python3.11-bookworm-slim` base image with `APP_DIR=/usr/local/src/app`. Runtime uses `WORKDIR /agents` so ADK discovers the agent package by convention. Split `ENTRYPOINT ["adk"]` / `CMD ["api_server", ...]`.
- **`agent_engine_proxy/Dockerfile`**: Same uv base image and `APP_DIR` pattern. uv-managed, own `pyproject.toml`. Split `ENTRYPOINT ["uvicorn"]` / `CMD ["main:app", ...]`.
- **`webapp/Dockerfile`**: deps -> builder -> standalone runner.

## Web App (Next.js Chat UI)
A Next.js chat interface in `webapp/` that can toggle between Cloud Run and Agent Engine backends.

### Run locally (without Docker)
```bash
cd webapp && npm install && npm run dev
```
Backend URLs (`CLOUD_RUN_API_URL`, `AGENT_ENGINE_PROXY_URL`) are managed via `.envrc` (direnv) at the project root — no `.env.local` needed. Next.js API routes read them from `process.env`. When running with Docker Compose, these are overridden by the `environment` block in `docker-compose.yaml`.

## Agent Engine Proxy (FastAPI)
A FastAPI proxy in `agent_engine_proxy/` that wraps the Vertex AI Agent Engine streaming API. Managed with uv via its own `pyproject.toml`.

The proxy creates a **session** before each query (`async_create_session`), then calls `async_stream_query` with the session ID. This is required — without a session, the MCP connection drops before the agent completes its reasoning loop.

### Run locally (without Docker)
```bash
cd agent_engine_proxy && uv run uvicorn main:app --port 8080
```

### Deploy
```bash
cd agent_engine_proxy && ./deploy.sh
```

## Reference
- [Deploy with Cloud API Registry](https://discuss.google.dev/t/where-is-the-mcp-server-deploy-your-agent-with-cloud-api-registry-on-vertex-ai-agent-engine/298130)
