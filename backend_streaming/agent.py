import logging
import os

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    cli,
)
from livekit.plugins import deepgram, openai, silero

# Load the .env file from the project root
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

logger = logging.getLogger("voice-agent")


class VoiceAgent(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a helpful, highly conversational voice assistant. "
                "Keep your responses short and concise since you are speaking. "
                "Do not use emojis, asterisks, markdown, or special characters. "
                "Be friendly and natural."
            ),
        )

    async def on_enter(self) -> None:
        self.session.generate_reply(
            instructions="Greet the user warmly and ask how you can help."
        )


server = AgentServer()


def prewarm(proc: JobProcess) -> None:
    proc.userdata["vad"] = silero.VAD.load()


server.setup_fnc = prewarm


@server.rtc_session()
async def entrypoint(ctx: JobContext) -> None:
    ctx.log_context_fields = {"room": ctx.room.name}

    session = AgentSession(
        # Direct to Deepgram API (uses DEEPGRAM_API_KEY from env)
        stt=deepgram.STT(model="nova-3", language="en"),
        # Use OpenRouter for LLM (fixes Groq 403 error)
        llm=openai.LLM(
            model="meta-llama/llama-3.3-70b-instruct",
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ.get("OPENROUTER_API_KEY"),
        ),
        # Use Deepgram for TTS (fixes OpenAI 429 Insufficient Quota)
        tts=deepgram.TTS(model="aura-asteria-en"),
        vad=ctx.proc.userdata["vad"],
    )

    await session.start(
        agent=VoiceAgent(),
        room=ctx.room,
    )


if __name__ == "__main__":
    cli.run_app(server)
