FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    PATH="/root/.local/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    ca-certificates \
    openjdk-17-jdk-headless \
    maven \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv semgrep

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY app ./app

RUN mkdir -p /app/.codeshift/analyses /app/.codeshift/workspaces

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]