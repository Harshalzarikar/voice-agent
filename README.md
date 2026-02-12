# 🎙️ VoiceAI - Real-Time Intelligent Voice Assistant

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Render-46E3B7?style=for-the-badge&logo=render)](https://voice-agent-1-cvzd.onrender.com/)
[![Tech Stack](https://img.shields.io/badge/Stack-Django%20%7C%20FastAPI%20%7C%20React-blue?style=for-the-badge)](https://github.com/Harshalzarikar/voice-agent)

> **A low-latency, real-time voice orchestration platform that allows users to create and talk to custom AI agents with unique personalities.**

---

## 🚀 Key Features

*   **⚡ Sub-Second Latency**: Optimized for real-time conversation using WebSockets and async Python.
*   **🗣️ Real-Time Voice Processing**: Bi directional audio streaming with **Deepgram Nova-2** (STT) and **Aura** (TTS).
*   **🧠 Intelligent Agent Orchestration**: Uses **LangGraph** to manage conversation state, intent classification, and personality routing.
*   **🤖 Custom Personalities**: Users can build agents with distinct prompts (e.g., "Sarcastic Bot", "Helpful Tutor") that persist via Django.
*   **🔐 Secure Architecture**: Full JWT authentication flow with role-based access control.

---

## 🏗️ System Architecture

This project uses a **Hybrid Monolithic Architecture** deployed on a single Docker container for efficiency.

```
┌──────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────────────────┐  │
│  │   Login     │  │   Dashboard │  │      Voice Chat          │  │
│  │   (JWT)     │  │   (Agents)  │  │  (Microphone → Speaker)  │  │
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
| **Orchestration** | LangGraph + Groq (Llama 3.3) | Intent classification, routing logic |
| **Conversational** | Liquid LFM 2.5 | Fast, personality-driven responses |
| **STT** | Deepgram Nova-2 | Live speech transcription (<300ms latency) |
| **TTS** | Deepgram Aura | Natural voice synthesis |
| **WebSockets** | FastAPI | Real-time bi-directional audio streaming |


---

## 🛠️ Technical Deep Dive

### **1. Real-Time Audio Pipeline**
Unlike traditional assistants that record -> process -> play, VoiceAI streams audio **continuously**.
1.  **Input**: Browser sends raw PCM audio bytes via WebSocket.
2.  **Transcription**: Deepgram generates text in <300ms.
3.  **Reasoning**: LangGraph Router decides if the user finished a thought or is just pausing.
4.  **Response**: The LLM generates text tokens which are immediately sent to the TTS engine.
5.  **Output**: Audio is played back to the user while the AI is still "thinking" the rest of the sentence.

### **2. LangGraph Orchestration**
Instead of a simple LLM call, the system uses a graph-based state machine:
*   **Router Node**: Classifies user intent (e.g., "Question", "End Conversation", "Joke").
*   **Responder Node**: Generates the actual response based on the Agent's system prompt.
*   **Memory**: Maintains chat history for context-aware replies.

### **3. Production Deployment**
Deployed on **Render** using a custom Docker strategy:
*   **Nginx** acts as a reverse proxy, routing `/` to React, `/api` to Django, and `/ws` to FastAPI.
*   **Supervisord** manages all three processes inside a single container to maximize resource usage on the free tier.
*   **Database Migrations** run automatically on container startup to ensure data integrity.

---

## 🚀 Getting Started Locally

### **Prerequisites**
*   Docker & Docker Compose
*   (Optional) API Keys: Deepgram, Groq, OpenRouter

### **Installation**
1.  **Clone the repository**
    ```bash
    git clone https://github.com/Harshalzarikar/voice-agent.git
    cd voice-agent
    ```

2.  **Set up Environment Environment**
    Create a `.env` file in the root directory:
    ```env
    DEEPGRAM_API_KEY=your_key
    GROQ_API_KEY=your_key
    OPENROUTER_API_KEY=your_key
    ```

3.  **Run with Docker (Recommended)**
    ```bash
    docker-compose up --build
    ```
    *   Frontend: `http://localhost:5173`
    *   Backend API: `http://localhost:8000`

---

## � Screenshots

*(Add your screenshots here: Dashboard, Voice Chat Interface, Agent Builder)*

---

## 📬 Contact

**Harshal Zarikar**  
[LinkedIn](https://linkedin.com/in/harshalzarikar) | [GitHub](https://github.com/Harshalzarikar)

---
*Built as a showcase of modern Real-Time AI & Full Stack Engineering skills.*
