from langchain_core.tools import tool
from pydantic import BaseModel, Field
import requests
from bs4 import BeautifulSoup

class ScrapeInput(BaseModel):
    url: str = Field(..., description="The URL of the webpage to scrape")

@tool(args_schema=ScrapeInput)
def get_webpage_content(url: str) -> str:
    """Download and extract readable text content from a webpage."""
    try:
        resp = requests.get(url, timeout=15, headers={
            "User-Agent": "Mozilla/5.0 (compatible; MCPBot/1.0)"
        })
        resp.raise_for_status()
    except Exception as e:
        return f"Error fetching URL: {e}"

    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.extract()

    text = soup.get_text(separator="\n", strip=True)

    if len(text) > 10000:
        text = text[:10000] + "\n...[TRUNCATED]..."

    return text
