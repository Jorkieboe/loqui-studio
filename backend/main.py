import os
import json
import asyncio
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv

# Load environmental variables early
load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import socketio

from scripts.api.character import router as character_router, load_character_config_sync
from scripts.api.conversation import router as conversation_router
from scripts.db.database import init_db
from scripts.services.transcription_service import transcribe_audio, load_whisper_async
from scripts.services.tts_service import synthesize_tts_wav, load_tts_async, is_tts_enabled
from scripts.core.orchestrator import run_dialogue_pipeline
from scripts.core.session_manager import SessionManager
from scripts.utils.logger import PipelineLogger

session_manager = SessionManager()

# Initialize socket.io server with strict binary buffer allowances
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    max_http_buffer_size=100000000
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    load_tts_async()
    yield

# Initialize FastAPI
app = FastAPI(title="Loqui Studio Backend API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(character_router, prefix="/api/characters")
app.include_router(conversation_router, prefix="/api/conversations")

init_db()

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

@app.get("/api/config")
async def get_config():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            return {"error": f"Failed to parse config: {str(e)}"}
    return {"error": "Configuration file not found"}

@sio.event
async def connect(sid, environ):
    PipelineLogger.info(f"Client connected: {sid}")
    session_manager.create_session(sid)
    load_whisper_async()
    load_tts_async()
    await sio.emit("status_update", {"whisper_ready": True}, to=sid)

@sio.event
async def disconnect(sid):
    PipelineLogger.info(f"Client disconnected: {sid}")
    session_manager.remove_session(sid)

def _get_or_create_chatsession(sid: str):
    session = session_manager.get_session(sid)
    if not session:
        session = session_manager.create_session(sid)
    return session.chatsession

async def process_dialogue_turn(
    sid: str,
    chatsession,
    user_text: str,
    char_id: str | None = None,
    active_node_id: str | None = None,
    history: list | None = None,
    char_config: dict | None = None,
):
    if chatsession.character_id is None and char_id:
        chatsession.character_id = char_id
    if chatsession.current_node_id is None:
        chatsession.current_node_id = active_node_id or "start"
    if not chatsession.history and history:
        chatsession.history = history

    if char_config is None:
        char_config = load_character_config_sync(chatsession.character_id)

    loop_state = {
        "counters": chatsession.loop_counters,
        "active_loop_id": chatsession.active_loop_id
    }

    pipeline_result = run_dialogue_pipeline(
        user_input=user_text,
        active_node_id=chatsession.current_node_id,
        history=chatsession.history,
        character_config=char_config,
        loop_state=loop_state,
        session_instance=chatsession
    )

    chatsession.active_loop_id = loop_state.get("active_loop_id")
    chatsession.next_node_id = pipeline_result["next_node_id"]
    chatsession.possible_next_nodes = pipeline_result["possible_next_nodes"]
    response_stream = pipeline_result["response_stream"]
    full_text = ""

    for chunk in response_stream:
        full_text += chunk
        await sio.emit("response_chunk", {"text": chunk}, to=sid)

    chatsession.history.append({"role": "user", "text": user_text})
    chatsession.history.append({"role": "assistant", "text": full_text})
    chatsession.current_node_id = chatsession.next_node_id

    PipelineLogger.info(f"try start syntesising {is_tts_enabled()}")
    if is_tts_enabled():
        PipelineLogger.llm_status("start syntesising")
        char_info = char_config.get("info", {})
        tts_audio_bytes = await asyncio.to_thread(
            synthesize_tts_wav,
            full_text,
            character_id=chatsession.character_id,
            ref_audio=char_info.get("ref_audio"),
            ref_text=char_info.get("ref_text")
        )
        if tts_audio_bytes:
            await sio.emit("audio_response", {"audio": tts_audio_bytes, "mime_type": "audio/wav"}, to=sid)

    session_ended = chatsession.current_node_id in ["end", "end-node"]
    await sio.emit("response_complete", {
        "next_node_id": chatsession.current_node_id,
        "possible_next_nodes": chatsession.possible_next_nodes,
        "session_ended": session_ended,
        "retrieved_chunks": pipeline_result["retrieved_chunks"]
    }, to=sid)

@sio.event
async def chat_message(sid, data):
    """
    Handles standard text chat message.
    data format: {
        "character_id": str,
        "text": str,
        "active_node_id": str,
        "history": list
    }
    """
    try:
        chatsession = _get_or_create_chatsession(sid)
        await process_dialogue_turn(
            sid=sid,
            chatsession=chatsession,
            user_text=data.get("text", ""),
            char_id=data.get("character_id"),
            active_node_id=data.get("active_node_id"),
            history=data.get("history", []),
        )
    except Exception as e:
        PipelineLogger.error("Error in chat_message socket event", e)
        await sio.emit("error", {"detail": str(e)}, to=sid)

@sio.event
async def audio_message(sid, data):
    """
    Handles WebM audio stream packets.
    data format: dict with binary sound data or raw bytes
    """
    try:
        chatsession = _get_or_create_chatsession(sid)

        audio_bytes = b""
        char_id = "example"
        active_node_id = None
        history = []

        if isinstance(data, dict):
            audio_bytes = data.get("audio", b"")
            char_id = data.get("character_id", "example")
            active_node_id = data.get("active_node_id")
            history = data.get("history", [])
        elif isinstance(data, bytes):
            audio_bytes = data
        else:
            PipelineLogger.error(f"Unsupported audio_message data format: {type(data)}")
            return

        if not audio_bytes:
            PipelineLogger.info("Empty audio received in audio_message")
            return

        effective_char_id = chatsession.character_id or char_id
        char_config = load_character_config_sync(effective_char_id)
        char_language = char_config.get("info", {}).get("language")

        transcription = transcribe_audio(audio_bytes, language=char_language)

        await sio.emit("transcription", {"text": transcription}, to=sid)

        if not transcription.strip():
            session_ended = chatsession.current_node_id in ["end", "end-node"]
            await sio.emit("response_complete", {
                "next_node_id": chatsession.current_node_id,
                "possible_next_nodes": chatsession.possible_next_nodes,
                "session_ended": session_ended,
                "retrieved_chunks": []
            }, to=sid)
            return

        await process_dialogue_turn(
            sid=sid,
            chatsession=chatsession,
            user_text=transcription,
            char_id=char_id,
            active_node_id=active_node_id,
            history=history,
            char_config=char_config,
        )
    except Exception as e:
        PipelineLogger.error("Error in audio_message socket event", e)
        await sio.emit("error", {"detail": str(e)}, to=sid)

# Mount Vue production build files if they exist
dist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../frontend/dist"))
if os.path.exists(dist_dir):
    app.mount("/", StaticFiles(directory=dist_dir, html=True), name="static")

# Bind Socket.IO ASGI application together with FastAPI routes
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:socket_app", host="0.0.0.0", port=5000, reload=True)