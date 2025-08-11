from typing import List, Dict, Any, Optional, Tuple
from fastmcp import Context
from tools.rewrite import rewrite_query
from tools.scrape import get_webpage_content
from tools.smart_search import _tavily_search
from tools.summarize import summarize_text
from utils.sse import chunk_text
from utils.state import STATE_STORE, SearchState, SearchTurn
from utils.logger import log_event, report_progress

async def step_load_state(session_id: str, ctx: Optional[Context]) -> SearchState:
    state = STATE_STORE.get(session_id) or SearchState(session_id=session_id)
    await log_event(ctx, "info", f"state loaded | recent_turns={len(state.turns)}", session_id=session_id)
    await report_progress(ctx, 3)
    return state

async def step_rewrite(query: str, prefs: Dict[str, Any], ctx: Optional[Context]) -> Tuple[Optional[str], str]:
    await log_event(ctx, "info", "rewriting query…")
    try:
        rewritten = rewrite_query.invoke({"query": query, **prefs}).strip()
        use_query = rewritten or query
        await log_event(ctx, "info", f"rewrite done → {use_query}")
        await report_progress(ctx, 15)
        return rewritten, use_query
    except Exception as e:
        await log_event(ctx, "warning", f"rewrite failed, fallback | {e!r}")
        await report_progress(ctx, 15)
        return None, query

async def step_search(use_query: str, ctx: Optional[Context]) -> Tuple[Dict[str, Any], int]:
    await log_event(ctx, "info", f"searching: {use_query}")
    sr = _tavily_search(use_query)
    raw = sr.get("raw")
    latency_ms = sr.get("latency_ms")
    await log_event(ctx, "info", f"search latency: {latency_ms} ms")
    await report_progress(ctx, 35)
    return raw, latency_ms

def step_extract_urls(raw: Dict[str, Any]) -> List[str]:
    urls: List[str] = []
    if isinstance(raw, dict):
        hits = raw.get("results") or raw.get("data") or []
        for h in hits[:3]:
            url = h.get("url") or h.get("link")
            if url:
                urls.append(url)
    return urls

async def step_scrape(urls: List[str], ctx: Optional[Context]) -> List[str]:
    await log_event(ctx, "info", f"top URLs: {urls}")
    await report_progress(ctx, 40)
    scraped: List[str] = []
    if not urls:
        await log_event(ctx, "info", "no URLs to scrape")
        return scraped

    per_url_step = 40 // max(1, len(urls))
    base = 40
    for i, url in enumerate(urls, start=1):
        await log_event(ctx, "info", f"scraping [{i}/{len(urls)}]: {url}")
        try:
            content: str = get_webpage_content.invoke({"url": url}) or ""
            if content:
                scraped.append(content)
                for j, chunk in enumerate(chunk_text(content, size=1200)):
                    if j >= 3:
                        await log_event(ctx, "debug", f"(truncated preview for {url})")
                        break
                    await log_event(ctx, "info", f"{url} · chunk {j+1}\n{chunk[:1200]}")
                await log_event(ctx, "info", f"scraped {url} | chars={len(content)}")
            else:
                await log_event(ctx, "warning", f"empty content: {url}")
        except Exception as e:
            await log_event(ctx, "error", f"scrape failed: {url} | {e!r}")
        await report_progress(ctx, min(base + i * per_url_step, 80))
    return scraped

def step_combine(state: SearchState, scraped: List[str]) -> str:
    historical = "\n\n".join(
        t.original_query + " → " + (t.rewritten_query or t.original_query)
        for t in state.turns[-3:]
    )
    combined = "\n\n".join(scraped)
    if historical:
        combined = f"Previous search context:\n{historical}\n\nCurrent content:\n{combined}"
    return combined

async def step_summarize(combined: str, query: str, target_language: Optional[str], ctx: Optional[Context]) -> Optional[str]:
    await log_event(ctx, "info", "summarizing…")
    try:
        summary = summarize_text.invoke({
            "text": combined,
            "max_words": 250,
            "language": target_language,
            "style": "balanced",
            "include_bullets": True,
            "title": query
        })
        if isinstance(summary, str) and summary:
            for k, c in enumerate(chunk_text(summary, size=800)):
                await log_event(ctx, "info", f"summary chunk {k+1}:\n{c}")
        await log_event(ctx, "info", "summary done")
        await report_progress(ctx, 92)
        return summary
    except Exception as e:
        await log_event(ctx, "error", f"summary failed | {e!r}")
        await report_progress(ctx, 92)
        return None