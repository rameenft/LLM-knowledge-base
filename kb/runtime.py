"""Process-wide wiring for the Functions app and CLI: builds storage, KB, and pipeline runs lazily."""

from functools import lru_cache

from . import answer, pipeline, storage
from .service import KnowledgeBase


@lru_cache(maxsize=1)
def get_storage():
    return storage.from_env()


@lru_cache(maxsize=1)
def get_kb() -> KnowledgeBase:
    return KnowledgeBase(get_storage())


def run_ingestion(force: bool = False) -> pipeline.RunReport:
    return pipeline.run_pipeline(get_storage(), answer.get_client(), force=force)
