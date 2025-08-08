from langchain_core.tools import tool
from pydantic import BaseModel, Field
import json
from utils.state import STATE_STORE

class ContextGetInput(BaseModel):
    session_id: str = Field(...)

class ContextClearInput(BaseModel):
    session_id: str = Field(...)

@tool(args_schema=ContextGetInput)
def get_context(session_id: str) -> str:
    """Return saved search context/state for this session_id."""
    st = STATE_STORE.get(session_id)
    if not st:
        return json.dumps({"session_id": session_id, "turns": []}, ensure_ascii=False)
    return st.model_dump_json()

@tool(args_schema=ContextClearInput)
def clear_context(session_id: str) -> str:
    """Clear saved search context/state for this session_id."""
    STATE_STORE.clear(session_id)
    return json.dumps({"cleared": True, "session_id": session_id}, ensure_ascii=False)