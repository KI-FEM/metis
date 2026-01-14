# STAGE 1: Builder image
FROM python:3.12-slim

# Install uv.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy the application into the container.
COPY . /app

# Set the working directory
WORKDIR /app

# Install application dependencies
RUN uv sync --frozen --no-cache

# Set cache directories
ENV HUGGINGFACE_HUB_CACHE="/app/.cache/huggingface"
ENV HF_ENDPOINT="https://hf-mirror.com"

# Expose port
EXPOSE 8000

# Start the application
CMD ["/app/.venv/bin/fastapi", "run", "/app/src/api.py", "--port", "8000", "--host", "0.0.0.0"]