FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY backend_core ./backend_core
# Copy .env if needed or rely on docker-compose env_file (better)

# Set working directory to inside backend_core so "config" is a top-level package
WORKDIR /app/backend_core

# Expose port
EXPOSE 8000

# Set python path
ENV PYTHONPATH=/app/backend_core

# Command to run (from backend_core dir)
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
