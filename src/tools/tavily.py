from langchain_core.tools import tool
from pydantic import BaseModel
import requests
from utils.env import get_env_variable

class TavilySearchInput(BaseModel):
    query: str


@tool(args_schema=TavilySearchInput)
def tavily_search(query: str) -> str:
    """Search the web using Tavily API"""
    response = requests.post(
        "https://api.tavily.com/search",
        json={"query": query},
        headers={"Authorization": f"Bearer {get_env_variable('TAVILY_API_KEY')}"}
    )
    return response.text
