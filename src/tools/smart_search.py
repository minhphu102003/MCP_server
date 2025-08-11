from pydantic import BaseModel, Field
from typing import Iterable, Optional, List, Dict, Any
from langchain_core.tools import tool
from datetime import datetime
import requests, re, json

from services.smart_search_service import step_combine, step_extract_urls, step_load_state, step_rewrite, step_scrape, step_search, step_summarize
from tools.scrape import get_webpage_content
from tools.summarize import summarize_text
from utils.env import get_env_variable
from utils.logger import log_event, report_progress
from utils.sse import chunk_text
from utils.state import STATE_STORE, SearchState, SearchTurn
from tools.rewrite import rewrite_query
from fastmcp import Context

class SmartSearchInput(BaseModel):
    session_id: str = Field(
        ...,
        description="Conversation/session identifier to persist context"
    )
    query: str = Field(
        ...,
        description="User's original query"
    )
    prefer_academic: Optional[bool] = Field(
        None,
        description="Prefer academic or scholarly sources if True"
    )
    time_range: Optional[str] = Field(
        None,
        description="Limit search to a specific time range, e.g., 'past_year', 'past_month'"
    )
    extra_sites: Optional[List[str]] = Field(
        None,
        description="Additional websites to prioritize in the search"
    )
    filetype_pdf: Optional[bool] = Field(
        None,
        description="If True, limit results to PDF files only"
    )
    target_language: Optional[str] = Field(
        None,
        description="Language code for translating or summarizing results, e.g., 'en', 'vi'"
    )

def _infer_prefs(q: SmartSearchInput) -> Dict[str, Any]:
    text = q.query.lower()
    prefer_academic = (
        q.prefer_academic
        if q.prefer_academic is not None
        else any(k in text for k in [
            "paper", "research", "survey", "sota", "benchmark",
            "peer-reviewed", "arxiv", "doi", "regulation", "law", "standard"
        ])
    )

    time_range = q.time_range
    if not time_range:
        if any(k in text for k in ["latest", "gần đây", "mới nhất", "this year"]):
            y = datetime.now().year
            time_range = f"{y}..{y+1}"

    filetype_pdf = (
        q.filetype_pdf
        if q.filetype_pdf is not None
        else prefer_academic or any(k in text for k in ["paper", "report", "whitepaper"])
    )

    extra_sites = q.extra_sites or []
    if "eu " in f" {text} " or "european union" in text or "eu ai act" in text:
        extra_sites = list(set(extra_sites + ["europa.eu"]))
    if re.search(r"\bwho\b", text):
        extra_sites = list(set(extra_sites + ["who.int"]))

    target_language = q.target_language
    if not target_language:
        if re.search(r"[àáảãạâầấẩẫậăằắẳẵặđèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵ]", q.query.lower()):
            target_language = "vi"
        else:
            target_language = "en"
        
    return dict(
        prefer_academic=prefer_academic,
        time_range=time_range,
        extra_sites=extra_sites or None,
        filetype_pdf=filetype_pdf,
        target_language=target_language
    )

def _tavily_search(raw_query: str) -> Dict[str, Any]:
    import time
    t0 = time.perf_counter()
    resp = requests.post(
        "https://api.tavily.com/search",
        json={"query": raw_query},
        headers={"Authorization": f"Bearer {get_env_variable('TAVILY_API_KEY')}"},
        timeout=20
    )
    latency_ms = int((time.perf_counter() - t0)*1000)
    resp.raise_for_status()
    data = resp.json()
    return {"raw": data, "latency_ms": latency_ms}

@tool(args_schema=SmartSearchInput)
def smart_search(**kwargs) -> str:
    """
    One-shot search with state:
    1) Load state by session_id
    2) Infer rewrite params (optionally combine with historical preferences)
    3) Rewrite via Gemini 2.5
    4) Tavily search
    5) Persist turn into state
    Return: JSON string { rewritten_query, used_query, result, state_meta }
    """
    args = SmartSearchInput(**kwargs)
    state = STATE_STORE.get(args.session_id) or SearchState(session_id=args.session_id)

    prefs = _infer_prefs(args)

    try:
        rewritten = rewrite_query.invoke({
            "query": args.query,
            **prefs
        }).strip()
        use_query = rewritten if rewritten else args.query
    except Exception:
        rewritten = None
        use_query = args.query

    sr = _tavily_search(use_query)
    raw = sr["raw"]
    latency_ms = sr["latency_ms"]

    top_urls = []
    if isinstance(raw, dict):
        hits = raw.get("results") or raw.get("data") or []
        for h in hits[:3]: 
            url = h.get("url") or h.get("link")
            if url:
                top_urls.append(url)

    scraped_contents = []
    for url in top_urls:
        try:
            content = get_webpage_content.invoke({"url": url})
            if content:
                scraped_contents.append(content)
        except Exception:
            continue

    historical_context = "\n\n".join(
        t.original_query + " → " + (t.rewritten_query or t.original_query)
        for t in state.turns[-3:] 
    )

    combined_text = "\n\n".join(scraped_contents)
    if historical_context:
        combined_text = f"Previous search context:\n{historical_context}\n\nCurrent content:\n{combined_text}"

    try:
        summary = summarize_text.invoke({
            "text": combined_text,
            "max_words": 250,
            "language": prefs.get("target_language"),
            "style": "balanced",
            "include_bullets": True,
            "title": args.query
        })
    except Exception:
        summary = None

    turn = SearchTurn(
        original_query=args.query,
        inferred_prefs=prefs,
        rewritten_query=rewritten,
        used_query=use_query,
        provider="tavily",
        result_meta={
            "top_urls": top_urls,
            "latency_ms": latency_ms,
            "summary": summary
        }
    )
    state.turns.append(turn)
    STATE_STORE.set(state)

    out = {
        "rewritten_query": rewritten,
        "used_query": use_query,
        "result": raw,
        "summary": summary,
        "state_meta": {
            "session_id": state.session_id,
            "turn_count": len(state.turns),
            "latest_top_urls": top_urls,
            "latency_ms": latency_ms
        }
    }
    return json.dumps(out, ensure_ascii=False)


async def smart_search_stream_mcp(
    session_id: str,
    query: str,
    prefer_academic: Optional[bool] = None,
    time_range: Optional[str] = None,
    extra_sites: Optional[List[str]] = None,
    filetype_pdf: Optional[bool] = None,
    target_language: Optional[str] = None,
    ctx: Context = None,
) -> Dict[str, Any]:
    await log_event(ctx, "info", f"smart_search start | session={session_id}", session_id=session_id)
    await report_progress(ctx, 1)

    state = await step_load_state(session_id, ctx)
    args = dict(
        session_id=session_id, query=query,
        prefer_academic=prefer_academic, time_range=time_range,
        extra_sites=extra_sites, filetype_pdf=filetype_pdf, target_language=target_language
    )
    prefs = _infer_prefs(type("Tmp", (), args)) 
    await log_event(ctx, "info", f"prefs inferred | {prefs}", session_id=session_id)
    await report_progress(ctx, 7)

    rewritten, use_query = await step_rewrite(query, prefs, ctx)
    raw, latency_ms = await step_search(use_query, ctx)
    urls = step_extract_urls(raw)
    scraped = await step_scrape(urls, ctx)
    combined = step_combine(state, scraped)
    await log_event(ctx, "info", f"combine ready | total_chars={len(combined)} | has_history={combined.startswith('Previous search context:')}")
    summary = await step_summarize(combined, query, prefs.get("target_language"), ctx)

    turn = SearchTurn(
        original_query=query,
        inferred_prefs=prefs,
        rewritten_query=rewritten,
        used_query=use_query,
        provider="tavily",
        result_meta={"top_urls": urls, "latency_ms": latency_ms, "summary": summary}
    )
    state.turns.append(turn)
    STATE_STORE.set(state)
    await log_event(ctx, "info", "state persisted")
    await report_progress(ctx, 100)

    return {
        "rewritten_query": rewritten,
        "used_query": use_query,
        "result": raw,
        "summary": summary,
        "state_meta": {
            "session_id": state.session_id,
            "turn_count": len(state.turns),
            "latest_top_urls": urls,
            "latency_ms": latency_ms
        }
    }