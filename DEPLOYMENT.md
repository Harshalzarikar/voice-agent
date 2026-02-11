# 🐳 Deployment Guide

This project is fully containerized using Docker Compose. This is the **best way** to deploy and run the application as it ensures all services (Django, FastAPI, React, Nginx) run in a consistent environment.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running.

## 🚀 Quick Start

1.  **Stop any running local services** (Django, Uvicorn, React dev server) to free up ports.
2.  **Open a terminal** in the project root (`voice_agent/`).
3.  **Run the deployment command**:

    ```bash
    docker-compose up --build
    ```

4.  **Access the application**:
    -   Open your browser and verify: **http://localhost**
    -   (Note: It runs on port 80, so no need for `:5173` or `:8000`)

## 🛠️ Service Architecture in Docker

| Service | Internal Port | Exposed Port | Description |
| :--- | :--- | :--- | :--- |
| **nginx** | 80 | **80** | Reverse proxy. Entry point for Browser. |
| **frontend** | 80 | - | React App (served by internal Nginx). |
| **backend_core** | 8000 | - | Django API (Auth, Agents). |
| **backend_streaming**| 8001 | - | FastAPI (Voice Processing). |
| **db** | 5432 | - | PostgreSQL (Optional, currently using SQLite). |

## 🔧 Configuration

### Environment Variables
The `.env` file in the root directory is used by all services. Ensure it contains:

```env
DEEPGRAM_API_KEY=your_key
OPENROUTER_API_KEY=your_key
GROQ_API_KEY=your_key
# Django Secret Key (optional for dev, needed for prod)
SECRET_KEY=...
```

### Troubleshooting

-   **Port Conflicts**: If port 80 is occupied, modify `docker-compose.yml` under `nginx` service:
    ```yaml
    ports:
      - "8080:80"  # Example: Change host port to 8080
    ```
    Then access via `http://localhost:8080`.

-   **Rebuild**: If you make code changes, rebuild the containers:
    ```bash
    docker-compose up --build
    ```
