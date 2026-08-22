"""main.py —— 821 FastAPI 服务：模板上传/分析 + 课件项目 + 生成/修订/下载 + 前端。

启动：
    先启动 PPT-Template-Lab（:8127），再：
    uvicorn app.main:app --port 8840   （或 python -m app.main）
"""
from __future__ import annotations

import io
import time
import urllib.parse
import zipfile
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from . import config, deckgen, lab_client, llm, mapper, store, stylecard

app = FastAPI(title="课件生成（教案/课件文字 × PPT 模板）", version="0.1.0")

STATIC = Path(__file__).resolve().parent.parent / "static"


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "lab": {"url": config.LAB_BASE_URL, "ok": lab_client.health()},
        "llm": {"model": config.LLM_MODEL,
                "configured": bool(config.LLM_API_KEY)},
    }


# ------------------------------------------------------------ 模板

@app.post("/api/templates")
def upload_template(file: UploadFile = File(...)) -> dict:
    if not (file.filename or "").lower().endswith(".pptx"):
        raise HTTPException(400, "只支持 .pptx 模板。")
    data = file.file.read()
    if not data or len(data) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(400, "模板为空或超过大小限制。")
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            if ("[Content_Types].xml" not in archive.namelist()
                    or not any(n.startswith("ppt/") for n in archive.namelist())):
                raise HTTPException(400, "文件不是有效的 PowerPoint 模板。")
    except zipfile.BadZipFile as exc:
        raise HTTPException(400, "文件不是有效的 PowerPoint 模板。") from exc

    saved = config.UPLOADS / f"{int(time.time())}_{Path(file.filename).stem[:40]}.pptx"
    saved.write_bytes(data)
    try:
        meta = lab_client.upload_template(saved, file.filename or "template.pptx")
    except lab_client.LabError as exc:
        raise HTTPException(502, str(exc)) from exc
    catalog = lab_client.template_slides(meta["template_id"])
    card = stylecard.build_style_card(saved, catalog)
    return {
        "template_id": meta["template_id"],
        "name": meta.get("name", ""),
        "slide_count": meta.get("slide_count", len(catalog)),
        "catalog": catalog,
        "style_card": card,
        "saved_path": str(saved),
    }


@app.get("/api/templates/{template_id}/slides/{slide_index}/preview")
def template_preview(template_id: str, slide_index: int) -> Response:
    try:
        svg = lab_client.template_preview_svg(template_id, slide_index)
    except lab_client.LabError as exc:
        raise HTTPException(404, str(exc)) from exc
    return Response(svg, media_type="image/svg+xml")


# ------------------------------------------------------------ 项目

@app.get("/api/projects")
def projects() -> list[dict]:
    return store.list_projects()


@app.post("/api/projects")
def create_project(body: dict) -> dict:
    mode = str(body.get("mode") or "")
    if mode not in ("lesson_plan", "courseware_text"):
        raise HTTPException(400, "mode 必须是 lesson_plan 或 courseware_text。")
    source = str(body.get("source_text") or "")
    template = body.get("template") or {}
    template_id = str(template.get("template_id") or "")
    if not template_id:
        raise HTTPException(400, "请先上传并分析模板。")
    if not source.strip():
        raise HTTPException(400, "请填写教案或课件文字内容。")

    if mode == "lesson_plan":
        try:
            deck = deckgen.deck_from_lesson_plan(
                source,
                slide_target=int(body.get("slide_target") or 0),
                extra_instructions=str(body.get("instructions") or ""))
        except llm.LLMError as exc:
            raise HTTPException(502, f"课件文字生成失败：{exc}") from exc
    else:
        try:
            deck = deckgen.parse_courseware_text(source)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc

    project_id = store.new_project_id()
    state = {
        "id": project_id,
        "title": deck.get("title") or "未命名课件",
        "mode": mode,
        "source_text": source,
        "template": {"template_id": template_id,
                     "name": template.get("name", "")},
        "deck": deck,
        "lab": {},
        "mapping": [],
        "log": [f"deck 解析完成：{len(deck['slides'])} 页（mode={mode}）"],
        "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    store.save(project_id, state)
    return state


@app.get("/api/projects/{project_id}")
def get_project(project_id: str) -> dict:
    state = store.load(project_id)
    if not state:
        raise HTTPException(404, "项目不存在。")
    return state


@app.post("/api/projects/{project_id}/build")
def build_deck(project_id: str) -> dict:
    """语义页 -> 参考页映射 -> lab 生成 deck（含预览）。"""
    state = store.load(project_id)
    if not state:
        raise HTTPException(404, "项目不存在。")
    template_id = state["template"]["template_id"]
    try:
        catalog = lab_client.template_slides(template_id)
    except lab_client.LabError as exc:
        raise HTTPException(502, f"lab 模板目录不可用：{exc}") from exc

    try:
        instances, report = mapper.plan_pages(state["deck"], catalog)
    except llm.LLMError as exc:
        raise HTTPException(502, f"槽位映射失败：{exc}") from exc

    try:
        result = lab_client.create_deck(template_id, {
            "name": state["title"] or "课件", "slides": instances})
    except lab_client.LabError as exc:
        raise HTTPException(502, str(exc)) from exc

    for slide, item in zip(state["deck"]["slides"], report):
        slide["template_source_slide"] = item["source_slide"]
    state["mapping"] = report
    state["lab"] = {
        "deck_id": result["deck_id"],
        "revision": result.get("revision", 1),
        "slide_count": result.get("slide_count", len(instances)),
        "preview_base": result.get("preview_base", ""),
        "quality": result.get("quality"),
    }
    state["log"].append(
        f"deck 生成：{len(instances)} 页，lab deck {result['deck_id']} rev"
        f"{result.get('revision', 1)}")
    state["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    store.save(project_id, state)
    return state


@app.post("/api/projects/{project_id}/pages/{page_id}/revise")
def revise_page_endpoint(project_id: str, page_id: str, body: dict) -> dict:
    """单页修订：instruction（自然语言）+ 可选 source_slide（换参考页）。"""
    state = store.load(project_id)
    if not state:
        raise HTTPException(404, "项目不存在。")
    lab_info = state.get("lab") or {}
    deck_id = lab_info.get("deck_id")
    if not deck_id:
        raise HTTPException(400, "请先生成课件（build）。")
    slide = next((s for s in state["deck"]["slides"] if s["id"] == page_id), None)
    if slide is None:
        raise HTTPException(404, f"页面 {page_id} 不存在。")
    instruction = str(body.get("instruction") or "").strip()
    source_slide = body.get("source_slide")
    if not instruction and source_slide is None:
        raise HTTPException(400, "请填写修改意见或选择新的模板参考页。")

    try:
        catalog = lab_client.template_slides(state["template"]["template_id"])
        current_index = int(slide.get("template_source_slide")
                            or (state["mapping"][0]["source_slide"]
                                if state.get("mapping") else 1))
        reference = next((c for c in catalog if int(c["index"]) == current_index),
                         catalog[0])
        if source_slide is not None:
            reference = next(
                (c for c in catalog if int(c["index"]) == int(source_slide)),
                None)
            if reference is None:
                raise HTTPException(400, f"参考页 {source_slide} 不存在。")
        payload = mapper.revise_page(
            slide, reference, instruction or "按当前语义页重新填充。",
            int(source_slide) if source_slide is not None else None)
        result = lab_client.revise_slide(deck_id, page_id, payload)
    except (lab_client.LabError, llm.LLMError) as exc:
        raise HTTPException(502, str(exc)) from exc

    slide["template_source_slide"] = result.get("source_slide",
                                                current_index)
    state["lab"]["revision"] = result.get("revision",
                                          state["lab"].get("revision", 1) + 1)
    state["log"].append(
        f"页 {page_id} 修订：{instruction[:40] or '换参考页'} -> rev"
        f"{state['lab']['revision']}")
    state["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    store.save(project_id, state)
    return state


@app.get("/api/projects/{project_id}/download")
def download(project_id: str) -> Response:
    state = store.load(project_id)
    if not state or not (state.get("lab") or {}).get("deck_id"):
        raise HTTPException(404, "项目不存在或尚未生成课件。")
    try:
        payload = lab_client.download_deck(state["lab"]["deck_id"])
    except (lab_client.LabError, Exception) as exc:
        raise HTTPException(502, f"下载失败：{exc}") from exc
    filename = f"{state.get('title') or '课件'}.pptx"
    quoted = urllib.parse.quote(filename)
    return Response(
        payload,
        media_type="application/vnd.openxmlformats-officedocument"
                   ".presentationml.presentation",
        headers={"Content-Disposition":
                 f"attachment; filename*=UTF-8''{quoted}"})


@app.get("/api/projects/{project_id}/previews/{slide_index}")
def deck_preview(project_id: str, slide_index: int) -> Response:
    state = store.load(project_id)
    if not state or not (state.get("lab") or {}).get("deck_id"):
        raise HTTPException(404, "尚未生成课件。")
    lab_info = state["lab"]
    try:
        png = lab_client.deck_preview_png(
            lab_info["deck_id"], lab_info.get("revision", 1), slide_index)
    except lab_client.LabError as exc:
        raise HTTPException(404, str(exc)) from exc
    return Response(png, media_type="image/png")


# ------------------------------------------------------------ 前端

@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8840)
