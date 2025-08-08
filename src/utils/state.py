from __future__ import annotations
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime
import threading

class SearchTurn(BaseModel):
    t: datetime = Field(default_factory=datetime.utcnow)
    original_query: str
    inferred_prefs: Dict[str, Any]
    rewritten_query: Optional[str] = None
    used_query: str
    provider: str = "tavily"
    result_meta: Dict[str, Any] = {}

class SearchState(BaseModel):
    session_id: str
    turns: List[SearchTurn] = []
    user_notes: Dict[str, Any] = {}   

class BaseStateStore:
    def get(self, session_id: str) -> Optional[SearchState]:
        raise NotImplementedError
    def set(self, state: SearchState) -> None:
        raise NotImplementedError
    def clear(self, session_id: str) -> None:
        raise NotImplementedError

class InMemoryStateStore(BaseStateStore):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._data: Dict[str, SearchState] = {}

    def get(self, session_id: str) -> Optional[SearchState]:
        with self._lock:
            return self._data.get(session_id)

    def set(self, state: SearchState) -> None:
        with self._lock:
            self._data[state.session_id] = state

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._data.pop(session_id, None)

STATE_STORE = InMemoryStateStore()