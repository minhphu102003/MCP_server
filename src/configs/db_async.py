from functools import lru_cache
import asyncio
from supabase import acreate_client 
from utils.env import get_env_variable

_async_client = None
_async_lock = asyncio.Lock()

async def get_supabase_async():
    global _async_client
    if _async_client is None:
        async with _async_lock:
            if _async_client is None:
                url = get_env_variable("SUPABASE_URL")
                key = get_env_variable("SUPABASE_SERVICE_ROLE_KEY")
                _async_client = await acreate_client(url, key)
    return _async_client