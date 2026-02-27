# STAGE 1: Builder image
FROM python:3.12-slim AS builder

# Set the working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
	build-essential \
	libssl-dev \
	libffi-dev \
	libgmp-dev \
	python3-tk \
	&& rm -rf /var/lib/apt/lists/*

# Create a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install hypercorn

# Set cache directories
ENV HUGGINGFACE_HUB_CACHE="/app/.cache/huggingface"
ENV PIP_CACHE_DIR="/app/.cache/pip"
ENV HF_ENDPOINT="https://hf-mirror.com"
ENV PYTHONPATH="/app/src"

# Copy application code
COPY . .

# Create embeddings
RUN python3 src/ingest.py

# STAGE 2: Runtime image
FROM python:3.12-slim

WORKDIR /app

# Install only runtime dependencies (no build tools)
RUN apt-get update && apt-get install -y \
	libgmp-dev \
	python3-tk \
	&& rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application files
COPY --from=builder /app/src /app/src
COPY --from=builder /app/vectorstore /app/vectorstore

# Set environment variables
ENV HUGGINGFACE_HUB_CACHE="/app/.cache/huggingface"
ENV PYTHONPATH="/app/src"
ENV HF_ENDPOINT="https://hf-mirror.com"

# Expose port
EXPOSE 8000

# Start the application
CMD ["hypercorn", "--bind", "0.0.0.0:8000", "src.api:app"]
