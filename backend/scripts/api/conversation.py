from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from scripts.db import conversation_repo as repo

router = APIRouter()


class CreateConversationRequest(BaseModel):
    character_id: str
    character_name: str
    character_avatar: Optional[str] = None


class UpdateConversationRequest(BaseModel):
    current_node_id: str


class AddMessageRequest(BaseModel):
    role: str   # 'user' | 'character'
    content: str


@router.get("")
def list_conversations():
    return repo.list_conversations()


@router.post("", status_code=201)
def create_conversation(body: CreateConversationRequest):
    return repo.create_conversation(body.character_id, body.character_name, body.character_avatar)


@router.get("/{conversation_id}")
def get_conversation(conversation_id: str):
    conv = repo.get_conversation(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.patch("/{conversation_id}")
def update_conversation(conversation_id: str, body: UpdateConversationRequest):
    if not repo.update_conversation(conversation_id, body.current_node_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return repo.get_conversation(conversation_id)


@router.delete("/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str):
    if not repo.delete_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")


@router.post("/{conversation_id}/messages", status_code=201)
def add_message(conversation_id: str, body: AddMessageRequest):
    if body.role not in ("user", "character"):
        raise HTTPException(status_code=400, detail="role must be 'user' or 'character'")
    if not repo.get_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return repo.add_message(conversation_id, body.role, body.content)
