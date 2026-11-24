from typing import Any, Iterator, Tuple

def is_empty_pov(pov: Any) -> bool:
    return pov is None or str(pov).strip().lower() in ["none", "null", ""]

def extract_chunk_id_and_text(chunk: Any, default_id: str = "") -> Tuple[str, str]:
    if isinstance(chunk, dict):
        chunk_id = chunk.get("chunk_id") or chunk.get("id") or default_id
        text_val = chunk.get("text_content") or chunk.get("text") or ""
        return chunk_id, text_val
    return default_id, str(chunk)

def iter_history_turns(history: list) -> Iterator[Tuple[str, str]]:
    for turn in history:
        if isinstance(turn, str):
            yield "user", turn
        elif isinstance(turn, dict):
            role = turn.get("role", "user")
            text = turn.get("text", turn.get("content", ""))
            yield role, text