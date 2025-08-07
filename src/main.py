from fastapi import FastAPI
from langchain_core.tools import tool
from pydantic import BaseModel
import requests
from src.utils.env import get_env_variable

class TavilySearchInput(BaseModel):
    query: str

app = FastAPI()

@tool(args_schema=TavilySearchInput)
def tavily_search(query: str) -> str:
    """Search the web using Tavily"""
    response = requests.post( 
        "https://api.tavily.com/search",
        json={"query": query}, 
        headers={"Authorization": f"Bearer {get_env_variable('TAVILY_API_KEY')}"}
    )
    return response.text

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
