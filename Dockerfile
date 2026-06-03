FROM python:3.12-slim

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

# Default: run API server
EXPOSE 8000 8501

CMD ["python", "api_server.py", "--host", "0.0.0.0", "--port", "8000"]
