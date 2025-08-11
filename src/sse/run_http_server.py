import json
from typing import List, Optional
from fastmcp import FastMCP, Context
from tools.smart_search import smart_search, smart_search_stream_mcp
from tools.tavily import tavily_search
from tools.rewrite import rewrite_query
from tools.summarize import summarize_text

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

@mcp.tool(
    name="summarize_text",
    description=(
        "Summarize long text using Gemini 2.5. "
        "Args: text, max_words, language, style, include_bullets, title."
    ),
    tags={"summarize", "gemini", "text"}
)
def summarize_text_tool(
    text: str,
    max_words: int = 200,
    language: Optional[str] = None,
    style: Optional[str] = "balanced",
    include_bullets: bool = True,
    title: Optional[str] = None,
) -> str:
    return summarize_text.invoke({
        "text": text,
        "max_words": max_words,
        "language": language,
        "style": style,
        "include_bullets": include_bullets,
        "title": title,
    })

@mcp.tool(
    name="rewrite_query",
    description=(
        "Rewrite a search query to be more suitable for web search. "
        "Args: query, prefer_academic, time_range, extra_sites, filetype_pdf, target_language."
    ),
    tags={"search", "rewrite", "gemini"}
)
def rewrite_query_tool(
    query: str,
    prefer_academic: Optional[bool] = False,
    time_range: Optional[str] = None,
    extra_sites: Optional[List[str]] = None,
    filetype_pdf: Optional[bool] = False,
    target_language: Optional[str] = None,
) -> str:
    return rewrite_query.invoke({
        "query": query,
        "prefer_academic": prefer_academic,
        "time_range": time_range,
        "extra_sites": extra_sites,
        "filetype_pdf": filetype_pdf,
        "target_language": target_language,
    })

@mcp.tool(
    name="smart_search_stream",
    description=(
        "Stateful meta-search with live progress/log streaming over MCP. "
        "Args: session_id, query, prefer_academic, time_range, extra_sites, filetype_pdf, target_language."
    ),
    tags={"search", "web", "rewrite", "stream"},
)
async def smart_search_stream_tool(
    session_id: str,
    query: str,
    prefer_academic: Optional[bool] = None,
    time_range: Optional[str] = None,
    extra_sites: Optional[List[str]] = None,
    filetype_pdf: Optional[bool] = None,
    target_language: Optional[str] = None,
    ctx: Context = None,  
):
    out = await smart_search_stream_mcp(
        session_id=session_id,
        query=query,
        prefer_academic=prefer_academic,
        time_range=time_range,
        extra_sites=extra_sites,
        filetype_pdf=filetype_pdf,
        target_language=target_language,
        ctx=ctx,
    )
    return out 
