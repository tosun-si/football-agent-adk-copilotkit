FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

ENV APP_DIR=/usr/local/src/app
WORKDIR ${APP_DIR}

COPY pyproject.toml .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev --no-install-project

COPY main.py .

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-dev

FROM python:3.11-slim

ENV APP_DIR=/usr/local/src/app

RUN groupadd --gid 1001 appuser && \
    useradd --uid 1001 --gid 1001 --create-home appuser

WORKDIR ${APP_DIR}

COPY --from=builder --chown=appuser:appuser ${APP_DIR}/.venv ${APP_DIR}/.venv
COPY --from=builder --chown=appuser:appuser ${APP_DIR}/main.py .

ENV PATH="${APP_DIR}/.venv/bin:$PATH"

USER appuser

ENTRYPOINT ["uvicorn"]
CMD ["main:app", "--host", "0.0.0.0", "--port", "8080"]
