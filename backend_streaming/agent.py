import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    JobContext,
    JobProcess,
    RoomInputOptions,
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


# ─── prewarm: MUST be a regular (sync) function ───────────────────────────────
# livekit-agents 1.5.x calls this synchronously in the subprocess.
# Pre-instantiate all plugins so they are ready the moment a user connects.
def prewarm(proc: JobProcess) -> None:
    proc.userdata["vad"] = silero.VAD.load()

    proc.userdata["llm"] = openai.LLM(
        model="llama-3.3-70b-versatile",
        base_url="https://api.groq.com/openai/v1",
        api_key=os.environ.get("GROQ_API_KEY"),
    )

    if AGENT_LANGUAGE == "hindi":
        proc.userdata["stt"] = deepgram.STT(
            model="nova-3",          # nova-3 has better Hindi support than nova-2
            language="hi",
            interim_results=True,    # keeps WebSocket alive, enables fast partial results
            smart_format=True,       # better punctuation and formatting
            endpointing_ms=200,      # 200ms of silence = end of utterance (conversational)
            filler_words=False,      # don't transcribe "um", "uh" etc.
            vad_events=True,         # VAD events for better interruption handling
            no_delay=True,           # send audio immediately, no buffering
        )
        proc.userdata["tts"] = KokoroHindiTTS(
            voice=os.environ.get("KOKORO_VOICE", "hf_alpha"),
            fal_key=os.environ.get("FAL_KEY"),
        )
    else:
        proc.userdata["stt"] = deepgram.STT(
            model="nova-3",
            language="en-US",
            interim_results=True,
            smart_format=True,
            endpointing_ms=200,
            filler_words=False,
            vad_events=True,
            no_delay=True,
        )
        proc.userdata["tts"] = deepgram.TTS(model="aura-asteria-en")


# ─── entrypoint: async, runs per job ──────────────────────────────────────────
async def entrypoint(ctx: JobContext) -> None:
    ctx.log_context_fields = {"room": ctx.room.name, "language": AGENT_LANGUAGE}
    logger.info(f"Starting agent in language mode: {AGENT_LANGUAGE}")

    # ── CRITICAL: connect to the LiveKit room FIRST ────────────────────────────
    # Without this, the room connection never opens and the job times out
    # with "room connection was not established within 10 seconds".
    await ctx.connect()

    tts_plugin = ctx.proc.userdata["tts"]

    # Kick off fal.ai warmup concurrently — it runs in the background while
    # the agent greets the user, so it does NOT add to perceived latency.
    # The _warmed_up flag ensures this only does real work on the first call
    # per process — subsequent jobs reuse the already-warm connection.
    if AGENT_LANGUAGE == "hindi" and isinstance(tts_plugin, KokoroHindiTTS):
        asyncio.ensure_future(tts_plugin.warmup_endpoint())

    session = AgentSession(
        stt=ctx.proc.userdata["stt"],
        llm=ctx.proc.userdata["llm"],
        tts=tts_plugin,
        vad=ctx.proc.userdata["vad"],
    )

    await session.start(
        agent=build_agent(),
        room=ctx.room,
        room_input_options=RoomInputOptions(
            # Keep session alive even if the user briefly disconnects
            close_on_disconnect=False,
        ),
    )


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            prewarm_fnc=prewarm,
            num_idle_processes=1,
            initialize_process_timeout=60.0,
            load_threshold=0.99,
        )
    )