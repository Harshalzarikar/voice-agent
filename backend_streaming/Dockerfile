FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (ffmpeg needed by openai-whisper, libsndfile1 by soundfile)
RUN apt-get update && apt-get install -y \
    build-essential \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install dependencies
COPY requirements.txt .
# Install CPU-only PyTorch first to save ~2GB of space (since Whisper depends on torch)
RUN pip install --no-cache-dir torch torchaudio --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY backend_streaming ./backend_streaming

# Expose port
EXPOSE 8001

# Set python path
ENV PYTHONPATH=/app

# Command to run (from root)
CMD ["uvicorn", "backend_streaming.app.main:app", "--host", "0.0.0.0", "--port", "8001"]
