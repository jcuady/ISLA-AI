"""Local llama.cpp server client.

Talks to a llama-server bound to 127.0.0.1 only. If the server is not running,
`available()` returns False and the copilot falls back to extractive answers -
the demo survives a model that failed to load.

Start the server with:
    models\\llamacpp\\vulkan\\llama-server.exe -m <model.gguf> --port 8080 --host 127.0.0.1
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_HOST = os.environ.get("KALIX_LLM_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("KALIX_LLM_PORT", "8080"))
DEFAULT_TIMEOUT = float(os.environ.get("KALIX_LLM_TIMEOUT", "120"))


class LlamaCppClient:
    """Thin OpenAI-compatible client. Never raises on construction."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT) -> None:
        self.base_url = f"http://{host}:{port}"
        self.model_name: str | None = None
        self.reason = "unknown"
        self._ok = False
        self._client = httpx.Client(timeout=DEFAULT_TIMEOUT)

        try:
            resp = self._client.get(f"{self.base_url}/v1/models", timeout=5.0)
            if resp.status_code == 200:
                data = resp.json().get("data") or []
                self.model_name = data[0].get("id") if data else "local-model"
                self.reason = "ready"
                self._ok = True
            else:
                self.reason = f"llama-server returned HTTP {resp.status_code}"
        except Exception as exc:  # noqa: BLE001
            self.reason = f"{type(exc).__name__}: {exc}"

    def available(self) -> bool:
        return self._ok

    def generate(self, prompt: str, max_tokens: int = 400, temperature: float = 0.1) -> str | None:
        if not self._ok:
            return None
        try:
            resp = self._client.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": self.model_name or "local-model",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "stream": False,
                },
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception:  # noqa: BLE001
            return None

    def health(self) -> dict:
        return {"available": self._ok, "model": self.model_name, "reason": self.reason,
                "base_url": self.base_url}