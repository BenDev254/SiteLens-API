# Minimal Dockerfile for FastAPI app (Cloud Run compatible)
FROM python:3.11-slim

# Install system deps
RUN apt-get update && apt-get install -y build-essential libpq-dev --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements first for caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app
COPY . .

ENV PYTHONUNBUFFERED=1
ENV PORT=8080

EXPOSE 8080

# Use uvicorn for running
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
