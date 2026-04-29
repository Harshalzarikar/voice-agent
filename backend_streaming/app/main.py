from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .core.config import settings
from .api import websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    import asyncio
    loop = asyncio.get_event_loop()

    # ── Pre-load Whisper (local openai-whisper) ──────────────────────────
    # Removed to save memory on startup. Whisper will lazy-load in VoiceProcessor
    # when the first user speaks.

    # ── Pre-connect Kokoro TTS (via HuggingFace Spaces) ──────────────────
    try:
        from gradio_client import Client as GradioClient
        print("[Startup] Connecting to Kokoro TTS HF Space …")
        def _connect_kokoro():
            return GradioClient("Pendrokar/Kokoro-TTS")
        app.state.kokoro_client = await loop.run_in_executor(None, _connect_kokoro)
        print("[Startup] Kokoro TTS connected ✓")
    except Exception as e:
        app.state.kokoro_client = None
        print(f"[Startup] Kokoro TTS pre-connect skipped: {e}")

    yield

    print("[Shutdown] Cleaning up …")


app = FastAPI(
    title="Voice Agent Streaming API",
    lifespan=lifespan,
    description="""
## Real-Time AI Voice Orchestration System

### Features
- **WebSocket Voice Chat**: `/ws/chat/{agent_id}`
- **STT**: Local OpenAI Whisper (no API cost)
- **TTS**: Kokoro TTS via HuggingFace Spaces
- **LangGraph Orchestration**: Intent classification + response generation

### Architecture
- **STT**: Local Whisper `base` model → fallback: Deepgram Nova-2
- **TTS**: Kokoro (HF Spaces) → fallback: Deepgram Aura
- **Router LLM**: Groq Llama-3.3-70b-versatile
- **Responder LLM**: Groq Llama-3.3-70b-versatile
- **Backup Router**: Groq Llama-3.1-8b-instant
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])


@app.get("/", tags=["Health"])
async def root():
    return {"message": "Voice Agent Streaming API is running", "status": "healthy"}


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "voice-agent-streaming",
        "version": "2.0.0",
    }


@app.get("/info", tags=["Info"])
async def get_info():
    kokoro_status = (
        "kokoro-hf-spaces (active)"
        if getattr(app.state, "kokoro_client", None)
        else "deepgram-aura (fallback)"
    )
    return {
        "stt": "local-whisper (active)",
        "tts": kokoro_status,
        "kokoro_voices": [
            {"id": "af_heart",   "name": "Heart",   "gender": "Female", "accent": "American"},
            {"id": "af_bella",   "name": "Bella",   "gender": "Female", "accent": "American"},
            {"id": "af_nicole",  "name": "Nicole",  "gender": "Female", "accent": "American"},
            {"id": "af_sarah",   "name": "Sarah",   "gender": "Female", "accent": "American"},
            {"id": "am_adam",    "name": "Adam",    "gender": "Male",   "accent": "American"},
            {"id": "am_michael", "name": "Michael", "gender": "Male",   "accent": "American"},
            {"id": "bf_emma",    "name": "Emma",    "gender": "Female", "accent": "British"},
            {"id": "bf_isabella","name": "Isabella","gender": "Female", "accent": "British"},
            {"id": "bm_george",  "name": "George",  "gender": "Male",   "accent": "British"},
            {"id": "bm_lewis",   "name": "Lewis",   "gender": "Male",   "accent": "British"},
        ],
        "deepgram_voices_fallback": [
            {"id": "aura-asteria-en", "name": "Asteria", "gender": "Female"},
            {"id": "aura-luna-en",    "name": "Luna",    "gender": "Female"},
            {"id": "aura-orion-en",   "name": "Orion",   "gender": "Male"},
        ],
        "websocket_endpoint": "/ws/chat/{agent_id}",
        "orchestration": {
            "router_model":    "groq/llama-3.3-70b-versatile",
            "responder_model": "groq/llama-3.3-70b-versatile",
            "backup_router":   "groq/llama-3.1-8b-instant",
        },
    }