from omnivoice import OmniVoice
import soundfile as sf
import torch

model = OmniVoice.from_pretrained(
    "k2-fsa/OmniVoice",
    device_map="cuda:0",
    dtype=torch.float16
)
# Apple Silicon users: use device_map="mps" instead
# Intel Arc GPU users: use device_map="xpu" instead

audio = model.generate(
    text="Hé, welkom! Henk hier, geboren en getogen in Breda en inmiddels vooral druk met koffie en sleutels. Waar ben je benieuwd naar: de oude stad, een plek om te eten of iets leuks om te doen?",
    ref_audio="ref.wav",
    # ref_text="Transcription of the reference audio.",
) # audio is a list of `np.ndarray` with shape (T,) at 24 kHz.

# If you don't want to input `ref_text` manually, you can directly omit the `ref_text`.
# The model will use Whisper ASR to auto-transcribe it. To use a local copy (or
# a different Whisper model), pass `asr_model_name="..."` to `from_pretrained`.
# To control which device Whisper is loaded on (e.g. another GPU in multi-GPU
# setups, or the CPU), pass `asr_device="cuda:1"` (or `"cpu"`).

sf.write("out.wav", audio[0], 24000)