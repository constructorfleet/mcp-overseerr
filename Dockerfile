# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --upgrade pip

COPY pyproject.toml README.md uv.lock ./
COPY src ./src
COPY openapi.yaml ./openapi.yaml

RUN pip install --no-cache-dir .

CMD ["overseerr-mcp"]
