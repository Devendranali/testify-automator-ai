ARG PYTHON_VERSION=python3.12.3
FROM ${PYTHON_VERSION}-slim-bookworm AS build

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Install system dependencies for Playwright + OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt /app

RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --upgrade pip && \
    /opt/venv/bin/pip install --no-cache-dir --only-binary=:all: --prefer-binary -r requirements.txt && \
    /opt/venv/bin/pip install --no-cache-dir uvicorn "playwright==1.52.0" && \
    python -m playwright install --with-deps chromium

FROM ${PYTHON_VERSION}-slim AS runtime

ENV PATH="PATH:/opt/venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

ARG USER_NAME=python
ARG UID=10001

USER adduser \
    --disabled-password \
    --gecos "" \
    --home "/nonexistent" \
    --shell "/sbin/nologin" \
    --no-create-home \
    --uid ${UID} \
    ${USER_NAME}

WORKDIR /app

# Copy application code
COPY --from=build /opt/venv /opt/venv

COPY . /app

# Disable tokenizer warnings from HuggingFace
ENV TOKENIZERS_PARALLELISM=false


EXPOSE 8001

USER ${USER_NAME}

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
