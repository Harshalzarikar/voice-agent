import logging
import os
import sys

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    WorkerOptions,
    cli,
)
from livekit.plugins import deepgram, openai, silero

# Allow importing our custom kokoro plugin from the same directory
sys.path.insert(0, os.path.dirname(__file__))
from kokoro_tts_plugin import KokoroHindiTTS

# Load the .env file from the project root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

logger = logging.getLogger("voice-agent")

# Set the language mode: "hindi" or "english"
AGENT_LANGUAGE = os.environ.get("AGENT_LANGUAGE", "english").lower()


def build_agent() -> Agent:
    """Build the Agent with the correct language instructions."""
    if AGENT_LANGUAGE == "hindi":
        instructions = (
            "आप एक सहायक वॉइस असिस्टेंट हैं। "
            "आपको हमेशा हिंदी में जवाब देना है। "
            "अपने उत्तर संक्षिप्त और स्पष्ट रखें। "
            "इमोजी, स्टार, या मार्कडाउन का उपयोग न करें। "
            "स्वाभाविक और मित्रवत रहें।"
        )
    else:
        instructions = (
            "You are a helpful voice assistant. "
            "Keep your responses short and concise since you are speaking. "
            "Do not use emojis, asterisks, markdown, or special characters. "
            "Be friendly and natural."
        )

    class VoiceAgent(Agent):
        def __init__(self) -> None:
            super().__init__(instructions=instructions)

        async def on_enter(self) -> None:
            if AGENT_LANGUAGE == "hindi":
                self.session.generate_reply(
                    instructions="उपयोगकर्ता का गर्मजोशी से स्वागत करें और पूछें कि आप कैसे मदद कर सकते हैं।"
                )
            else:
                self.session.generate_reply(
                    instructions="Greet the user warmly and ask how you can help."
                )

    return VoiceAgent()


async def prewarm(proc: JobProcess) -> None:
    # Load VAD in advance to save time during job connection
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext) -> None:
    ctx.log_context_fields = {"room": ctx.room.name, "language": AGENT_LANGUAGE}
    logger.info(f"Starting agent in language mode: {AGENT_LANGUAGE}")

    if AGENT_LANGUAGE == "hindi":
        # Hindi mode: Deepgram STT (Hindi) + OpenRouter LLM + Kokoro Hindi TTS (Fal AI)
        session = AgentSession(
            stt=deepgram.STT(model="nova-3", language="hi"),
            llm=openai.LLM(
                model="meta-llama/llama-3.3-70b-instruct",
                base_url="https://openrouter.ai/api/v1",
                api_key=os.environ.get("OPENROUTER_API_KEY"),
            ),
            tts=KokoroHindiTTS(
                voice=os.environ.get("KOKORO_VOICE", "hf_alpha"),
                fal_key=os.environ.get("FAL_KEY"),
            ),
            vad=ctx.proc.userdata["vad"],
        )
    else:
        # English mode: Deepgram STT + OpenRouter LLM + Deepgram TTS
        session = AgentSession(
            stt=deepgram.STT(model="nova-3", language="en"),
            llm=openai.LLM(
                model="meta-llama/llama-3.3-70b-instruct",
                base_url="https://openrouter.ai/api/v1",
                api_key=os.environ.get("OPENROUTER_API_KEY"),
            ),
            tts=deepgram.TTS(model="aura-asteria-en"),
            vad=ctx.proc.userdata["vad"],
        )

    await session.start(
        agent=build_agent(),
        room=ctx.room,
    )


if __name__ == "__main__":
    # In production, we customize WorkerOptions for stability on limited-CPU environments.
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            prewarm_count=1,
            initialize_timeout=60,
            load_threshold=0.99,
        )
    )
