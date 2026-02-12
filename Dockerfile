# Base image: Python 3.11 (Debian based)
FROM python:3.11-slim

# Install system dependencies (Nginx, Node.js, Supervisor)
RUN apt-get update && apt-get install -y \
    nginx \
    nodejs \
    npm \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# --- Backend Core & Streaming Setup ---
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn uvicorn

COPY backend_core ./backend_core
COPY backend_streaming ./backend_streaming
# COPY .env .

# --- Frontend Build ---
WORKDIR /app/frontend_react
COPY frontend_react/package.json frontend_react/yarn.lock ./
RUN npm install
COPY frontend_react ./

# Configured for Space: zarikarharry1412/voice_agent
# Note: Underscores in space names usually turn into hyphens in the direct URL.
ENV VITE_API_URL=""
ENV VITE_WS_URL=""

RUN npm run build

# Move build to Nginx location
RUN rm -rf /var/www/html/* && cp -r dist/* /var/www/html/

# --- Nginx Configuration ---
COPY nginx_hf.conf /etc/nginx/sites-available/default

# --- Supervisor Configuration ---
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Permissions
RUN chown -R www-data:www-data /var/www/html
RUN chmod -R 755 /var/www/html

# Expose HF Port
EXPOSE 7860

# Start Supervisor (runs everything)
# Set correct working directory for CMD
WORKDIR /app
# Start Supervisor (runs everything) after migrating
CMD bash -c "python backend_core/manage.py migrate && /usr/bin/supervisord"
