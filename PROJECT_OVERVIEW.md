# 🎙️ Voice Agent Project - Complete Overview & Interview Guide

## 📌 What Does This Project Do?

This is a **Real-Time AI Voice Assistant Platform** where users can:
1. **Create custom AI agents** with unique personalities (e.g., "Sarcastic Bot", "Friendly Tutor")
2. **Talk to these agents** using their microphone
3. **Hear the agent respond** in a natural voice

Think of it like creating your own **custom Alexa or Siri** with any personality you want!

---

## 🔄 How Does It Work? (Complete Flow)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER FLOW                                       │
└─────────────────────────────────────────────────────────────────────────────┘

Step 1: User speaks into microphone
         │
         ▼
Step 2: Browser captures audio → sends via WebSocket to FastAPI
         │
         ▼
Step 3: FastAPI sends audio to Deepgram STT (Speech-to-Text)
         │
         ▼
Step 4: Deepgram returns text: "What is the weather today?"
         │
         ▼
Step 5: LangGraph processes the text:
         ├── Router Node: Analyzes intent (is this a question? goodbye? etc.)
         └── Responder Node: Generates response using LLM
         │
         ▼
Step 6: LLM (Liquid LFM) generates: "I don't have weather data, but it's always sunny in my digital world!"
         │
         ▼
Step 7: FastAPI sends text to Deepgram TTS (Text-to-Speech)
         │
         ▼
Step 8: Deepgram returns audio bytes
         │
         ▼
Step 9: FastAPI sends audio via WebSocket to browser
         │
         ▼
Step 10: Browser plays audio → User hears the response!
```

---

## 🏗️ The Three Servers Explained

### 1️⃣ Django (Port 8000) - "The Database Manager"
**Purpose**: Stores users and agent configurations

| What It Does | How |
|--------------|-----|
| User Authentication | JWT tokens (login/logout) |
| Store Agent Data | SQLite database |
| Provide REST API | `/api/agents/`, `/api/token/` |

**Example Flow**:
```
User creates "Sarcastic Bot" → Django saves to database → Returns agent ID = 1
```

---

### 2️⃣ FastAPI (Port 8001) - "The Voice Engine"
**Purpose**: Real-time voice processing

| What It Does | How |
|--------------|-----|
| WebSocket Connection | Browser connects to `/ws/chat/1` |
| Speech Recognition | Deepgram Nova-2 (live streaming) |
| AI Responses | LangGraph + OpenRouter (Liquid/Qwen) |
| Voice Synthesis | Deepgram Aura TTS |

**Example Flow**:
```
User speaks "Hello" → Deepgram transcribes → LLM responds → Deepgram speaks back
```

---

### 3️⃣ Streamlit (Port 8501) - "The User Interface"
**Purpose**: Web dashboard for users

| Page | Purpose |
|------|---------|
| Home | Login with username/password |
| Dashboard | See your agents |
| Agent Builder | Create new agents |
| Voice Chat | Talk to your agent |

---

## 🧠 LangGraph Architecture Explained

### What is LangGraph?
LangGraph is a framework for building **stateful AI workflows**. Instead of just sending text to an LLM, we create a "graph" of nodes that process the conversation.

### Our Graph Structure:
```
              ┌─────────────┐
              │   START     │
              └──────┬──────┘
                     │
                     ▼
              ┌─────────────┐
              │   ROUTER    │  ← Analyzes user intent
              └──────┬──────┘
                     │
         ┌───────────┼───────────┐
         │           │           │
         ▼           ▼           ▼
    (end_conv)  (general)   (other intents)
         │           │           │
         │           ▼           │
         │    ┌─────────────┐    │
         │    │  RESPONDER  │    │
         │    └──────┬──────┘    │
         │           │           │
         └───────────┼───────────┘
                     │
                     ▼
              ┌─────────────┐
              │    END      │
              └─────────────┘
```

### Why Qwen + Liquid?

| LLM | Model | Purpose | Why? |
|-----|-------|---------|------|
| Router | Qwen-4b (Free) | Intent classification | Efficient reasoning on free tier |
| Responder | Liquid LFM 2.5 | Generate responses | Fast, lightweight, efficient |

This is called **"Modular Intelligence"** - separating logic from personality.

---

## 🔐 Authentication Flow

```
┌──────────────┐    POST /api/token/     ┌──────────────┐
│   Browser    │ ───────────────────────▶│    Django    │
│  (Streamlit) │   {username, password}  │   (JWT)      │
└──────────────┘                         └──────────────┘
       │                                        │
       │◀───────────────────────────────────────┤
       │    {access_token, refresh_token}       │
       │                                        │
       ▼                                        │
┌──────────────┐    Authorization: Bearer      │
│  Store in    │ ──────────────────────────────▶
│ session_state│   GET /api/agents/            │
└──────────────┘                               │
```

---

## ❓ Interview Questions & Answers

### Q1: "Explain the architecture of your project"

**Answer**:
> "I built a three-tier architecture:
> 1. **Django** handles authentication and data persistence using JWT tokens
> 2. **FastAPI** handles real-time WebSocket connections for voice streaming
> 3. **Streamlit** provides the user interface
> 
> For AI processing, I used **LangGraph** to create a modular workflow with a Router node for intent classification and a Responder node for generating personality-driven responses. Voice processing uses Deepgram for both STT and TTS."

---

### Q2: "Why did you use LangGraph instead of a simple LLM call?"

**Answer**:
> "LangGraph provides several advantages:
> 1. **Separation of concerns** - The router handles logic, the responder handles personality
> 2. **Extensibility** - I can easily add more nodes (like a fact-checker or memory node)
> 3. **State management** - LangGraph maintains conversation state across turns
> 4. **Conditional routing** - I can route to different nodes based on intent (e.g., end conversation early)"

---

### Q3: "How do you achieve low latency?"

**Answer**:
> "I optimized for latency at every layer:
> 1. **Streaming STT** - Deepgram processes audio in real-time, not after recording
> 2. **Efficient LLMs** - Using lightweight models (Liquid 1.2B, Qwen 4B) for speed
> 3. **Streaming TTS** - Audio is sent in chunks as it's generated
> 4. **WebSockets** - Persistent connection avoids HTTP overhead
> 5. **Async Python** - Non-blocking I/O for concurrent processing"

---

### Q4: "Why separate Django and FastAPI?"

**Answer**:
> "Each framework excels at different things:
> - **Django** is perfect for user auth, ORM, and admin interface
> - **FastAPI** is optimized for async WebSocket handling and high concurrency
> 
> By separating them, I get the best of both worlds. Django handles CRUD operations, while FastAPI handles real-time streaming without blocking."

---

### Q5: "How does authentication work between services?"

**Answer**:
> "I use **JWT (JSON Web Tokens)**:
> 1. User logs in via Streamlit → Django validates credentials → Returns JWT
> 2. Streamlit stores the token in session state
> 3. All API calls include the token in the Authorization header
> 4. FastAPI can optionally pass the token to Django for user-specific agent loading
> 
> For internal service communication (FastAPI → Django for agent config), I use `IsAuthenticatedOrReadOnly` so reading is permitted without auth."

---

### Q6: "What happens if Deepgram disconnects?"

**Answer**:
> "I implemented several safeguards:
> 1. The connection auto-closes on client disconnect
> 2. Error handlers log issues and clean up resources
> 3. The frontend can detect disconnection and prompt the user to reconnect
> 4. Previously I had KeepAlive messages, but removed them due to a race condition in the websockets library"

---

### Q7: "How would you scale this system?"

**Answer**:
> "For production scaling:
> 1. **Django** - Deploy behind Gunicorn/Nginx, use PostgreSQL instead of SQLite
> 2. **FastAPI** - Deploy multiple instances behind a load balancer
> 3. **Redis** - Add for session management and caching
> 4. **Kubernetes** - Containerize and orchestrate all services
> 5. **Deepgram** - They handle scaling on their end (cloud service)
> 6. **OpenRouter** - Aggregates multiple providers, handling scalability"

---

### Q8: "What's the system prompt for an agent?"

**Answer**:
> "The system prompt defines the agent's personality. For example:
> ```
> You are a sarcastic assistant who always responds with witty, slightly rude humor.
> Keep responses brief and punchy.
> ```
> This is stored in Django and injected into every LLM call. It's prepended to the conversation history before generating a response."

---

## 📁 Key Files to Know

| File | Purpose |
|------|---------|
| `backend_streaming/app/services/voice_processor.py` | Core voice processing logic |
| `backend_streaming/app/api/websocket.py` | WebSocket endpoint handler |
| `backend_core/agents/views.py` | Agent CRUD API |
| `backend_core/config/settings.py` | Django settings (JWT config) |
| `frontend_streamlit/pages/3_Voice_Chat.py` | Voice chat UI with audio streaming |

---

## 🎯 Technologies Summary

| Category | Technology | Why? |
|----------|------------|------|
| Backend API | Django REST Framework | Robust, built-in auth |
| Real-time | FastAPI + WebSockets | Async, high performance |
| AI Orchestration | LangGraph | Stateful workflows |
| LLM Provider | OpenRouter (Liquid + Qwen) | Cost-effective, diverse models |
| Speech-to-Text | Deepgram Nova-2 | Real-time streaming |
| Text-to-Speech | Deepgram Aura | Natural voices |
| Auth | SimpleJWT | Industry standard |
| Frontend | Streamlit | Rapid prototyping |

---

## ✅ Checklist Before Interview

- [ ] Can explain the 3-server architecture
- [ ] Understand LangGraph flow (Router → Responder)
- [ ] Know why we use two LLMs
- [ ] Explain JWT authentication flow  
- [ ] Describe the WebSocket audio streaming
- [ ] Know the key files and their purposes
- [ ] Can discuss scaling strategies

---

Good luck with your interview! 🚀
