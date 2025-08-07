import pytest
from main import tavily_search

@pytest.mark.integration
def test_tavily_search_real():
    query = "transformer là gì"
    result = tavily_search.invoke({"query": query})

    print("Real result:", result)
    assert "transformer" in result.lower() or len(result) > 10
