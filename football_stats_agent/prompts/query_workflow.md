## Query Workflow
1. ALWAYS use `get_table_info` first if you are unsure about column names.
2. When calling `execute_sql`, use these exact parameter names:
   - `projectId` (camelCase, NOT project_id)
   - `query` (NOT sql)
3. Always fully qualify the table: `{{PROJECT_ID}}.qatar_fifa_world_cup.team_players_stat_raw`
4. Filter teams using the `nationality` column (e.g., WHERE nationality = 'France').
