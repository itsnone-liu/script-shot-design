"""Thin sequential adapter from 821 shot packets to 820's RH task client.

820 remains the owner of RunningHub authentication, upload, polling and download.
This module only translates a shot into the known video workflow inputs and never
launches tasks concurrently (important for a personal account and rate limits).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_820 = Path(__file__).resolve().parents[2] / "820"
if str(ROOT_820) not in sys.path:
    sys.path.insert(0, str(ROOT_820))

from experiments import rh_task  # type: ignore  # noqa: E402


# Legacy dual-sampling/upscale card: dynamic duration node exists, but >10s
# can OOM at its baked 1.2x second-pass settings. Keep it as t2v_quality.
T2V_WORKFLOW = "2092847765977378817"
# Variable-duration single-pass card (5-15s) is populated after the RH copy/bake
# step; until then calls fail locally rather than silently using the legacy card.
T2V_VARIABLE_WORKFLOW = ""
I2V_WORKFLOW = "2092512701252022274"


def _prompt(packet: dict) -> str:
    return str(packet.get("prompt") or "")


def build_node_info(packet: dict, *, workflow: str = "t2v", reference_file: str = "",
                    last_reference_file: str = "") -> list[dict]:
    """Build the minimum verified nodeInfoList for 820's video cards."""
    duration=float(packet["duration"])
    ranges={"t2v":(4,10),"t2v_quality":(4,10),"t2v_variable":(5,15),"i2v":(4,15)}
    if workflow not in ranges: raise ValueError(f"unsupported workflow profile={workflow}")
    min_duration,max_duration=ranges[workflow]
    if duration < min_duration or duration > max_duration:
        raise ValueError(f"{workflow} workflow duration must be in [{min_duration}, {max_duration}], got {duration:g}")
    if workflow=="t2v_variable" and not T2V_VARIABLE_WORKFLOW:
        raise RuntimeError("t2v_variable workflow is not baked yet; configure T2V_VARIABLE_WORKFLOW after RH validation")
    if workflow == "i2v":
        if not reference_file:
            raise ValueError("i2v requires an explicit first-frame reference; refusing cached workflow defaults")
        nodes = [
            {"nodeId": "136", "fieldName": "prompt", "fieldValue": _prompt(packet)},
            {"nodeId": "135", "fieldName": "value", "fieldValue": str(round(float(packet["duration"])))},
        ]
        if reference_file:
            # This workflow caches both a first-frame and a last-frame input.
            # Both must be overridden or stale images from the RH snapshot leak
            # into the result (observed as an unrelated anime character).
            nodes.extend([
                {"nodeId": "137", "fieldName": "image", "fieldValue": reference_file},
                {"nodeId": "143", "fieldName": "image", "fieldValue": last_reference_file or reference_file},
            ])
        return nodes
    nodes = [
        {"nodeId": "138", "fieldName": "value", "fieldValue": _prompt(packet)},
        # The RH card requires duration to be sent even though its cache has a default.
        {"nodeId": "132", "fieldName": "value", "fieldValue": str(round(float(packet["duration"])))},
    ]
    if reference_file:
        nodes.extend([
            {"nodeId": "137", "fieldName": "image", "fieldValue": reference_file},
            {"nodeId": "139", "fieldName": "image", "fieldValue": reference_file},
        ])
    return nodes


def render_packet(packet: dict, output_dir: str | Path, *, workflow: str = "t2v",
                  api_key: str = "", dry_run: bool = False, poll: float = 10.0,
                  max_wait: float = 1200.0, reference_file: str = "",
                  last_reference_file: str = "") -> dict:
    """Render one packet synchronously and download its video outputs."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    workflow_id = (I2V_WORKFLOW if workflow == "i2v" else
                   T2V_VARIABLE_WORKFLOW if workflow == "t2v_variable" else T2V_WORKFLOW)
    nodes = build_node_info(packet, workflow=workflow, reference_file=reference_file,
                            last_reference_file=last_reference_file)
    if dry_run:
        return {"shot_id": packet["shot_id"], "workflow_id": workflow_id,
                "nodeInfoList": nodes, "status": "dry-run"}
    key = rh_task.load_api_key(api_key)
    if not key:
        raise RuntimeError("RH API key unavailable; configure 820/.rh_apikey or RH_API_KEY")
    task_id = rh_task.run_workflow(key, workflow_id, nodes)
    result = rh_task.wait_task(key, task_id, poll=poll, max_wait=max_wait,
                               on_progress=lambda _tid, state: print(f"[{packet['shot_id']}] {state}"))
    urls = rh_task.collect_file_urls(result)
    files = []
    for index, url in enumerate(urls):
        if any(ext in url.lower() for ext in (".mp4", ".webm", ".mov", ".mkv", ".gif")):
            files.append(str(rh_task.download(url, output_dir / f"{packet['shot_id']}_{index:02d}.mp4")))
    return {"shot_id": packet["shot_id"], "workflow_id": workflow_id,
            "task_id": task_id, "status": "success", "outputs": files}
