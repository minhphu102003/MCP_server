from typing import Optional, Literal, List

def build_rewrite_prompt(user_query: str,
                         prefer_academic: bool = False,
                         time_range: str = None,
                         extra_sites: list[str] = None,
                         filetype_pdf: bool = False,
                         target_language: str = None) -> str:
    """
    Build a search query rewriting prompt for LLMs (e.g., Gemini 2.5).
    """

    base = f"""
You are a query rewriting assistant for web search engines (e.g., Tavily/Google).
Your task: convert a natural-language question into a concise, keyword-optimized search query.

Rules:
- Keep only high-signal keywords and entities. Remove filler words (“how”, “what”, “does”, etc.).
- Prefer nouns and key verb phrases; include common synonyms if helpful.
- {"Bias toward academic sources (e.g., site:gov, site:edu, arxiv.org, aclweb.org, nih.gov, nature.com)." if prefer_academic else "Use general high-quality sources."}
- When academic bias is ON, consider adding site filters and filetype:pdf for research papers.
- Keep the query under ~15 words where possible.
- Do NOT answer the question. Output only the rewritten query text.
- Language: {"use the specified target language: " + target_language if target_language else "keep the output in the same language as the user’s query"}.

If helpful, add:
- time filters (e.g., “2023..2025”)
- domain constraints (site:gov, site:edu or provided sites)
- format filters (filetype:pdf)

Examples:
User: "How does AI help agriculture?"
Output: AI applications in agriculture site:gov site:edu filetype:pdf

User: "Latest research about large language models safety"
Output: large language models safety survey site:arxiv.org site:acm.org 2023..2025 filetype:pdf

User: "What are European Union regulations on AI transparency?"
Output: EU AI Act transparency requirements site:europa.eu 2023..2025

User: "Best practices for RAG evaluation"
Output: retrieval augmented generation evaluation best practices site:arxiv.org site:aclweb.org filetype:pdf
"""

    sites = []
    if prefer_academic:
        sites += [
            "site:gov", "site:edu", "site:arxiv.org", "site:nih.gov",
            "site:nature.com", "site:acm.org", "site:ieee.org", "site:aclweb.org"
        ]
    if extra_sites:
        sites += [f"site:{s}" if not s.startswith("site:") else s for s in extra_sites]

    site_clause = " ".join(dict.fromkeys(sites)) if sites else ""
    time_clause = f" {time_range}" if time_range else ""
    pdf_clause = " filetype:pdf" if (filetype_pdf or prefer_academic) else ""

    tail = f"""
Now rewrite this query for web search:
"{user_query}"

If useful, you may append: "{site_clause}{time_clause}{pdf_clause}". 
Return only the rewritten query.
"""
    return base.strip() + "\n" + tail.strip()


def build_chunk_prompt(chunk: str, language: Optional[str], style: str, include_bullets: bool) -> str:
    lang_line = (
        "Write the summary in Vietnamese."
        if language == "vi"
        else "Write the summary in English." if language == "en"
        else "Write the summary in the same language as the input."
    )
    style_map = {
        "concise": "Be highly concise, only critical points.",
        "balanced": "Be concise but keep key context and facts.",
        "detailed": "Be more detailed, but avoid redundancy."
    }
    bullets_line = "Add a short bullet list of key takeaways at the end." if include_bullets else "Do not add bullet lists."

    return f"""
You are a professional summarization assistant.
Summarize the following content faithfully with no hallucinations.

Rules:
- {lang_line}
- {style_map.get(style, style_map["balanced"])}
- Keep names, figures, citations if present.
- Do not invent facts; if unsure, say 'unknown' or omit.
- Preserve important entities (people, orgs, dates, numbers).
- Use neutral tone and avoid opinions.
- {bullets_line}

Content:
\"\"\"{chunk}\"\"\"
"""

def build_merge_prompt(part_summaries: List[str], language: Optional[str], style: str, max_words: int, title: Optional[str], include_bullets: bool) -> str:
    lang_line = (
        "Write the final summary in Vietnamese."
        if language == "vi"
        else "Write the final summary in English." if language == "en"
        else "Use the same language as the input."
    )
    bullets_line = "Include a brief bullet list of key takeaways at the end." if include_bullets else "Do not include bullet lists."

    title_line = f"Title/Topic to anchor: {title}\n" if title else ""

    joined = "\n\n---\n\n".join(part_summaries)
    return f"""
You previously summarized multiple parts of a long document. Merge them into ONE coherent summary
of no more than ~{max_words} words.

{title_line}
Guidelines:
- {lang_line}
- Keep chronology and logical flow.
- Remove duplicates and contradictions across parts.
- Prefer facts over opinions; avoid hallucinations.
- If there are numbers/dates, keep them accurate.
- {bullets_line}

Partial summaries:
\"\"\"{joined}\"\"\"
"""