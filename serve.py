"""
Launches the ResearchOS web interface.

    python serve.py                # http://localhost:8080
    python serve.py --port 9000
    python serve.py --host 127.0.0.1 --reload   # local dev

No project scaffolding is required beforehand -- on first visit the app
walks you through creating the login account and configuring provider
API keys + which model powers each agent, then you can submit goals from
the browser the same way `run.py` does from the CLI.
"""
import argparse

import uvicorn

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the ResearchOS web UI.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    uvicorn.run("web.app:app", host=args.host, port=args.port, reload=args.reload)
