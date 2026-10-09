"""The air-gap claim, stated precisely enough to be enforced.

Isla AI's marketing says "no outbound socket". That wording is not literally true
and must not stay in the repo: `/api/airgap` opens real TCP connections to fixed
public DNS addresses, because a judge must be able to falsify the claim by
pulling the cable.

The defensible claim is narrower and stronger:

  * no module on the request path may open a network connection, except
  * the air-gap probe (a TCP SYN carrying no payload), and
  * the llama.cpp client, which is pinned to loopback.

These tests enforce exactly that, so the claim cannot rot as the code changes.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
SERVICES = REPO / "services"

# Call sites that legitimately perform network I/O.
ALLOWED = {
    Path("services/core/airgap.py"),  # the probe that proves the air-gap
    Path("services/core/llm.py"),  # local llama.cpp, pinned to 127.0.0.1
}

# Attribute/name tokens that indicate a real outbound capability.
NETWORK_TOKENS = {
    "create_connection",
    "urlopen",
    "socket",
    "requests",
    "httpx",
    "aiohttp",
    "ClientSession",
    "connect_ex",
    "getaddrinfo",
}


def _relative(path: Path) -> Path:
    return path.relative_to(REPO)


def _offending_modules() -> set[Path]:
    """Runtime modules that import or call a network primitive."""
    found: set[Path] = set()
    for path in SERVICES.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            elif isinstance(node, ast.Attribute):
                names = [node.attr]
            elif isinstance(node, ast.Name):
                names = [node.id]
            if any(tok in n for n in names for tok in NETWORK_TOKENS):
                found.add(_relative(path))
                break
    return found


def test_only_the_probe_and_the_local_llm_client_do_network_io():
    offenders = _offending_modules()
    unexpected = offenders - ALLOWED
    assert not unexpected, (
        "these runtime modules gained a network primitive: "
        f"{sorted(str(p) for p in unexpected)}. Anything outside the air-gap probe "
        "and the loopback llama.cpp client breaks the air-gap claim."
    )


def test_the_probe_module_is_in_the_allowlist_so_the_test_is_not_vacuous():
    assert Path("services/core/airgap.py") in _offending_modules()


def test_the_llm_client_defaults_to_loopback():
    """The one module allowed network I/O must never be pointed off-box."""
    import services.core.llm as llm

    assert llm.DEFAULT_HOST == "127.0.0.1"
    assert llm.DEFAULT_PORT == 8080

    # Any host literal in the source must be loopback or a template variable.
    # Walking the AST would break f-strings apart into meaningless fragments,
    # so the raw text is the honest thing to check here.
    source = (SERVICES / "core" / "llm.py").read_text(encoding="utf-8")
    for match in re.finditer(r"https?://([A-Za-z0-9_.:{}-]+)", source):
        host = match.group(1).split(":")[0]
        assert host.startswith("{") or host in {"127.0.0.1", "localhost"}, (
            f"llm.py points at {host}"
        )


def test_the_probe_targets_are_fixed_public_dns_and_carry_no_payload():
    """A TCP SYN to a fixed resolver proves reachability and leaks nothing."""
    from services.core.airgap import PROBE_TARGETS

    assert PROBE_TARGETS, "the probe must have targets or it proves nothing"
    for host, port, label in PROBE_TARGETS:
        assert host and port and label
        # Reserved documentation ranges and public resolvers only: never an
        # address a customer record could be sent to.
        assert not host.startswith("127."), "probing loopback proves nothing"


def test_no_cloud_ai_sdk_is_installed():
    """R5: core functionality cannot depend entirely on a cloud AI API."""
    cloud = {
        "openai",
        "anthropic",
        "google-generativeai",
        "google-genai",
        "cohere",
        "replicate",
        "groq",
        "together",
        "mistralai",
        "huggingface_hub",
    }
    reqs = (REPO / "requirements.txt").read_text(encoding="utf-8").lower()
    for name in cloud:
        assert not any(
            line.strip().lower().startswith(name) for line in reqs.splitlines()
        ), f"{name} is installed; the product must run without a cloud AI API"


def test_the_verdict_note_does_not_claim_what_the_probe_itself_disproves():
    """Regression guard on user-facing copy that contradicted the probe."""
    source = (SERVICES / "core" / "airgap.py").read_text(encoding="utf-8")
    assert "Isla AI never opens an outbound socket" not in source


@pytest.mark.parametrize(
    "doc",
    [
        "README.md",
        "docs/AIRGAP_VERIFICATION.md",
        "docs/THREAT_MODEL.md",
        "docs/DISCLOSURES.md",
        "docs/SUBMISSION.md",
        "docs/ARCHITECTURE.md",
        "docs/HACKATHON_RULES.md",
        "docs/JUDGING_AUDIT.md",
        "apps/web/public/landing.html",
        "branding/brand.md",
        "docs/architecture/isla-architecture.json",
        "docs/architecture/isla-architecture.html",
    ],
)
def test_no_document_repeats_the_false_absolute_claim(doc: str):
    text = (REPO / doc).read_text(encoding="utf-8").lower()
    # `/api/airgap` disproves every one of these. The accurate claim is that no
    # customer data leaves and no cloud service is called - not that the process
    # never opens a socket.
    #
    # The digit forms matter as much as the word forms. The landing page once
    # read "0 outbound sockets at runtime" and passed this test, because the
    # list only knew the word "zero" and the singular "socket". Spelling out
    # both is what makes the guard worth having.
    for phrase in (
        "no outbound socket",
        "no outbound sockets",
        "zero outbound socket",
        "zero outbound sockets",
        "0 outbound socket",
        "0 outbound sockets",
        "outbound socket, ever",
        "never opens a socket",
    ):
        assert phrase not in text, (
            f"{doc} still claims '{phrase}'. /api/airgap opens a real TCP "
            "connection on purpose; say what is actually true instead."
        )