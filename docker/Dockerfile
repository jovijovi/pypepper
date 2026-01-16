# syntax=docker/dockerfile:1.20.0

# Global args
ARG PYTHON_VER=3.13
ARG IMAGE_TAG=slim
ARG BASE_IMAGE=python:${PYTHON_VER}-${IMAGE_TAG}
ARG UV_IMAGE=ghcr.io/astral-sh/uv:0.9.26

FROM ${UV_IMAGE} AS uvbin

# ---------- STAGE: builder ----------
FROM ${BASE_IMAGE} AS builder

COPY --from=uvbin /uv /uvx /bin/

ENV UV_LINK_MODE=copy \
    UV_NO_DEV=1

WORKDIR /opt/app_src

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    procps \
    iputils-ping \
 && rm -rf /var/lib/apt/lists/*

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock,readonly \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml,readonly \
    uv sync --locked --no-install-project

ADD conf /opt/app_src/conf
ADD pypepper /opt/app_src/pypepper
ADD example/server /opt/app_src/example/server
COPY scripts /opt/app_src/scripts
COPY git.json /opt/app_src/git.json

RUN python ./scripts/build.py


# ---------- STAGE: runtime ----------
FROM ${BASE_IMAGE} AS runtime

ARG APP_UID=10001
ARG APP_GID=10001
RUN groupadd -g ${APP_GID} appuser \
 && useradd  -m -u ${APP_UID} -g ${APP_GID} -s /usr/sbin/nologin appuser

ENV VIRTUAL_ENV=/opt/app/.venv/ \
    PATH="/opt/app/.venv/bin:${PATH}" \
    PYTHONPATH="${PYTHONPATH}:/opt/app/"

COPY --from=builder --chown=appuser:appuser /opt/app_src/dist /opt/app
COPY --from=builder --chown=appuser:appuser /opt/app_src/git.json /opt/app/

WORKDIR /opt/app

USER appuser

ENTRYPOINT ["/opt/app/.venv/bin/python"]
CMD ["example/server/app.py", "--config", "./conf/app.config.yaml"]
