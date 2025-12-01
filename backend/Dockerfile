FROM python:3.12.3-slim-bookworm

WORKDIR /app

# Install system dependencies for Playwright + OCR + Java 17 + curl
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
    ca-certificates \
    openjdk-17-jdk \
    && rm -rf /var/lib/apt/lists/*

# Set Java 17 environment variables
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="$JAVA_HOME/bin:$PATH"

# ---- Best-effort Allure CLI install ----
# If download fails (no internet / DNS issues), don't fail the build.
RUN ALLURE_VERSION=2.29.0; \
    if curl -fSL "https://repo.maven.org/maven2/io/qameta/allure/allure-commandline/${ALLURE_VERSION}/allure-commandline-${ALLURE_VERSION}.tgz" -o allure.tgz; then \
        echo "Downloaded Allure CLI ${ALLURE_VERSION}"; \
        tar -zxf allure.tgz -C /opt/; \
        ln -s /opt/allure-${ALLURE_VERSION}/bin/allure /usr/bin/allure; \
        rm -f allure.tgz; \
        allure --version || true; \
    else \
        echo "WARN: Failed to download Allure CLI. Tests will fall back to pytest-html."; \
    fi

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    pip install --no-cache-dir uvicorn "playwright==1.52.0" && \
    python -m playwright install --with-deps chromium

# Disable tokenizer warnings
ENV TOKENIZERS_PARALLELISM=false

# Copy backend project files
COPY . .

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
