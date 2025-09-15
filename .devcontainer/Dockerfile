ARG PY_VERSION=3.12
ARG UV_VERSION=latest

FROM ghcr.io/astral-sh/uv:$UV_VERSION AS uv

FROM mcr.microsoft.com/devcontainers/python:$PY_VERSION

COPY --from=uv --chown=vscode: /uv /uvx /bin/

RUN pipx install rust-just

WORKDIR /app
