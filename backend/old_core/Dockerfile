FROM python:3.12-slim

ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    POETRY_VERSION=1.5.1

RUN pip install uv

WORKDIR /app

#RUN apt-get update && apt-get install -y \
#    build-essential \
#    && rm -rf /var/lib/apt/lists/*

COPY uv.lock pyproject.toml /app/

RUN uv sync --no-dev

COPY src /app/src


CMD ["uv", "run", "python", "-m", "src", "--host", "0.0.0.0", "--port", "5000", "--timeout-keep-alive", "600", "--timeout-graceful-shutdown", "600"]