"""Azure Functions entry point (Python v2 programming model).

Routes (all under /api):
    GET  /health    anonymous liveness probe
    POST /search    {"query": str, "top_k": int?}          -> ranked article hits
    POST /answer    {"question": str}                      -> cited Gemini answer
    GET  /articles  list article names
    POST /ingest    run the ingestion pipeline now
Timer: runs the same pipeline daily; it is a no-op (no Gemini calls) when raw notes are unchanged.

Auth: non-health routes use AuthLevel.FUNCTION, i.e. callers must send a function key
(`x-functions-key` header or `?code=`). Keys are generated and held by the Functions host,
not by this repo. See docs/SECURITY.md for the Entra ID upgrade path.
"""

import json
import logging

import azure.functions as func

from kb import api, runtime
from kb.logging_utils import log_event

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
MAX_BODY_BYTES = 10_000


def _respond(status_body) -> func.HttpResponse:
    status, body = status_body
    return func.HttpResponse(json.dumps(body), status_code=status, mimetype="application/json")


def _json_body(req: func.HttpRequest):
    raw = req.get_body()
    if len(raw) > MAX_BODY_BYTES:
        return None, _respond((413, {"error": {"code": "payload_too_large", "message": "Request body too large."}}))
    try:
        return json.loads(raw or b"null"), None
    except ValueError:
        return None, _respond((400, {"error": {"code": "invalid_json", "message": "Body is not valid JSON."}}))


@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health(req: func.HttpRequest) -> func.HttpResponse:
    return _respond((200, {"status": "ok"}))


@app.route(route="search", methods=["POST"])
def search(req: func.HttpRequest) -> func.HttpResponse:
    body, err = _json_body(req)
    return err or _respond(api.handle_search(runtime.get_kb(), body))


@app.route(route="answer", methods=["POST"])
def answer(req: func.HttpRequest) -> func.HttpResponse:
    body, err = _json_body(req)
    return err or _respond(api.handle_answer(runtime.get_kb(), body))


@app.route(route="articles", methods=["GET"])
def articles(req: func.HttpRequest) -> func.HttpResponse:
    return _respond(api.handle_articles(runtime.get_kb()))


@app.route(route="ingest", methods=["POST"])
def ingest(req: func.HttpRequest) -> func.HttpResponse:
    return _respond(api.handle_ingest(runtime.run_ingestion))


@app.timer_trigger(schedule="0 0 6 * * *", arg_name="timer", run_on_startup=False)
def scheduled_ingest(timer: func.TimerRequest) -> None:
    report = runtime.run_ingestion()
    log_event(logging.getLogger("kb.timer"), "scheduled_ingest", ok=report.ok, **{
        k: len(v) for k, v in (("compiled", report.compiled), ("skipped", report.skipped),
                               ("failed", report.failed), ("quarantined", report.quarantined))})
    if not report.ok:
        raise RuntimeError(f"Ingestion finished with failures: {sorted(report.failed)}")
