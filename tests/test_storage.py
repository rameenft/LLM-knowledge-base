"""Same contract tests run against the local backend and (if running) Azurite."""

import socket
import uuid

import pytest

from kb import storage
from kb.storage import AzureBlobStorage, BlobNotFound, IntegrityError, LocalStorage, StorageError


# Azurite releases lag the Azure SDK; pin a REST API version Azurite 3.37 supports.
AZURITE_API_VERSION = "2026-06-06"


def _azurite_up() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", 10000), timeout=0.5):
            return True
    except OSError:
        return False


@pytest.fixture(
    params=["local", pytest.param("azurite", marks=pytest.mark.skipif(
        not _azurite_up(), reason="Azurite not running on 127.0.0.1:10000"))]
)
def store(request, tmp_path):
    if request.param == "local":
        return LocalStorage(tmp_path)
    return AzureBlobStorage.from_connection_string("UseDevelopmentStorage=true", api_version=AZURITE_API_VERSION)


@pytest.fixture
def container():
    return f"test-{uuid.uuid4().hex[:12]}"  # isolated per test; valid container name


def test_roundtrip_preserves_bytes_and_checksum(store, container):
    data = "héllo wörld\n".encode() * 1000
    info = store.upload(container, "notes/a.md", data)
    assert info.sha256 == storage.sha256_hex(data)
    assert store.download(container, "notes/a.md") == data
    assert store.info(container, "notes/a.md").size == len(data)


def test_missing_blob_raises_not_found(store, container):
    with pytest.raises(BlobNotFound):
        store.download(container, "nope.md")
    with pytest.raises(BlobNotFound):
        store.info(container, "nope.md")
    with pytest.raises(BlobNotFound):
        store.delete(container, "nope.md")
    assert store.exists(container, "nope.md") is False


def test_overwrite_flag(store, container):
    store.upload(container, "a.md", b"one")
    with pytest.raises(StorageError):
        store.upload(container, "a.md", b"two", overwrite=False)
    store.upload(container, "a.md", b"two")
    assert store.download(container, "a.md") == b"two"


def test_list_with_prefix_and_delete(store, container):
    for n in ("raw/1.md", "raw/2.md", "other/3.md"):
        store.upload(container, n, b"x")
    assert store.list(container) == ["other/3.md", "raw/1.md", "raw/2.md"]
    assert store.list(container, "raw/") == ["raw/1.md", "raw/2.md"]
    store.delete(container, "raw/1.md")
    assert store.exists(container, "raw/1.md") is False


def test_empty_blob_roundtrip(store, container):
    store.upload(container, "empty.md", b"")
    assert store.download(container, "empty.md") == b""


@pytest.mark.parametrize("bad", ["", "/abs", "../x", "a/../b", "a//b", "./x"])
def test_invalid_blob_names_rejected(store, container, bad):
    with pytest.raises(ValueError):
        store.upload(container, bad, b"x")


def test_invalid_container_name_rejected(tmp_path):
    with pytest.raises(ValueError):
        LocalStorage(tmp_path).upload("Bad_Container", "a", b"x")


def test_local_tampering_detected(tmp_path):
    s = LocalStorage(tmp_path)
    s.upload("raw", "a.md", b"original")
    (tmp_path / "raw" / "a.md").write_bytes(b"tampered")
    with pytest.raises(IntegrityError):
        s.download("raw", "a.md")


def test_azure_tampering_detected(container):
    if not _azurite_up():
        pytest.skip("Azurite not running")
    s = AzureBlobStorage.from_connection_string("UseDevelopmentStorage=true", api_version=AZURITE_API_VERSION)
    s.upload(container, "a.md", b"original")
    # Overwrite the bytes out-of-band, keeping the old (now wrong) checksum metadata.
    blob = s._blob(container, "a.md")
    blob.upload_blob(b"tampered", overwrite=True, metadata={"sha256": storage.sha256_hex(b"original")})
    with pytest.raises(IntegrityError):
        s.download(container, "a.md")


def test_azure_unreachable_raises_storage_error():
    from azure.storage.blob import BlobServiceClient

    # Nothing listens on port 1; the SDK error must be wrapped, not leaked raw.
    client = BlobServiceClient("http://127.0.0.1:1/acct", credential="sas=x", retry_total=0)
    with pytest.raises(StorageError):
        AzureBlobStorage(client).upload("raw", "a.md", b"x")


def test_from_env_defaults_to_local(monkeypatch, tmp_path):
    monkeypatch.delenv("KB_STORAGE_BACKEND", raising=False)
    monkeypatch.setenv("KB_LOCAL_STORAGE_DIR", str(tmp_path))
    assert isinstance(storage.from_env(), LocalStorage)


def test_from_env_azure_without_credentials_is_clear(monkeypatch):
    monkeypatch.setenv("KB_STORAGE_BACKEND", "azure")
    monkeypatch.delenv("AZURE_STORAGE_CONNECTION_STRING", raising=False)
    monkeypatch.delenv("AZURE_STORAGE_ACCOUNT_URL", raising=False)
    with pytest.raises(StorageError, match="AZURE_STORAGE"):
        storage.from_env()
