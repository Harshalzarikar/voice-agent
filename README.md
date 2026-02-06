# 🎙️ Real-Time AI Voice Orchestration System

### Artizence Systems LLP - Technical Assessment
**Role**: AI Developer / Full Stack Engineer  
**Author**: Harshal Zarikar  
**Submission Date**: February 7, 2026

---

## 🌟 Project Overview

A modular, high-concurrency platform designed for **low-latency AI voice interactions**. Users can create custom AI agents with unique personalities and have real-time voice conversations with them through a web browser.

### Key Highlights
- **Sub-second latency** voice-to-voice interaction
- **Custom personality agents** via system prompts
- **LangGraph orchestration** for intelligent conversation flow
- **JWT-secured API** for production readiness

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Streamlit)                       │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────┐  │
│  │   Login     │  │   Agent     │  │      Voice Chat          │  │
│  │   Page      │  │   Builder   │  │  (Microphone → Speaker)  │  │
│  └─────────────┘  └─────────────┘  └──────────────────────────┘  │
└────────────────────────────┬─────────────────────────────────────┘
                             │ WebSocket (Audio)
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                  BACKEND - STREAMING (FastAPI)                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │                    VoiceProcessor                          │  │
│  │  ┌─────────────┐    ┌─────────────┐    ┌───────────────┐  │  │
│  │  │ Deepgram    │───▶│  LangGraph  │───▶│   Deepgram    │  │  │
│  │  │ STT (Nova-2)│    │ (Router +   │    │   TTS (Aura)  │  │  │
│  │  │             │    │  Responder) │    │               │  │  │
│  │  └─────────────┘    └─────────────┘    └───────────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
└────────────────────────────┬─────────────────────────────────────┘
                             │ HTTP (REST)
                             ▼
┌──────────────────────────────────────────────────────────────────┐
│                   BACKEND - CORE (Django)                         │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────┐  │
│  │ JWT Auth    │  │   Agent     │  │     SQLite Database      │  │
│  │ (SimpleJWT) │  │   CRUD API  │  │   (Users + Agents)       │  │
│  └─────────────┘  └─────────────┘  └──────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

### Layer Breakdown

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Orchestration** | LangGraph + Qwen-32B | Intent classification, routing logic |
| **Conversational** | Llama-3.1-8b-instant | Fast, personality-driven responses |
| **STT** | Deepgram Nova-2 | Live speech transcription |
| **TTS** | Deepgram Aura | Natural voice synthesis |

---

## 💻 Technical Stack

| Component | Technology |
|-----------|------------|
| Backend (Core) | Django REST Framework, JWT Authentication |
| Backend (Streaming) | FastAPI, WebSockets, Async Python |
| Frontend | Streamlit (Prototyping UI) |
| AI Logic | LangChain, LangGraph |
| LLM Provider | Groq (Qwen-32B + Llama 3.1) |
| Voice APIs | Deepgram (STT + TTS) |
| Testing | Postman Collection (included) |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or higher
- A **Deepgram API Key** (free at [deepgram.com](https://deepgram.com))
- A **Groq API Key** (free at [console.groq.com](https://console.groq.com))

### 1. Clone & Install

```bash
# Clone the repository
git clone <your-repo-url>
cd voice_agent

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root:

```env
DEEPGRAM_API_KEY=your_deepgram_api_key_here
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Initialize Database

```bash
# Apply migrations
.\venv\Scripts\python backend_core/manage.py migrate

# Create your admin account
.\venv\Scripts\python backend_core/manage.py createsuperuser
```
Follow the prompts to create a username and password.

### 4. Start All Services

Open **three separate terminals** and run:

**Terminal 1 - Django API (Port 8000)**
```bash
.\venv\Scripts\python backend_core/manage.py runserver 8000
```

**Terminal 2 - FastAPI Streaming (Port 8001)**
```bash
.\venv\Scripts\uvicorn backend_streaming.app.main:app --reload --port 8001
```

**Terminal 3 - Streamlit UI (Port 8501)**
```bash
.\venv\Scripts\streamlit run frontend_streamlit/Home.py
```

### 5. Access the Application

Open your browser and navigate to: **http://localhost:8501**

---

## 📖 User Guide

### Step 1: Login
1. Go to the **Home** page.
2. Enter your username and password (created during `createsuperuser`).
3. Click **Login**.

### Step 2: Create an Agent
1. Navigate to **Agent Builder** in the sidebar.
2. Fill in:
   - **Agent Name**: e.g., "Friendly Tutor"
   - **System Prompt**: e.g., "You are a patient, encouraging tutor who explains concepts simply."
   - **Voice**: Select from available Deepgram voices.
3. Click **Create Agent**.

### Step 3: Talk to Your Agent
1. Navigate to **Voice Chat** in the sidebar.
2. Select your agent from the dropdown.
3. Click **Start Call**.
4. **Allow microphone access** when prompted.
5. Speak naturally — the agent will respond in real-time!
6. Click **End Call** when finished.

---

## 🔌 API Reference

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/token/` | POST | Get JWT access & refresh tokens |
| `/api/token/refresh/` | POST | Refresh an expired access token |

**Login Request:**
```json
POST /api/token/
{
    "username": "your_username",
    "password": "your_password"
}
```

**Response:**
```json
{
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

### Agents

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/agents/` | GET | Optional | List all agents |
| `/api/agents/` | POST | Required | Create a new agent |
| `/api/agents/{id}/` | GET | Optional | Get agent details |
| `/api/agents/{id}/` | PUT | Required | Update agent |
| `/api/agents/{id}/` | DELETE | Required | Delete agent |

**Create Agent Request:**
```json
POST /api/agents/
Authorization: Bearer <access_token>
{
    "name": "Sales Agent",
    "system_prompt": "You are a persuasive but friendly sales agent.",
    "voice_id": "aura-asteria-en"
}
```

### WebSocket (Voice Chat)

| Endpoint | Protocol | Description |
|----------|----------|-------------|
| `/ws/chat/{agent_id}` | WebSocket | Real-time voice streaming |

**Connection Flow:**
1. Browser opens WebSocket to `ws://localhost:8001/ws/chat/1`
2. Server confirms connection
3. Browser sends binary audio chunks (16kHz, mono, PCM)
4. Server returns binary audio responses

---

## 🎨 Available Voices

| Voice ID | Description |
|----------|-------------|
| `aura-asteria-en` | Female, American, Professional |
| `aura-luna-en` | Female, American, Warm |
| `aura-stella-en` | Female, American, Friendly |
| `aura-orion-en` | Male, American, Deep |
| `aura-arcas-en` | Male, American, Confident |

---

## 🧪 Testing with Postman

1. Import `Voice_Agent_API.postman_collection.json` into Postman.
2. Use the **Login** request to get an access token.
3. Copy the `access` token from the response.
4. In the collection variables, set `access_token` to your token.
5. Test the Agent CRUD endpoints.

---

## 📁 Project Structure

```
voice_agent/
├── backend_core/           # Django REST API
│   ├── agents/             # Agent model, views, serializers
│   ├── config/             # Django settings, URLs
│   └── manage.py
├── backend_streaming/      # FastAPI WebSocket Server
│   └── app/
│       ├── api/            # WebSocket endpoint
│       ├── core/           # Configuration
│       └── services/       # VoiceProcessor (LangGraph + Deepgram)
├── frontend_streamlit/     # Streamlit UI
│   ├── Home.py             # Login page
│   └── pages/              # Dashboard, Agent Builder, Voice Chat
├── .env                    # API Keys (create this)
├── requirements.txt        # Python dependencies
├── Voice_Agent_API.postman_collection.json
└── README.md               # This file
```

---

## ⚠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| `401 Unauthorized` on login | Check username/password, ensure Django is running |
| `Connection refused` on Voice Chat | Ensure FastAPI server is running on port 8001 |
| No audio response | Check browser microphone permissions |
| `Deepgram Error 1011` | Connection timeout — ensure audio is streaming |
| `AssertionError` in websockets | Ensure `websockets==13.1` is installed |

---

## 🏆 Credits

- **LLM Provider**: [Groq](https://console.groq.com) (Ultra-fast inference)
- **Voice APIs**: [Deepgram](https://deepgram.com) (STT + TTS)
- **Orchestration**: [LangGraph](https://github.com/langchain-ai/langgraph)

---

## 📄 License

This project is submitted as part of the Artizence Technical Assessment and is for evaluation purposes.
