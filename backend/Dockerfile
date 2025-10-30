# =========================
# Dockerfile
# =========================
FROM python:3.12.3-slim-bookworm

WORKDIR /app

# --- Install system dependencies for Playwright + OCR + GUI + noVNC ---
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
    xvfb \
    x11vnc \
    fluxbox \
    novnc \
    websockify \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# --- Install Python dependencies ---
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir uvicorn "playwright==1.52.0" && \
    python -m playwright install --with-deps chromium

# --- Copy application code ---
COPY . .

# --- Environment variables ---
ENV DISPLAY=:99
ENV TOKENIZERS_PARALLELISM=false

# --- Expose backend + noVNC ports ---
EXPOSE 8001 6080

# --- Fix: auto-redirect / to /vnc.html ---
RUN ln -s /usr/share/novnc/vnc.html /usr/share/novnc/index.html

# --- Launch virtual display + window manager + noVNC + FastAPI ---
CMD bash -c "\
  echo '🚀 Starting virtual display and VNC stack...' && \
  Xvfb :99 -screen 0 1920x1080x24 & \
  sleep 2 && \
  fluxbox & \
  echo '🧩 Starting x11vnc server...' && \
  x11vnc -display :99 -nopw -forever -shared -listen 127.0.0.1 -rfbport 5900 -rfbportv6 5900 & \
  sleep 2 && \
  echo '🌐 Starting noVNC web interface...' && \
  websockify --web=/usr/share/novnc/ 6080 127.0.0.1:5900 & \
  echo '🧠 Starting FastAPI backend...' && \
  python -m uvicorn main:app --host 0.0.0.0 --port 8001"

