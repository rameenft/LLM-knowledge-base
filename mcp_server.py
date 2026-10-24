"""MCP server exposing the knowledge base to AI assistants (stdio transport).

The server is a thin, read-only client of the REST API in function_app.py, so the API remains
the single place where validation, auth and logging happen. Configuration (env vars):

    KB_API_URL   base URL of the API       (default http://localhost:7071/api)
    KB_API_KEY   Azure Functions key       (optional locally; required against a deployed app)

Tools (all read-only):
    search_documents(query, top_k)   ranked wiki articles for a query
    answer_question(question)        Gemini answer with citations
    list_articles()                  names of available articles

Deliberately NOT exposed: the ingest endpoint. Assistants can read, never modify, the corpus.
"""

import os

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("llm-knowledge-base")


def _client() -> httpx.Client:
    headers = {}
    if key := os.environ.get("KB_API_KEY"):
        headers["x-functions-key"] = key
    return httpx.Client(
        base_url=os.environ.get("KB_API_URL", "http://localhost:7071/api").rstrip("/") + "/",
        headers=headers,
        timeout=60.0,
    )


def _call(method: str, path: str, payload: dict | None = None) -> dict:
    """Call the API; turn failures into short messages that are safe to show an assistant."""
    try:
        with _client() as client:
            resp = client.request(method, path, json=payload)
    except httpx.HTTPError:
        raise RuntimeError("The knowledge base API is unreachable.") from None
    if resp.status_code in (401, 403):
        raise RuntimeError("The knowledge base API rejected the credentials (check KB_API_KEY).")
    try:
        body = resp.json()
    except ValueError:
        raise RuntimeError(f"Unexpected response from the API (HTTP {resp.status_code}).") from None
    if resp.status_code >= 400:
        message = body.get("error", {}).get("message", "request failed")
        raise RuntimeError(f"{message} (HTTP {resp.status_code}, request_id={body.get('request_id', 'n/a')})")
    return body


@mcp.tool()
def search_documents(query: str, top_k: int = 4) -> dict:
    """Find the wiki articles most relevant to a query. Returns article names with similarity scores
    (0-1, higher is closer). Use list_articles / answer_question to go further."""
    body = _call("POST", "search", {"query": query, "top_k": top_k})
    return {"query": body["query"], "results": body["results"]}


@mcp.tool()
def answer_question(question: str) -> dict:
    """Answer a question using only the knowledge base, citing the articles used."""
    body = _call("POST", "answer", {"question": question})
    return {"answer": body["answer"], "sources": body["sources"]}


@mcp.tool()
def list_articles() -> dict:
    """List the names of all articles in the knowledge base."""
    return {"articles": _call("GET", "articles")["articles"]}


if __name__ == "__main__":
    mcp.run(transport="stdio")
