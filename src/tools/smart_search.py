from pydantic import BaseModel, Field
from typing import Iterable, Optional, List, Dict, Any
from langchain_core.tools import tool
from datetime import datetime
import requests, re, json

from tools.scrape import get_webpage_content
from tools.summarize import summarize_text
from utils.env import get_env_variable
from utils.sse import chunk_text
from utils.state import STATE_STORE, SearchState, SearchTurn
from tools.rewrite import rewrite_query

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


def smart_search_stream(**kwargs) -> Iterable[Dict[str, Any]]:

    args = SmartSearchInput(**kwargs)
    yield {"event": "start", "session_id": args.session_id, "query": args.query}

    state: SearchState = STATE_STORE.get(args.session_id) or SearchState(session_id=args.session_id)
    yield {"event": "state_loaded", "turn_count": len(state.turns)}

    prefs = _infer_prefs(args)
    yield {"event": "prefs_inferred", "prefs": prefs}

    yield {"event": "rewrite_started", "query": args.query}
    try:
        rewritten = rewrite_query.invoke({"query": args.query, **prefs}).strip()
        use_query = rewritten if rewritten else args.query
        yield {"event": "rewrite_done", "rewritten_query": rewritten, "used_query": use_query}
    except Exception as e:
        rewritten = None
        use_query = args.query
        yield {"event": "rewrite_failed", "error": str(e), "used_query": use_query}

    yield {"event": "search_started", "used_query": use_query}
    sr = _tavily_search(use_query) 
    raw = sr.get("raw")
    latency_ms = sr.get("latency_ms")
    yield {"event": "search_meta", "latency_ms": latency_ms}

    top_urls: List[str] = []
    if isinstance(raw, dict):
        hits = raw.get("results") or raw.get("data") or []
        for h in hits[:3]:
            url = h.get("url") or h.get("link")
            if url:
                top_urls.append(url)
    yield {"event": "search_top_urls", "top_urls": top_urls}

    scraped_contents: List[str] = []
    for url in top_urls:
        yield {"event": "scrape_started", "url": url}
        try:
            content = get_webpage_content.invoke({"url": url})  # string dài
            if content:
                scraped_contents.append(content)
                for i, chunk in enumerate(chunk_text(content, size=2000)):
                    yield {"event": "scrape_chunk", "url": url, "index": i, "content": chunk}
                yield {"event": "scrape_done", "url": url, "length": len(content)}
            else:
                yield {"event": "scrape_empty", "url": url}
        except Exception as e:
            yield {"event": "scrape_failed", "url": url, "error": str(e)}

    historical_context = "\n\n".join(
        t.original_query + " → " + (t.rewritten_query or t.original_query)
        for t in state.turns[-3:]
    )
    combined_text = "\n\n".join(scraped_contents)
    if historical_context:
        combined_text = f"Previous search context:\n{historical_context}\n\nCurrent content:\n{combined_text}"

    yield {
        "event": "combine_ready",
        "has_history": bool(historical_context),
        "combined_chars": len(combined_text)
    }

    yield {"event": "summary_started"}
    try:
        summary = summarize_text.invoke({
            "text": combined_text,
            "max_words": 250,
            "language": prefs.get("target_language"),
            "style": "balanced",
            "include_bullets": True,
            "title": args.query
        })
        if isinstance(summary, str):
            for i, chunk in enumerate(chunk_text(summary, size=1200)):
                yield {"event": "summary_chunk", "index": i, "content": chunk}
        yield {"event": "summary_done"}
    except Exception as e:
        summary = None
        yield {"event": "summary_failed", "error": str(e)}

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
    yield {"event": "end", "final": out}