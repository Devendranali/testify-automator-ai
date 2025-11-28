FROM python:3.12.3-slim-bookworm

WORKDIR /app

# Install system dependencies for Playwright + OCR + Java 17 + Allure CLI requirements
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
    unzip \
    openjdk-17-jdk \
    && rm -rf /var/lib/apt/lists/*

# Set Java 17 environment variables
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="$JAVA_HOME/bin:$PATH"

# Install Allure CLI (latest stable using Maven central)
RUN curl -o allure.tgz -Ls https://repo.maven.org/maven2/io/qameta/allure/allure-commandline/2.29.0/allure-commandline-2.29.0.tgz \
    && tar -zxvf allure.tgz -C /opt/ \
    && ln -s /opt/allure-2.29.0/bin/allure /usr/bin/allure \
    && rm -rf allure.tgz

# Verify Allure installed
RUN allure --version || true

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
