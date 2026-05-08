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

sys.path.insert(0, os.path.dirname(__file__))
from kokoro_tts_plugin import KokoroHindiTTS

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

logger = logging.getLogger("voice-agent")

AGENT_LANGUAGE = os.environ.get("AGENT_LANGUAGE", "english").lower()


def build_agent() -> Agent:
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
    """
    Pre-initialize ALL heavy components here so the entrypoint
    can start instantly without waiting for client setup.
    """
    logger.info("Prewarming components...")

    # VAD (loads local model weights)
    proc.userdata["vad"] = silero.VAD.load()

    # STT — create client once, reuse per job
    if AGENT_LANGUAGE == "hindi":
        proc.userdata["stt"] = deepgram.STT(model="nova-3", language="hi")
    else:
        proc.userdata["stt"] = deepgram.STT(model="nova-3", language="en")

    # LLM — shared client, thread-safe
    proc.userdata["llm"] = openai.LLM(
        model="meta-llama/llama-3.3-70b-instruct",
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ.get("OPENROUTER_API_KEY"),
    )

    # TTS — most expensive to init, especially Kokoro/Fal
    if AGENT_LANGUAGE == "hindi":
        proc.userdata["tts"] = KokoroHindiTTS(
            voice=os.environ.get("KOKORO_VOICE", "hf_alpha"),
            fal_key=os.environ.get("FAL_KEY"),
        )
    else:
        proc.userdata["tts"] = deepgram.TTS(model="aura-asteria-en")

    logger.info("Prewarm complete.")


async def entrypoint(ctx: JobContext) -> None:
    ctx.log_context_fields = {"room": ctx.room.name, "language": AGENT_LANGUAGE}
    logger.info(f"Starting agent in language mode: {AGENT_LANGUAGE}")

    # Reuse prewarmed clients — no cold-start delay
    session = AgentSession(
        stt=ctx.proc.userdata["stt"],
        llm=ctx.proc.userdata["llm"],
        tts=ctx.proc.userdata["tts"],
        vad=ctx.proc.userdata["vad"],
    )

    await session.start(
        agent=build_agent(),
        room=ctx.room,
    )


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            prewarm_count=1,
            initialize_timeout=60,
            load_threshold=0.99,
        )
    )