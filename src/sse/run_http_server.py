from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional, Dict, Any
from tools.smart_search import smart_search, smart_search_stream 
from tools.tavily import tavily_search
import json
import time

app = FastAPI()

# ====== REGISTER TOOLS ======

REGISTERED_TOOLS = {
    'smart_search': smart_search,
    'tavily_search': tavily_search,
}

# ====== REGISTER STREAMING TOOLS======
STREAMING_TOOLS = {
    "smart_search": smart_search_stream, 
}

def tool_to_mcp_desc(t):
    """Map 1 LangChain tool -> MCP tool descriptor"""
    # Lấy JSON schema từ Pydantic model của tool (nếu có)
    input_schema = {}
    if getattr(t, "args_schema", None):
        try:
            input_schema = t.args_schema.model_json_schema()
        except Exception:
            try:
                input_schema = t.args_schema.schema()
            except Exception:
                input_schema = {}
    return {
        "name": t.name,
        "description": getattr(t, "description", "") or (t.__doc__ or "").strip(),
        "input_schema": input_schema,
    }


# ====== TOOLS DISCOVERY ======
@app.get("/mcp/tools")
def mcp_list_tools(authorization: Optional[str] = Header(default=None)):
    # if REQUIRED and not valid: raise HTTPException(status_code=401, detail="Unauthorized")
    tools = [tool_to_mcp_desc(t) for t in REGISTERED_TOOLS.values()]
    return {"tools": tools}


# ====== INVOKE TOOL ======
@app.post("/mcp/invoke")
async def mcp_invoke(payload: Dict[str, Any], authorization: Optional[str] = Header(default=None)):
    """
    Body: {"name": "smart_search", "arguments": {...}}
    Return: {"content": <string or object>, "isError": false}
    """
    name = payload.get("name")
    args = payload.get("arguments", {}) or {}

    if name not in REGISTERED_TOOLS:
        raise HTTPException(404, f"Tool '{name}' not found")

    tool = REGISTERED_TOOLS[name]
    try:
        result = await tool.ainvoke(args) if hasattr(tool, "ainvoke") else tool.invoke(args)
        return {"content": result, "isError": False}
    except Exception as e:
        return JSONResponse(status_code=500, content={"content": str(e), "isError": True})

# ====== INVOKE STREAM (SSE) ======
def sse_event(obj: Dict[str, Any]) -> str:
    return f"data: {json.dumps(obj, ensure_ascii=False)}\n\n"

@app.get("/mcp/invoke_stream")
def mcp_invoke_stream(
    name: str,
    arguments: str = "{}",
    authorization: Optional[str] = Header(default=None)
):
    """
    Query:
      - name=smart_search
      - arguments='{"session_id":"s1","query":"AI in agriculture"}'
    """
    if name not in STREAMING_TOOLS:
        raise HTTPException(400, f"Tool '{name}' does not support streaming")

    try:
        args = json.loads(arguments) if arguments else {}
    except Exception:
        args = {}

    stream_func = STREAMING_TOOLS[name]

    def gen():
        for evt in stream_func(**args):
            yield sse_event(evt)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


def run_http_server():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
