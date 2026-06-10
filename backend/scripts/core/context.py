from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class SessionState(BaseModel):
    active_node_id: Optional[str] = None
    history: List[Dict[str, str]] = Field(default_factory=list)

class DraftConfig(BaseModel):
    info: Dict[str, Any] = Field(default_factory=dict)
    prompts: Dict[str, Any] = Field(default_factory=dict)
    layout: Dict[str, Any] = Field(default_factory=dict)

class EphemeralPayload(BaseModel):
    draft_config: DraftConfig
    session_state: SessionState
    user_input: str