import numpy as np
import pytest

from kb.storage import LocalStorage

WORDS = " ".join(["word"] * 150)  # passes the minimum-length article check


def fake_embedder(texts):
    out = []
    for t in texts:
        t = t.lower()
        v = np.array([2.0 if "sad" in t else 0.1, 2.0 if "voice" in t else 0.1, 0.1], dtype=np.float32)
        out.append(v / np.linalg.norm(v))
    return np.array(out)


@pytest.fixture
def store(tmp_path):
    return LocalStorage(tmp_path)


@pytest.fixture
def raw_store(store):
    store.upload("raw", "01.md", b"notes about sad users")
    store.upload("raw", "02.md", b"notes about voice latency")
    return store


TOPICS = [("Affect", "sad"), ("Voice", "voice")]
