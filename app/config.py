"""config.py —— 821 配置：.env / 环境变量 / 密钥文件。"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PROJECTS = DATA / "projects"
UPLOADS = DATA / "uploads"

for _d in (PROJECTS, UPLOADS):
    _d.mkdir(parents=True, exist_ok=True)


def _load_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"'))


def _find_key() -> str:
    # 1) 显式环境变量 2) .env 已并入环境 3) 密钥文件（兼容 820 惯例）
    for candidate in (ROOT / ".qwen_key", ROOT.parent / "820" / ".qwen_key"):
        if candidate.is_file():
            text = candidate.read_text(encoding="utf-8").strip()
            if text:
                return text.splitlines()[0].strip()
    return ""


_load_env()

LAB_BASE_URL = os.environ.get("LAB_BASE_URL", "http://127.0.0.1:8127").rstrip("/")
LLM_BASE_URL = os.environ.get(
    "LLM_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/")
LLM_MODEL = os.environ.get("LLM_MODEL", "qwen-plus")
LLM_API_KEY = os.environ.get("LLM_API_KEY", "") or _find_key()
LLM_TIMEOUT = int(os.environ.get("LLM_TIMEOUT", "240"))
LAB_TIMEOUT = int(os.environ.get("LAB_TIMEOUT", "600"))
MAX_UPLOAD_BYTES = int(os.environ.get("MAX_UPLOAD_BYTES", str(30 * 1024 * 1024)))
