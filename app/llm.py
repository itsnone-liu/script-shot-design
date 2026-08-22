"""llm.py —— 最小 OpenAI 兼容 chat 客户端（移植自 OpenTutor 的调用契约）。

chat(system, user) -> str
json(system, user) -> dict   # 剥 ```json 围栏 + 捞首个 JSON 对象
"""
from __future__ import annotations

import json
import re

import httpx

from . import config


class LLMError(RuntimeError):
    pass


def chat(system: str, user: str, *, model: str | None = None,
         temperature: float = 0.4) -> str:
    if not config.LLM_API_KEY:
        raise LLMError("未配置 LLM_API_KEY（.env / 环境变量 / .qwen_key）")
    payload = {
        "model": model or config.LLM_MODEL,
        "temperature": temperature,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    headers = {"Authorization": f"Bearer {config.LLM_API_KEY}"}
    try:
        with httpx.Client(timeout=config.LLM_TIMEOUT) as client:
            resp = client.post(f"{config.LLM_BASE_URL}/chat/completions",
                               json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPError as exc:
        raise LLMError(f"LLM 请求失败：{exc}") from exc
    try:
        return data["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"LLM 返回结构异常：{str(data)[:200]}") from exc


def json_call(system: str, user: str, *, model: str | None = None) -> dict:
    raw = chat(system, user, model=model)
    cleaned = raw.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if not match:
            raise LLMError(f"LLM 未返回 JSON：{raw[:200]}")
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError as exc:
            raise LLMError(f"LLM JSON 解析失败：{raw[:200]}") from exc
    if not isinstance(parsed, dict):
        raise LLMError("LLM JSON 顶层不是对象")
    return parsed
