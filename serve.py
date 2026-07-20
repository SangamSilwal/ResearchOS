"""
Launches the ResearchOS web API.

    python serve.py                # http://localhost:8080
    python serve.py --port 9000
    python serve.py --host 127.0.0.1 --reload   # local dev

JSON API only -- see README.md's "Web API" section for setup (Postgres
migration, OAuth app credentials) and endpoints. Log in via
GET /auth/google/login or /auth/github/login, then use the returned JWT
as an Authorization: Bearer header for everything else.
"""
import argparse

import uvicorn

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the ResearchOS web API.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    uvicorn.run("web.app:app", host=args.host, port=args.port, reload=args.reload)
