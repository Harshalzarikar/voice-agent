"""
Custom LiveKit TTS Plugin that wraps FalKokoroHindiTTS.
This allows using fal-ai/kokoro/hindi inside AgentSession.
Compatible with livekit-agents v1.5+
"""
import io
import os
import asyncio
import httpx
import numpy as np
import soundfile as sf

from livekit.agents import tts, utils
from livekit.agents.types import APIConnectOptions, DEFAULT_API_CONNECT_OPTIONS


SAMPLE_RATE = 24000  # Kokoro outputs 24kHz
NUM_CHANNELS = 1

# Only these voices are valid for the fal-ai/kokoro/hindi endpoint.
# English voices (af_*, am_*) will cause a 422 Unprocessable Entity error.
_VALID_HINDI_VOICES = {"hf_alpha", "hf_beta", "hm_omega", "hm_psi"}
_DEFAULT_HINDI_VOICE = "hf_alpha"


class KokoroHindiTTS(tts.TTS):
    """
    LiveKit-compatible TTS plugin that calls fal-ai/kokoro/hindi.
    Supports Hindi voices: hf_alpha, hf_beta, hm_omega, hm_psi
    """

    def __init__(
        self,
        *,
        voice: str = _DEFAULT_HINDI_VOICE,
        speed: float = 1.0,
        fal_key: str | None = None,
    ):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=SAMPLE_RATE,
            num_channels=NUM_CHANNELS,
        )
        # Validate voice — English voices (e.g. af_heart) cause a 422 on the Hindi endpoint
        if voice not in _VALID_HINDI_VOICES:
            import logging
            logging.getLogger("kokoro_tts_plugin").warning(
                "KokoroHindiTTS: voice '%s' is not a valid Hindi voice "
                "(valid: %s). Falling back to '%s'.",
                voice, ", ".join(sorted(_VALID_HINDI_VOICES)), _DEFAULT_HINDI_VOICE,
            )
            voice = _DEFAULT_HINDI_VOICE
        self._voice = voice
        self._speed = speed
        self._fal_key = fal_key or os.environ.get("FAL_KEY", "")

    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> "KokoroHindiStream":
        return KokoroHindiStream(
            tts=self,
            input_text=text,
            conn_options=conn_options,
        )


class KokoroHindiStream(tts.ChunkedStream):
    def __init__(
        self,
        *,
        tts: KokoroHindiTTS,
        input_text: str,
        conn_options: APIConnectOptions,
    ):
        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
        self._kokoro_tts = tts

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        import logging
        logger = logging.getLogger("kokoro_tts_plugin")

        text = self._input_text.strip()
        fal_key = self._kokoro_tts._fal_key
        voice = self._kokoro_tts._voice
        speed = self._kokoro_tts._speed

        if not fal_key:
            raise RuntimeError("FAL_KEY is missing. Set it in your .env file.")

        # Guard: skip API call if text is empty — fal.ai returns 422 for empty prompts
        if not text:
            logger.warning("KokoroHindiTTS: received empty text, skipping synthesis.")
            return

        payload = {"prompt": text, "voice": voice, "speed": speed}

        # fal.ai Kokoro Hindi has slow cold starts — use 90s timeout + 2 retries
        MAX_RETRIES = 2
        TIMEOUT_SECONDS = 90.0
        last_exc: Exception | None = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                if attempt > 0:
                    wait = 2 ** attempt  # 2s, 4s backoff
                    logger.warning(
                        "KokoroHindiTTS: retry %d/%d after %ds (last error: %s)",
                        attempt, MAX_RETRIES, wait, last_exc,
                    )
                    await asyncio.sleep(wait)

                async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
                    resp = await client.post(
                        "https://fal.run/fal-ai/kokoro/hindi",
                        headers={
                            "Authorization": f"Key {fal_key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                    if resp.status_code == 422:
                        logger.error(
                            "Fal AI 422 error. Request payload: %s | Response: %s",
                            payload, resp.text,
                        )
                    resp.raise_for_status()
                    data = resp.json()
                    audio_url = data.get("audio", {}).get("url")
                    if not audio_url:
                        raise RuntimeError(
                            f"Fal AI returned no audio URL. Response: {data}"
                        )

                    audio_resp = await client.get(audio_url, timeout=30.0)
                    audio_resp.raise_for_status()
                    audio_bytes = audio_resp.content

                # Success — break out of retry loop
                break

            except httpx.TimeoutException as exc:
                last_exc = exc
                logger.warning(
                    "KokoroHindiTTS: timeout on attempt %d/%d (%s)",
                    attempt + 1, MAX_RETRIES + 1, exc,
                )
                if attempt == MAX_RETRIES:
                    logger.error(
                        "KokoroHindiTTS: all %d attempts timed out, giving up.",
                        MAX_RETRIES + 1,
                    )
                    raise
                continue

            except httpx.HTTPStatusError:
                # Don't retry on 4xx client errors (wrong payload etc.)
                raise

        # Decode the audio file to raw 16-bit PCM
        with io.BytesIO(audio_bytes) as buf:
            audio_data, sample_rate = sf.read(buf, dtype="int16")

        # Downmix to mono if stereo
        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1).astype(np.int16)

        pcm_bytes = audio_data.tobytes()

        # Initialize emitter with actual sample rate from Fal response
        output_emitter.initialize(
            request_id=utils.shortuuid(),
            sample_rate=sample_rate,
            num_channels=NUM_CHANNELS,
            mime_type="audio/pcm",
        )

        # Push in 100ms chunks so LiveKit can stream it out smoothly
        CHUNK_SAMPLES = sample_rate // 10  # 100ms
        chunk_bytes = CHUNK_SAMPLES * NUM_CHANNELS * 2  # 2 bytes per int16

        for i in range(0, len(pcm_bytes), chunk_bytes):
            output_emitter.push(pcm_bytes[i : i + chunk_bytes])

        output_emitter.flush()
