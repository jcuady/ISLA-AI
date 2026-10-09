"""Test isolation for anything that touches the app's startup path.

The single most important thing this file does is point the audit ledger at a
temporary path before `services.core.app` is imported.

Every other module-level fixture is convenience. This one is correctness. The
app opens the real `data/audit_ledger.jsonl` at import time and writes a
`session_start` entry during lifespan startup, so a test that enters the
lifespan - which it must, to exercise anything real - appends to the same
hash-chained file the live server is using. Two writers on one chain means the
hashes stop verifying, and the product's central tamper-evidence claim becomes
false because a test suite ran. That is not a test bug that shows up in the
test run; it shows up in pre-flight, on a real chain, after 746 entries.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

# Must be set before services.core.app is imported anywhere in the session.
_TMP = Path(tempfile.mkdtemp(prefix="isla-test-ledger-"))
os.environ.setdefault("ISLA_LEDGER_PATH", str(_TMP / "audit_ledger.jsonl"))