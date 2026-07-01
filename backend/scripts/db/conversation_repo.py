import json
import uuid
from datetime import datetime, timezone
from typing import Optional

from .database import get_connection


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _deserialize(row) -> Optional[dict]:
    if not row:
        return None
    d = dict(row)
    d["messages"] = json.loads(d["messages"])
    return d


# ── Conversations ─────────────────────────────────────────────────────────────

def create_conversation(character_name: str) -> dict:
    cid = str(uuid.uuid4())
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO conversations (id, character_name) VALUES (?, ?)",
            (cid, character_name),
        )
    return get_conversation(cid)


def list_conversations() -> list[dict]:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC"
        ).fetchall()
    return [_deserialize(r) for r in rows]


def get_conversation(conversation_id: str) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
    return _deserialize(row)


def delete_conversation(conversation_id: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM conversations WHERE id = ?", (conversation_id,)
        )
    return cur.rowcount > 0


# ── Messages ──────────────────────────────────────────────────────────────────

def add_message(conversation_id: str, role: str, content: str) -> dict:
    message = {"id": str(uuid.uuid4()), "role": role, "content": content, "created_at": _now()}
    with get_connection() as conn:
        row = conn.execute(
            "SELECT messages FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        if not row:
            return None
        messages = json.loads(row["messages"])
        messages.append(message)
        conn.execute(
            "UPDATE conversations SET messages = ?, updated_at = ? WHERE id = ?",
            (json.dumps(messages), _now(), conversation_id),
        )
    return message
