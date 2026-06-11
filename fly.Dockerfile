# fly.Dockerfile — All-in-one MySQL + FastAPI for Fly.io
FROM python:3.14-slim

LABEL maintainer="Gokul Koduri"
LABEL description="Opportunity Intelligence Platform — Live Demo"

WORKDIR /app

# Install MySQL Server + system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-mysql-server \
    default-mysql-client \
    git \
    curl \
    && rm -rf /var/lib/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir fastapi uvicorn

# Copy project files
COPY . .

# Make scripts executable
RUN chmod +x scripts/fly-start.sh

# MySQL data dir will be on persistent volume at /data
# Fly.io mounts the volume at /data; we symlink MySQL there
ENV MYSQL_DATA_DIR=/data/mysql

EXPOSE 8000

CMD ["scripts/fly-start.sh"]
