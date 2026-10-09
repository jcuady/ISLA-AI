"""Fetch tokenizer.json with ranged parallel requests.

The single-stream transfer truncates on this network (IncompleteRead at ~3.7 MB of 17 MB), so the
same ranged-block strategy used for model weights is applied here. Blocks are written to a sparse
file and the assembled result is validated by parsing it as JSON.
"""

from __future__ import annotations

import concurrent.futures as cf
import json
import sys
import threading
import time
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEST_DIR = REPO_ROOT / "models" / "weights" / "multilingual-e5-small-int8"
URL = "https://huggingface.co/intfloat/multilingual-e5-small/resolve/main/tokenizer.json"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36"

BLOCK = 1 * 1024 * 1024
WORKERS = 8
RETRIES = 6


def total_size() -> int:
    req = urllib.request.Request(URL, headers={"User-Agent": UA}, method="HEAD")
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
        return int(resp.headers["Content-Length"])


def fetch_block(start: int, end: int, path: Path, lock: threading.Lock) -> int:
    last = ""
    for attempt in range(RETRIES):
        try:
            req = urllib.request.Request(
                URL, headers={"User-Agent": UA, "Range": f"bytes={start}-{end}"}
            )
            with urllib.request.urlopen(req, timeout=90) as resp:  # noqa: S310
                data = resp.read()
            expected = end - start + 1
            if len(data) != expected:
                raise OSError(f"short block {len(data)}/{expected}")
            with lock:
                with path.open("r+b") as fh:
                    fh.seek(start)
                    fh.write(data)
            return len(data)
        except Exception as exc:  # noqa: BLE001
            last = f"{type(exc).__name__}: {exc}"
            time.sleep(2 * (attempt + 1))
    print(f"  block {start}-{end} FAILED: {last}", file=sys.stderr)
    return 0


def main() -> int:
    DEST_DIR.mkdir(parents=True, exist_ok=True)
    target = DEST_DIR / "tokenizer.json"
    tmp = DEST_DIR / "tokenizer.json.part"

    size = total_size()
    print(f"[get ] tokenizer.json {size / 1e6:.1f} MB")
    with tmp.open("wb") as fh:
        fh.truncate(size)

    blocks = [(i, min(i + BLOCK - 1, size - 1)) for i in range(0, size, BLOCK)]
    lock = threading.Lock()
    done = 0
    started = time.time()

    with cf.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs = [pool.submit(fetch_block, s, e, tmp, lock) for s, e in blocks]
        for fut in cf.as_completed(futs):
            done += fut.result()
            if done % (BLOCK * 4) < BLOCK:
                el = max(time.time() - started, 0.001)
                print(f"      {100 * done / size:5.1f}%  {done / 1e6:.1f}/{size / 1e6:.1f} MB  "
                      f"{done / 1e6 / el:.2f} MB/s", flush=True)

    if done < size:
        print(f"[FAIL] incomplete {done}/{size}", file=sys.stderr)
        return 1

    try:
        with tmp.open("r", encoding="utf-8") as fh:
            json.load(fh)
    except Exception as exc:  # noqa: BLE001
        print(f"[FAIL] JSON validation: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    tmp.replace(target)
    print(f"[ok  ] tokenizer.json {size / 1e6:.1f} MB, valid JSON")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())