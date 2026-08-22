"""lab_client.py —— PPT-Template-Lab HTTP 客户端（移植自 OpenTutor 同名模块，改同步）。"""
from __future__ import annotations

from pathlib import Path

import httpx

from . import config

PPTX_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


class LabError(RuntimeError):
    pass


def _client(timeout: float | None = None) -> httpx.Client:
    return httpx.Client(base_url=config.LAB_BASE_URL,
                        timeout=timeout or config.LAB_TIMEOUT)


def health() -> bool:
    try:
        with _client(5) as client:
            resp = client.get("/health")
            return resp.status_code == 200 and resp.json().get("status") == "ok"
    except httpx.HTTPError:
        return False


def upload_template(path: Path, filename: str) -> dict:
    with path.open("rb") as source:
        with _client() as client:
            resp = client.post("/api/v1/templates",
                               files={"file": (filename, source, PPTX_MIME)})
    if resp.status_code >= 400:
        raise LabError(f"模板导入失败({resp.status_code})：{resp.text[:200]}")
    return resp.json()


def template_slides(template_id: str) -> list[dict]:
    with _client() as client:
        resp = client.get(f"/api/v1/templates/{template_id}/slides")
    if resp.status_code == 404:
        raise LabError("模板不存在（可能 lab 数据目录被清理）")
    resp.raise_for_status()
    return resp.json()


def template_preview_svg(template_id: str, slide_index: int) -> bytes:
    with _client(120) as client:
        resp = client.get(
            f"/api/v1/templates/{template_id}/slides/{slide_index}/preview")
    if resp.status_code >= 400:
        raise LabError("预览不存在")
    return resp.content


def upload_asset(path: Path) -> dict:
    with path.open("rb") as source:
        with _client() as client:
            resp = client.post(
                "/api/v1/assets",
                files={"file": (path.name, source,
                                "application/octet-stream")})
    resp.raise_for_status()
    return resp.json()


def create_deck(template_id: str, payload: dict) -> dict:
    with _client() as client:
        resp = client.post(f"/api/v1/templates/{template_id}/decks",
                           json=payload)
    if resp.status_code >= 400:
        raise LabError(f"deck 生成失败({resp.status_code})：{resp.text[:300]}")
    return resp.json()


def revise_slide(deck_id: str, page_id: str, payload: dict) -> dict:
    with _client() as client:
        resp = client.patch(
            f"/api/v1/decks/{deck_id}/slides/{page_id}", json=payload)
    if resp.status_code >= 400:
        raise LabError(f"单页修订失败({resp.status_code})：{resp.text[:300]}")
    return resp.json()


def get_deck(deck_id: str) -> dict:
    with _client() as client:
        resp = client.get(f"/api/v1/decks/{deck_id}")
    if resp.status_code == 404:
        raise LabError("deck 不存在")
    resp.raise_for_status()
    return resp.json()


def download_deck(deck_id: str) -> bytes:
    with _client() as client:
        resp = client.get(f"/api/v1/decks/{deck_id}/download")
    resp.raise_for_status()
    return resp.content


def deck_preview_png(deck_id: str, revision: int, slide_index: int) -> bytes:
    path = (f"/api/v1/decks/{deck_id}/revisions/{revision}"
            f"/slides/{slide_index}/preview")
    with _client(120) as client:
        resp = client.get(path)
    if resp.status_code >= 400:
        raise LabError("页面预览不存在")
    return resp.content
