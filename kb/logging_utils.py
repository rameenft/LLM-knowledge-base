"""Structured (JSON) logging helpers.

Each event is one JSON object in the log message, so it is greppable locally and
queryable in Application Insights (`traces | extend e = parse_json(message)`).
"""

import json
import logging


def log_event(logger: logging.Logger, event: str, level: int = logging.INFO, **fields) -> None:
    logger.log(level, json.dumps({"event": event, **fields}, default=str, sort_keys=True))
