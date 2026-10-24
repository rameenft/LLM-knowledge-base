"""Blob storage abstraction with local-folder and Azure Blob backends.

Containers used by the pipeline:
    raw         source notes as uploaded
    processed   compiled wiki articles
    artifacts   indexes, embeddings, manifests
    quarantine  inputs that failed validation

Every upload records a SHA-256 in blob metadata; every download verifies it, so
silent corruption or out-of-band edits surface as `IntegrityError`.

Credentials are never in code: Azure access comes from the environment
(`AZURE_STORAGE_CONNECTION_STRING`, or `AZURE_STORAGE_ACCOUNT_URL` with
`DefaultAzureCredential`, which uses managed identity when deployed).
"""

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

CONTAINERS = ("raw", "processed", "artifacts", "quarantine")
_CONTAINER_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])$")


class StorageError(RuntimeError):
    """Base class for storage failures."""


class BlobNotFound(StorageError):
    pass


class IntegrityError(StorageError):
    pass


@dataclass(frozen=True)
class BlobInfo:
    container: str
    name: str
    size: int
    sha256: str


class Storage(Protocol):
    def upload(self, container: str, name: str, data: bytes, overwrite: bool = True) -> BlobInfo: ...
    def download(self, container: str, name: str) -> bytes: ...
    def info(self, container: str, name: str) -> BlobInfo: ...
    def exists(self, container: str, name: str) -> bool: ...
    def list(self, container: str, prefix: str = "") -> list[str]: ...
    def delete(self, container: str, name: str) -> None: ...


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate(container: str, name: str) -> None:
    if not _CONTAINER_RE.match(container):
        raise ValueError(f"Invalid container name: {container!r}")
    parts = name.split("/")
    if not name or name.startswith("/") or any(p in ("", ".", "..") for p in parts):
        raise ValueError(f"Invalid blob name: {name!r}")


def _verify(container: str, name: str, data: bytes, expected: str | None) -> None:
    if expected is None:
        raise IntegrityError(f"{container}/{name} has no recorded checksum")
    actual = sha256_hex(data)
    if actual != expected:
        raise IntegrityError(
            f"{container}/{name} checksum mismatch (expected {expected[:12]}…, got {actual[:12]}…)"
        )


class LocalStorage:
    """Stores blobs as files under `root/<container>/<name>`; checksums in a sidecar tree."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    def _paths(self, container: str, name: str) -> tuple[Path, Path]:
        _validate(container, name)
        return (self.root / container / name, self.root / ".meta" / container / f"{name}.json")

    def upload(self, container, name, data, overwrite=True):
        path, meta = self._paths(container, name)
        if path.exists() and not overwrite:
            raise StorageError(f"{container}/{name} already exists")
        path.parent.mkdir(parents=True, exist_ok=True)
        meta.parent.mkdir(parents=True, exist_ok=True)
        digest = sha256_hex(data)
        path.write_bytes(data)
        meta.write_text(json.dumps({"sha256": digest}), encoding="utf-8")
        return BlobInfo(container, name, len(data), digest)

    def download(self, container, name):
        path, meta = self._paths(container, name)
        if not path.is_file():
            raise BlobNotFound(f"{container}/{name} not found")
        data = path.read_bytes()
        expected = json.loads(meta.read_text())["sha256"] if meta.exists() else None
        _verify(container, name, data, expected)
        return data

    def info(self, container, name):
        path, meta = self._paths(container, name)
        if not path.is_file():
            raise BlobNotFound(f"{container}/{name} not found")
        digest = json.loads(meta.read_text())["sha256"] if meta.exists() else ""
        return BlobInfo(container, name, path.stat().st_size, digest)

    def exists(self, container, name):
        return self._paths(container, name)[0].is_file()

    def list(self, container, prefix=""):
        _validate(container, "x")
        base = self.root / container
        if not base.is_dir():
            return []
        names = (p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file())
        return sorted(n for n in names if n.startswith(prefix))

    def delete(self, container, name):
        path, meta = self._paths(container, name)
        if not path.is_file():
            raise BlobNotFound(f"{container}/{name} not found")
        path.unlink()
        meta.unlink(missing_ok=True)


class AzureBlobStorage:
    """Azure Blob Storage (or Azurite). Containers are created on first use."""

    def __init__(self, service_client):
        self._svc = service_client
        self._ensured: set[str] = set()

    @classmethod
    def from_connection_string(cls, conn_str: str, **client_kwargs) -> "AzureBlobStorage":
        """`client_kwargs` go to BlobServiceClient, e.g. api_version for older emulators."""
        from azure.storage.blob import BlobServiceClient

        return cls(BlobServiceClient.from_connection_string(conn_str, **client_kwargs))

    @classmethod
    def from_account_url(cls, account_url: str) -> "AzureBlobStorage":
        from azure.identity import DefaultAzureCredential
        from azure.storage.blob import BlobServiceClient

        return cls(BlobServiceClient(account_url, credential=DefaultAzureCredential()))

    def _container(self, container: str):
        from azure.core.exceptions import AzureError, ResourceExistsError

        if container not in self._ensured:
            try:
                self._svc.create_container(container)
            except ResourceExistsError:
                pass
            except AzureError as e:
                raise StorageError(f"Could not reach or create container {container!r}: {e}") from e
            self._ensured.add(container)
        return self._svc.get_container_client(container)

    def _blob(self, container: str, name: str):
        _validate(container, name)
        return self._container(container).get_blob_client(name)

    def upload(self, container, name, data, overwrite=True):
        from azure.core.exceptions import AzureError, ResourceExistsError

        digest = sha256_hex(data)
        try:
            self._blob(container, name).upload_blob(
                data, overwrite=overwrite, metadata={"sha256": digest}
            )
        except ResourceExistsError as e:
            raise StorageError(f"{container}/{name} already exists") from e
        except AzureError as e:
            raise StorageError(f"Upload of {container}/{name} failed: {e}") from e
        return BlobInfo(container, name, len(data), digest)

    def download(self, container, name):
        from azure.core.exceptions import AzureError, ResourceNotFoundError

        blob = self._blob(container, name)
        try:
            props = blob.get_blob_properties()
            data = blob.download_blob().readall()
        except ResourceNotFoundError as e:
            raise BlobNotFound(f"{container}/{name} not found") from e
        except AzureError as e:
            raise StorageError(f"Download of {container}/{name} failed: {e}") from e
        _verify(container, name, data, (props.metadata or {}).get("sha256"))
        return data

    def info(self, container, name):
        from azure.core.exceptions import AzureError, ResourceNotFoundError

        try:
            props = self._blob(container, name).get_blob_properties()
        except ResourceNotFoundError as e:
            raise BlobNotFound(f"{container}/{name} not found") from e
        except AzureError as e:
            raise StorageError(f"Could not read {container}/{name}: {e}") from e
        return BlobInfo(container, name, props.size, (props.metadata or {}).get("sha256", ""))

    def exists(self, container, name):
        return self._blob(container, name).exists()

    def list(self, container, prefix=""):
        _validate(container, "x")
        return sorted(self._container(container).list_blob_names(name_starts_with=prefix or None))

    def delete(self, container, name):
        from azure.core.exceptions import AzureError, ResourceNotFoundError

        try:
            self._blob(container, name).delete_blob()
        except ResourceNotFoundError as e:
            raise BlobNotFound(f"{container}/{name} not found") from e
        except AzureError as e:
            raise StorageError(f"Delete of {container}/{name} failed: {e}") from e


def from_env() -> Storage:
    """Pick a backend from the environment.

    KB_STORAGE_BACKEND = "local" (default) | "azure"
    azure: AZURE_STORAGE_CONNECTION_STRING (e.g. "UseDevelopmentStorage=true" for Azurite)
           or AZURE_STORAGE_ACCOUNT_URL (uses DefaultAzureCredential / managed identity)
           optional AZURE_STORAGE_API_VERSION to pin the REST API version (older emulators)
    local: KB_LOCAL_STORAGE_DIR (default ./.local_storage)
    """
    backend = os.environ.get("KB_STORAGE_BACKEND", "local").lower()
    if backend == "local":
        return LocalStorage(os.environ.get("KB_LOCAL_STORAGE_DIR", ".local_storage"))
    if backend == "azure":
        if conn := os.environ.get("AZURE_STORAGE_CONNECTION_STRING"):
            kwargs = {}
            if version := os.environ.get("AZURE_STORAGE_API_VERSION"):
                kwargs["api_version"] = version  # needed when Azurite lags the SDK
            return AzureBlobStorage.from_connection_string(conn, **kwargs)
        if url := os.environ.get("AZURE_STORAGE_ACCOUNT_URL"):
            return AzureBlobStorage.from_account_url(url)
        raise StorageError(
            "KB_STORAGE_BACKEND=azure needs AZURE_STORAGE_CONNECTION_STRING or AZURE_STORAGE_ACCOUNT_URL"
        )
    raise StorageError(f"Unknown KB_STORAGE_BACKEND: {backend!r}")
