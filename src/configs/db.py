from functools import lru_cache
from supabase import create_client, Client
from utils.env import get_env_variable 

@lru_cache(maxsize=1)
def get_supabase() -> Client:
    url = get_env_variable("SUPABASE_URL")
    key = get_env_variable("SUPABASE_SERVICE_ROLE_KEY")
    return create_client(url, key) 