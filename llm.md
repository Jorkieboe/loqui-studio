# Notes on project quirks for language models

**Core Directive: Act as a support programmer.**
Assume the user has full project context. Do not explain obvious code, file structures, or self-evident logic.

**The Litmus Test: The "Surprise" Factor**
Before adding a note, ask: **"Would an experienced developer be surprised by this code? Is it a workaround, a counter-intuitive performance hack, or a deviation from a standard pattern?"** If the answer is no, do not add a note.

---

## Code Quirks & Workarounds
*(Append new notes below this line)*
- `backend/scripts/services/transcription_service.py`: `torch.compile` is explicitly disabled to avoid silent segmentation faults and runtime crashes on Windows hosts.
- `backend/scripts/core/chatsession.py`: Uses a custom `LiteralDumper` with a specified line-width representer to enforce block-style formatting (`|` and `|-`) when saving long context strings, preserving formatting across edits.
- `frontend/src/views/02_MuseumView.vue`: Keeps the microphone capture stream active ("Hot Mic" strategy) after the initial user permission grant. This design avoids cold-start hardware initialization latencies on subsequent user touch inputs.