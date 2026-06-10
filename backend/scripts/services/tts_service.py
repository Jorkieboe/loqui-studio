import os
import sys
import tempfile
import subprocess
import logging
from typing import Generator
import numpy as np
import scipy.io.wavfile as wavfile

logger = logging.getLogger(__name__)

def generate_local_tts_wav(text: str) -> bytes:
    if sys.platform == "win32":
        try:
            fd, temp_path = tempfile.mkstemp(suffix=".wav")
            os.close(fd)
            os.remove(temp_path)

            ps_cmd = (
                f"Add-Type -AssemblyName System.Speech; "
                f"$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                f"$synth.SetOutputToWaveFile('{temp_path}'); "
                f"$synth.Speak('{text}'); "
                f"$synth.Dispose();"
            )
            subprocess.run(
                ["powershell", "-Command", ps_cmd],
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            if os.path.exists(temp_path):
                with open(temp_path, "rb") as f:
                    data = f.read()
                try:
                    os.remove(temp_path)
                except Exception:
                    pass
                return data
        except Exception as e:
            logger.warning(f"[TTS] Native Windows TTS failed: {e}. Falling back to synthetic audio.")

    try:
        sample_rate = 16000
        duration = 0.5
        t = np.linspace(0, duration, int(sample_rate * duration), False)
        tone = np.sin(440 * 2 * np.pi * t) * 0.5

        fd, temp_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        wavfile.write(temp_path, sample_rate, tone.astype(np.float32))

        with open(temp_path, "rb") as f:
            data = f.read()
        try:
            os.remove(temp_path)
        except Exception:
            pass
        return data
    except Exception as e:
        logger.error(f"[TTS] Fallback synthetic generator failed: {e}")
        return b""

def stream_tts(text: str) -> Generator[bytes, None, None]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key)
            response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text,
                response_format="mp3"
            )
            for chunk in response.iter_bytes(chunk_size=4096):
                yield chunk
            return
        except Exception as e:
            logger.error(f"[TTS] OpenAI TTS API request failed: {e}. Trying local fallback.")

    wav_bytes = generate_local_tts_wav(text)
    if wav_bytes:
        chunk_size = 4096
        for i in range(0, len(wav_bytes), chunk_size):
            yield wav_bytes[i:i+chunk_size]