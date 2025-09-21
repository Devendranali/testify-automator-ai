# -------- Stage 1: Builder -------- #
FROM python:3.12.3-slim-bookworm AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 libsm6 libxext6 libxrender-dev libffi-dev \
    libgl1 tesseract-ocr curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --target=/python_deps -r requirements.txt && \
    pip install --no-cache-dir uvicorn  # ✅ ensure uvicorn installed

# -------- Stage 2: Production -------- #
FROM python:3.12.3-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libglib2.0-0 libsm6 libxext6 libxrender1 libgl1 tesseract-ocr \
    && rm -rf /var/lib/apt/lists/*

# Copy dependencies
COPY --from=builder /python_deps /usr/local/lib/python3.12/site-packages

# Copy app code
COPY . .

# Expose backend port
EXPOSE 8001

# ✅ Run uvicorn directly
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]

