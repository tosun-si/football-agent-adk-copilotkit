# Football Agent ADK — Copilot Kit Variant

This repository is a fork of [`football-agent-adk`](../football-agent-adk) that pairs the same ADK + BigQuery MCP agent with a **Copilot Kit** frontend that renders **dynamic Recharts visualizations** when the agent decides a chart is appropriate.

> Ask "Top 5 buteurs d'Argentine ?" and the chat replies with a natural-language sentence **plus** a bar chart, generated on the fly. No UI work was done for that specific chart — the agent emits its spec as JSON, the front renders it.

## How it works

```
                     ┌─────────────────────────────┐
   User    ────────▶ │  Copilot Kit Chat UI        │
   (chat)            │  (Next.js + @copilotkit/*)  │
                     └──────────────┬──────────────┘
                                    │  CopilotKit runtime endpoint
                                    ▼
                     ┌─────────────────────────────┐
                     │  /api/copilotkit (custom    │
                     │  CopilotServiceAdapter)     │
                     └──────────────┬──────────────┘
                                    │  HTTP POST /run
                                    ▼
                     ┌─────────────────────────────┐
                     │  ADK Cloud Run API          │
                     │  (LlmAgent + BigQuery MCP)  │
                     └──────────────┬──────────────┘
                                    │
                                    ▼
                            BigQuery (Qatar 2022)

   Agent response (text) ──► fenced ```chart {…json…} ``` block
                          │
                          ▼
   ┌──────────────────────────────────────┐
   │ CopilotMarkdown.tsx detects the      │
   │ block in the markdown renderer and   │
   │ swaps it for <DynamicChart spec={…}> │
   └──────────────────────────────────────┘
```

## Diff vs. upstream

Differences from [`football-agent-adk`](../football-agent-adk):

1. **`football_stats_agent/agent.py`** — `SYSTEM_INSTRUCTION` extended with a "Visualization Output" section telling the agent to emit a JSON chart spec in a fenced ```chart``` block when the question implies a visualization.
2. **MCP discovery** — migrated from the deprecated `ApiRegistry` (Cloud API Registry) to `AgentRegistry` (Google Cloud Agent Registry). The client class changes (`get_toolset` → `get_mcp_toolset`) AND the resource names changed: Agent Registry assigns opaque UUIDs to MCP servers, so the agent now looks them up by `displayName` (`bigquery.googleapis.com`) instead of hardcoding the resource path. See `_resolve_mcp_server_name()` in `agent.py`. See `CLAUDE.md` for the rationale.
3. **`webapp/`** — completely rewritten:
   - `@copilotkit/react-ui` for the chat UI (`<CopilotChat>`)
   - `app/api/copilotkit/route.ts` — `CopilotRuntime` + a `BuiltInAgent` with a custom factory yielding AG-UI events, proxying to the ADK Cloud Run API
   - `components/DynamicChart.tsx` — Recharts component (bar / line / pie)
   - `components/CopilotMarkdown.tsx` — chart-aware markdown renderer that detects ```chart``` blocks
4. **Python deps** — `google-adk[agent-identity, mcp, a2a]>=2.1.0` and `google-cloud-aiplatform>=1.154.0`. The `a2a` extra is required transitively for `AgentRegistry`.
5. **Agent Engine deploy** — both `deploy_agent_engine.sh` and the Cloud Build pipeline (`deploy-services-to-cloud-run.yaml`) now regenerate `football_stats_agent/requirements.txt` from `pyproject.toml` via `uv export` before calling `adk deploy`. Without this, `adk deploy` strips the ADK extras and the deployed container fails to start with `ImportError: Missing required dependencies for Agent Identity Auth Manager`. The generated requirements.txt is gitignored — single source of truth stays `pyproject.toml`.
6. **Infra trim** — `agent-engine-proxy` removed from `docker-compose.yaml` and `docker-bake-agentic-apps.hcl`. Only the ADK agent + the webapp are built and run. Image names are suffixed `-copilotkit` to avoid clashing with the upstream repo.

The rest (Dockerfile, agent_config.yaml, raw_data, .envrc) is unchanged from the upstream repo.

### Required IAM roles

Both the invoking principal (user / compute SA) and — if you deploy to Agent Engine — the Vertex AI Reasoning Engine SA (`service-{PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com`) need these roles:

| Role | Why |
|------|-----|
| `roles/agentregistry.viewer` | Discover MCP servers in Agent Registry |
| `roles/mcp.toolUser` | Call MCP tools |
| `roles/aiplatform.user` | Vertex AI / Gemini calls |
| `roles/bigquery.dataViewer` | Read the underlying table |
| `roles/bigquery.jobUser` | Run BigQuery query jobs |
| `roles/storage.objectAdmin` | Staging bucket — only needed when deploying to Agent Engine |

The `agentregistry.googleapis.com` API must be enabled in the project (`gcloud services enable agentregistry.googleapis.com`).

The legacy `roles/cloudapiregistry.viewer` does NOT grant access to Agent Registry — it's a deprecated role for the old Cloud API Registry. Drop it once migrated.

## Run locally

```bash
# 1. Install Python deps + start ADK agent
uv sync
./reset_and_start.sh        # wipes local session DB then starts adk api_server
# or, plain:  uv run adk api_server --host 0.0.0.0 --port 8080

# 2. In another terminal, install JS deps + start the webapp
cd webapp
npm install
npm run dev
```

> **Demo tip** — use `./reset_and_start.sh` before each rehearsal and right before going on stage. It wipes the local SQLite session store, which prevents `ADK error 500: Internal Server Error` if ADK was previously killed mid-write.

Open `http://localhost:3000` and try one of the examples below.

## Example questions

The agent picks the chart type automatically from the question's intent. You can also force a type by saying "bar chart", "pie chart" or "line chart" in your prompt.

### Bar chart — rankings, top-N, comparisons across categories

- *"Top 10 buteurs de la Coupe du monde 2022"*
- *"Quels sont les 5 meilleurs passeurs de l'Argentine ?"*
- *"Compare le nombre de buts entre la France, l'Argentine et le Brésil"*
- *"Top 5 gardiens par pourcentage d'arrêts"*
- *"Top 5 joueurs de France par tacles par 90 minutes"*

### Pie chart — shares of a whole (≤ 6 slices)

- *"Donne-moi un pie chart de la répartition des positions (GK / DF / MF / FW) dans l'équipe de France"*
- *"Pie chart : part de chacun des 5 meilleurs buteurs dans le total de buts de la France"*
- *"Pie chart des top 6 clubs représentés dans la sélection argentine"*

### Line chart — trends over an ordered axis

The Qatar 2022 dataset is a snapshot (no time series), so line charts are niche but still meaningful when you have a natural ordering:

- *"Trace en line chart le total de buts marqués par les 10 meilleures équipes du classement FIFA, de la 1ère à la 10ème place"*
- *"Line chart : buts cumulés des 10 meilleurs buteurs de la compétition"*

### No chart — single-value or factual questions

- *"Combien de buts a marqué Mbappé ?"*
- *"Quel est le club de Lionel Messi ?"*
- *"Quelle est la position d'Hugo Lloris ?"*

For these, the agent answers in plain text without emitting a chart block.

### DevLille demo — 3-prompt sequence

Three prompts in order, designed to ramp up engagement during the live demo:

1. **Opener (safe, instant wow)** — simple mono-series bar chart, the audience instantly recognises the players:
   > *"Quels sont les 3 meilleurs buteurs de la Coupe du Monde 2022 ?"*

2. **Middle (multi-series, the GOAT debate)** — shows off the multi-series chart (`y_keys`), fuels the eternal Messi vs Mbappé argument:
   > *"Compare Kylian Mbappé et Lionel Messi sur leurs buts marqués, passes décisives et dribbles par 90 minutes."*

3. **Closer (local twist + punchline)** — DevLille local pride: reveals the two LOSC players who played in Qatar 2022 (Tim Weah and Jonathan David), then benchmarks them against Mbappé. The chart has 3 × 3 = 9 bars, all non-zero:
   > *"Quels joueurs de Lille ont disputé la Coupe du Monde 2022 ? Compare leurs stats offensives (buts, passes décisives, dribbles par 90) à celles de Mbappé."*

## With Docker Compose

```bash
docker buildx bake
docker compose up
```

Three services: `adk-web` (`:8000`) + `adk-agent` (`:8080`) + `webapp` (`:3000`).

## Local URLs (demo cheatsheet)

Everything below is available once `docker compose up` is running. Keep this list one tab away during a live demo.

| What | URL | Purpose |
|------|-----|---------|
| **Native ADK UI** | http://localhost:8000 | Out-of-the-box ADK chat — Phase 1 of the talk demo |
| **Copilot Kit webapp** | http://localhost:3000 | Custom UI + Recharts visualizations — Phase 2 |
| **ADK API — Swagger UI** | http://localhost:8080/docs | Interactive API explorer for the REST endpoints |
| **ADK API — `/run` endpoint** | http://localhost:8080/run | Raw POST endpoint consumed by the webapp |
| **ADK API — sessions root** | http://localhost:8080/apps/football_stats_agent/users/{userId}/sessions/{sessionId} | Session bootstrap before any `/run` call |
| **Copilot Kit runtime probe** | `POST http://localhost:3000/api/copilotkit` with `{"method":"info"}` | Verify the BuiltInAgent is registered (returns `agents.default`) |

### Optional — Agent Engine path (if you also run the proxy)

The proxy is NOT in `docker compose` (we trimmed it to keep the demo focused), but you can spin it up manually to test the Vertex AI Agent Engine path locally:

```bash
cd agent_engine_proxy
uv run uvicorn main:app --port 8081
# ENGINE_ID / PROJECT_NUMBER / LOCATION come from .envrc via direnv
```

| What | URL | Purpose |
|------|-----|---------|
| **Proxy `/health`** | http://localhost:8081/health | Liveness check |
| **Proxy `/query`** | `POST http://localhost:8081/query` with `{"message": "..."}` | Wraps `async_create_session` + `async_stream_query` on Agent Engine |

### Cloud / production URLs (used in Phases 4 and 5 of the demo)

All Cloud Run services and the Agent Engine display name are suffixed `-copilotkit` to avoid clashing with the upstream `football-agent-adk` deployments in the same GCP project.

| What | URL |
|------|-----|
| **Cloud Run webapp** (prod) | `https://football-stats-webapp-copilotkit-…run.app` (resolve with `gcloud run services describe football-stats-webapp-copilotkit --region=europe-west1 --format='value(status.url)'`) |
| **Cloud Run ADK API** (prod) | `https://football-stats-api-copilotkit-…run.app` (`gcloud run services describe football-stats-api-copilotkit --region=europe-west1 --format='value(status.url)'`) |
| **Cloud Run Agent Engine Proxy** (prod) | `https://agent-engine-proxy-copilotkit-…run.app` (`gcloud run services describe agent-engine-proxy-copilotkit --region=europe-west1 --format='value(status.url)'`) |
| **Vertex AI Agent Engine list** | https://console.cloud.google.com/vertex-ai/agents/agent-engines?project=gb-poc-373711 (look for `football-stats-agent-copilotkit`, then click into its Playground) |
| **Agent Registry MCP servers** in the GCP console | https://console.cloud.google.com/agent-registry/mcp-servers?project=gb-poc-373711 |

## CI/CD with Cloud Build

`deploy-services-to-cloud-run.yaml` is the end-to-end pipeline that builds the images, deploys the agent to Vertex AI Agent Engine, and rolls out the three Cloud Run services in one shot.

### Run the pipeline

```bash
gcloud builds submit \
  --config deploy-services-to-cloud-run.yaml \
  --project gb-poc-373711 \
  --region europe-west1
```

`$PROJECT_ID` and `$LOCATION` come from `--project` and `--region`; everything else is derived or hardcoded in the YAML.

### What runs (in order)

1. **Build + push images** (`docker buildx bake --push`) — uses `docker-bake-agentic-apps.hcl`, ships the 3 images to Artifact Registry with registry-cached layers.
2. **Deploy agent to Vertex AI Agent Engine** —
   - `uv export --no-dev --no-hashes --no-emit-project -o football_stats_agent/requirements.txt` regenerates the pinned requirements.txt from `pyproject.toml` (single source of truth, extras included).
   - `uv pip install --system -r football_stats_agent/requirements.txt` makes the `adk` CLI available in the build container.
   - `adk deploy agent_engine ...` packages and registers the agent.
3. **Deploy 3 Cloud Run services** (all suffixed `-copilotkit` to avoid clashes with the upstream repo) —
   - `gcloud projects describe` derives `PROJECT_NUMBER` from `$PROJECT_ID`.
   - A REST call against `aiplatform.googleapis.com` looks up the freshly-deployed Agent Engine ID by `display_name=football-stats-agent-copilotkit`.
   - `gcloud run deploy football-stats-api-copilotkit` (ADK REST API).
   - `gcloud run deploy agent-engine-proxy-copilotkit` with `PROJECT_NUMBER` and `ENGINE_ID` injected as env vars.
   - `gcloud run deploy football-stats-webapp-copilotkit`, wired to the two backends above via their freshly-resolved `status.url`.

### Prerequisites

- `gcloud auth login` and the right billing project set.
- The Cloud Build service account (`{PROJECT_NUMBER}@cloudbuild.gserviceaccount.com`) needs roles to:
  - push to Artifact Registry (`roles/artifactregistry.writer`)
  - deploy to Cloud Run (`roles/run.admin` + `roles/iam.serviceAccountUser` on the Cloud Run runtime SA)
  - deploy to Vertex AI Agent Engine (`roles/aiplatform.user`, `roles/storage.objectAdmin` for the staging bucket)
  - read Agent Registry / call MCP (`roles/agentregistry.viewer`, `roles/mcp.toolUser`)
- The APIs enabled: `cloudbuild.googleapis.com`, `run.googleapis.com`, `aiplatform.googleapis.com`, `agentregistry.googleapis.com`, `artifactregistry.googleapis.com`, `bigquery.googleapis.com`.
- `.gcloudignore` filters the source upload — keep it in sync if you add new directories that should not be shipped.

### Iterate fast

If only the agent code changed and you don't want to wait for the image build, use `./deploy_agent_engine.sh` locally — it skips Cloud Build and runs `adk deploy agent_engine` directly with the same `uv export` pattern.

## Configuration

Same as upstream — GCP project `gb-poc-373711`, dataset `qatar_fifa_world_cup.team_players_stat_raw`, region `europe-west1`. The webapp reads `CLOUD_RUN_API_URL` (defaults to `http://localhost:8080` in `.envrc` for local dev).

## Troubleshooting

**`ADK error 500: Internal Server Error` after several restarts** — the local SQLite session store (`football_stats_agent/.adk/session.db`) got corrupted. Stop ADK, delete the `.adk/` directory, restart:

```bash
rm -rf football_stats_agent/.adk
uv run adk api_server --host 0.0.0.0 --port 8080
```

This is a known risk during dev when ADK is killed mid-write. The `.adk/` directory is gitignored, so this is safe.

**Empty / blank chart in the UI** — check the browser network tab for the assistant message text. If `x_key` / `y_key` in the chart spec don't match the keys in the `data` items, Recharts can't resolve values. The DynamicChart component has a fallback that tries `name` / `value` and the first data-item key, but if everything fails the chart is empty. The system instruction now forces `name` / `value` everywhere; this should be rare.

## Status

- ✅ Local dev works end-to-end (Copilot Kit ↔ ADK ↔ BigQuery)
- ✅ Bar / line / pie chart rendering via Recharts
- ⚠️ Cloud Run deployment of the webapp untested with new deps — should work but `deploy_api.sh` etc. reference the upstream image names; rename to `-copilotkit` before pushing
- ⚠️ Agent Engine deployment not validated for this variant

## See also

- Upstream repo: [`football-agent-adk`](../football-agent-adk) — same agent, plain Next.js chat UI
- Used as **Démo 2** of the DevLille / Google Cloud Summit France 2026 talk
