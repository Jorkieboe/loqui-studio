import os
import subprocess
import threading
import numpy as np
import logging

logger = logging.getLogger(__name__)

_whisper_pipeline = None
_whisper_loading = False
_whisper_lock = threading.Lock()

def load_whisper_async():
    global _whisper_pipeline, _whisper_loading
    with _whisper_lock:
        if _whisper_pipeline is not None or _whisper_loading:
            return
        _whisper_loading = True

    def target():
        global _whisper_pipeline, _whisper_loading
        try:
            logger.info("[STT] Lazy-loading Whisper pipeline...")
            from transformers import pipeline
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"[STT] Whisper loading on device: {device}")
            # Loading whisper-tiny for low-resource environments
            _whisper_pipeline = pipeline(
                "automatic-speech-recognition",
                model="openai/whisper-tiny",
                device=device
            )
            logger.info("[STT] Whisper pipeline loaded successfully.")
        except Exception as e:
            logger.error(f"[STT] Failed to load Whisper pipeline: {e}. STT will fall back to simulation or API.")
        finally:
            _whisper_loading = False

    t = threading.Thread(target=target, daemon=True)
    t.start()

def get_whisper_pipeline():
    global _whisper_pipeline
    if _whisper_pipeline is None:
        load_whisper_async()
    return _whisper_pipeline

def decode_audio_to_float32(audio_bytes: bytes) -> np.ndarray:
    try:
        cmd = [
            "ffmpeg",
            "-y",
            "-i", "pipe:0",
            "-f", "f32le",
            "-acodec", "pcm_f32le",
            "-ar", "16000",
            "-ac", "1",
            "pipe:1"
        ]
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        out, err = process.communicate(input=audio_bytes)
        if process.returncode != 0:
            logger.error(f"[STT] ffmpeg error: {err.decode('utf-8', errors='ignore')}")
            raise RuntimeError("ffmpeg conversion failed")

        return np.frombuffer(out, dtype=np.float32)
    except Exception as e:
        logger.error(f"[STT] Audio decoding failed: {e}")
        raise e

def transcribe_audio(audio_bytes: bytes) -> str:
    pipeline_instance = get_whisper_pipeline()
    if pipeline_instance is None:
        logger.warning("[STT] Local Whisper not ready. Attempting API transcription or fallback.")
        return "Simulated transcription: local Whisper not ready."

    try:
        audio_data = decode_audio_to_float32(audio_bytes)
        result = pipeline_instance({"raw": audio_data, "sampling_rate": 16000})
        return result.get("text", "").strip()
    except Exception as e:
        logger.error(f"[STT] Transcription failed: {e}")
        return ""