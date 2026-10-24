import asyncio
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import httpx
import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

import mcp_server

ROOT = Path(__file__).resolve().parent.parent
SEEN_HEADERS: list[dict] = []


class Stub(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        SEEN_HEADERS.append(dict(self.headers))
        self._send(200, {"articles": ["A", "B"]})

    def do_POST(self):
        SEEN_HEADERS.append(dict(self.headers))
        body = json.loads(self.rfile.read(int(self.headers["content-length"])))
        if self.path.endswith("/search"):
            if body.get("query") == "boom":
                return self._send(400, {"error": {"code": "invalid_request", "message": "bad"}, "request_id": "r1"})
            return self._send(200, {"query": body["query"], "results": [{"topic": "A", "score": 0.9}], "request_id": "r"})
        self._send(200, {"answer": "42", "sources": ["A"], "request_id": "r"})


@pytest.fixture
def stub_api():
    server = HTTPServer(("127.0.0.1", 0), Stub)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    SEEN_HEADERS.clear()
    yield f"http://127.0.0.1:{server.server_port}/api"
    server.shutdown()


def test_tools_call_api_and_send_key(stub_api, monkeypatch):
    monkeypatch.setenv("KB_API_URL", stub_api)
    monkeypatch.setenv("KB_API_KEY", "test-key")
    assert mcp_server.search_documents("x")["results"][0]["topic"] == "A"
    assert mcp_server.answer_question("q") == {"answer": "42", "sources": ["A"]}
    assert mcp_server.list_articles() == {"articles": ["A", "B"]}
    assert all(h.get("x-functions-key") == "test-key" for h in SEEN_HEADERS)


def test_api_errors_become_safe_messages(stub_api, monkeypatch):
    monkeypatch.setenv("KB_API_URL", stub_api)
    with pytest.raises(RuntimeError, match=r"bad \(HTTP 400, request_id=r1\)"):
        mcp_server.search_documents("boom")


def test_unreachable_api_message(monkeypatch):
    monkeypatch.setenv("KB_API_URL", "http://127.0.0.1:1/api")
    with pytest.raises(RuntimeError, match="unreachable"):
        mcp_server.list_articles()


def test_auth_rejection_message(monkeypatch):
    monkeypatch.setattr(mcp_server, "_client", lambda: httpx.Client(
        base_url="http://x/", transport=httpx.MockTransport(lambda r: httpx.Response(401))))
    with pytest.raises(RuntimeError, match="KB_API_KEY"):
        mcp_server.list_articles()


def test_only_read_only_tools_are_exposed():
    names = {t.name for t in asyncio.run(mcp_server.mcp.list_tools())}
    assert names == {"search_documents", "answer_question", "list_articles"}


def test_real_mcp_client_over_stdio(stub_api):
    """Spawn the server as a subprocess and talk to it with the official MCP client."""
    params = StdioServerParameters(
        command=sys.executable, args=[str(ROOT / "mcp_server.py")],
        env={**os.environ, "KB_API_URL": stub_api, "KB_API_KEY": "k"})

    async def go():
        async with stdio_client(params) as (r, w):
            async with ClientSession(r, w) as session:
                await session.initialize()
                tools = {t.name for t in (await session.list_tools()).tools}
                res = await session.call_tool("search_documents", {"query": "sad", "top_k": 2})
                err = await session.call_tool("search_documents", {"query": "boom"})
                return tools, res, err

    tools, res, err = asyncio.run(asyncio.wait_for(go(), 60))
    assert tools == {"search_documents", "answer_question", "list_articles"}
    assert not res.isError and "0.9" in res.content[0].text
    assert err.isError and "request_id=r1" in err.content[0].text
