"""B1: the HF fast tokenizer is shared by model.encode and count_tokens; concurrent use raised
"Already borrowed". Uses the REAL `_load_minilm` closure over a REAL Rust tokenizer (the conftest
embedder is a lock-free pure function and cannot show the race; `transformers` is mocked in this
suite, so `tokenizers` is driven directly the way transformers drives it). Not requires_real_st.
"""

from __future__ import annotations

import sys
import threading
import types

import numpy as np
import pytest

from cohezion.flume import canonical_latent as cl
from cohezion.flume.canonical_latent import CanonicalTextLatent


tokenizers = pytest.importorskip("tokenizers")

WINDOW = 16
# Captured at import: the autouse conftest fixture replaces cl._load_minilm per test.
_REAL_LOAD_MINILM = cl._load_minilm


class _HFStyleTokenizer:
    """Mirrors how transformers drives the Rust tokenizer: every call re-sets truncation/padding
    on the shared object (a mutable borrow) and then runs encode_batch (GIL released). `transformers`
    itself is mocked in this suite, so the real `tokenizers` Rust object is used directly."""

    def __init__(self):
        vocab = {"[UNK]": 0, "[PAD]": 1, **{f"w{i}": i + 2 for i in range(50)}}
        self._tk = tokenizers.Tokenizer(tokenizers.models.WordLevel(vocab, unk_token="[UNK]"))
        self._tk.pre_tokenizer = tokenizers.pre_tokenizers.Whitespace()

    def __call__(self, text, add_special_tokens=True, truncation=False):
        if truncation:
            self._tk.enable_truncation(WINDOW)
            self._tk.enable_padding()
        else:
            self._tk.no_truncation()
            self._tk.no_padding()
        enc = self._tk.encode_batch([text], add_special_tokens=add_special_tokens)[0]
        return {"input_ids": enc.ids}


class _FakeSentenceTransformer:
    max_seq_length = WINDOW

    def __init__(self, *_a, **_k):
        self.tokenizer = _HFStyleTokenizer()

    def encode(self, text):
        ids = self.tokenizer(text, truncation=True)["input_ids"]
        vec = np.zeros(32, dtype=np.float32)
        for i in ids:
            vec[int(i) % 32] += 1.0
        return vec


@pytest.fixture
def real_loader(monkeypatch):
    fake_mod = types.SimpleNamespace(SentenceTransformer=_FakeSentenceTransformer)
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_mod)
    monkeypatch.setattr(cl, "_resolve_snapshot", lambda: "unused")
    return _REAL_LOAD_MINILM


HUGE = " ".join(f"w{i % 50}" for i in range(20000))  # makes the Rust call long enough to overlap
LONG_A = " ".join(f"w{i % 50}" for i in range(40)) + " w1"
LONG_B = " ".join(f"w{i % 50}" for i in range(40)) + " w2"  # same first 16 tokens as LONG_A


def test_concurrent_encode_and_count_tokens_do_not_race(real_loader):
    """B1: encode (mutates the shared tokenizer) vs count_tokens (reads it), from threads."""
    enc = CanonicalTextLatent(real_loader)
    enc.encode("w1 w2")  # load once, outside the race
    errors: list[str] = []

    def hammer_encode():
        for _ in range(100):
            try:
                enc.encode(HUGE)
            except Exception as exc:
                errors.append(f"{type(exc).__name__}: {exc}")

    def hammer_count():
        for _ in range(100):
            try:
                enc.exceeds_token_limit(HUGE)
            except Exception as exc:
                errors.append(f"{type(exc).__name__}: {exc}")

    threads = [threading.Thread(target=f) for f in (hammer_encode, hammer_count) * 2]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert errors == [], errors[:3]
