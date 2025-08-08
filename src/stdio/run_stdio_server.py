import sys
import json
from tools.tavily import tavily_search
from tools.smart_search import smart_search, SmartSearchInput

def run_stdio_server():
  """
  Run the MCP server over stdio (JSON-RPC).
  Read requests from stdin, process them, and send responses to stdout.
  """
  for line in sys.stdin:
    try:
      req = json.loads(line.strip())
      method = req.get("method")
      params = req.get("params", {}) or {}
      req_id = req.get("id")

      if method == "list_tools":
        result = [
          {"name": "tavily_search", "description": "Search web via Tavily"},
          {"name": "smart_search", "description": "One-shot search with state, rewrite, scrape, summarize"}
        ]
        resp = {"id": req_id, "result": result}

      elif method == "invoke_tool":
        name = params.get("name")
        args = params.get("arguments", {}) or {}

        if name == "tavily_search":
          out = tavily_search.invoke(args) 
          resp = {"id": req_id, "result": out}

        elif name == "smart_search":
          try:
            SmartSearchInput(**args)  
          except Exception as e:
            resp = {"id": req_id, "error": f"Invalid arguments: {e}"}
          else:
            out = smart_search.invoke(args) 
            resp = {"id": req_id, "result": out}

        else:
          resp = {"id": req_id, "error": f"Unknown tool: {name}"}

      else:
        resp = {"id": req_id, "error": f"Unknown method: {method}"}

    except Exception as e:
      resp = {"id": req.get("id"), "error": str(e)}

    sys.stdout.write(json.dumps(resp) + "\n")
    sys.stdout.flush()