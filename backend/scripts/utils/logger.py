import logging
from typing import Any
from rich.console import Console
from rich.theme import Theme

custom_theme = Theme({
    "rag": "bold cyan",
    "llm_status": "bold yellow",
    "llm_output": "green",
    "transcription": "bold magenta",
    "info": "dim white",
    "error": "bold red"
})

console = Console(theme=custom_theme)

class PipelineLogger:
    @staticmethod
    def rag(message: str, details: Any = None):
        if details is not None:
            console.print(f"[rag][RAG][/rag] {message} - {details}")
        else:
            console.print(f"[rag][RAG][/rag] {message}")

    @staticmethod
    def llm_status(message: str, details: Any = None):
        if details is not None:
            console.print(f"[llm_status][LLM STATUS][/llm_status] {message} - {details}")
        else:
            console.print(f"[llm_status][LLM STATUS][/llm_status] {message}")

    @staticmethod
    def llm_output(chunk: str, is_end: bool = False):
        if is_end:
            console.print("")
        else:
            console.print(f"[llm_output][LLM OUTPUT][/llm_output] {chunk}")

    @staticmethod
    def transcription(text: str):
        console.print(f"[transcription][STT][/transcription] Transcribed: '{text}'")

    @staticmethod
    def info(message: str):
        console.print(f"[info][INFO][/info] {message}")

    @staticmethod
    def error(message: str, error_obj: Any = None):
        if error_obj is not None:
            console.print(f"[error][ERROR][/error] {message}: {error_obj}")
        else:
            console.print(f"[error][ERROR][/error] {message}")