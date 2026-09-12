"""Deterministic offline LLM fixture client."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

class MockClient:
    def __init__(self, fixture_dir: Path): self.fixture_dir = fixture_dir
    def complete(self, messages, schema, *, stage: str) -> dict[str, Any]:
        path = self.fixture_dir / f"{stage}.json"
        if not path.exists(): raise FileNotFoundError(path)
        return json.loads(path.read_text(encoding="utf-8"))
