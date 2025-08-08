### Running 
```
# STDIO
python src/main.py --mode stdio

# HTTP (SSE)  http://localhost:8000/mcp/
python src/main.py --mode http --host 0.0.0.0 --port 8000 --path /mcp
```