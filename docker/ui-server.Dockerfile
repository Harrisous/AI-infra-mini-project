# UI Server Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy UI server code
COPY ui-server/ /app/ui-server/

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/ || exit 1

# Run server
WORKDIR /app/ui-server
CMD ["python3", "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080"]
