
from __future__ import annotations

from typing import Optional, Literal, List
from pydantic import BaseModel, Field
from langchain_core.tools import tool
import google.generativeai as genai
from utils.env import get_env_variable
from utils.prompt import build_chunk_prompt, build_merge_prompt

GEMINI_MODEL = "gemini-2.5-pro"
CHUNK_SIZE = 6000
CHUNK_OVERLAP = 400

def _get_model():
    genai.configure(api_key=get_env_variable("GEMINI_API_KEY"))
    return genai.GenerativeModel(GEMINI_MODEL)

class SummarizeInput(BaseModel):
    text: str = Field(..., description="Raw text to summarize")
    max_words: int = Field(200, ge=50, le=1200, description="Maximum words for the final summary")
    language: Optional[Literal["vi", "en"]] = Field(
        default=None, description="Force output language: 'vi' or 'en' (auto if None)"
    )
    style: Optional[Literal["concise", "balanced", "detailed"]] = Field(
        default="balanced", description="Summary style preference"
    )
    include_bullets: bool = Field(
        default=True, description="Include key bullet points in the output"
    )
    title: Optional[str] = Field(
        default=None, description="Optional title/topic to anchor the summary"
    )

# ============== Chunking ==============
def _chunk_text(s: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    s = s.strip()
    if len(s) <= chunk_size:
        return [s]
    chunks = []
    start = 0
    while start < len(s):
        end = min(start + chunk_size, len(s))
        chunks.append(s[start:end])
        if end == len(s):
            break
        start = max(0, end - overlap)
    return chunks

def _summarize_chunk(model, chunk: str, language: Optional[str], style: str, include_bullets: bool) -> str:
    prompt = build_chunk_prompt(chunk, language, style, include_bullets)
    resp = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.2,
            max_output_tokens=800, 
        ),
    )
    return (getattr(resp, "text", "") or "").strip()

def _merge_summaries(model, parts: List[str], language: Optional[str], style: str, max_words: int, title: Optional[str], include_bullets: bool) -> str:
    prompt = build_merge_prompt(parts, language, style, max_words, title, include_bullets)
    resp = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.2,
            max_output_tokens=600,
        ),
    )
    return (getattr(resp, "text", "") or "").strip()

@tool(args_schema=SummarizeInput)
def summarize_text(**kwargs) -> str:
    """
    Summarize long text safely with Gemini 2.5.
    - Auto-chunk long input, summarize per chunk, then merge into a coherent final summary.
    - Parameters: max_words, language ('vi'/'en'), style ('concise'|'balanced'|'detailed'), include_bullets, title.
    """
    args = SummarizeInput(**kwargs)
    model = _get_model()

    chunks = _chunk_text(args.text)
    part_summaries = []
    for ch in chunks:
        s = _summarize_chunk(model, ch, args.language, args.style, args.include_bullets)
        if s:
            part_summaries.append(s)

    if not part_summaries:
        return "No summary could be generated."

    final = _merge_summaries(model, part_summaries, args.language, args.style, args.max_words, args.title, args.include_bullets)
    return final or "\n\n".join(part_summaries)
