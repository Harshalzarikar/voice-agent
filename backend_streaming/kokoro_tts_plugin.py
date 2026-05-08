"""
Custom LiveKit TTS Plugin that wraps fal-ai/kokoro/hindi.
Compatible with livekit-agents v1.5+

Key fixes vs original:
  - Persistent httpx.AsyncClient with connection pooling (created once, reused forever)
  - Warm-up call during __init__ to wake the fal.ai container before any user speaks
  - Reduced per-attempt timeout now that cold-start is handled at init
"""
import io
import os
import asyncio
import logging
import httpx
import numpy as np
import soundfile as sf

from livekit.agents import tts, utils
from livekit.agents.types import APIConnectOptions, DEFAULT_API_CONNECT_OPTIONS

logger = logging.getLogger("kokoro_tts_plugin")

SAMPLE_RATE = 24000
NUM_CHANNELS = 1

_VALID_HINDI_VOICES = {"hf_alpha", "hf_beta", "hm_omega", "hm_psi"}
_DEFAULT_HINDI_VOICE = "hf_alpha"

# Short warm-up text — just enough to wake the fal.ai container
_WARMUP_TEXT = "नमस्ते"


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
        warmup: bool = True,
    ):
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=SAMPLE_RATE,
            num_channels=NUM_CHANNELS,
        )

        if voice not in _VALID_HINDI_VOICES:
            logger.warning(
                "KokoroHindiTTS: voice '%s' is not valid (valid: %s). "
                "Falling back to '%s'.",
                voice, ", ".join(sorted(_VALID_HINDI_VOICES)), _DEFAULT_HINDI_VOICE,
            )
            voice = _DEFAULT_HINDI_VOICE

        self._voice = voice
        self._speed = speed
        self._fal_key = fal_key or os.environ.get("FAL_KEY", "")
        self._warmup = warmup

        # ── Persistent client: created once, reused for every synthesis call ──
        # limits=10 keeps at most 10 simultaneous connections open.
        # keepalive_expiry=30 holds idle TCP connections alive for 30s so
        # subsequent requests skip the TCP + TLS handshake entirely.
        self._client = httpx.AsyncClient(
            timeout=60.0,
            limits=httpx.Limits(
                max_connections=10,
                max_keepalive_connections=5,
                keepalive_expiry=30,
            ),
            headers={
                "Authorization": f"Key {self._fal_key}",
                "Content-Type": "application/json",
            },
        )
        self._warmed_up = False

    # ──────────────────────────────────────────────────────────────────────────
    # Call this once inside prewarm() to wake the fal.ai container early,
    # before any user connects.  If warmup=False the call is skipped.
    # ──────────────────────────────────────────────────────────────────────────
    async def warmup_endpoint(self) -> None:
        """Send a short silent request to wake the fal.ai container."""
        if not self._warmup or self._warmed_up:
            return
        logger.info("KokoroHindiTTS: warming up fal.ai endpoint...")
        try:
            resp = await self._client.post(
                "https://fal.run/fal-ai/kokoro/hindi",
                json={"prompt": _WARMUP_TEXT, "voice": self._voice, "speed": self._speed},
                timeout=90.0,   # allow full cold-start time only here
            )
            resp.raise_for_status()
            self._warmed_up = True
            logger.info("KokoroHindiTTS: endpoint is warm.")
        except Exception as exc:
            # Don't crash prewarm if fal.ai is flaky — real calls will still retry
            logger.warning("KokoroHindiTTS: warm-up failed (will retry on first call): %s", exc)

    async def aclose(self) -> None:
        await self._client.aclose()
        await super().aclose()

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
        text = self._input_text.strip()
        if not text:
            logger.warning("KokoroHindiTTS: empty text, skipping synthesis.")
            return

        tts_instance = self._kokoro_tts
        client = tts_instance._client   # reuse the persistent client
        payload = {
            "prompt": text,
            "voice": tts_instance._voice,
            "speed": tts_instance._speed,
        }

        MAX_RETRIES = 2
        last_exc: Exception | None = None

        for attempt in range(MAX_RETRIES + 1):
            try:
                if attempt > 0:
                    wait = 2 ** attempt
                    logger.warning(
                        "KokoroHindiTTS: retry %d/%d after %ds (last error: %s)",
                        attempt, MAX_RETRIES, wait, last_exc,
                    )
                    await asyncio.sleep(wait)

                # ── Step 1: request audio generation ──────────────────────────
                resp = await client.post(
                    "https://fal.run/fal-ai/kokoro/hindi",
                    json=payload,
                    # After warm-up, generation should complete in < 10s
                    timeout=30.0,
                )
                if resp.status_code == 422:
                    logger.error(
                        "Fal AI 422 error. Payload: %s | Response: %s",
                        payload, resp.text,
                    )
                resp.raise_for_status()

                audio_url = resp.json().get("audio", {}).get("url")
                if not audio_url:
                    raise RuntimeError(f"Fal AI returned no audio URL. Response: {resp.json()}")

                # ── Step 2: download the audio file ───────────────────────────
                audio_resp = await client.get(audio_url, timeout=15.0)
                audio_resp.raise_for_status()
                audio_bytes = audio_resp.content
                break  # success

            except httpx.TimeoutException as exc:
                last_exc = exc
                logger.warning(
                    "KokoroHindiTTS: timeout on attempt %d/%d: %s",
                    attempt + 1, MAX_RETRIES + 1, exc,
                )
                if attempt == MAX_RETRIES:
                    logger.error("KokoroHindiTTS: all attempts timed out.")
                    raise
                continue

            except httpx.HTTPStatusError:
                raise  # 4xx → don't retry

        # ── Decode WAV → raw int16 PCM ─────────────────────────────────────────
        with io.BytesIO(audio_bytes) as buf:
            audio_data, sample_rate = sf.read(buf, dtype="int16")

        if audio_data.ndim > 1:
            audio_data = audio_data.mean(axis=1).astype(np.int16)

        pcm_bytes = audio_data.tobytes()

        output_emitter.initialize(
            request_id=utils.shortuuid(),
            sample_rate=sample_rate,
            num_channels=NUM_CHANNELS,
            mime_type="audio/pcm",
        )

        CHUNK_SAMPLES = sample_rate // 10  # 100 ms chunks
        chunk_bytes = CHUNK_SAMPLES * NUM_CHANNELS * 2

        for i in range(0, len(pcm_bytes), chunk_bytes):
            output_emitter.push(pcm_bytes[i : i + chunk_bytes])

        output_emitter.flush()