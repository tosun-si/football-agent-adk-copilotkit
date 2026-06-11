# CLAUDE.md — Copilot Kit variant of football-agent-adk

## What this repo is

A fork of `football-agent-adk` that pairs the same ADK + BigQuery MCP agent with a **Copilot Kit + Recharts** frontend, demonstrating **dynamic chart generation** triggered by the agent's response.

This repo is the basis of the **Démo 2** of the DevLille / Google Cloud Summit France 2026 talk.

## MCP discovery: Agent Registry (replaces Cloud API Registry)

The agent discovers the BigQuery MCP server through **Google Cloud Agent Registry** (`google.adk.integrations.agent_registry.AgentRegistry`). Agent Registry replaces the deprecated Cloud API Registry for MCP-server discovery as of early 2026.

### Resource names changed — lookup by `displayName`, do not hardcode

Cloud API Registry exposed MCP servers under human-readable names like `projects/{PROJECT_ID}/locations/global/mcpServers/google-bigquery.googleapis.com-mcp`. Agent Registry assigns **opaque UUID resource names** instead:

```
projects/{PROJECT_ID}/locations/global/mcpServers/agentregistry-00000000-0000-0000-921a-c233b003d75f
                                                  ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                                  opaque, may differ per project / over time
```

The human-readable identifier lives in a separate `displayName` field (e.g. `bigquery.googleapis.com` for the BigQuery MCP server). Hardcoding the resource name will break the moment you switch projects or Google rotates IDs.

`agent.py` implements this correctly via `_resolve_mcp_server_name()`:

1. Call `registry.list_mcp_servers()` once at agent creation.
2. Iterate the result and find the entry whose `displayName == "bigquery.googleapis.com"`.
3. Use that entry's `name` field as input to `registry.get_mcp_toolset(name)`.

Constant: `BIGQUERY_MCP_DISPLAY_NAME = "bigquery.googleapis.com"` in `agent.py`. If you need a different MCP server, change the display name — do NOT hardcode a UUID.

### Required IAM roles

Both the **invoking principal** (your user / compute SA) and the **Vertex AI Reasoning Engine SA** (`service-{PROJECT_NUMBER}@gcp-sa-aiplatform-re.iam.gserviceaccount.com` — only present when deploying to Agent Engine) need these roles:

- `roles/agentregistry.viewer` — discover MCP servers
- `roles/mcp.toolUser` — call MCP tools
- `roles/aiplatform.user` — Vertex AI / Gemini
- `roles/bigquery.dataViewer`, `roles/bigquery.jobUser` — query the actual data
- `roles/storage.objectAdmin` — staging bucket (deploy-time only)

If only the user SA has `agentregistry.viewer`, the local agent works but the Agent Engine deploy fails at runtime with `403 Forbidden` on the Agent Registry call. Symmetric grant is required.

The legacy `roles/cloudapiregistry.viewer` does NOT grant access to Agent Registry — it's a separate, deprecated role. Drop it once the migration to Agent Registry is complete.

### Setup notes

- The `agentregistry.googleapis.com` API must be enabled in the project.
- Python dependencies use the ADK extras pattern: `google-adk[agent-identity, mcp, a2a, otel-gcp]>=2.1.0` plus a direct dep on `opentelemetry-exporter-gcp-trace>=1.12.0`. The `a2a` extra pulls in the right transitive versions for AgentRegistry (notably `a2a-sdk` at the version ADK was built against); without it, importing `AgentRegistry` raises `ModuleNotFoundError: No module named 'a2a'`. The `otel-gcp` extra auto-instruments Gemini calls. `opentelemetry-exporter-gcp-trace` provides `CloudTraceSpanExporter` used by `adk api_server --trace_to_cloud` on the Cloud Run path; without it the container crashes at startup with `ModuleNotFoundError: No module named 'opentelemetry.exporter'`. We add it directly rather than via `google-adk[gcp]` because that extra pulls in every google-cloud-* library.

## Telemetry / Tracing

Two runtimes, two different gates:

- **Cloud Run path**: `adk api_server --trace_to_cloud` flag in the Dockerfile `CMD`. Requires `GOOGLE_CLOUD_PROJECT` env var (not `GCP_PROJECT_ID` — ADK looks at the former specifically). Set in the `gcloud run deploy ... --set-env-vars`. Without it, ADK logs "GOOGLE_CLOUD_PROJECT environment variable is not set. Tracing will not be enabled" at startup. Runtime SA also needs `roles/cloudtrace.agent` (or any role granting `cloudtrace.spans.create`).
- **Agent Engine path**: `--trace_to_cloud` flag is a **no-op here** — AE has its own platform-managed telemetry gate via the env var `GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY=true`. This must be set at deploy time and bundled with the agent. We do this via `--env_file football_stats_agent/.env`, which `adk deploy agent_engine` bundles into the agent package. The companion env var `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=true` adds prompt/response content to spans — fine here because the dataset is public; remove it for any deployment handling PII. `.gcloudignore` has an explicit exception `!football_stats_agent/.env` so Cloud Build uploads the file even though `.env` is otherwise excluded. **Also required**: the dep `opentelemetry-exporter-otlp-proto-http>=1.38.0` must be in `pyproject.toml`. AE's runtime template uses this package to push spans to its managed OTLP endpoint; without it, the import silently fails inside the AE container and the Trace tab stays empty even though `GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY=true` is set.
- **Where to view traces**: AE traces in Agent Engine console → "Trace" tab. Cloud Run traces in Cloud Trace console (linked from Cloud Run logs via the `trace` field on each log entry — Cloud Run does not have its own Trace tab).

## Agent change vs. upstream

`football_stats_agent/agent.py` adds a **"Visualization Output"** section to the `SYSTEM_INSTRUCTION` (everything else is identical to the upstream agent). The agent is told to:

1. Reply with a short natural-language answer first.
2. Append a single fenced ```chart``` JSON block when the question implies a comparison / ranking / distribution / top-N.

Schema (literal — keys are NOT semantic):

```json
{
  "chart_type": "bar" | "line" | "pie",
  "title": "...",
  "x_key": "name",
  "y_key": "value",
  "data": [{"name": "...", "value": <number>}, ...]
}
```

The "keys MUST be `name` and `value`" constraint is repeated explicitly in the system instruction to keep the agent from inventing semantic keys (`playerName`, `goals`, etc.) that the frontend chart resolver would then have to guess.

Single-value / yes-no questions → no chart block. Limit data to 10 items max.

## Webapp architecture (webapp/)

- **Framework**: Next.js 15 + React 19 (same as upstream)
- **Chat UI**: `@copilotkit/react-ui` (`CopilotChat` component)
- **Chart-aware markdown**: `components/CopilotMarkdown.tsx` exports a `chartTagRenderers` object passed via `<CopilotChat markdownTagRenderers={chartTagRenderers}>`. The `code` renderer detects `language === "chart"` and swaps the code block for `<DynamicChart>` (Recharts).
- **Chart component**: `components/DynamicChart.tsx` — bar / line / pie via Recharts. Falls back to `name` / `value` keys if `x_key` / `y_key` don't match data items (defensive against system-instruction drift).
- **Runtime adapter**: `app/api/copilotkit/route.ts` — see below.

### Critical: Copilot Kit runtime wiring (v1.10+ pattern)

Copilot Kit v1.10 deprecated the `CopilotServiceAdapter` interface for custom backends. **The working pattern is `BuiltInAgent` with `type: "custom"` factory yielding AG-UI events.** Non-obvious imports:

```typescript
import { CopilotRuntime, copilotRuntimeNextJSAppRouterEndpoint } from "@copilotkit/runtime";
import { BuiltInAgent } from "@copilotkit/runtime/v2";   // NOT the main entry
import { EventType } from "@ag-ui/core";

const adkAgent = new BuiltInAgent({
  type: "custom",
  factory: async function* (ctx) {
    const userText = extractText(ctx.input.messages);
    const responseText = await callAdkCloudRun(userText);
    const messageId = crypto.randomUUID();
    yield { type: EventType.TEXT_MESSAGE_START, messageId, role: "assistant" } as never;
    yield { type: EventType.TEXT_MESSAGE_CONTENT, messageId, delta: responseText } as never;
    yield { type: EventType.TEXT_MESSAGE_END, messageId } as never;
  },
});

const runtime = new CopilotRuntime({ agents: { default: adkAgent } });
```

If `agents` is missing or only `serviceAdapter` is passed, you get `CopilotApiDiscoveryError: Service adapter "unknown" does not provide model information`.

Validate with `POST /api/copilotkit {"method":"info"}` — should return `{"agents":{"default":{"className":"BuiltInAgent",...}}}`.

This is **Copilot Kit "lite"**: the chat UI and runtime ARE Copilot Kit, but the LLM is ADK (called over HTTP). The custom adapter is the bridge — it does not advertise tools, the chart spec travels as text in the assistant message and is detected by `chartTagRenderers` on the frontend.

## Local dev

The recommended path is Docker Compose — it runs everything (native ADK UI, REST API, webapp) without polluting the local Python env. Run individual pieces locally only when iterating on one specific component.

### Docker Compose (canonical)

```bash
docker buildx bake          # builds adk image + webapp image (first time only)
docker compose up           # starts the 3 services
```

Three services, isolated containers (no shared `.adk/session.db`):

| Service | Port | Role |
|---------|------|------|
| `adk-web` | 8000 | Native ADK UI (`adk web`) — used in talk demo phase 1 |
| `adk-agent` | 8080 | REST API (`adk api_server`) — consumed by the webapp |
| `webapp` | 3000 | Next.js + Copilot Kit + Recharts — used in talk demo phase 2 |

The `adk-agent` and `adk-web` services share a single image (`football-stats-adk-copilotkit:local`) via a `x-adk-base` YAML anchor in `docker-compose.yaml`. Only the command differs.

### Outside Docker (for one-component iteration)

```bash
uv sync
uv run adk api_server --host 0.0.0.0 --port 8080
# in another terminal:
cd webapp && npm install && npm run dev
```

The webapp needs `CLOUD_RUN_API_URL=http://localhost:8080` — already in `.envrc`.

## Demo helper scripts

For live talks and rehearsals. Located in `scripts/` (utility, rare use) and at the project root (deploy entrypoints).

- **`docker compose down -v && docker compose up`** — the clean-slate recipe before a rehearsal or going on stage. `-v` wipes volumes so any stale SQLite session DB is gone, which avoids `ADK error 500: Internal Server Error` if ADK was killed mid-write previously.
- **`scripts/cleanup_old_engines.sh`** — utility to garbage-collect old Reasoning Engine deployments in the project. Dry-run by default; pass `--apply` to actually delete. Keeps the latest engine per `displayName`.
- **`talks/DEMO_KIT.md`** — symptom-based recovery commands + the 5-phase demo flow for DevLille / GCS France. Designed to be readable on a phone in 5 seconds during a live talk.

## Golden dataset (regression tests for the agent)

`golden_dataset/` — reference questions + expected behaviors, replayable against any live ADK instance.

```
golden_dataset/
├── dataset.yaml      # 5 cases covering factual / ranking / chart-spec / no-chart
├── response.py       # parses ADK response: text, chart block, extracted numbers
├── runner.py         # standalone runner (no pytest) + assertions
└── README.md
```

### Two entry points, same dataset and assertions

1. **Standalone script** — `uv run python -m golden_dataset.runner`. You start the agent yourself (`docker compose up`). Exit 0/1 for CI.
2. **Pytest** — `uv run pytest tests/test_golden.py -v`. The session-scoped fixture in `tests/conftest.py` auto-detects whether something is already serving on 8080; if not, it runs `docker compose up -d adk-agent`, waits for readiness, runs the tests, then `docker compose down`. If the agent is already running, the fixture reuses it and does NOT touch your stack (principle of least surprise). LLM flakiness is absorbed by `@pytest.mark.flaky(reruns=2, reruns_delay=3)`.

Override target with `ADK_URL=https://prod-cloud-run-url ...` — with a remote URL the pytest fixture stays out of Docker.

### Assertion types in `runner.ASSERTIONS`

| Type | Checks |
|------|--------|
| `contains_number` | Number appears in response text OR in chart `value` fields |
| `ordered_list` | First N entities in chart data (or in text) match expected order, **Unicode-normalized** (so `Tchouaméni` matches `Tchouameni`) |
| `chart_spec` | Response contains a chart block of the right `chart_type` and data-point count range |
| `no_chart` | Response is text-only and contains at least one of the `must_contain` strings (list or single string) |

The assertions deliberately tolerate the kinds of LLM variability we observed during validation: accents, abbreviations vs. full names (`PSG` vs `Paris Saint-Germain`), digits-vs-words, chart-emitted-instead-of-text. They do NOT tolerate semantic regressions (wrong values, missing chart, wrong type).

### Adding cases / updating expected values

The dataset is a **contract** — when you change the agent intentionally (new business rule, prompt refactor, schema change), run the agent manually on the affected questions, verify the new answers, and commit dataset + code in the same PR.

## Docker Bake image naming

Images here are suffixed `-copilotkit` to avoid clashing with the upstream `football-agent-adk` images when both repos push to the same Artifact Registry:

- `football-stats-api-copilotkit:latest`
- `football-stats-webapp-copilotkit:latest`

Deploy scripts (`deploy_api.sh`, `deploy-services-to-cloud-run.yaml`) inherited from upstream still reference the old names — update before deploying.

## Agent Engine deployment

Validated. Deploy via `./deploy_agent_engine.sh` (or the Cloud Build pipeline). The script + CI step share the same pattern:

1. **`uv export --no-dev --no-hashes --no-emit-project -o football_stats_agent/requirements.txt`** — regenerates the requirements.txt from `pyproject.toml` (single source of truth). Without this, `adk deploy` auto-derives a requirements.txt from imports and **drops the extras** (`[agent-identity, mcp, a2a]`), which makes the container fail to start with `ImportError: Missing required dependencies for Agent Identity Auth Manager` or `No module named 'a2a'`.
2. **`uv pip install --system -r football_stats_agent/requirements.txt`** (CI only) — installs the ADK CLI in the build container.
3. **`adk deploy agent_engine ...`** — packages the agent, ships the staged dir + requirements.txt, Google rebuilds the runtime from scratch.
4. **trap cleanup** (local script only) — `football_stats_agent/requirements.txt` is regenerated each time and gitignored.

The webapp side talks to Cloud Run, not Agent Engine. To wire both, you'd need an Agent Engine proxy similar to the upstream repo (see `agent_engine_proxy/main.py` for the SDK pattern: `query_reasoning_engine` with `async_create_session` then `stream_query_reasoning_engine` with `async_stream_query`).

### Display name and Cloud Run service naming

To avoid colliding with the upstream `football-agent-adk` deployments in the same GCP project, every deployable resource is suffixed `-copilotkit`:

| Resource | Name |
|----------|------|
| Agent Engine display name | `football-stats-agent-copilotkit` |
| Cloud Run ADK API service | `football-stats-api-copilotkit` |
| Cloud Run Agent Engine Proxy service | `agent-engine-proxy-copilotkit` |
| Cloud Run Webapp service | `football-stats-webapp-copilotkit` |
| Artifact Registry images | `football-stats-api-copilotkit`, `agent-engine-proxy-copilotkit`, `football-stats-webapp-copilotkit` (set in `docker-bake-agentic-apps.hcl`) |

The Cloud Build pipeline's filter to look up the latest engine ID uses the same suffix: `display_name="football-stats-agent-copilotkit"`. Both `deploy_agent_engine.sh` and `deploy-services-to-cloud-run.yaml` are aligned.

`agent_engine_proxy/main.py` reads the engine ID from the `ENGINE_ID` env var. The `.envrc` sets it via direnv for local use. In Cloud Run, the deploy pipeline injects it.

> After a fresh `./deploy_agent_engine.sh` run, update `ENGINE_ID` in `.envrc` with the new engine id (returned by `adk deploy agent_engine` in the success message). The Cloud Build path resolves it dynamically — no manual update needed there.

### Cold-start MCP bug (historical) — RESOLVED in this stack

Prior to ADK 2.1.0 + AgentRegistry, an idle Agent Engine that thawed (after scale-to-zero) had stale MCP toolset state, and required `./deploy_agent_engine.sh` before every demo to recover. **The migration to ADK 2.1.0 + AgentRegistry + `google-cloud-aiplatform` 1.154.0 fixed this** — likely thanks to AgentRegistry's `StreamableHTTPConnectionParams` (stateless per-request HTTP transport) and ADK's toolset (de)serialization rewrite. Verified end-to-end: engine left idle ~12h, then a single query via the proxy returns the full NL + chart-block response in ~10s with no redeploy. The "redeploy before each demo" workaround is no longer needed.

## Cloud Build CI/CD pipeline

`deploy-services-to-cloud-run.yaml` is the canonical end-to-end deploy. One command rebuilds the images, redeploys the agent to Agent Engine, and rolls out the three Cloud Run services with the right env vars wired between them.

```bash
gcloud builds submit --config deploy-services-to-cloud-run.yaml \
  --project gb-poc-373711 --region europe-west1
```

### Pipeline shape (3 steps)

1. **Step 1 — `gcr.io/cloud-builders/docker`** — `docker buildx bake --push` builds the 3 images (adk-agent, agent-engine-proxy, webapp) via `docker-bake-agentic-apps.hcl`, with registry-cached layers. All targets are tagged `*-copilotkit` in Artifact Registry to avoid clashing with the upstream repo.
2. **Step 2 — `ghcr.io/astral-sh/uv:python3.11-alpine`** — same `uv export` + `adk deploy agent_engine` pattern as `deploy_agent_engine.sh` (single source of truth = `pyproject.toml`). Without this regen, `adk deploy` strips the ADK extras and Agent Engine fails to start at runtime.
3. **Step 3 — `gcr.io/google.com/cloudsdktool/google-cloud-cli:slim`** — wiring step:
   - `PROJECT_NUMBER=$(gcloud projects describe ${PROJECT_ID} --format='value(projectNumber)')` derives the numeric project number from the project id.
   - A `curl` against `aiplatform.googleapis.com/v1beta1/.../reasoningEngines?filter=display_name="football-stats-agent-copilotkit"` looks up the freshly-deployed Agent Engine id by display name (so the proxy always points at the latest version).
   - `gcloud run deploy` x3 — ADK API (no Engine ID needed), Agent Engine Proxy (gets `PROJECT_NUMBER` + `ENGINE_ID` via `--set-env-vars`), webapp (its `CLOUD_RUN_API_URL` and `AGENT_ENGINE_PROXY_URL` are resolved on the fly from `gcloud run services describe ... --format='value(status.url)'`).

### IAM the Cloud Build SA needs (`{PROJECT_NUMBER}@cloudbuild.gserviceaccount.com`)

- `roles/artifactregistry.writer` — push images
- `roles/run.admin` + `roles/iam.serviceAccountUser` on the Cloud Run runtime SA — deploy services
- `roles/aiplatform.user` — deploy to Agent Engine + later list the reasoning engines
- `roles/storage.objectAdmin` — staging bucket used by `adk deploy`
- `roles/agentregistry.viewer`, `roles/mcp.toolUser` — needed during build-time validation of the agent

### Iterate without rebuilding images

If only the agent code changed: `./deploy_agent_engine.sh` redeploys the agent directly via the same `uv export` pattern, skipping the full Cloud Build pipeline. The Cloud Run services keep running their existing images and pick up the new agent on the next request via the env-injected `ENGINE_ID`.

## GCP Project (same as upstream)

- Project ID: `gb-poc-373711`
- BigQuery: `qatar_fifa_world_cup.team_players_stat_raw`
- Region: `europe-west1`

For BigQuery schema, IAM, business rules → upstream `football-agent-adk/CLAUDE.md`.

## Talk demo flow (DevLille / GCS France 2026)

| Phase | URL | What you show |
|---|---|---|
| 1 | `http://localhost:8000` | Native ADK UI — bare agent rendering |
| 2 | `http://localhost:3000` | Copilot Kit webapp — same agent, charts inline |
| 3 | (editor) | Code + CI/CD walkthrough |
| 4 | `https://football-stats-webapp-…run.app` | Production Cloud Run |
| 5 | `console.cloud.google.com/vertex-ai/agents/agent-engines` | Agent Engine playground |

Single command to start everything: `docker compose up`. Zero transitions between phases. See `talks/DEMO_KIT.md` for full details.
