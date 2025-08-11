from configs.db import get_supabase
from typing import Any, Dict
from configs.db_async import get_supabase_async

def save_turn(session_id, turn_dict):
    sb = get_supabase()
    res = sb.table("search_turns").insert({**turn_dict, "session_id": session_id}).execute()
    return res.data

async def save_turn_supabase(session_id: str, turn: Dict[str, Any]):
    sb = await get_supabase_async()
    payload = {**turn, "session_id": session_id}
    await sb.table("search_turns").insert(payload).execute()