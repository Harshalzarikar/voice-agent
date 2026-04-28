import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    KOKORO_VOICE=os.getenv("KOKORO_VOICE") or "af_heart"
    CORS_ORIGINS = ["*"]

settings = Settings()
