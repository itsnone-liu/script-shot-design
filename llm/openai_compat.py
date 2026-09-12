"""Small OpenAI-compatible adapter using only the Python standard library."""
from __future__ import annotations
import json, urllib.request
from typing import Any

class OpenAICompatibleClient:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: int = 180):
        self.base_url, self.api_key, self.model, self.timeout = base_url.rstrip("/"), api_key, model, timeout
    def complete(self, messages, schema, *, stage: str) -> dict[str, Any]:
        prompt = list(messages) + [{"role":"user", "content": "Return JSON matching this schema:\n" + json.dumps(schema, ensure_ascii=False)}]
        payload = json.dumps({"model": self.model, "temperature": 0.8, "messages": prompt, "response_format": {"type":"json_object"}}).encode()
        req = urllib.request.Request(self.base_url, payload, {"Content-Type":"application/json", "Authorization":f"Bearer {self.api_key}"})
        with urllib.request.urlopen(req, timeout=self.timeout) as r: data = json.loads(r.read().decode())
        text = data["choices"][0]["message"]["content"].strip()
        if text.startswith("```"): text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        return json.loads(text)
