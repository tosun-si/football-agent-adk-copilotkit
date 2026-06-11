# Golden dataset

Reference questions + expected behaviors for the football stats agent. Replay it in CI to catch regressions when the `SYSTEM_INSTRUCTION` (or any of its `.md` modules) changes.

## Two ways to run

### 1. Standalone script (`golden_dataset/runner.py`)

Minimal, zero pytest dependency. Best for CI scripts and ad-hoc runs.

```bash
# Start the agent first (it must already be reachable)
docker compose up

# Run the dataset
uv run python -m golden_dataset.runner
```

Override the target URL with `ADK_URL`:

```bash
ADK_URL=https://football-stats-api-…run.app uv run python -m golden_dataset.runner
```

### 2. Pytest (`tests/test_golden.py`)

Same dataset, same assertions — but with automatic agent lifecycle (the fixture in `tests/conftest.py` brings up `docker compose adk-agent` if nothing answers on port 8080, and tears it down on exit), automatic retries on flaky LLM responses (`pytest-rerunfailures`), and the standard pytest output / filter / debug story.

```bash
uv run pytest tests/test_golden.py -v
```

You don't need to start the agent manually — the fixture handles it. If you already have `docker compose up` running, the fixture detects it and reuses it (no restart).

Override:

```bash
ADK_URL=https://prod-cloud-run-url uv run pytest tests/test_golden.py -v
```

(With a remote `ADK_URL`, the fixture won't try to manage Docker — it assumes the URL is alive.)

Exit code `0` = green. Non-zero = at least one regression, with details printed.

## Adding a case

Edit `dataset.yaml`. Each entry has:

- `id`: short, unique, snake_case identifier (used in failure output)
- `question`: the natural-language prompt sent to the agent
- `expect.type`: one of the assertion types below
- `expect.<...>`: parameters specific to that assertion

## Assertion types

| Type | Checks | Parameters |
|------|--------|------------|
| `contains_number` | The given number appears in the natural-language text | `value: <number>` |
| `ordered_list` | The first N entities returned (chart data first, then text fallback) match the expected order | `values: [name1, name2, ...]` |
| `chart_spec` | Response contains a ` ```chart``` ` block of the right type and size | `chart_type: bar / line / pie`, `min_data_points`, `max_data_points` |
| `no_chart` | Response is text only (no chart block) and contains a given substring | `must_contain: <string>` |

Each assertion lives in `runner.py` as a single function returning `None` (pass) or an error string (fail). Add a new key in the `ASSERTIONS` map if you need a new kind.

## Updating expected values

When you intentionally change the agent's behavior (new business rule, schema change, prompt refactor):

1. Run the agent manually on the affected questions
2. Verify the new answers are correct
3. Pin the new ground truth in `dataset.yaml`
4. Commit dataset + code together

The dataset is a **contract** — it should evolve deliberately, not silently.

## CI wiring (example)

```yaml
# cloudbuild.yaml — sketch
- name: 'gcr.io/google.com/cloudsdktool/google-cloud-cli:stable'
  script: |
    # the ADK agent is reachable at the deployed Cloud Run URL
    ADK_URL=$(gcloud run services describe football-stats-api-copilotkit \
      --region europe-west1 --format='value(status.url)')
    export ADK_URL
    uv run python -m golden_dataset.runner
```

The PR is blocked if the runner exits non-zero.

## What this catches vs. doesn't

**Catches**: behavior regressions on reference questions — wrong values, dropped chart blocks, broken ordering after a prompt tweak.

**Doesn't catch**: hallucinations on out-of-dataset questions, latency / cost regressions, answer-style drift. Each of those is its own pattern (observability for latency, LLM-as-judge for style, broader sampling for hallucinations).
