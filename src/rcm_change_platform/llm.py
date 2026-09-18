"""Optional LLM backing for the agents.

Every agent has a deterministic implementation so the pipeline runs offline and
its tests are hermetic. Where natural language helps - parsing a free form
request, writing the narrative sections of a design document - the agent asks
the configured client first and falls back to the deterministic path when no
provider is configured or the call fails.

Configure with environment variables::

    RCM_LLM_PROVIDER=anthropic|openai|none   (default: auto)
    ANTHROPIC_API_KEY / OPENAI_API_KEY
    RCM_LLM_MODEL=<model name>
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any, Protocol, runtime_checkable

_TIMEOUT_SECONDS = 45


@runtime_checkable
class LLMClient(Protocol):
    name: str

    def available(self) -> bool: ...

    def complete(self, prompt: str, *, system: str = "", max_tokens: int = 1024) -> str | None: ...


class NullLLM:
    """Default client: always defers to the deterministic agent logic."""

    name = "deterministic"

    def available(self) -> bool:
        return False

    def complete(self, prompt: str, *, system: str = "", max_tokens: int = 1024) -> str | None:
        return None


class _HttpLLM:
    endpoint = ""
    name = "http"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def available(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict[str, str]:
        raise NotImplementedError

    def _payload(self, prompt: str, system: str, max_tokens: int) -> dict[str, Any]:
        raise NotImplementedError

    def _parse(self, payload: dict[str, Any]) -> str:
        raise NotImplementedError

    def complete(self, prompt: str, *, system: str = "", max_tokens: int = 1024) -> str | None:
        if not self.available():
            return None
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(self._payload(prompt, system, max_tokens)).encode("utf-8"),
            headers={"content-type": "application/json", **self._headers()},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
                return self._parse(json.loads(response.read().decode("utf-8")))
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError, OSError):
            return None


class AnthropicLLM(_HttpLLM):
    endpoint = "https://api.anthropic.com/v1/messages"
    name = "anthropic"

    def _headers(self) -> dict[str, str]:
        return {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}

    def _payload(self, prompt: str, system: str, max_tokens: int) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            payload["system"] = system
        return payload

    def _parse(self, payload: dict[str, Any]) -> str:
        return "".join(block.get("text", "") for block in payload.get("content", []))


class OpenAILLM(_HttpLLM):
    endpoint = "https://api.openai.com/v1/chat/completions"
    name = "openai"

    def _headers(self) -> dict[str, str]:
        return {"authorization": f"Bearer {self.api_key}"}

    def _payload(self, prompt: str, system: str, max_tokens: int) -> dict[str, Any]:
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        return {"model": self.model, "max_completion_tokens": max_tokens, "messages": messages}

    def _parse(self, payload: dict[str, Any]) -> str:
        return payload["choices"][0]["message"]["content"]


def default_client(env: dict[str, str] | None = None) -> LLMClient:
    environ = env if env is not None else dict(os.environ)
    provider = environ.get("RCM_LLM_PROVIDER", "auto").lower()
    anthropic_key = environ.get("ANTHROPIC_API_KEY", "")
    openai_key = environ.get("OPENAI_API_KEY", "")

    if provider in {"none", "off", "deterministic"}:
        return NullLLM()
    if provider == "anthropic" or (provider == "auto" and anthropic_key):
        if anthropic_key:
            return AnthropicLLM(anthropic_key, environ.get("RCM_LLM_MODEL", "claude-sonnet-4-5"))
    if provider == "openai" or (provider == "auto" and openai_key):
        if openai_key:
            return OpenAILLM(openai_key, environ.get("RCM_LLM_MODEL", "gpt-4.1-mini"))
    return NullLLM()


_JSON_BLOCK = re.compile(r"\{.*\}", re.DOTALL)


def complete_json(client: LLMClient, prompt: str, *, system: str = "") -> dict[str, Any] | None:
    """Ask the client for JSON, returning ``None`` when unavailable or unparsable."""

    if not client.available():
        return None
    raw = client.complete(prompt, system=system)
    if not raw:
        return None
    match = _JSON_BLOCK.search(raw)
    if not match:
        return None
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None
