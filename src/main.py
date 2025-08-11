import argparse
import asyncio
from db.sqlalchemy import init_db
from sse.run_http_server import mcp  
import models
from configs.db_async import get_supabase_async


if __name__ == "__main__":
    asyncio.run(get_supabase_async()) 
    init_db() 
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["stdio", "http"], default="stdio")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--path", default="/mcp") 
    args = parser.parse_args()

    if args.mode == "stdio":
        mcp.run(transport="stdio")
    else:
        mcp.run(transport="streamable-http", host=args.host, port=args.port, path=args.path)
