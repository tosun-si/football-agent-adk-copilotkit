# CLAUDE.md — Copilot Kit variant of football-agent-adk

## What this repo is

A fork of `football-agent-adk` that pairs the same ADK + BigQuery MCP agent with a **Copilot Kit + Recharts** frontend, demonstrating **dynamic chart generation** triggered by the agent's response.

## Agent change vs. upstream

`football_stats_agent/agent.py` has a single addition to `SYSTEM_INSTRUCTION`: a new **"Visualization Output"** section that asks the agent to emit a fenced ```chart``` JSON block when the question implies a comparison / ranking / distribution / top-N. The schema:

```json
{
  "chart_type": "bar" | "line" | "pie",
  "title": "...",
  "x_key": "name",
  "y_key": "value",
  "data": [{"name": "...", "value": <number>}, ...]
}
```

The agent still answers in natural language first; the chart block is appended. The agent is told to emit *exactly one* chart block per response, or none.

## Webapp architecture (webapp/)

- **Framework**: Next.js 15 + React 19 (same as upstream)
- **Chat UI**: `@copilotkit/react-ui` (`CopilotChat` component) — full Copilot Kit experience, not a custom chat
- **Custom Markdown renderer**: `components/CopilotMarkdown.tsx` — detects fenced `language === "chart"` blocks and renders `<DynamicChart>` (Recharts) inline instead of code text
- **Chart component**: `components/DynamicChart.tsx` — bar / line / pie via Recharts based on the `chart_type` field
- **Runtime adapter**: `app/api/copilotkit/route.ts` — `CopilotRuntime` with a **custom `CopilotServiceAdapter`** that:
  1. Receives a Copilot Kit chat completion request
  2. Extracts the latest user message
  3. Calls the ADK Cloud Run `/run` endpoint (with session bootstrap)
  4. Returns the assistant text response to Copilot Kit

This is **Copilot Kit "lite"**: the chat UI and runtime ARE Copilot Kit, but the LLM is ADK (not OpenAI/Anthropic/Gemini directly). The custom adapter is the bridge.

## Why no `useCopilotAction` for the chart?

In a canonical Copilot Kit setup, the LLM would call a frontend-defined action like `displayChart`. ADK has no native way to advertise Copilot Kit actions as tools, so we use the **text-channel-with-parsing** approach instead: the agent embeds the chart spec in its text response (fenced block), and the markdown renderer picks it up. Simpler, equally reliable for the demo.

## Local dev

```bash
# Backend (ADK on port 8080)
uv sync
uv run adk web   # or: uv run adk api_server --host 0.0.0.0 --port 8080

# Frontend (port 3000)
cd webapp
npm install
npm run dev
```

The webapp needs `CLOUD_RUN_API_URL=http://localhost:8080` in its env. The project's `.envrc` already exports it.

## Full stack locally with Docker Compose

```bash
docker buildx bake          # builds adk-agent + webapp
docker compose up
```

Two services only: `adk-agent` (`:8080`) + `webapp` (`:3000`). No `agent-engine-proxy` here — the Copilot Kit variant only targets Cloud Run.

## Docker Bake image naming

To avoid clashing with the upstream `football-agent-adk` images when both repos push to the same Artifact Registry, images here are suffixed `-copilotkit`:

- `football-stats-api-copilotkit:latest`
- `football-stats-webapp-copilotkit:latest`

The deploy scripts (`deploy_api.sh`, `deploy-services-to-cloud-run.yaml`) inherited from upstream still reference the old names — **update them before deploying** if you push to the same Artifact Registry.

## Agent Engine deployment

Untested in this variant. The agent itself is unchanged in shape (still an `LlmAgent` with the same toolset), so `adk deploy agent_engine` should work. But the Copilot Kit webapp expects the ADK Cloud Run API format, not the Agent Engine streaming format. If you want both backends, you'd need to add an Agent Engine proxy similar to the upstream repo and a backend toggle in the webapp (which we removed for simplicity).

## GCP Project (same as upstream)

- Project ID: `gb-poc-373711`
- BigQuery: `qatar_fifa_world_cup.team_players_stat_raw`
- Region: `europe-west1`

For BigQuery schema, IAM, business rules, see the upstream `football-agent-adk/CLAUDE.md`.

## Used in the talk

This repo is the basis of the **Démo 2** slide (slides 13 + 14) of the DevLille / GCS France 2026 talk. Live demo flow:

1. Open `http://localhost:3000`
2. Ask "Top 5 buteurs d'Argentine ?"
3. Agent answers in NL, emits chart block
4. `<DynamicChart>` renders a bar chart inline
