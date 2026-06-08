#!/usr/bin/env python
"""
HTTP/SSE wrapper for Chicago Marine Knowledge MCP.
"""

import os

import uvicorn
from fastapi import FastAPI

from server import mcp


app = FastAPI(title="Chicago Marine Knowledge MCP")


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "chicago-marine-knowledge-mcp"}


app.mount("/", mcp.sse_app())


def run():
    port = int(os.getenv("PORT", 3000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    run()
