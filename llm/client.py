"""Provider-neutral LLM client protocol."""
from __future__ import annotations
from typing import Any, Protocol

class LLMClient(Protocol):
    def complete(self, messages: list[dict[str, str]], schema: dict[str, Any], *, stage: str) -> dict[str, Any]: ...
