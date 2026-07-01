from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from scripts.db import conversation_repo as repo

router = APIRouter()


class CreateConversationRequest(BaseModel):
    character_name: str


class AddMessageRequest(BaseModel):
    role: str   # 'user' | 'character'
    content: str


@router.get("")
def list_conversations():
    return repo.list_conversations()


@router.post("", status_code=201)
def create_conversation(body: CreateConversationRequest):
    return repo.create_conversation(body.character_name)


@router.get("/{conversation_id}")
def get_conversation(conversation_id: str):
    conv = repo.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str):
    if not repo.delete_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")


@router.post("/{conversation_id}/messages", status_code=201)
def add_message(conversation_id: str, body: AddMessageRequest):
    if body.role not in ("user", "character"):
        raise HTTPException(status_code=400, detail="role must be 'user' or 'character'")
    conv = repo.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return repo.add_message(conversation_id, body.role, body.content)
