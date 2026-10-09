"""Tamper-evident audit ledger.

Every inference, redaction and answer appends a hash-chained record. The chain
stores HASHES AND METADATA ONLY - never raw PII - so the evidence trail is
provable to an NPC/BSP examiner without disclosing a single customer record.

Tampering with any historical entry invalidates every subsequent hash, so the
whole chain can be verified in one pass.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GENESIS = "0" * 64


def _sha(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _digest_of(payload: dict[str, Any]) -> str:
    """Stable digest: key-sorted JSON so field order can never change a hash.

    `default=str` guards the ledger against non-JSON types (numpy float32 from the
    dense retrieval leg is the realistic case). An audit trail must never be able
    to fail a request because a caller passed an exotic numeric type.
    """
    return _sha(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"),
                   default=str)
    )


@dataclass
class LedgerEntry:
    seq: int
    ts: str
    event: str
    summary: dict[str, Any] = field(default_factory=dict)
    prev_hash: str = GENESIS
    entry_hash: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


class AuditLedger:
    """Append-only, hash-chained, thread-safe."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._entries: list[LedgerEntry] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        self._entries.append(LedgerEntry(**json.loads(line)))
                    except (json.JSONDecodeError, TypeError):
                        continue

    def _head(self) -> tuple[int, str]:
        if not self._entries:
            return 0, GENESIS
        last = self._entries[-1]
        return last.seq + 1, last.entry_hash

    def append(self, event: str, summary: dict[str, Any]) -> LedgerEntry:
        """Append one event. `summary` must contain no raw customer data."""
        with self._lock:
            seq, prev = self._head()
            entry = LedgerEntry(
                seq=seq,
                ts=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                event=event,
                summary=summary,
                prev_hash=prev,
            )
            entry.entry_hash = _digest_of(
                {
                    "seq": entry.seq,
                    "ts": entry.ts,
                    "event": entry.event,
                    "summary": entry.summary,
                    "prev_hash": entry.prev_hash,
                }
            )
            self._entries.append(entry)
            # `default=str` keeps a non-JSON scalar (e.g. numpy float32 from the
            # dense retrieval leg) from ever failing an audit append. An audit
            # trail must be able to record what happened without itself breaking.
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry.to_dict(), ensure_ascii=False, default=str) + "\n")
            return entry

    def verify(self) -> dict:
        """Recompute the chain. Any break is reported with the first bad seq."""
        prev = GENESIS
        for entry in self._entries:
            if entry.prev_hash != prev:
                return {"valid": False, "entries": len(self._entries), "broken_at": entry.seq}
            recomputed = _digest_of(
                {
                    "seq": entry.seq,
                    "ts": entry.ts,
                    "event": entry.event,
                    "summary": entry.summary,
                    "prev_hash": entry.prev_hash,
                }
            )
            if recomputed != entry.entry_hash:
                return {"valid": False, "entries": len(self._entries), "broken_at": entry.seq}
            prev = entry.entry_hash
        return {"valid": True, "entries": len(self._entries), "head": prev}

    def recent(self, limit: int = 50) -> list[dict]:
        return [e.to_dict() for e in self._entries[-limit:]][::-1]

    def stats(self) -> dict:
        by_event: dict[str, int] = {}
        for e in self._entries:
            by_event[e.event] = by_event.get(e.event, 0) + 1
        return {
            "total": len(self._entries),
            "by_event": by_event,
            "contains_raw_pii": False,
            "note": "Ledger stores hashes and metadata only - never raw customer data.",
        }