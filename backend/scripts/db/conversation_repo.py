import uuid
from typing import Optional

from .database import get_connection


# ── Conversations ─────────────────────────────────────────────────────────────

def create_conversation(character_id: str, character_name: str, character_avatar: Optional[str]) -> dict:
    cid = str(uuid.uuid4())
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO conversations (id, character_id, character_name, character_avatar) VALUES (?, ?, ?, ?)",
            (cid, character_id, character_name, character_avatar),
        )
    return get_conversation(cid)


def list_conversations() -> list[dict]:
    with get_connection() as conn:
        # Subquery fetches the last message per conversation using rowid (insertion order)
        rows = conn.execute("""
            SELECT
                c.id,
                c.character_id,
                c.character_name,
                c.character_avatar,
                c.current_node_id,
                c.created_at,
                c.updated_at,
                m.content AS last_message
            FROM conversations c
            LEFT JOIN messages m ON m.rowid = (
                SELECT MAX(rowid) FROM messages WHERE conversation_id = c.id
            )
            ORDER BY c.updated_at DESC
        """).fetchall()
    return [dict(r) for r in rows]


def get_conversation(conversation_id: str) -> Optional[dict]:
    with get_connection() as conn:
        conv = conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        ).fetchone()
        if not conv:
            return None
        msgs = conn.execute(
            "SELECT id, role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY rowid",
            (conversation_id,),
        ).fetchall()
    result = dict(conv)
    result["messages"] = [dict(m) for m in msgs]
    return result


def update_conversation(conversation_id: str, current_node_id: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            """UPDATE conversations
               SET current_node_id = ?,
                   updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now')
               WHERE id = ?""",
            (current_node_id, conversation_id),
        )
    return cur.rowcount > 0


def delete_conversation(conversation_id: str) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM conversations WHERE id = ?", (conversation_id,)
        )
    return cur.rowcount > 0


# ── Messages ──────────────────────────────────────────────────────────────────

def add_message(conversation_id: str, role: str, content: str) -> dict:
    mid = str(uuid.uuid4())
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO messages (id, conversation_id, role, content) VALUES (?, ?, ?, ?)",
            (mid, conversation_id, role, content),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = strftime('%Y-%m-%dT%H:%M:%SZ', 'now') WHERE id = ?",
            (conversation_id,),
        )
        row = conn.execute(
            "SELECT id, role, content, created_at FROM messages WHERE id = ?", (mid,)
        ).fetchone()
    return dict(row)
