from typing import Any, Dict, Optional
from fastmcp import Context
from configs.db_async import get_supabase_async 
import json

LEVEL_MAP = {
    "debug": "debug",
    "info": "info",
    "warn": "warning",
    "warning": "warning",
    "error": "error",
}

async def log_event(
    ctx: Optional[Context],
    level: str,
    message: str,
    *,
    session_id: Optional[str] = None,
    request_id: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> None:
    lvl = LEVEL_MAP.get(level.lower(), "info")

    if ctx:
        if   lvl == "debug":   await ctx.debug(message)
        elif lvl == "warning": await ctx.warning(message)
        elif lvl == "error":   await ctx.error(message)
        else:                  await ctx.info(message)

    try:
        sb = await get_supabase_async()
        payload = {
            "session_id": session_id,
            "request_id": request_id,   
            "level": lvl,
            "message": message,
            "meta": meta or {},
        }
        await sb.table("mcp_logs").insert(payload).execute()
    except Exception:
        pass

async def report_progress(ctx: Optional[Context], progress: int, total: int = 100, message: Optional[str] = None):
    try:
        if ctx:
            await ctx.report_progress(progress, total)
    except Exception:
        pass