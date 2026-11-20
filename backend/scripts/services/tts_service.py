import io
import os
import threading
import numpy as np
import soundfile as sf
from dotenv import load_dotenv
from scripts.utils.logger import PipelineLogger

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHARACTERS_DIR = os.path.join(BACKEND_DIR, "assets", "characters")
REF_AUDIO_CANDIDATES = (
    "ref.wav",
    "ref.mp3",
    "ref.flac",
    "ref.ogg",
    "ref.m4a",
    "reference.wav",
    "reference.mp3",
)

load_dotenv()
load_dotenv(os.path.join(BACKEND_DIR, "..", ".env"))
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

_tts_engine = None
_tts_load_error = None
_tts_spawn_lock = threading.Lock()
_tts_init_lock = threading.Lock()
_tts_infer_lock = threading.Lock()
_tts_loading_thread = None

def is_tts_enabled() -> bool:
    val = os.environ.get("TTS_ENABLED", "true").strip().lower()
    return val not in ("false", "0", "no", "off")

def _get_device_and_dtype():
    import torch

    if torch.cuda.is_available():
        return "cuda:0", torch.float16
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps", torch.float16
    return "cpu", torch.float32

def _init_tts_engine():
    global _tts_engine, _tts_load_error
    if not is_tts_enabled():
        return None
    with _tts_init_lock:
        if _tts_engine is not None:
            return _tts_engine
        try:
            PipelineLogger.info("Preloading OmniVoice TTS model (k2-fsa/OmniVoice)...")
            from omnivoice import OmniVoice

            device_map, dtype = _get_device_and_dtype()
            PipelineLogger.info(f"OmniVoice loading on device_map={device_map}, dtype={dtype}")
            engine = OmniVoice.from_pretrained(
                "k2-fsa/OmniVoice",
                device_map=device_map,
                dtype=dtype,
            )
            _tts_engine = engine
            _tts_load_error = None
            PipelineLogger.info("OmniVoice TTS model loaded successfully.")
            return _tts_engine
        except Exception as e:
            _tts_load_error = e
            PipelineLogger.error("Failed to load OmniVoice TTS model", e)
            raise

def load_tts_async():
    global _tts_loading_thread
    if not is_tts_enabled():
        PipelineLogger.info("TTS is disabled via TTS_ENABLED. Skipping OmniVoice preload.")
        return
    with _tts_spawn_lock:
        if _tts_engine is not None:
            return
        if _tts_loading_thread is not None and _tts_loading_thread.is_alive():
            return

        def target():
            try:
                _init_tts_engine()
            except Exception:
                pass

        _tts_loading_thread = threading.Thread(target=target, daemon=True)
        _tts_loading_thread.start()

def get_tts_engine():
    if not is_tts_enabled():
        return None
    if _tts_engine is not None:
        return _tts_engine
    load_tts_async()
    if _tts_loading_thread is not None:
        _tts_loading_thread.join()
    if _tts_engine is not None:
        return _tts_engine
    if _tts_load_error is not None:
        raise RuntimeError(f"OmniVoice TTS initialization failed: {_tts_load_error}") from _tts_load_error
    return _init_tts_engine()

def resolve_character_ref_audio(
    character_id: str | None,
    ref_audio_name: str | None = None,
    ref_text_override: str | None = None,
) -> tuple[str | None, str | None]:
    if not character_id:
        return None, None

    char_dir = os.path.join(CHARACTERS_DIR, character_id)
    if not os.path.isdir(char_dir):
        return None, None

    audio_path = None
    if ref_audio_name:
        candidate = ref_audio_name if os.path.isabs(ref_audio_name) else os.path.join(char_dir, ref_audio_name)
        if os.path.isfile(candidate):
            audio_path = candidate

    if audio_path is None:
        for filename in REF_AUDIO_CANDIDATES:
            candidate = os.path.join(char_dir, filename)
            if os.path.isfile(candidate):
                audio_path = candidate
                break

    if audio_path is None:
        return None, None

    resolved_ref_text = ref_text_override.strip() if isinstance(ref_text_override, str) and ref_text_override.strip() else None
    if resolved_ref_text is None:
        stem, _ = os.path.splitext(audio_path)
        text_candidates = [
            f"{stem}.txt",
            os.path.join(char_dir, "ref_text.txt"),
            os.path.join(char_dir, "ref.txt"),
            os.path.join(char_dir, "reference.txt"),
        ]
        for txt_path in text_candidates:
            if os.path.isfile(txt_path):
                try:
                    with open(txt_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            resolved_ref_text = content
                            break
                except Exception as e:
                    PipelineLogger.error(f"Failed to read reference transcript '{txt_path}'", e)

    return audio_path, resolved_ref_text

def synthesize_tts_wav(
    text: str,
    character_id: str | None = None,
    ref_audio: str | None = None,
    ref_text: str | None = None,
) -> bytes:
    if not is_tts_enabled():
        return b""

    if not text or not text.strip():
        return b""

    resolved_audio, resolved_text = resolve_character_ref_audio(
        character_id=character_id,
        ref_audio_name=ref_audio,
        ref_text_override=ref_text,
    )
    if not resolved_audio:
        PipelineLogger.info(f"No reference audio found for character '{character_id}'. Skipping TTS.")
        return b""

    tts_engine = get_tts_engine()
    if tts_engine is None:
        return b""

    generate_kwargs = {
        "text": text,
        "ref_audio": resolved_audio,
    }
    if resolved_text:
        generate_kwargs["ref_text"] = resolved_text

    with _tts_infer_lock:
        audio = tts_engine.generate(**generate_kwargs)

    if not audio or len(audio) == 0:
        return b""

    waveform = audio[0]
    if hasattr(waveform, "detach"):
        waveform = waveform.detach().cpu().numpy()
    waveform_np = np.asarray(waveform, dtype=np.float32).squeeze()

    dur_sec = float(len(waveform_np)) / 24000.0
    PipelineLogger.info(
        f"OmniVoice TTS generated {dur_sec:.2f}s of audio (character={character_id}, ref_audio={os.path.basename(resolved_audio)})"
    )

    buffer = io.BytesIO()
    sf.write(buffer, waveform_np, 24000, format="WAV")
    return buffer.getvalue()