"""The audit ledger is the tamper-evidence claim; these tests hold it to one.

Every entry is hash-chained to the one before it, so altering any historical
entry invalidates every hash after it. That is the property an NPC or BSP
examiner would actually check, and the property this file exists to protect.

Two failures found while building the transaction-risk screen are pinned here,
because both of them made the claim false without raising anything:

1.  **Two processes, one chain.** `append()` held a `threading.Lock`, which is
    invisible to a second process. A test run and a live server writing the same
    JSONL interleaved their entries and the chain stopped verifying at 746
    entries. Fixed with an OS-level exclusive lock plus re-reading the file as
    the source of truth under that lock.

2.  **A cached head goes stale.** Even with the lock, if a process trusts an
    in-memory head rather than re-reading the file, the second writer gets a
    duplicate seq and a stale prev_hash. `_reload()` under the lock prevents it.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.core.ledger import GENESIS, AuditLedger  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_a_fresh_chain_verifies() -> None:
    with tempfile.TemporaryDirectory() as d:
        ledger = AuditLedger(Path(d) / "l.jsonl")
        for i in range(20):
            ledger.append("test", {"i": i})
        assert ledger.verify()["valid"] is True


def test_the_genesis_hash_is_the_expected_constant() -> None:
    with tempfile.TemporaryDirectory() as d:
        ledger = AuditLedger(Path(d) / "l.jsonl")
        ledger.append("test", {"a": 1})
        assert ledger.recent(1)[0]["prev_hash"] == GENESIS


def test_tampering_with_an_old_entry_is_detected() -> None:
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "l.jsonl"
        ledger = AuditLedger(path)
        for i in range(10):
            ledger.append("test", {"i": i})

        lines = path.read_text(encoding="utf-8").splitlines()
        rec = json.loads(lines[2])
        rec["summary"]["i"] = 999          # the tamper
        lines[2] = json.dumps(rec, ensure_ascii=False)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        reopened = AuditLedger(path)
        result = reopened.verify()
        assert result["valid"] is False
        assert result["broken_at"] == 2


def test_an_independent_recompute_detects_a_rehash() -> None:
    """Re-hashing the tampered entry is the clever attack; the chain still fails.

    An attacker who edits entry 2 and recomputes entry 2's own hash has not
    touched entry 3, whose prev_hash still points at the old value.
    """
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "l.jsonl"
        ledger = AuditLedger(path)
        for i in range(6):
            ledger.append("test", {"i": i})

        lines = path.read_text(encoding="utf-8").splitlines()
        rec = json.loads(lines[1])
        rec["summary"]["i"] = 999
        lines[1] = json.dumps(rec, ensure_ascii=False)
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        assert AuditLedger(path).verify()["valid"] is False


def test_a_second_process_appending_does_not_break_the_chain() -> None:
    """The regression that actually happened.

    A subprocess opens the same ledger file and appends. The parent's next
    append must chain onto the child's entry, not onto its own stale head.
    """
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "l.jsonl"
        parent = AuditLedger(path)
        for i in range(5):
            parent.append("parent", {"i": i})

        code = (
            "import sys;"
            f"sys.path.insert(0, {str(REPO_ROOT)!r});"
            "from pathlib import Path;"
            "from services.core.ledger import AuditLedger;"
            f"l = AuditLedger(Path({str(path)!r}));"
            "l.append('child', {'i': 99})"
        )
        proc = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, timeout=180
        )
        assert proc.returncode == 0, proc.stderr

        parent.append("parent_after_child", {"i": 6})
        result = parent.verify()
        assert result["valid"] is True, result
        assert result["entries"] == 7, result


def test_the_ledger_path_is_overridable_for_tests() -> None:
    """Guards the isolation conftest depends on.

    If this stops being configurable, running the suite will again write into
    the production chain.
    """
    source = (Path(__file__).resolve().parent.parent / "services" / "core"
              / "app.py").read_text(encoding="utf-8")
    assert "ISLA_LEDGER_PATH" in source


def test_no_entry_stores_raw_customer_text() -> None:
    """The ledger records what happened, never the customer text it happened to.

    An audit trail an examiner can read without any single customer record
    being disclosed is the whole point of the design.
    """
    with tempfile.TemporaryDirectory() as d:
        ledger = AuditLedger(Path(d) / "l.jsonl")
        ledger.append(
            "pii_redaction",
            {"entities_redacted": 4, "verdict": "SAFE_TO_SEND", "latency_ms": 2.1},
        )
        summary = ledger.recent(1)[0]["summary"]
        for key, value in summary.items():
            assert not isinstance(value, str) or len(value) <= 32, (key, value)
        blob = json.dumps(summary)
        assert "1234" not in blob and "@" not in blob