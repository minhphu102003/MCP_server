import asyncio
import json
from typing import List, Optional
from fastmcp import Context, FastMCP
from tools.smart_search import smart_search, smart_search_stream
from tools.tavily import tavily_search

mcp = FastMCP("ResearchTools")

@mcp.tool(
    name="smart_search",
    description=(
        "One-shot research with stateful rewriting and meta search. "
        "Args: session_id, query, prefer_academic, time_range, extra_sites, filetype_pdf, target_language."
    ),
    tags={"search", "web", "rewrite"}
)
def smart_search_tool(
    session_id: str,
    query: str,
    prefer_academic: Optional[bool] = None,
    time_range: Optional[str] = None,
    extra_sites: Optional[List[str]] = None,
    filetype_pdf: Optional[bool] = None,
    target_language: Optional[str] = None,
) -> dict:
    """One-shot search with state; returns structured JSON."""
    payload = {
        "session_id": session_id,
        "query": query,
        "prefer_academic": prefer_academic,
        "time_range": time_range,
        "extra_sites": extra_sites,
        "filetype_pdf": filetype_pdf,
        "target_language": target_language,
    }
    out = smart_search.invoke(payload)
    if isinstance(out, str):
        try:
            return json.loads(out)
        except Exception:
            return {"raw": out}
    return out


# @mcp.tool(
#     name="smart_search",
#     description=("One-shot research with stateful rewriting and meta search. "
#                  "Args: session_id, query, prefer_academic, time_range, extra_sites, filetype_pdf, target_language."),
#     tags={"search","web","rewrite"}
# )
# async def smart_search_tool(
#     session_id: str,
#     query: str,
#     prefer_academic: Optional[bool] = None,
#     time_range: Optional[str] = None,
#     extra_sites: Optional[List[str]] = None,
#     filetype_pdf: Optional[bool] = None,
#     target_language: Optional[str] = None,
#     ctx: Context = None, 
# ) -> dict:
#     await ctx.info("Starting smart_search…")             
#     await ctx.report_progress(0, 100)                  

#     payload = {
#         "session_id": session_id, "query": query,
#         "prefer_academic": prefer_academic, "time_range": time_range,
#         "extra_sites": extra_sites, "filetype_pdf": filetype_pdf,
#         "target_language": target_language,
#     }

#     await asyncio.sleep(0.1)
#     await ctx.report_progress(25, 100)
#     await ctx.info("Rewriting query…")

#     await asyncio.sleep(0.1)
#     await ctx.report_progress(50, 100)
#     await ctx.info("Running web search…")

#     out = smart_search.invoke(payload)

#     await ctx.report_progress(100, 100)                   # done
#     if isinstance(out, str):
#         try:
#             return json.loads(out)
#         except Exception:
#             return {"raw": out}
#     return out

@mcp.tool(
    name="tavily_search",
    description=(
        "Direct web search via Tavily with concise, source-grounded results. "
        "Args: query."
    ),
    tags={"search", "web", "tavily"}
)
def tavily_search_tool(query: str):
    return tavily_search.invoke({"query": query})

if __name__ == "__main__":
    mcp.run(host="0.0.0.0", port=8000, transport="streamable-http")
