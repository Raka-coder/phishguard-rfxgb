FROM python:3.11-slim

# Instal uv dan bun (dibutuhkan Reflex untuk compile frontend)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates unzip \
 && curl -fsSL https://bun.sh/install | bash \
 && rm -rf /var/lib/apt/lists/*
ENV PATH="/root/.bun/bin:${PATH}"

WORKDIR /app

# Dependensi Python (cached layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Kode sumber + artefak
COPY . .

# Compile frontend Reflex saat build (membutuhkan bun)
RUN uv run reflex init --no-agents 2>/dev/null || true
RUN uv run reflex compile

# Entrypoint
RUN chmod +x docker/entrypoint.sh

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

EXPOSE 3000 8000 8001

ENTRYPOINT ["/app/docker/entrypoint.sh"]