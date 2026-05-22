#!/usr/bin/env bash

set -e
set -o pipefail
set -u

echo "############# Create raw table and load data"

bq load \
  --project_id="$PROJECT_ID" \
  --location="$REGION" \
  --source_format=NEWLINE_DELIMITED_JSON \
  --autodetect \
  qatar_fifa_world_cup.team_players_stat_raw \
  "gs://$BUCKET_PATH/world_cup_team_players_stats_raw_ndjson.json"
