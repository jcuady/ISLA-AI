"""The audit ledger must record auditable EVENTS, not routine polling.

The console re-probes the network every 20 seconds so a judge can watch the
air-gap claim be falsified live. Writing every one of those probes to the
ledger produced roughly 4,300 identical entries a day, burying the redaction
and copilot entries the trail exists to prove.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from services.core import app as core  # noqa: E402
from services.core.ledger import AuditLedger  # noqa: E402


class FakeProbe:
    """Stand-in for the live probe so the test never touches real sockets."""

    def __init__(self, air_gapped: bool):
        self.air_gapped = air_gapped
        self.outbound_blocked = air_gapped

    def to_dict(self) -> dict:
        return {
            "air_gapped": self.air_gapped,
            "outbound_blocked": self.outbound_blocked,
            "resolver_available": not self.air_gapped,
            "bind_host": "127.0.0.1",
            "checked_at": "2026-10-06T00:00:00Z",
            "elapsed_ms": 1,
            "note": "",
            "probes": [],
        }


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    led = AuditLedger(tmp_path / "audit.jsonl")
    monkeypatch.setattr(core.state, "ledger", led)
    monkeypatch.setattr(core.state, "last_air_gapped", None)
    yield led
    monkeypatch.setattr(core.state, "ledger", None)
    monkeypatch.setattr(core.state, "last_air_gapped", None)


def probe(air_gapped: bool, monkeypatch) -> dict:
    monkeypatch.setattr(core, "run_probe", lambda _host: FakeProbe(air_gapped))
    return core.airgap()


def test_first_probe_is_recorded(ledger, monkeypatch):
    probe(True, monkeypatch)
    assert [e["event"] for e in ledger.recent(50)] == ["airgap_probe"]


def test_repeated_identical_probes_are_not_recorded(ledger, monkeypatch):
    for _ in range(50):
        probe(True, monkeypatch)
    assert len(ledger.recent(50)) == 1


def test_a_real_change_in_reachability_is_recorded(ledger, monkeypatch):
    probe(True, monkeypatch)
    probe(True, monkeypatch)
    probe(False, monkeypatch)  # cable pulled
    probe(False, monkeypatch)
    probe(True, monkeypatch)  # cable back

    entries = ledger.recent(50)
    assert [e["summary"]["air_gapped"] for e in reversed(entries)] == [True, False, True]


def test_the_probe_answer_is_unchanged_by_ledger_deduplication(ledger, monkeypatch):
    probe(True, monkeypatch)
    second = probe(True, monkeypatch)
    assert second["air_gapped"] is True
    assert "elapsed_ms" in second
    assert second["bind_host"] == "127.0.0.1"


def test_the_first_probe_is_flagged_as_a_baseline_not_a_change(ledger, monkeypatch):
    probe(True, monkeypatch)
    assert ledger.recent(1)[0]["summary"]["changed"] is False
    probe(False, monkeypatch)
    assert ledger.recent(1)[0]["summary"]["changed"] is True


def test_chain_stays_valid_across_deduplicated_probes(ledger, monkeypatch):
    probe(True, monkeypatch)
    for _ in range(10):
        probe(True, monkeypatch)
    probe(False, monkeypatch)
    report = ledger.verify()
    assert report["valid"], report


def test_no_ledger_means_no_probe_record(ledger, monkeypatch):
    monkeypatch.setattr(core.state, "ledger", None)
    result = probe(True, monkeypatch)
    assert result["air_gapped"] is True
    # The endpoint stays usable when the ledger is disabled, and the observed
    # state is still tracked so enabling the ledger later does not replay a
    # spurious "changed" event.
    assert core.state.last_air_gapped is True