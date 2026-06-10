# railway.Dockerfile — API + Dashboard for Railway (managed MySQL)
FROM python:3.12-slim

LABEL maintainer="Gokul Koduri"
LABEL description="Opportunity Intelligence Platform — Live Demo"

WORKDIR /app

# System deps only (no MySQL — Railway provides it)
RUN apt-get update && apt-get install -y --no-install-recommends \
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
RUN chmod +x scripts/railway-start.sh

EXPOSE 8000

CMD ["scripts/railway-start.sh"]
