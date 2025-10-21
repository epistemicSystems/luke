# Dockerfile for Insight Graph

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY insight_graph/ ./insight_graph/
COPY scripts/ ./scripts/
COPY docs/ ./docs/
COPY pyproject.toml .
COPY README.md .

# Create data directories
RUN mkdir -p /app/data/graph /app/data/chroma /app/data/voice

# Expose API port
EXPOSE 8000

# Default command (can be overridden)
CMD ["python", "-m", "uvicorn", "insight_graph.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
