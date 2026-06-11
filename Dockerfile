FROM python:3.14-slim

LABEL maintainer="Gokul Koduri"
LABEL description="Startup Research Report — AI-powered market intelligence platform"

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    curl \
    && rm -rf /var/lib/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir fastapi uvicorn streamlit plotly pandas

# Copy project
COPY . .

# Make scripts executable
RUN chmod +x scripts/railway-start.sh

# Default: run startup script (seed + API server)
EXPOSE 8000

CMD ["scripts/railway-start.sh"]
