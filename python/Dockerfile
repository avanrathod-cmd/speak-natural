# SpeakRight Coaching API Dockerfile

FROM --platform=linux/amd64 python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for audio processing and building Python packages
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    gcc \
    g++ \
    make \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy project files
COPY pyproject.toml .
COPY uv.lock .

# Install Python dependencies
RUN uv sync --frozen --no-dev

# Copy application code
COPY . .

# Create storage directory
RUN mkdir -p /tmp/speak-right

# Expose port (Cloud Run uses PORT env var, defaults to 8080)
EXPOSE 8080

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV STORAGE_DIR=/tmp/speak-right
ENV PORT=8080

# Health check (removed - Cloud Run has its own health checks)

# Run the application - use $PORT environment variable
CMD ["sh", "-c", "uv run uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
