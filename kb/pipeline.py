"""Incremental, idempotent ingestion pipeline: raw/ -> validate -> compile -> processed/ + artifacts/.

Design notes
- Each wiki article is synthesized from *all* raw notes, so "incremental" works at the
  corpus level: a SHA-256 over the valid documents (names + content hashes) is compared
  with the hash each article was last compiled from. Unchanged corpus => zero Gemini
  calls. Changed corpus => every article is stale and is recompiled.
- The manifest is saved after every successful article, so a run that crashes or times
  out resumes with only the remaining articles on the next run.
- A bad input never blocks the run: it is copied to `quarantine/` with a reason file and
  excluded from the corpus.
- Transient Gemini errors (429/5xx) are retried with backoff; a topic that still fails is
  recorded and the other topics continue.
"""

import hashlib
import io
import json
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from . import compiler, retrieval, wiki
from .logging_utils import log_event
from .retry import retry
from .storage import BlobNotFound, Storage, sha256_hex

logger = logging.getLogger("kb.pipeline")

MAX_DOC_BYTES = 500_000
MIN_ARTICLE_WORDS = 100
MANIFEST = "manifest.json"


class PipelineError(RuntimeError):
    pass


@dataclass
class RunReport:
    corpus_hash: str = ""
    compiled: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    failed: dict[str, str] = field(default_factory=dict)
    quarantined: dict[str, str] = field(default_factory=dict)
    duration_s: float = 0.0

    @property
    def ok(self) -> bool:
        return not self.failed

    def to_dict(self) -> dict:
        return {**asdict(self), "ok": self.ok}


def validate_document(name: str, data: bytes) -> str | None:
    """Return a rejection reason, or None if the document is acceptable."""
    if not data.strip():
        return "empty file"
    if len(data) > MAX_DOC_BYTES:
        return f"too large ({len(data)} bytes > {MAX_DOC_BYTES})"
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        return "not valid UTF-8"
    if "\x00" in text:
        return "contains NUL bytes (binary file?)"
    return None


def sync_raw_dir(storage: Storage, directory: str | Path) -> dict[str, list[str]]:
    """Upload local *.md files to raw/, skipping ones whose content is already there."""
    result = {"uploaded": [], "unchanged": []}
    for path in sorted(Path(directory).glob("*.md")):
        data = path.read_bytes()
        if storage.exists("raw", path.name) and storage.info("raw", path.name).sha256 == sha256_hex(data):
            result["unchanged"].append(path.name)
            continue
        storage.upload("raw", path.name, data)
        result["uploaded"].append(path.name)
    return result


def _load_manifest(storage: Storage) -> dict:
    try:
        return json.loads(storage.download("artifacts", MANIFEST))
    except BlobNotFound:
        return {"version": 1, "topics": {}}


def _save_manifest(storage: Storage, manifest: dict) -> None:
    storage.upload("artifacts", MANIFEST, json.dumps(manifest, indent=2).encode())


def _quarantine(storage: Storage, name: str, data: bytes, reason: str) -> None:
    storage.upload("quarantine", name, data)
    storage.upload("quarantine", f"{name}.reason.txt", reason.encode())


def _publish_artifacts(storage: Storage, embedder) -> None:
    """Rebuild index + embeddings from what is currently in processed/."""
    articles, versions = {}, {}
    for blob in storage.list("processed"):
        if blob.endswith(".md"):
            articles[blob[:-3]] = storage.download("processed", blob).decode("utf-8")
            versions[blob[:-3]] = storage.info("processed", blob).sha256
    if not articles:
        return
    storage.upload("artifacts", "index.json", json.dumps(wiki.build_index(articles), indent=2).encode())
    topics = list(articles)
    vectors = embedder([retrieval.article_text_for_embedding(t, articles[t]) for t in topics])
    buf = io.BytesIO()
    np.save(buf, vectors)
    storage.upload("artifacts", "embeddings.npy", buf.getvalue())
    storage.upload(
        "artifacts", "embeddings_meta.json",
        json.dumps({"topics": topics, "versions": versions}).encode(),
    )


def run_pipeline(
    storage: Storage,
    client,
    embedder=retrieval.default_embedder,
    topics=compiler.WIKI_TOPICS,
    force: bool = False,
    max_attempts: int = 4,
    base_delay: float = 2.0,
    sleep=time.sleep,
    compile_fn=compiler.compile_article,
) -> RunReport:
    started = time.monotonic()
    report = RunReport()

    # 1. Read + validate raw documents (blob checksums are verified by storage.download).
    valid: dict[str, bytes] = {}
    for name in storage.list("raw"):
        if not name.endswith(".md"):
            continue
        data = storage.download("raw", name)
        reason = validate_document(name, data)
        if reason:
            report.quarantined[name] = reason
            _quarantine(storage, name, data, reason)
            log_event(logger, "document_quarantined", logging.WARNING, name=name, reason=reason)
        else:
            valid[name] = data
    if not valid:
        raise PipelineError("No valid raw documents found in raw/; nothing to compile.")

    corpus_hash = sha256_hex(
        json.dumps(sorted((n, sha256_hex(d)) for n, d in valid.items())).encode()
    )
    report.corpus_hash = corpus_hash
    manifest = _load_manifest(storage)
    sources_text = compiler.sources_to_text({n: d.decode("utf-8") for n, d in sorted(valid.items())})

    # 2. Compile only stale articles.
    for topic, description in topics:
        blob = f"{topic}.md"
        entry = manifest["topics"].get(topic)
        up_to_date = (
            not force
            and entry
            and entry.get("corpus_hash") == corpus_hash
            and storage.exists("processed", blob)
            and storage.info("processed", blob).sha256 == entry.get("sha256")
        )
        if up_to_date:
            report.skipped.append(topic)
            continue
        try:
            text = retry(
                lambda: compile_fn(client, topic, description, sources_text),
                attempts=max_attempts,
                base_delay=base_delay,
                sleep=sleep,
                on_retry=lambda n, exc, d: log_event(
                    logger, "compile_retry", logging.WARNING,
                    topic=topic, attempt=n, delay_s=d, error=str(exc)[:200]),
            )
            if len(text.split()) < MIN_ARTICLE_WORDS:
                raise ValueError(f"article too short ({len(text.split())} words)")
        except Exception as exc:
            report.failed[topic] = f"{type(exc).__name__}: {str(exc)[:300]}"
            log_event(logger, "compile_failed", logging.ERROR, topic=topic, error=report.failed[topic])
            continue
        content = f"# {topic}\n\n{text}".encode("utf-8")
        info = storage.upload("processed", blob, content)
        manifest["topics"][topic] = {
            "corpus_hash": corpus_hash,
            "sha256": info.sha256,
            "compiled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
        _save_manifest(storage, manifest)  # resumable: progress persists per article
        report.compiled.append(topic)
        log_event(logger, "article_compiled", topic=topic, words=len(text.split()))

    # 3. Refresh derived artifacts when anything changed (or they are missing).
    if report.compiled or not storage.exists("artifacts", "embeddings.npy"):
        _publish_artifacts(storage, embedder)

    manifest["corpus_hash"] = corpus_hash
    manifest["last_run"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _save_manifest(storage, manifest)

    report.duration_s = round(time.monotonic() - started, 3)
    log_event(logger, "pipeline_finished", logging.INFO if report.ok else logging.ERROR,
              compiled=len(report.compiled), skipped=len(report.skipped),
              failed=len(report.failed), quarantined=len(report.quarantined),
              duration_s=report.duration_s)
    return report
