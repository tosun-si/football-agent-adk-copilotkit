FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

ENV APP_DIR=/usr/local/src/app
WORKDIR ${APP_DIR}

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY agent_config.yaml ./
COPY football_stats_agent/ ./football_stats_agent/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

FROM python:3.11-slim

ENV APP_DIR=/usr/local/src/app

RUN groupadd --gid 1001 appuser && \
    useradd --uid 1001 --gid 1001 --create-home appuser

# ADK requires WORKDIR to be the parent of the agent package for discovery
WORKDIR /agents

COPY --from=builder --chown=appuser:appuser ${APP_DIR}/.venv ${APP_DIR}/.venv
COPY --from=builder --chown=appuser:appuser ${APP_DIR}/football_stats_agent/ ./football_stats_agent/

ENV PATH="${APP_DIR}/.venv/bin:$PATH"

USER appuser

ENTRYPOINT ["adk"]
CMD ["api_server", "--host", "0.0.0.0", "--port", "8080"]
