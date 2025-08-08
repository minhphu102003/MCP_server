import argparse
from stdio.run_stdio_server import run_stdio_server
from sse.run_http_server import run_http_server

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["stdio", "http"], default="stdio")
    args = parser.parse_args()

    if args.mode == "stdio":
        run_stdio_server()
    else:
        run_http_server()
