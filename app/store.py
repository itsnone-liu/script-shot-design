"""store.py —— 项目持久化：data/projects/<id>/project.json（免 DB）。"""
from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path

from . import config

_LOCKS: dict[str, threading.Lock] = {}
_LOCKS_GUARD = threading.Lock()


def _lock(project_id: str) -> threading.Lock:
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(project_id, threading.Lock())


def new_project_id() -> str:
    return time.strftime("%Y%m%d_%H%M%S_") + uuid.uuid4().hex[:6]


def project_dir(project_id: str) -> Path:
    d = config.PROJECTS / project_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def save(project_id: str, state: dict) -> None:
    with _lock(project_id):
        path = project_dir(project_id) / "project.json"
        path.write_text(
            json.dumps(state, ensure_ascii=False, indent=1),
            encoding="utf-8")


def load(project_id: str) -> dict | None:
    path = config.PROJECTS / project_id / "project.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def list_projects() -> list[dict]:
    out = []
    for path in sorted(config.PROJECTS.glob("*/project.json"),
                       reverse=True):
        try:
            state = json.loads(path.read_text(encoding="utf-8"))
            out.append({
                "id": state.get("id"),
                "title": state.get("title") or "",
                "template_name": (state.get("template") or {}).get("name", ""),
                "updated_at": state.get("updated_at"),
                "lab_deck_id": (state.get("lab") or {}).get("deck_id"),
            })
        except (json.JSONDecodeError, OSError):
            continue
    return out
