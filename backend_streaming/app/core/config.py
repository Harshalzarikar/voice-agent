import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY")
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
    # Valid Hindi voices: hf_alpha, hf_beta, hm_omega, hm_psi
    # af_heart is an English-only voice and will cause 422 on the Hindi endpoint
    KOKORO_VOICE=os.getenv("KOKORO_VOICE") or "hf_alpha"
    HF_TOKEN = os.getenv("HF_TOKEN")
    FAL_KEY = os.getenv("FAL_KEY")
    CORS_ORIGINS = ["*"]

settings = Settings()
