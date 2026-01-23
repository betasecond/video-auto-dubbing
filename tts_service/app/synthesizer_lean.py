"""Lean TTS synthesizer using external index-tts-vllm package."""

import io
import logging
import tempfile
from pathlib import Path
from typing import Optional
import threading

import numpy as np
import soundfile as sf
import httpx

from app.config import settings
from app.exceptions import InvalidParameterError, ModelNotLoadedError, SynthesisError
from app.models import ProsodyControl

logger = logging.getLogger(__name__)


class LeanTTSSynthesizer:
    """Lean TTS synthesizer using external index-tts-vllm service or package."""

    def __init__(self):
        """Initialize the lean TTS synthesizer."""
        self._model_loaded = False
        self._client: Optional[httpx.AsyncClient] = None
        self._model_lock = threading.Lock()

    async def load_model(self) -> None:
        """Load the external TTS model/service.

        Raises:
            ModelNotLoadedError: If model loading fails.
        """
        if self._model_loaded:
            logger.info("TTS service already initialized")
            return

        try:
            # Initialize HTTP client for external TTS service
            self._client = httpx.AsyncClient(timeout=30.0)

            # Try to load local index-tts-vllm if available
            try:
                from indextts_vllm import IndexTTSVLLM
                logger.info("Found index-tts-vllm package, using local inference")
                self._use_local = True
            except ImportError:
                logger.info("index-tts-vllm not found, will use HTTP API mode")
                self._use_local = False

            self._model_loaded = True
            logger.info("Lean TTS synthesizer initialized successfully")
        except Exception as e:
            logger.error("Failed to initialize TTS synthesizer", extra={"error": str(e)}, exc_info=True)
            raise ModelNotLoadedError(f"Failed to initialize TTS: {e}") from e

    def is_model_loaded(self) -> bool:
        """Check if the synthesizer is initialized."""
        return self._model_loaded

    async def synthesize(
        self,
        text: str,
        speaker_id: str = "default",
        prompt_audio_path: Optional[str] = None,
        target_duration_ms: Optional[int] = None,
        language: str = "zh",
        prosody_control: Optional[ProsodyControl] = None,
        output_format: str = "wav",
        sample_rate: int = 22050,
    ) -> io.BytesIO:
        """Synthesize speech using external TTS service.

        Args:
            text: Text to synthesize
            speaker_id: Speaker identifier
            prompt_audio_path: Path to prompt audio file
            target_duration_ms: Target duration in milliseconds
            language: Target language
            prosody_control: Prosody control parameters
            output_format: Audio output format
            sample_rate: Audio sample rate

        Returns:
            Audio data as BytesIO stream

        Raises:
            SynthesisError: If synthesis fails
            ModelNotLoadedError: If model is not loaded
        """
        if not self._model_loaded:
            raise ModelNotLoadedError("TTS synthesizer not initialized")

        if not text.strip():
            raise InvalidParameterError("Text cannot be empty")

        try:
            if self._use_local and hasattr(self, '_local_model'):
                return await self._synthesize_local(
                    text, speaker_id, prompt_audio_path, target_duration_ms,
                    language, prosody_control, output_format, sample_rate
                )
            else:
                return await self._synthesize_http(
                    text, speaker_id, prompt_audio_path, target_duration_ms,
                    language, prosody_control, output_format, sample_rate
                )
        except Exception as e:
            logger.error("TTS synthesis failed", extra={"error": str(e), "text": text[:50]}, exc_info=True)
            raise SynthesisError(f"Synthesis failed: {e}") from e

    async def _synthesize_http(
        self,
        text: str,
        speaker_id: str,
        prompt_audio_path: Optional[str],
        target_duration_ms: Optional[int],
        language: str,
        prosody_control: Optional[ProsodyControl],
        output_format: str,
        sample_rate: int,
    ) -> io.BytesIO:
        """Synthesize using HTTP API."""
        # Prepare request payload
        payload = {
            "text": text,
            "speaker_id": speaker_id or "default",
            "language": language,
            "format": output_format,
            "sample_rate": sample_rate,
        }

        if target_duration_ms:
            payload["target_duration_ms"] = target_duration_ms

        if prompt_audio_path:
            payload["prompt_audio_url"] = prompt_audio_path

        if prosody_control:
            payload["prosody_control"] = prosody_control.model_dump()

        # Try multiple endpoint patterns
        endpoints = [
            "/synthesize",
            "/tts",
            "/api/synthesize",
            "/audio/speech",  # OpenAI compatible
            "/v1/audio/speech"
        ]

        base_url = getattr(settings, 'tts_remote_url', 'http://localhost:8000')

        for endpoint in endpoints:
            try:
                url = base_url.rstrip('/') + endpoint

                if endpoint in ["/audio/speech", "/v1/audio/speech"]:
                    # OpenAI compatible format
                    openai_payload = {
                        "model": "index-tts-v2",
                        "input": text,
                        "voice": speaker_id or "default",
                        "response_format": output_format
                    }
                    response = await self._client.post(url, json=openai_payload)
                else:
                    # Native format
                    response = await self._client.post(url, json=payload)

                if response.status_code == 200:
                    # Check if response is JSON (error) or binary (audio)
                    content_type = response.headers.get("content-type", "")
                    if "application/json" in content_type:
                        error_data = response.json()
                        raise SynthesisError(f"TTS service error: {error_data.get('detail', 'Unknown error')}")

                    # Return audio data
                    return io.BytesIO(response.content)

                elif response.status_code == 404:
                    continue  # Try next endpoint
                else:
                    logger.warning(f"TTS endpoint {url} returned {response.status_code}")
                    continue

            except httpx.RequestError as e:
                logger.warning(f"Failed to connect to {url}: {e}")
                continue
            except Exception as e:
                logger.warning(f"Error with endpoint {url}: {e}")
                continue

        raise SynthesisError("No working TTS endpoint found")

    async def _synthesize_local(
        self,
        text: str,
        speaker_id: str,
        prompt_audio_path: Optional[str],
        target_duration_ms: Optional[int],
        language: str,
        prosody_control: Optional[ProsodyControl],
        output_format: str,
        sample_rate: int,
    ) -> io.BytesIO:
        """Synthesize using local index-tts-vllm package (if available)."""
        # Placeholder for local synthesis
        # This would use the index-tts-vllm package directly
        raise NotImplementedError("Local synthesis not implemented yet")

    async def cleanup(self):
        """Cleanup resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
        self._model_loaded = False

    def __del__(self):
        """Destructor to ensure cleanup."""
        if self._client and not self._client.is_closed:
            # Note: This is not ideal for async cleanup, but serves as a fallback
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self.cleanup())
            except Exception:
                pass  # Ignore cleanup errors in destructor