import asyncio
import json
import io
import wave
import time
import tempfile
import os
try:
    from deepgram import AsyncDeepgramClient
    from deepgram.core.events import EventType
    from deepgram.extensions.types.sockets import (
        ListenV1ControlMessage,
        SpeakV1TextMessage,
        SpeakV1ControlMessage,
        ListenV1SpeechStartedEvent,
    )
except ImportError:
    AsyncDeepgramClient = None
    EventType = None
    class ListenV1ControlMessage: pass
    class SpeakV1TextMessage: pass
    class SpeakV1ControlMessage: pass
    class ListenV1SpeechStartedEvent: pass
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List
import httpx
import operator
import traceback
from ..core.config import settings

# ─────────────────────────────────────────────
#  Optional imports for primary providers
# ─────────────────────────────────────────────
try:
    from gradio_client import Client as GradioClient
    import soundfile as sf
    KOKORO_AVAILABLE = True
    print("[TTS] gradio_client + soundfile found (Kokoro TTS via HF Spaces)")
    SVARA_AVAILABLE = True
except ImportError:
    KOKORO_AVAILABLE = False
    SVARA_AVAILABLE = False
    print("[TTS] gradio_client not installed – will fall back to Deepgram TTS")

try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
    print("[STT] Local faster-whisper found")
except ImportError:
    WHISPER_AVAILABLE = False
    print("[STT] faster-whisper not installed – will fall back to Deepgram STT")


class AgentState(TypedDict):
    messages: Annotated[List[HumanMessage | AIMessage | SystemMessage], operator.add]
    intent: str


# ─────────────────────────────────────────────
#  Local Whisper STT helper
# ─────────────────────────────────────────────
_GLOBAL_WHISPER_MODEL = None

class WhisperSTT:
    SAMPLE_RATE           = 16_000
    CHANNELS              = 1
    SAMPLE_WIDTH          = 2
    SILENCE_RMS_THRESHOLD = 300
    SILENCE_DURATION_S    = 0.6
    MIN_SPEECH_DURATION_S = 0.3
    MODEL_SIZE            = "tiny.en"

    def __init__(self, language: str = "en"):
        self._language              = language
        self._buffer: bytearray     = bytearray()
        self._speech_started        = False
        self._last_speech_ts: float = 0.0
        self._silence_start_ts: float | None = None
        self.on_transcript          = None
        self.on_speech_started      = None
        self._lock                  = asyncio.Lock()
        self._running               = True
        self._monitor_task: asyncio.Task | None = None

    def _load_model(self):
        global _GLOBAL_WHISPER_MODEL
        if _GLOBAL_WHISPER_MODEL is None:
            print(f"[Whisper] Loading '{self.MODEL_SIZE}' model into global memory (int8, 1 thread) …")
            _GLOBAL_WHISPER_MODEL = WhisperModel(
                self.MODEL_SIZE, 
                device="cpu", 
                compute_type="int8", 
                cpu_threads=1, 
                num_workers=1
            )
            print("[Whisper] Global model ready")
        return _GLOBAL_WHISPER_MODEL

    def start(self):
        self._monitor_task = asyncio.create_task(self._silence_monitor())

    def stop(self):
        self._running = False
        if self._monitor_task:
            self._monitor_task.cancel()

    @staticmethod
    def _rms(chunk: bytes) -> float:
        import struct, math
        # Ensure even length for 16-bit unpacking
        usable = len(chunk) - (len(chunk) % 2)
        if usable < 2:
            return 0.0
        count = usable // 2
        shorts = struct.unpack(f"{count}h", chunk[:usable])
        return math.sqrt(sum(s * s for s in shorts) / count)

    async def feed(self, chunk: bytes):
        if not chunk or len(chunk) < 2:
            return
        # Truncate to even byte boundary (16-bit PCM)
        usable_len = len(chunk) - (len(chunk) % 2)
        chunk = chunk[:usable_len]
        try:
            async with self._lock:
                rms = self._rms(chunk)
                # Debug: log every 50th chunk to see audio levels
                if not hasattr(self, '_chunk_count'):
                    self._chunk_count = 0
                self._chunk_count += 1
                if self._chunk_count % 50 == 1:
                    print(f"[Whisper] chunk #{self._chunk_count}: {len(chunk)} bytes, RMS={rms:.0f}, threshold={self.SILENCE_RMS_THRESHOLD}, speech={self._speech_started}")
                now = time.monotonic()
                if rms > self.SILENCE_RMS_THRESHOLD:
                    if not self._speech_started:
                        self._speech_started   = True
                        self._silence_start_ts = None
                        if self.on_speech_started:
                            asyncio.create_task(self.on_speech_started())
                    self._last_speech_ts   = now
                    self._silence_start_ts = None
                    self._buffer.extend(chunk)
                else:
                    if self._speech_started:
                        self._buffer.extend(chunk)
                        if self._silence_start_ts is None:
                            self._silence_start_ts = now
        except Exception as e:
            print(f"[Whisper] feed error: {e}")

    async def _silence_monitor(self):
        while self._running:
            await asyncio.sleep(0.1)
            async with self._lock:
                if (
                    self._speech_started
                    and self._silence_start_ts is not None
                    and (time.monotonic() - self._silence_start_ts) >= self.SILENCE_DURATION_S
                ):
                    buf_copy = bytes(self._buffer)
                    self._buffer.clear()
                    self._speech_started   = False
                    self._silence_start_ts = None
                    asyncio.create_task(self._transcribe(buf_copy))

    async def _transcribe(self, pcm: bytes):
        min_bytes = int(self.SAMPLE_RATE * self.SAMPLE_WIDTH * self.MIN_SPEECH_DURATION_S)
        if len(pcm) < min_bytes:
            return
        loop = asyncio.get_event_loop()
        try:
            text = await loop.run_in_executor(None, self._transcribe_sync, pcm)
            if text and self.on_transcript:
                await self.on_transcript(text)
        except Exception as e:
            print(f"[Whisper STT] Transcription error: {e}")

    def _transcribe_sync(self, pcm: bytes) -> str:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_path = tmp.name
            with wave.open(tmp_path, "wb") as wf:
                wf.setnchannels(self.CHANNELS)
                wf.setsampwidth(self.SAMPLE_WIDTH)
                wf.setframerate(self.SAMPLE_RATE)
                wf.writeframes(pcm)
        try:
            # ── Optimal 0MB RAM Fix: Offload STT to Groq API ──
            groq_api_key = getattr(settings, "GROQ_API_KEY", None)
            if groq_api_key:
                import requests
                
                # Fetch available Whisper models dynamically (cache it on the class to save time)
                if not getattr(self, "_groq_model", None):
                    print("[Whisper] Fetching available Groq Whisper models...")
                    resp = requests.get(
                        "https://api.groq.com/openai/v1/models",
                        headers={"Authorization": f"Bearer {groq_api_key}"}
                    )
                    models = [m["id"] for m in resp.json().get("data", []) if "whisper" in m["id"]]
                    print(f"[Whisper] Available Groq Models: {models}")
                    
                    if "whisper-large-v3-turbo" in models:
                        self._groq_model = "whisper-large-v3-turbo"
                    elif "whisper-large-v3" in models:
                        self._groq_model = "whisper-large-v3"
                    elif len(models) > 0:
                        self._groq_model = models[0]
                    else:
                        raise ValueError("No Whisper models available on Groq!")

                print(f"[Whisper] Calling Groq Whisper API ({self._groq_model})...")
                with open(tmp_path, "rb") as f:
                    response = requests.post(
                        "https://api.groq.com/openai/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {groq_api_key}"},
                        data={"model": self._groq_model},
                        files={"file": ("audio.wav", f, "audio/wav")},
                        timeout=15.0
                    )
                if response.status_code != 200:
                    print(f"[Whisper STT] Groq API Error: {response.status_code} - {response.text}")
                response.raise_for_status()
                text = response.json().get("text", "").strip()
                return text
            else:
                # Fallback to local memory model
                model = self._load_model()
                segments, _ = model.transcribe(tmp_path, language=self._language, beam_size=1)
                text = "".join(segment.text for segment in segments).strip()
                return text
        except Exception as e:
            print(f"[Whisper STT] Transcription error: {e}")
            return ""
        finally:
            os.unlink(tmp_path)


# ─────────────────────────────────────────────
#  Kokoro TTS helper  (via HuggingFace Spaces API)
# ─────────────────────────────────────────────
class KokoroTTS:
    """
    Calls the hosted Kokoro TTS on HuggingFace Spaces via gradio_client.
    Returns raw PCM bytes (16-bit, mono) at the native sample rate.
    """

    HF_SPACE = "Pendrokar/Kokoro-TTS"

    def __init__(self, voice: str = "af_heart", speed: float = 1.0):
        self._voice  = voice
        self._speed  = speed
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            print(f"[TTS] Connecting to Kokoro HF Space ({self.HF_SPACE}) …")
            hf_token = getattr(settings, "HF_TOKEN", None)
            kwargs = {}
            if hf_token: kwargs["token"] = hf_token
            self._client = GradioClient(self.HF_SPACE, **kwargs)
            print("[TTS] Kokoro HF Space connected")

    async def synthesize(self, text: str) -> bytes:
        """Returns raw PCM bytes (16-bit, mono)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._synthesize_sync, text)

    def _synthesize_sync(self, text: str) -> bytes:
        import numpy as np
        self._ensure_client()
        # Call the HF Space — returns a path to a temp audio file
        temp_filepath = self._client.predict(
            text=text,
            voice=self._voice,
            speed=self._speed,
            api_name="/predict",
        )
        # Read audio into numpy array
        audio_data, sample_rate = sf.read(temp_filepath)
        # Convert float audio to 16-bit PCM
        pcm16 = (audio_data * 32767).clip(-32768, 32767).astype(np.int16)
        return pcm16.tobytes()

# ─────────────────────────────────────────────
#  Svara TTS helper  (via HuggingFace Spaces API for Hindi)
# ─────────────────────────────────────────────
class SvaraTTS:
    """
    Calls the hosted Svara TTS on HuggingFace Spaces via gradio_client.
    Returns raw PCM bytes (16-bit, mono) at the native sample rate (24kHz).
    """
    HF_SPACE = "kenpath/svara-tts"

    def __init__(self, language: str = "Hindi (हिन्दी)", gender: str = "Female"):
        self._language = language
        self._gender = gender
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            print(f"[TTS] Connecting to Svara HF Space ({self.HF_SPACE}) …")
            hf_token = getattr(settings, "HF_TOKEN", None)
            kwargs = {}
            if hf_token: kwargs["token"] = hf_token
            self._client = GradioClient(self.HF_SPACE, **kwargs)
            print("[TTS] Svara HF Space connected")

    async def synthesize(self, text: str) -> bytes:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._synthesize_sync, text)

    def _synthesize_sync(self, text: str) -> bytes:
        import numpy as np
        self._ensure_client()
        # Call the HF Space predict function
        # signature: generate_speech(language, gender, text, temperature, top_p, repetition_penalty, max_new_tokens)
        try:
            result = self._client.predict(
                language=self._language,
                gender=self._gender,
                text=text,
                temperature=0.7,
                top_p=0.8,
                repetition_penalty=1.1,
                max_new_tokens=2048,
                api_name="/generate_speech"
            )
        except Exception as e:
            print(f"[SvaraTTS] Error with named parameters, trying positional: {e}")
            result = self._client.predict(
                self._language,
                self._gender,
                text,
                0.7, # temperature
                0.8, # top_p
                1.1, # repetition_penalty
                2048, # max_new_tokens
                api_name="/generate_speech"
            )
            
        # The result is typically a tuple (sample_rate, file_path) from Gradio Audio output
        if isinstance(result, tuple) and len(result) == 2:
            temp_filepath = result[1]
        elif isinstance(result, str):
            temp_filepath = result
        else:
            print(f"[SvaraTTS] Unexpected return format: {type(result)}")
            return b""
            
        audio_data, sample_rate = sf.read(temp_filepath)
        pcm16 = (audio_data * 32767).clip(-32768, 32767).astype(np.int16)
        return pcm16.tobytes()



# ─────────────────────────────────────────────
#  VoiceProcessor
# ─────────────────────────────────────────────
class VoiceProcessor:
    def __init__(
        self,
        agent_id: str,
        websocket,
        system_prompt: str,
        voice_id: str,
        token: str = None,
        session_id: str = None,
        language: str = "English"
    ):
        self.agent_id      = agent_id
        self.websocket     = websocket
        self.system_prompt = system_prompt
        self.voice_id      = voice_id
        self.auth_token    = token
        self.session_id    = session_id
        self.language      = language

        # ── Deepgram (fallback) ──────────────────────────────────────────
        if AsyncDeepgramClient:
            self.deepgram = AsyncDeepgramClient(api_key=settings.DEEPGRAM_API_KEY)
        else:
            self.deepgram = None

        # ── Primary STT: local Whisper ───────────────────────────────────
        if WHISPER_AVAILABLE:
            print("[STT] Primary: local openai-whisper")
            self._use_whisper = True
            self._whisper = WhisperSTT(language="en")
        else:
            print("[STT] Falling back to Deepgram STT")
            self._use_whisper = False
            self._whisper = None

        # ── Primary TTS: Kokoro/Svara ─────────────────
        if self.language.lower() == "hindi" and SVARA_AVAILABLE:
            print("[TTS] Primary: Svara HF Spaces for Hindi")
            self._use_kokoro = False
            self._kokoro = None
            self._use_svara = True
            self._svara = SvaraTTS(language="Hindi (हिन्दी)")
        elif KOKORO_AVAILABLE:
            kokoro_voice = getattr(settings, "KOKORO_VOICE", "af_heart")
            print(f"[TTS] Primary: Kokoro HF Spaces (voice={kokoro_voice})")
            self._use_kokoro = True
            self._kokoro = KokoroTTS(voice=kokoro_voice)
            self._use_svara = False
            self._svara = None
        else:
            print("[TTS] Falling back to Deepgram TTS")
            self._use_kokoro = False
            self._kokoro = None
            self._use_svara = False
            self._svara = None

        # ── LLMs (all Groq for speed + reliability) ────────────────────────
        self.router_llm_primary = ChatGroq(
            temperature=0,
            model="llama-3.3-70b-versatile",
            api_key=settings.GROQ_API_KEY,
        )
        self.router_llm_backup = ChatGroq(
            temperature=0,
            model="llama-3.1-8b-instant",
            api_key=settings.GROQ_API_KEY,
        )
        self.llm = ChatGroq(
            temperature=0.7,
            model="llama-3.3-70b-versatile",
            api_key=settings.GROQ_API_KEY,
            max_tokens=150,
        )

        # ── LangGraph ────────────────────────────────────────────────────
        self.graph = self._build_graph()

        # ── Deepgram connection handles (fallback) ───────────────────────
        self.dg_connection     = None
        self.dg_connection_ctx = None
        self.dg_tts_connection = None
        self.dg_tts_context    = None

        self.stt_lock = asyncio.Lock()
        self.tts_lock = asyncio.Lock()
        self.is_running = True
        self.conversation_history: list = []

    # ─────────────────────────────────────────
    #  start / stop
    # ─────────────────────────────────────────
    async def start(self):
        try:
            await self._start_stt()
            await self._start_tts()
            asyncio.create_task(self._keep_alive())
            print("[VoiceProcessor] Started successfully")
            return True
        except Exception as e:
            print(f"[VoiceProcessor] Error during start: {e}")
            traceback.print_exc()
            return False

    async def _start_stt(self):
        if self._use_whisper:
            async def _on_transcript(text: str):
                print(f"[Whisper] transcript: {text}")
                await self._stop_tts()
                await self.process_text(text)

            async def _on_speech_started():
                print("[Whisper] speech started")
                await self._stop_tts()

            self._whisper.on_transcript     = _on_transcript
            self._whisper.on_speech_started = _on_speech_started
            self._whisper.start()
            print("[STT] Whisper listener started")
        else:
            await self._start_deepgram_stt()

    async def _start_deepgram_stt(self):
        print("[STT] Connecting to Deepgram STT (fallback)...")
        self.dg_connection_ctx = self.deepgram.listen.v1.connect(
            model="nova-2",
            language="en-IN",
            smart_format="true",
            endpointing=500,
        )
        self.dg_connection = await self.dg_connection_ctx.__aenter__()
        print("[STT] Deepgram STT connected")

        def on_stt_message(result, **kwargs):
            try:
                if isinstance(result, ListenV1SpeechStartedEvent) or (
                    hasattr(result, "type") and result.type == "SpeechStarted"
                ):
                    print("[Deepgram STT] SpeechStarted")
                    asyncio.create_task(self._stop_tts())
                    return
                if hasattr(result, "channel"):
                    alts = result.channel.alternatives
                    if alts:
                        sentence = alts[0].transcript
                        if result.speech_final or (len(sentence.strip()) > 0 and result.is_final):
                            if sentence.strip():
                                print(f"[Deepgram STT] Final: {sentence}")
                                asyncio.create_task(self._stop_tts())
                                asyncio.create_task(self.process_text(sentence))
            except Exception as e:
                print(f"[Deepgram STT] Error: {e}")

        self.dg_connection.on(EventType.MESSAGE, on_stt_message)
        self.dg_connection.on(EventType.ERROR, lambda e: print(f"[Deepgram STT] Error event: {e}"))
        asyncio.create_task(self.dg_connection.start_listening())

    async def _start_tts(self):
        if not self._use_kokoro:
            await self._start_deepgram_tts()
        # kokoro-onnx is stateless — no persistent connection needed

    async def _start_deepgram_tts(self):
        print(f"[TTS] Connecting to Deepgram TTS (fallback, voice={self.voice_id})...")
        self.dg_tts_context = self.deepgram.speak.v1.connect(
            model=self.voice_id,
            encoding="linear16",
            sample_rate=24000,
        )
        self.dg_tts_connection = await self.dg_tts_context.__aenter__()
        print("[TTS] Deepgram TTS connected")

        async def on_tts_message(result, **kwargs):
            if isinstance(result, (bytes, bytearray)):
                await self.websocket.send_bytes(result)

        self.dg_tts_connection.on(EventType.MESSAGE, on_tts_message)
        self.dg_tts_connection.on(EventType.ERROR, lambda e: print(f"[Deepgram TTS] Error: {e}"))
        asyncio.create_task(self.dg_tts_connection.start_listening())

    async def stop(self):
        self.is_running = False
        if self._whisper:
            self._whisper.stop()
        if self.dg_connection_ctx:
            await self.dg_connection_ctx.__aexit__(None, None, None)
        if self.dg_tts_context:
            await self.dg_tts_context.__aexit__(None, None, None)

    # ─────────────────────────────────────────
    #  Audio ingestion
    # ─────────────────────────────────────────
    async def process_audio(self, data: bytes):
        if self._use_whisper and self._whisper:
            await self._whisper.feed(data)
        elif self.dg_connection:
            async with self.stt_lock:
                await self.dg_connection.send_media(data)

    # ─────────────────────────────────────────
    #  TTS
    # ─────────────────────────────────────────
    async def _stop_tts(self):
        try:
            if self.dg_tts_connection:
                async with self.tts_lock:
                    await self.dg_tts_connection.send_control(SpeakV1ControlMessage(type="Clear"))
            if self.websocket:
                await self.websocket.send_text(json.dumps({"type": "control", "action": "stop_audio"}))
        except Exception as e:
            print(f"[TTS] Error stopping: {e}")

    async def generate_speech(self, text: str):
        clean_text = self._sanitize_for_speech(text)

        # ── Primary: Svara/Kokoro (HF Spaces) ──────────────────────────────────
        if getattr(self, "_use_svara", False) and self._svara:
            try:
                print("[TTS] Synthesizing with Svara (Hindi)...")
                pcm = await self._svara.synthesize(clean_text)
                if pcm:
                    chunk_size = 4096
                    for i in range(0, len(pcm), chunk_size):
                        await self.websocket.send_bytes(pcm[i : i + chunk_size])
                    print(f"[TTS] Svara sent {len(pcm)} bytes")
                    return
                else:
                    print("[TTS] Svara returned empty – falling back to Deepgram")
            except Exception as e:
                print(f"[TTS] Svara error: {e} – falling back to Deepgram")
        elif self._use_kokoro and self._kokoro:
            try:
                print("[TTS] Synthesizing with Kokoro...")
                pcm = await self._kokoro.synthesize(clean_text)
                if pcm:
                    chunk_size = 4096
                    for i in range(0, len(pcm), chunk_size):
                        await self.websocket.send_bytes(pcm[i : i + chunk_size])
                    print(f"[TTS] Kokoro sent {len(pcm)} bytes")
                    return
                else:
                    print("[TTS] Kokoro returned empty – falling back to Deepgram")
            except Exception as e:
                print(f"[TTS] Kokoro error: {e} – falling back to Deepgram")

        # ── Fallback: Deepgram TTS ───────────────────────────────────────
        if self.dg_tts_connection:
            safe_text = clean_text[:1800]
            if len(clean_text) > 1800:
                print(f"[TTS] Truncating to 1800 chars (was {len(clean_text)})")
            async with self.tts_lock:
                await self.dg_tts_connection.send_text(
                    SpeakV1TextMessage(type="Speak", text=safe_text)
                )
                await self.dg_tts_connection.send_control(SpeakV1ControlMessage(type="Flush"))
        else:
            print("[TTS] Deepgram TTS not connected – attempting lazy connect")
            try:
                await self._start_deepgram_tts()
                await self.generate_speech(text)
            except Exception as e:
                print(f"[TTS] Deepgram fallback failed: {e}")

    # ─────────────────────────────────────────
    #  LangGraph
    # ─────────────────────────────────────────
    def _build_graph(self):
        workflow = StateGraph(AgentState)

        def router_node(state):
            last_message = state["messages"][-1].content
            print(f"[Router] Analyzing: {last_message}")
            system_msg = SystemMessage(content="""
You are a Router. Analyze the user's input and classify the intent.
Return ONLY one of the following JSON strings:
{"intent": "end_conversation"}
{"intent": "general_chat"}

Rules:
- "end_conversation": If user says bye, stop, exit, quit.
- "general_chat": For everything else.
Do not output thinking or markdown. Just the JSON.
""")
            try:
                try:
                    response = self.router_llm_primary.invoke(
                        [system_msg, HumanMessage(content=last_message)]
                    )
                except Exception as e:
                    print(f"[Router] Primary failed: {e}. Switching to Backup...")
                    response = self.router_llm_backup.invoke(
                        [system_msg, HumanMessage(content=last_message)]
                    )

                content = response.content.strip()
                if "</think>" in content:
                    content = content.split("</think>")[-1].strip()
                try:
                    data = json.loads(content)
                    return {"intent": data.get("intent", "general_chat")}
                except Exception:
                    if "end_conversation" in content:
                        return {"intent": "end_conversation"}
                    return {"intent": "general_chat"}
            except Exception as e:
                print(f"[Router] Error: {e}, using regex fallback")
                import re
                if re.search(r"\b(bye|goodbye|stop|exit|quit)\b", last_message.lower()):
                    return {"intent": "end_conversation"}
                return {"intent": "general_chat"}

        async def responder_node(state):
            history_messages = self.conversation_history[-10:]
            short_instruction = (
                "\n\nIMPORTANT: Keep responses SHORT and conversational (1-2 sentences max). "
                "This is a voice conversation. "
            )
            
            if self.language.lower() == "hindi":
                short_instruction += (
                    "CRITICAL: The user is speaking Hindi. You MUST reply in conversational Hindi (written in Devanagari script, e.g. 'आप कैसे हैं?'). "
                    "Do NOT use English or Hinglish for Hindi responses. You may add emotional tags at the end like <happy> or <sad>."
                )
            else:
                short_instruction += (
                    "CRITICAL: If the user speaks to you in Hindi, you must understand them, "
                    "but you MUST reply in 'Hinglish' (Hindi language written in English alphabet characters, e.g., 'Aap kaise ho?'). "
                    "Do NOT use Devanagari script because the default Text-to-Speech engine cannot read it."
                )
            system_msg = SystemMessage(content=self.system_prompt + short_instruction)
            full_messages = [system_msg] + history_messages + state["messages"]
            print(f"[Responder] Generating with {len(history_messages)} history msgs")
            response = await self.llm.ainvoke(full_messages)
            return {"messages": [response]}

        workflow.add_node("router", router_node)
        workflow.add_node("responder", responder_node)

        async def route_decision(state):
            if state["intent"] == "end_conversation":
                if self.websocket:
                    await self.websocket.send_text(
                        json.dumps({"type": "control", "action": "stop_audio"})
                    )
                return END
            return "responder"

        workflow.set_entry_point("router")
        workflow.add_conditional_edges(
            "router", route_decision, {END: END, "responder": "responder"}
        )
        workflow.add_edge("responder", END)
        return workflow.compile()

    # ─────────────────────────────────────────
    #  process_text
    # ─────────────────────────────────────────
    async def process_text(self, text: str):
        try:
            print(f"[process_text] {text}")
            await self.websocket.send_text(
                json.dumps({"type": "text", "role": "user", "content": text})
            )
            self.conversation_history.append(HumanMessage(content=text))
            asyncio.create_task(self.save_message("user", text))

            if self.session_id and len(self.conversation_history) <= 1:
                asyncio.create_task(self.generate_session_title(text))

            inputs = {"messages": [HumanMessage(content=text)], "intent": ""}
            result = await self.graph.ainvoke(inputs)

            messages = result["messages"]
            if not messages or isinstance(messages[-1], HumanMessage):
                response_text = "Goodbye."
            else:
                response_text = messages[-1].content

            self.conversation_history.append(AIMessage(content=response_text))
            asyncio.create_task(self.save_message("assistant", response_text))
            print(f"[process_text] Response: {response_text}")

            await self.websocket.send_text(
                json.dumps({"type": "text", "role": "assistant", "content": response_text})
            )
            await self.generate_speech(response_text)

        except Exception as e:
            print(f"[process_text] Error: {e}")
            traceback.print_exc()

    # ─────────────────────────────────────────
    #  Utilities
    # ─────────────────────────────────────────
    def _sanitize_for_speech(self, text: str) -> str:
        import re
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\*(.+?)\*",     r"\1", text)
        text = re.sub(r"__(.+?)__",     r"\1", text)
        text = re.sub(r"_(.+?)_",       r"\1", text)
        text = re.sub(r"^#+\s*", "",    text, flags=re.MULTILINE)
        text = re.sub(r"\[(.+?)\]\(.+?\)", r"\1", text)
        text = re.sub(r"`(.+?)`",       r"\1", text)
        text = re.sub(r"[\*_]{1,2}",   "",    text)
        return text.strip()

    async def save_message(self, role: str, content: str):
        if not self.auth_token:
            return
        try:
            async with httpx.AsyncClient() as client:
                payload = {"agent": self.agent_id, "role": role, "content": content}
                if self.session_id:
                    payload["session"] = self.session_id
                await client.post(
                    "http://localhost:8000/api/messages/",
                    json=payload,
                    headers={"Authorization": f"Bearer {self.auth_token}"},
                )
        except Exception as e:
            print(f"[save_message] Error: {e}")

    async def generate_session_title(self, first_message: str):
        if not self.session_id or not self.auth_token:
            return
        try:
            prompt = (
                "Generate a very short title (3-5 words max) for a conversation that starts "
                "with this message. Return ONLY the title, no quotes."
            )
            response = await self.llm.ainvoke(
                [SystemMessage(content=prompt), HumanMessage(content=first_message)]
            )
            title = response.content.strip()
            async with httpx.AsyncClient() as client:
                await client.patch(
                    f"http://localhost:8000/api/sessions/{self.session_id}/",
                    json={"title": title},
                    headers={"Authorization": f"Bearer {self.auth_token}"},
                )
            print(f"[session_title] Updated: {title}")
        except Exception as e:
            print(f"[session_title] Error: {e}")

    async def _keep_alive(self):
        while self.is_running:
            try:
                if not self._use_whisper and self.dg_connection:
                    async with self.stt_lock:
                        if self.is_running:
                            await self.dg_connection.send_control(
                                ListenV1ControlMessage(type="KeepAlive")
                            )
                await asyncio.sleep(5)
            except Exception as e:
                if "no close frame" in str(e):
                    print("[KeepAlive] STT connection closed")
                    break
                if self.is_running:
                    print(f"[KeepAlive] Error: {e}")
                break