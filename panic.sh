#!/usr/bin/env bash
# Nuke option for live demos — kills everything related to this project,
# then wipes local state. Does NOT restart anything; you run
# ./reset_and_start.sh + `cd webapp && npm run dev` after.
#
# Use when something is wedged and you don't want to diagnose mid-demo.

set -u   # do NOT `set -e` — we want every step to attempt even if some fail

cd "$(dirname "$0")"

echo "→ Stopping Docker Compose (if running)"
docker compose down 2>/dev/null || true

echo "→ Killing ADK / uvicorn processes"
pkill -f "adk " 2>/dev/null || true
pkill -f "uvicorn" 2>/dev/null || true

echo "→ Killing Next.js dev server"
pkill -f "next dev" 2>/dev/null || true
pkill -f "next-server" 2>/dev/null || true

echo "→ Freeing demo ports (8080, 3000, 8000, 8081)"
for port in 8080 3000 8000 8081; do
  pids=$(lsof -ti ":${port}" 2>/dev/null || true)
  if [ -n "${pids}" ]; then
    echo "   port ${port}: killing ${pids}"
    kill -9 ${pids} 2>/dev/null || true
  fi
done

echo "→ Wiping local SQLite session store"
rm -rf football_stats_agent/.adk

echo "→ Wiping Next.js build cache"
rm -rf webapp/.next

echo ""
echo "✓ Clean slate. Now run:"
echo "   ./reset_and_start.sh             # terminal 1 (ADK)"
echo "   cd webapp && npm run dev         # terminal 2 (webapp)"
