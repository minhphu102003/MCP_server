import json
from typing import Dict, Any, Iterable

def sse_event(data: Dict[str, Any]) -> str:
    """Format 1 SSE frame"""
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

def chunk_text(text: str, size: int = 2000) -> Iterable[str]:
    if not text:
        return []
    for i in range(0, len(text), size):
        yield text[i:i+size]
