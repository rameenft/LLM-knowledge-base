"""Framework-free HTTP handlers: (parsed JSON body) -> (status, JSON-serialisable dict).

Kept separate from Azure Functions so validation and error mapping are unit-testable.
Internal exception details are logged, never returned to the caller.
"""

import logging
import uuid

from .config import ConfigError
from .logging_utils import log_event
from .storage import StorageError

logger = logging.getLogger("kb.api")

MAX_QUERY_CHARS = 1000
MAX_TOP_K = 10
DEFAULT_TOP_K = 4


def _error(status: int, code: str, message: str, request_id: str):
    return status, {"error": {"code": code, "message": message}, "request_id": request_id}


def _validate_text(body, field: str):
    if not isinstance(body, dict):
        return None, "Request body must be a JSON object."
    value = body.get(field)
    if not isinstance(value, str) or not value.strip():
        return None, f"'{field}' is required and must be a non-empty string."
    if len(value) > MAX_QUERY_CHARS:
        return None, f"'{field}' must be at most {MAX_QUERY_CHARS} characters."
    return value.strip(), None


def _validate_top_k(body):
    top_k = body.get("top_k", DEFAULT_TOP_K)
    if isinstance(top_k, bool) or not isinstance(top_k, int) or not 1 <= top_k <= MAX_TOP_K:
        return None, f"'top_k' must be an integer between 1 and {MAX_TOP_K}."
    return top_k, None


def _guard(handler_name: str, request_id: str, fn):
    try:
        return fn()
    except ConfigError:
        log_event(logger, "service_not_configured", logging.ERROR, handler=handler_name, request_id=request_id)
        return _error(503, "service_not_configured", "The service is missing required configuration.", request_id)
    except ValueError as e:  # e.g. empty knowledge base
        log_event(logger, "knowledge_base_empty", logging.WARNING, handler=handler_name, request_id=request_id, error=str(e))
        return _error(503, "knowledge_base_empty", "The knowledge base has no content yet.", request_id)
    except StorageError as e:
        log_event(logger, "storage_error", logging.ERROR, handler=handler_name, request_id=request_id, error=str(e))
        return _error(503, "storage_unavailable", "Storage is temporarily unavailable.", request_id)
    except Exception as e:
        log_event(logger, "unhandled_error", logging.ERROR, handler=handler_name, request_id=request_id,
                  error_type=type(e).__name__, error=str(e)[:300])
        return _error(502, "upstream_error", "The request could not be completed.", request_id)


def handle_search(kb, body):
    request_id = uuid.uuid4().hex
    query, err = _validate_text(body, "query")
    if err:
        return _error(400, "invalid_request", err, request_id)
    top_k, err = _validate_top_k(body)
    if err:
        return _error(400, "invalid_request", err, request_id)

    def run():
        results = kb.search(query, top_k)
        log_event(logger, "search", request_id=request_id, top_k=top_k, results=len(results))
        return 200, {"query": query, "results": results, "request_id": request_id}

    return _guard("search", request_id, run)


def handle_answer(kb, body):
    request_id = uuid.uuid4().hex
    question, err = _validate_text(body, "question")
    if err:
        return _error(400, "invalid_request", err, request_id)

    def run():
        ans = kb.answer(question)
        log_event(logger, "answer", request_id=request_id, sources=ans.sources)
        return 200, {"question": question, "answer": ans.text, "sources": ans.sources,
                     "scores": ans.scores, "request_id": request_id}

    return _guard("answer", request_id, run)


def handle_articles(kb):
    request_id = uuid.uuid4().hex
    return _guard("articles", request_id, lambda: (200, {"articles": kb.list_articles(), "request_id": request_id}))


def handle_ingest(run_pipeline_fn):
    request_id = uuid.uuid4().hex

    def run():
        report = run_pipeline_fn()
        return (200 if report.ok else 207), {**report.to_dict(), "request_id": request_id}

    return _guard("ingest", request_id, run)
