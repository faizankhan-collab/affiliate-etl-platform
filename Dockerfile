# Production Dockerfile for Affiliate ETL & RPC Platform
# Uses official Playwright Python image so automated scraper bots run seamlessly in headless mode

FROM mcr.microsoft.com/playwright/python:v1.48.0-jammy

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ensure Playwright browser binaries are present
RUN playwright install chromium

# Copy application files
COPY . .

# Create volume directories for persisted reports and downloads
RUN mkdir -p /app/backend/saved_reports /app/downloads /app/backend/sample_data

EXPOSE 8000

CMD ["sh", "-c", "uvicorn backend.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
