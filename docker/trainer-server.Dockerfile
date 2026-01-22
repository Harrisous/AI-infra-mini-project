# Trainer Server Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy trainer server code
COPY trainer-server/ /app/trainer-server/

# Expose port
EXPOSE 8080

# Run trainer
WORKDIR /app/trainer-server
CMD ["python3", "trainer.py"]
