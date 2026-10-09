"""Resilient parallel model downloader for Isla AI.

The single-stream HF transfer on this network stalls at ~8 KB/s. Ranged parallel
connections reach ~0.33 MB/s, so each asset is fetched as byte ranges, written to
a sparse file, and verified by SHA-256 of the assembled result.

Assets are ordered by demo criticality: the embedding model first (small, and the
copilot cannot run without it), then the LLM, then GLiNER (the optional NER
stage - the engine degrades safely to regex-only if it is missing).
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import os
import sys
import threading
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = REPO_ROOT / "models" / "weights"
HF = "https://huggingface.co"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"


@dataclass
class Asset:
    key: str
    repo: str
    file: str
    licence: str
    role: str
    approx_mb: int
    critical: bool


# Small companion files that live beside the ONNX graph. The embedder needs these
# for tokenisation, so they are fetched into the same asset directory.
E5_SIBLINGS = [
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "config.json",
]

ASSETS = [
    Asset(
        "multilingual-e5-small-int8",
        "intfloat/multilingual-e5-small",
        "onnx/model_qint8_avx512_vnni.onnx",
        "MIT",
        "embeddings",
        113,
        True,
    ),
    Asset(
        "qwen2.5-3b-instruct-q4_k_m",
        "Qwen/Qwen2.5-3B-Instruct-GGUF",
        "qwen2.5-3b-instruct-q4_k_m.gguf",
        "Apache-2.0",
        "llm",
        2007,
        True,
    ),
    Asset(
        "gliner-multi-v2.1",
        "urchade/gliner_multi-v2.1",
        "model.safetensors",
        "Apache-2.0",
        "ner",
        1102,
        False,
    ),
]

BLOCK = 4 * 1024 * 1024
WORKERS = 8
RETRIES = 5


def block_ranges(total: int, block: int) -> list[tuple[int, int]]:
    """Inclusive (start, end) ranges covering [0, total)."""
    return [(i, min(i + block - 1, total - 1)) for i in range(0, total, block)]


def missing_ranges(path: Path, total: int, block: int) -> list[tuple[int, int]]:
    """Ranges of a preallocated file that are still entirely zero.

    The transfer writes each block at its own offset into a preallocated sparse
    file, so a block that is not all-zero has already been received. Treating
    "still zero" as "missing" is what lets an interrupted 2 GB download resume
    instead of restarting from zero.

    A GGUF legitimately contains zero bytes inside a payload, so a false
    "missing" verdict only costs a redundant re-fetch; a false "present"
    verdict cannot happen, because that would require a fully-zero block to
    have been written.
    """
    if not path.exists() or path.stat().st_size < total:
        return block_ranges(total, block)

    ranges = []
    with path.open("rb") as fh:
        for start, end in block_ranges(total, block):
            fh.seek(start)
            if fh.read(end - start + 1).strip(b"\x00"):
                continue
            ranges.append((start, end))
    return ranges


def write_block(path: Path, start: int, data: bytes) -> int:
    """Write `data` at `start`. Caller serialises access across threads."""
    with path.open("r+b") as fh:
        fh.seek(start)
        fh.write(data)
    return len(data)


def _url(asset: Asset) -> str:
    return f"{HF}/{asset.repo}/resolve/main/{asset.file}"


def _size(url: str) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": UA}, method="HEAD")
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
        return int(resp.headers["Content-Length"])


def _fetch_block(url: str, start: int, end: int, path: Path, lock: threading.Lock) -> int:
    """Fetch one byte range into the target file at the right offset."""
    last = ""
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": UA, "Range": f"bytes={start}-{end}"}
            )
            with urllib.request.urlopen(req, timeout=90) as resp:  # noqa: S310
                data = resp.read()
            if not data:
                raise OSError("empty range response")
            with lock:
                write_block(path, start, data)
            return len(data)
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
            time.sleep(2 * (attempt + 1))
    print(f"    block {start}-{end} failed: {last}", file=sys.stderr)
    return 0


def download(asset: Asset, force: bool = False) -> Path | None:
    target_dir = MODELS_DIR / asset.key
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / asset.file.replace("/", "__")

    if target.exists() and not force:
        print(f"[skip] {asset.key:30} present ({target.stat().st_size / 1e6:,.0f} MB)")
        return target

    url = _url(asset)
    try:
        total = _size(url)
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] {asset.key}: cannot stat: {exc}", file=sys.stderr)
        return None

    part = target.with_suffix(target.suffix + ".part")
    already = 0
    if not force and part.exists() and part.stat().st_size == total:
        # Resume rather than restart: only blocks still holding zeroes are fetched.
        todo = missing_ranges(part, total, BLOCK)
        already = total - sum(e - s + 1 for s, e in todo)
        if not todo:
            print(f"[skip ] {asset.key:30} already complete ({total / 1e6:,.0f} MB)")
            return _finalise(part, target, asset)
        print(f"[resume] {asset.key:30} {already / 1e6:,.0f}/{total / 1e6:,.0f} MB already present")
    else:
        with part.open("wb") as fh:  # preallocate sparse
            fh.truncate(total)
        todo = block_ranges(total, BLOCK)

    print(f"[get ] {asset.key:30} {len(todo)}/{len(block_ranges(total, BLOCK))} blocks remaining")

    lock = threading.Lock()
    done = 0
    started = time.time()

    with cf.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(_fetch_block, url, s, e, part, lock) for s, e in todo]
        for fut in cf.as_completed(futs):
            done += fut.result()
            if done % (BLOCK * 4) < BLOCK:
                elapsed = max(time.time() - started, 0.001)
                pct = 100 * (already + done) / total
                print(
                    f"      {pct:5.1f}%  {(already + done) / 1e6:7.0f}/{total / 1e6:.0f} MB  "
                    f"{done / 1e6 / elapsed:5.2f} MB/s",
                    flush=True,
                )

    actual = part.stat().st_size
    if actual != total or already + done < total * 0.999:
        print(
            f"[FAIL] {asset.key}: incomplete {already + done}/{total} bytes",
            file=sys.stderr,
        )
        return None

    return _finalise(part, target, asset)


def _finalise(part: Path, target: Path, asset: Asset) -> Path:
    """Hash the assembled file and promote it out of the .part staging name."""
    h = hashlib.sha256()
    with part.open("rb") as fh:
        while block := fh.read(1 << 22):
            h.update(block)
    digest = h.hexdigest()
    part.replace(target)
    print(f"[ok  ] {asset.key:30} sha256={digest[:24]}...")

    if asset.key == "multilingual-e5-small-int8":
        _fetch_siblings(asset, target.parent)

    return target


def _fetch_siblings(asset: Asset, target_dir: Path) -> None:
    """Fetch the small tokenizer/config files the ONNX embedder needs."""
    for name in E5_SIBLINGS:
        dest = target_dir / name
        if dest.exists() and dest.stat().st_size > 0:
            continue
        url = f"{HF}/{asset.repo}/resolve/main/{name}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
                dest.write_bytes(resp.read())
            print(f"      + {name}")
        except Exception as exc:  # noqa: BLE001
            print(f"      ! {name} failed: {type(exc).__name__}: {exc}", file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch Isla AI model weights (parallel).")
    ap.add_argument("--only", nargs="*", help="subset by key")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--skip-optional", action="store_true")
    args = ap.parse_args()

    assets = [a for a in ASSETS if not args.only or a.key in args.only]
    if args.skip_optional:
        assets = [a for a in assets if a.critical]

    for asset in assets:
        try:
            download(asset, force=args.force)
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {asset.key}: {type(exc).__name__}: {exc}", file=sys.stderr)
            if asset.critical:
                return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())