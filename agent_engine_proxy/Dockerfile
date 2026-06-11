FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

ENV APP_DIR=/usr/local/src/app
WORKDIR ${APP_DIR}

# Workspace bootstrap: root pyproject + lockfile + this member's
# pyproject before any code, so the dep-install layer is cached
# across code-only changes.
COPY pyproject.toml uv.lock ./
COPY agent_engine_proxy/pyproject.toml agent_engine_proxy/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-workspace --package agent-engine-proxy

COPY agent_engine_proxy/main.py agent_engine_proxy/

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --package agent-engine-proxy

FROM python:3.11-slim

ENV APP_DIR=/usr/local/src/app

RUN groupadd --gid 1001 appuser && \
    useradd --uid 1001 --gid 1001 --create-home appuser

# uvicorn imports `main:app` from the cwd, so we put main.py at WORKDIR.
WORKDIR ${APP_DIR}

COPY --from=builder --chown=appuser:appuser ${APP_DIR}/.venv ${APP_DIR}/.venv
COPY --from=builder --chown=appuser:appuser ${APP_DIR}/agent_engine_proxy/main.py .

ENV PATH="${APP_DIR}/.venv/bin:$PATH"

USER appuser

ENTRYPOINT ["uvicorn"]
CMD ["main:app", "--host", "0.0.0.0", "--port", "8080"]
