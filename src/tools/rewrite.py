from pydantic import BaseModel, Field
from typing import Optional, List
from langchain_core.tools import tool
from utils.env import get_env_variable
import google.generativeai as genai
from utils.prompt import build_rewrite_prompt

class RewriteQueryInput(BaseModel):
    query: str = Field(..., description="Original natural language query")
    prefer_academic: bool = Field(default=False, description="Bias towards academic/government sources")
    time_range: Optional[str] = Field(default=None, description='Optional year range like "2023..2025"')
    extra_sites: Optional[List[str]] = Field(default=None, description="Optional list of site: filters")
    filetype_pdf: bool = Field(default=False, description="Add filetype:pdf for reports/papers")
    target_language: Optional[str] = Field(default=None, description="Force output language (e.g., 'en', 'vi')")

@tool(args_schema=RewriteQueryInput)
def rewrite_query(**kwargs) -> str:
    """Rewrite the query to be more suitable for web search via Gemini 2.5"""
    genai.configure(api_key=get_env_variable("GEMINI_API_KEY"))
    model = genai.GenerativeModel("gemini-2.5-pro")

    prompt = build_rewrite_prompt(**kwargs)

    resp = model.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0,
            max_output_tokens=64,
        )
    )
    return (resp.text or "").strip()