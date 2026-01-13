#official Python runtime as a parent image
FROM python:3.13-slim-bullseye

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PATH="/home/appuser/.local/bin:$PATH"

# Create working directory
WORKDIR /app

# Install OS-level build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m appuser

# Copy project files before switching user
COPY . /app/

# Permissions for the app directory
RUN chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Install pipx and uv as non-root user
RUN pip install --user pipx && pipx ensurepath && pipx install uv

# Install project dependencies using uv
RUN uv sync

ENV PATH="/app/.venv/bin:$PATH"
# Install Gunicorn via uv
RUN uv add gunicorn

# Expose the app port
EXPOSE 8004

# Run the FastAPI app using Gunicorn and Uvicorn worker
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "app.main:app", "-b", "0.0.0.0:8004", "--worker-tmp-dir", "/dev/shm"]
