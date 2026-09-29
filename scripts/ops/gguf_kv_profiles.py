"""Regenerate ``src/cohezion/inference/gguf_kv_profiles.json`` from public GGUF headers.

The model store (/var/lib/lemonade/.cache) is not readable by the agent user, but every catalog
checkpoint is a public HuggingFace GGUF whose first few MB hold the full metadata block. This
range-requests that header, keeps only the keys ``kv_budget.kv_profile_from_gguf_meta`` reads,
and writes them keyed by Lemonade model id. Runtime stays offline: it reads the committed JSON.

Usage: python scripts/ops/gguf_kv_profiles.py MODEL_ID=repo:quant_substring [...]
"""

from __future__ import annotations

import json
import struct
import sys
import urllib.request
from pathlib import Path


OUT = Path(__file__).resolve().parents[2] / "src/cohezion/inference/gguf_kv_profiles.json"
_KEYS = (
    "block_count", "head_count", "head_count_kv", "key_length", "value_length",
    "embedding_length", "context_length", "full_attention_interval", "attention.sliding_window",
    "attention.sliding_window_pattern", "attention.kv_lora_rank", "ssm.inner_size", "ssm.state_size",
)  # fmt: skip
_SCALAR = {
    0: "B",
    1: "b",
    2: "H",
    3: "h",
    4: "I",
    5: "i",
    6: "f",
    7: "?",
    10: "Q",
    11: "q",
    12: "d",
}
_HEADERS_TRIES = (4 << 20, 12 << 20, 40 << 20)


class _Reader:
    def __init__(self, data: bytes) -> None:
        self.data, self.pos = data, 0

    def scalar(self, fmt: str):
        (v,) = struct.unpack_from("<" + fmt, self.data, self.pos)
        self.pos += struct.calcsize(fmt)
        return v

    def string(self) -> str:
        n = self.scalar("Q")
        v = self.data[self.pos : self.pos + n].decode("utf8", "replace")
        self.pos += n
        return v

    def value(self, vtype: int):
        if vtype in _SCALAR:
            return self.scalar(_SCALAR[vtype])
        if vtype == 8:
            return self.string()
        if vtype == 9:  # array
            etype, n = self.scalar("I"), self.scalar("Q")
            if etype in _SCALAR and n > 64:  # long numeric arrays (tokenizer scores): skip
                self.pos += n * struct.calcsize(_SCALAR[etype])
                return None
            return [self.value(etype) for _ in range(n)]
        raise ValueError(f"unknown GGUF value type {vtype}")


def _https(url: str) -> str:
    if not url.startswith("https://huggingface.co/"):
        raise ValueError(f"refusing non-HuggingFace url: {url}")
    return url


def _get(url: str, headers: dict | None = None) -> bytes:
    req = urllib.request.Request(_https(url), headers=headers or {})  # noqa: S310 - https-only via _https
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - https-only above
        return resp.read()


def read_header(url: str) -> dict:
    for size in _HEADERS_TRIES:
        data = _get(url, {"Range": f"bytes=0-{size - 1}"})
        if data[:4] != b"GGUF":
            raise ValueError("not a GGUF file")
        r = _Reader(data)
        r.pos = 8
        r.scalar("Q")  # tensor count
        try:
            return {r.string(): r.value(r.scalar("I")) for _ in range(r.scalar("Q"))}
        except (struct.error, IndexError):
            continue  # header longer than this window — widen and retry
    raise ValueError("GGUF header exceeds the largest window")


def trim(meta: dict) -> dict:
    """Keep only what the KV estimator reads."""
    a = meta["general.architecture"]
    out = {"general.architecture": a}
    for k in _KEYS:
        for full in (f"{a}.{k}", f"{a}.attention.{k}"):
            if full in meta:
                out[full] = meta[full]
    return out


def main(argv: list[str]) -> int:
    profiles = json.loads(OUT.read_text()) if OUT.exists() else {}
    for spec in argv:
        model_id, _, target = spec.partition("=")
        repo, _, quant = target.partition(":")
        listing = json.loads(_get(f"https://huggingface.co/api/models/{repo}"))
        names = sorted(
            f["rfilename"] for f in listing["siblings"] if f["rfilename"].endswith(".gguf")
        )
        pick = [n for n in names if quant.lower() in n.lower() and "mmproj" not in n.lower()]
        profiles[model_id] = trim(
            read_header(f"https://huggingface.co/{repo}/resolve/main/{pick[0]}")
        )
        print(model_id, "->", pick[0])
    OUT.write_text(json.dumps(profiles, indent=1, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
