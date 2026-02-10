from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .core.config import settings
from .api import websocket

app = FastAPI(
    title="Voice Agent Streaming API",
    description="""
## Real-Time AI Voice Orchestration System

This API provides real-time voice streaming capabilities for AI agents.

### Features
- **WebSocket Voice Chat**: Connect to `/ws/chat/{agent_id}` for real-time voice interaction
- **LangGraph Orchestration**: Intelligent routing and response generation
- **Deepgram Integration**: Low-latency STT and TTS

### Architecture
- **Orchestration Layer**: Qwen-32B for intent classification
- **Conversational Layer**: Llama-3.1-8b for fast responses
- **Voice Processing**: Deepgram Nova-2 (STT) + Aura (TTS)
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include WebSocket router
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])


@app.get("/", tags=["Health"])
async def root():
    """
    Root endpoint - confirms the API is running.
    """
    return {"message": "Voice Agent Streaming API is running", "status": "healthy"}


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    """
    return {
        "status": "healthy",
        "service": "voice-agent-streaming",
        "version": "1.0.0"
    }


@app.get("/info", tags=["Info"])
async def get_info():
    """
    Get information about the available voice models and configuration.
    """
    return {
        "available_voices": [
            {"id": "aura-asteria-en", "name": "Asteria", "gender": "Female", "accent": "American"},
            {"id": "aura-luna-en", "name": "Luna", "gender": "Female", "accent": "American"},
            {"id": "aura-stella-en", "name": "Stella", "gender": "Female", "accent": "American"},
            {"id": "aura-orion-en", "name": "Orion", "gender": "Male", "accent": "American"},
            {"id": "aura-arcas-en", "name": "Arcas", "gender": "Male", "accent": "American"},
        ],
        "websocket_endpoint": "/ws/chat/{agent_id}",
        "stt_model": "deepgram-nova-2",
        "tts_model": "deepgram-aura",
        "orchestration": {
            "router_model": "qwen/qwen3-4b:free",
            "responder_model": "liquid/lfm-2.5-1.2b-instruct:free"
        }
    }

