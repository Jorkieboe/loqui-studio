import uuid
from typing import Optional

from .database import get_connection


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
        rows = conn.execute("""
            SELECT
                c.id,
                c.character_name,
                c.created_at,
                c.updated_at,
                COUNT(m.id)          AS message_count,
                MAX(m.content)       AS last_message
            FROM conversations c
            LEFT JOIN messages m ON m.conversation_id = c.id
            GROUP BY c.id
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
        # ORDER BY rowid guarantees insertion order regardless of timestamp precision
        msgs = conn.execute(
            "SELECT id, role, content, created_at FROM messages WHERE conversation_id = ? ORDER BY rowid",
            (conversation_id,),
        ).fetchall()
    result = dict(conv)
    result["messages"] = [dict(m) for m in msgs]
    return result


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
