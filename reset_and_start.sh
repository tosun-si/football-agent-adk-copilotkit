#!/usr/bin/env bash
# Reset local session storage and start ADK API server.
# Use before each demo / rehearsal to guarantee a clean SQLite state.
#
# Why: ADK persists sessions to football_stats_agent/.adk/session.db.
# Interrupting ADK during a write (Ctrl+C, kill -9, laptop sleep) can
# corrupt that file and trigger "ADK error 500: Internal Server Error"
# on the next request. Wiping it gives us a guaranteed-clean slate.
#
# Env vars (GCP_PROJECT_ID, GOOGLE_CLOUD_PROJECT, LOCATION, ...) come
# from .envrc via direnv — make sure `direnv allow` has been run once.

set -euo pipefail

cd "$(dirname "$0")"

ADK_STATE_DIR="football_stats_agent/.adk"
PORT="${PORT:-8080}"

echo "→ Wiping local session storage at ${ADK_STATE_DIR}"
rm -rf "${ADK_STATE_DIR}"

echo "→ Killing any process on port ${PORT}"
lsof -ti ":${PORT}" 2>/dev/null | xargs -r kill -9 2>/dev/null || true

echo "→ Starting ADK on http://localhost:${PORT}"
exec uv run adk api_server --host 0.0.0.0 --port "${PORT}"
