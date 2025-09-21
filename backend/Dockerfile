# -------- Stage 1: Builder -------- #
FROM python:3.12.3-slim-bookworm AS builder

WORKDIR /app

# Install build dependencies + Playwright browser deps
RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libffi-dev \
    libgl1 \
    libnss3 \
    libatk-bridge2.0-0 \
    libx11-xcb1 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libgtk-3-0 \
    tesseract-ocr \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --target=/python_deps -r requirements.txt && \
    pip install --no-cache-dir uvicorn playwright && \
    python -m playwright install --with-deps

# -------- Stage 2: Runtime -------- #
FROM python:3.12.3-slim-bookworm

WORKDIR /app

# Install only runtime system dependencies for Playwright and Tesseract
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgl1 \
    libnss3 \
    libatk-bridge2.0-0 \
    libx11-xcb1 \
    libdrm2 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libgtk-3-0 \
    tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy installed dependencies and app code
COPY --from=builder /python_deps /usr/local/lib/python3.12/site-packages
COPY . .

EXPOSE 8001

CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
