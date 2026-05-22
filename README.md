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

Only three things are different from [`football-agent-adk`](../football-agent-adk):

1. **`football_stats_agent/agent.py`** — `SYSTEM_INSTRUCTION` extended with a "Visualization Output" section telling the agent to emit a JSON chart spec in a fenced ```chart``` block when the question implies a visualization.
2. **`webapp/`** — completely rewritten:
   - `@copilotkit/react-ui` for the chat UI (`<CopilotChat>`)
   - `app/api/copilotkit/route.ts` — `CopilotRuntime` + custom `CopilotServiceAdapter` proxying to the ADK Cloud Run API
   - `components/DynamicChart.tsx` — Recharts component (bar / line / pie)
   - `components/CopilotMarkdown.tsx` — custom markdown renderer that detects ```chart``` blocks
3. **Infra trim** — `agent-engine-proxy` removed from `docker-compose.yaml` and `docker-bake-agentic-apps.hcl`. Only the ADK agent + the webapp are built and run. Image names are suffixed `-copilotkit` to avoid clashing with the upstream repo.

The rest (Dockerfile, agent_config.yaml, raw_data, .envrc, deploy scripts) is unchanged.

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

## With Docker Compose

```bash
docker buildx bake
docker compose up
```

Two services: `adk-agent` (`:8080`) + `webapp` (`:3000`). Both wired together.

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
