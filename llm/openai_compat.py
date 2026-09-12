"""Small OpenAI-compatible adapter using only the Python standard library."""
from __future__ import annotations
import json, urllib.request
from typing import Any

class OpenAICompatibleClient:
    def __init__(self, base_url: str, api_key: str, model: str, timeout: int = 180, enable_thinking: bool = False):
        self.base_url, self.api_key, self.model, self.timeout, self.enable_thinking = base_url.rstrip("/"), api_key, model, timeout, enable_thinking
    def complete(self, messages, schema, *, stage: str) -> dict[str, Any]:
        prompt = list(messages) + [{"role":"user", "content": "Return JSON matching this schema:\n" + json.dumps(schema, ensure_ascii=False)}]
        body = {"model": self.model, "temperature": 0.7, "max_tokens": 5000, "messages": prompt, "response_format": {"type":"json_object"}}
        # Alibaba Bailian exposes thinking control as enable_thinking. Keeping it
        # off is essential for this structured-output path: reasoning must not
        # consume the completion budget while content stays empty.
        if not self.enable_thinking:
            body["enable_thinking"] = False
        payload = json.dumps(body).encode()
        req = urllib.request.Request(self.base_url, payload, {"Content-Type":"application/json", "Authorization":f"Bearer {self.api_key}"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r: data = json.loads(r.read().decode())
        except Exception as exc:
            raise RuntimeError(f"LLM request failed for stage={stage}: {exc}") from exc
        message = data["choices"][0]["message"]
        text = (message.get("content") or "").strip()
        if not text and message.get("reasoning_content"):
            raise RuntimeError(f"LLM returned reasoning without JSON for stage={stage}; increase max_tokens or simplify prompt")
        if text.startswith("```"): text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"LLM returned invalid JSON for stage={stage}: {text[:240]}") from exc
