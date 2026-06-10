import os
import json
import logging
from dotenv import load_dotenv

# Load environmental variables early
load_dotenv()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import socketio

from scripts.api.character import router as character_router, load_character_config_sync
from scripts.services.transcription_service import transcribe_audio, load_whisper_async
from scripts.services.tts_service import stream_tts
from scripts.core.orchestrator import run_dialogue_pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")

# Initialize socket.io server with strict binary buffer allowances
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',
    max_http_buffer_size=100000000
)

# Initialize FastAPI
app = FastAPI(title="New Parley Backend API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(character_router, prefix="/api/characters")

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
    logger.info(f"Client connected: {sid}")
    load_whisper_async()
    await sio.emit("status_update", {"whisper_ready": True}, to=sid)

@sio.event
async def disconnect(sid):
    logger.info(f"Client disconnected: {sid}")

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
        char_id = data.get("character_id")
        text = data.get("text", "")
        active_node_id = data.get("active_node_id")
        history = data.get("history", [])

        char_config = load_character_config_sync(char_id)

        pipeline_result = run_dialogue_pipeline(
            user_input=text,
            active_node_id=active_node_id,
            history=history,
            character_config=char_config
        )

        response_stream = pipeline_result["response_stream"]
        full_text = ""

        for chunk in response_stream:
            full_text += chunk
            await sio.emit("response_chunk", {"text": chunk}, to=sid)

        for audio_chunk in stream_tts(full_text):
            await sio.emit("audio_chunk", audio_chunk, to=sid)

        await sio.emit("response_complete", {
            "next_node_id": pipeline_result["next_node_id"],
            "retrieved_chunks": pipeline_result["retrieved_chunks"]
        }, to=sid)

    except Exception as e:
        logger.error(f"Error in chat_message socket event: {e}")
        await sio.emit("error", {"detail": str(e)}, to=sid)

@sio.event
async def audio_message(sid, data):
    """
    Handles WebM audio stream packets.
    data format: dict with binary sound data or raw bytes
    """
    try:
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
            logger.error(f"Unsupported audio_message data format: {type(data)}")
            return

        if not audio_bytes:
            logger.warning("Empty audio received in audio_message")
            return

        transcription = transcribe_audio(audio_bytes)
        logger.info(f"[STT] Transcribed: '{transcription}'")

        await sio.emit("transcription", {"text": transcription}, to=sid)

        if not transcription.strip():
            await sio.emit("response_complete", {
                "next_node_id": active_node_id,
                "retrieved_chunks": []
            }, to=sid)
            return

        char_config = load_character_config_sync(char_id)

        pipeline_result = run_dialogue_pipeline(
            user_input=transcription,
            active_node_id=active_node_id,
            history=history,
            character_config=char_config
        )

        response_stream = pipeline_result["response_stream"]
        full_text = ""

        for chunk in response_stream:
            full_text += chunk
            await sio.emit("response_chunk", {"text": chunk}, to=sid)

        for audio_chunk in stream_tts(full_text):
            await sio.emit("audio_chunk", audio_chunk, to=sid)

        await sio.emit("response_complete", {
            "next_node_id": pipeline_result["next_node_id"],
            "retrieved_chunks": pipeline_result["retrieved_chunks"]
        }, to=sid)

    except Exception as e:
        logger.error(f"Error in audio_message socket event: {e}")
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