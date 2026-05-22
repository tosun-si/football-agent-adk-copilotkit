# Demo Survival Kit

Quick reference for live demos. Open in a split pane or on your phone.

---

## ⭐ Demo flow — DevLille / GCS France

**Everything is launched via Docker Compose. No transition commands between phases.**

### Before going on stage (5 min beforehand)

```bash
cd ~/my-projects/blogarticles/football-agent-adk-copilotkit
./panic.sh                   # guaranteed clean slate
docker compose up            # starts all 3 services
```

Wait ~30s for everything to be up, then ask **one test question** on `http://localhost:3000` ("Top 5 buteurs France ?"). If the chart appears, you're ready.

### During the talk

| Phase | What you show | URL | Notes |
|---|---|---|---|
| **1** | Native ADK UI | `http://localhost:8000` | 1-2 questions, shows ADK's out-of-the-box rendering |
| **2** | Copilot Kit webapp | `http://localhost:3000` | Same agent, custom UI + Recharts visualizations |
| **3** | Code + CI/CD | (editor) | No URL |
| **4** | Webapp in production | `https://football-stats-webapp-…run.app` | Shows it lives in prod, no need to re-query |
| **5** | Agent Engine console | `console.cloud.google.com/vertex-ai/agents/agent-engines?project=gb-poc-373711` | Managed Playground |

You **just switch browser tabs** between phases. You don't touch any terminal.

### At the end

```bash
Ctrl+C        # in the compose terminal
docker compose down
```

### Why this is safe

- `adk web` (port 8000) and `adk api_server` (port 8080) run in **isolated** Docker containers → each has its own ephemeral `.adk/session.db`, zero SQLite conflict risk
- The webapp (port 3000) talks to `adk-agent` over the internal Docker network → not dependent on your localhost
- No phase transitions = no risk of forgetting a cleanup
- If something breaks anyway: `./panic.sh` then `docker compose up` — back up in 2 commands

---

## Symptom-based commands

### "Address already in use" / "EADDRINUSE" / port already taken

```bash
# Specific ports used by this project
lsof -ti :8080 | xargs kill -9    # ADK API server
lsof -ti :3000 | xargs kill -9    # Next.js webapp
lsof -ti :8000 | xargs kill -9    # adk web default port

# Generic — any port
lsof -ti :<PORT> | xargs kill -9
```

### `adk web` or `adk api_server` won't start

```bash
pkill -f "adk "        # kill all ADK processes by command
pkill -f "uvicorn"     # if a stray uvicorn is hanging
# or BSD-style if pkill is missing:
killall adk
```

### Docker Compose is hogging ports

```bash
docker compose down              # stop + remove compose services
docker ps                        # see what's still running
docker ps | grep -E "8080|3000"  # filter on demo ports
docker stop <container_id>       # kill specific container
docker kill $(docker ps -q)      # NUKE: stop all running containers
```

### Next.js broken / blank page / `_document.js` errors

```bash
cd webapp
rm -rf .next
npm run dev
```

(Only relevant if you run the webapp outside Docker, which is not the demo path.)

### `ADK error 500: Internal Server Error` (corrupted SQLite session)

Inside the Docker setup this shouldn't happen (each container has its own ephemeral DB). If you ran `adk` locally without Docker:

```bash
rm -rf football_stats_agent/.adk
./reset_and_start.sh
```

### Everything is broken, I want to start from scratch

```bash
./panic.sh                   # kill everything + wipe local state
docker compose up            # restart full stack
```

---

## Ports used by this project

| Service | Port | Launched by |
|---------|------|---------------|
| `adk-web` (native ADK UI) | 8000 | `docker compose up` |
| `adk-agent` (REST API) | 8080 | `docker compose up` |
| `webapp` (Copilot Kit + Next.js) | 3000 | `docker compose up` |

## One-liner diagnostic

```bash
# See all project ports at once
lsof -i :8080 -i :3000 -i :8000
```

## Recovery scripts

- `./panic.sh` — kills ADK + Next.js + Docker containers + wipes SQLite + wipes `.next/`. Leaves the environment in a zero state. Run `docker compose up` afterward.
- `./reset_and_start.sh` — wipes local `.adk/` and runs `adk api_server` directly via `uv` (no Docker). Useful only if you want to run ADK outside Docker for some reason; not part of the talk demo path.
