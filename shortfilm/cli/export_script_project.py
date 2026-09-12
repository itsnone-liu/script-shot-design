"""Bridge an approved LLM script package into the existing shot project contract."""
from __future__ import annotations
import argparse, json
from pathlib import Path

def load(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("package", type=Path, help="LLM package output directory")
    ap.add_argument("template", type=Path, help="existing valid shot project template")
    ap.add_argument("output", type=Path)
    args=ap.parse_args()
    diagnostics=load(args.package/"diagnostics.json")
    reviews=load(args.package/"reviews.json") if (args.package/"reviews.json").exists() else {}
    approval_path=args.package/"user_script_review.json"
    approval=load(approval_path) if approval_path.exists() else {"status":"pending"}
    severe_reviews=[issue for review in reviews.get("reviews", []) for issue in (review.get("issues", []) if isinstance(review, dict) else []) if issue.get("severity") == "blocker"]
    approval_errors=[]
    if approval.get("status") != "approved": approval_errors.append("explicit user approval is required")
    if not str(approval.get("script_version","")).strip(): approval_errors.append("approved script_version is required")
    if not str(approval.get("reviewed_by","")).strip(): approval_errors.append("approved reviewed_by is required")
    if diagnostics.get("status") != "pass" or severe_reviews or approval_errors:
        print("SCRIPT GATE BLOCKED")
        if severe_reviews: print(f"blocking review issues: {len(severe_reviews)}")
        for error in approval_errors: print(f"approval: {error}")
        return 1
    project=load(args.template)
    beats=load(args.package/"beat_sheet.json").get("beats",[])
    scenes=load(args.package/"scene_cards.json").get("scenes",[])
    beat_by_id={b.get("id"):b for b in beats}
    scene_by_id={s.get("id"):s for s in scenes}
    for shot in project.get("shots",[]):
        scene=scene_by_id.get(shot.get("scene_id"),{})
        beat=beat_by_id.get(scene.get("beat_id"),{})
        if beat:
            shot["story_beat"]=beat.get("visible_event") or beat.get("state_out") or shot.get("story_beat")
        if scene:
            shot["subject_action"]=scene.get("action") or shot.get("subject_action")
            hints=scene.get("shot_hints") or []
            notes=scene.get("visual_notes") or ""
            audio=scene.get("audio_notes") or ""
            edit_design=scene.get("shot_list") or scene.get("editorial_shots") or []
            shot["generation_prompt"]="; ".join([str(x) for x in hints] + [notes, f"approved script-first internal shot list: {json.dumps(edit_design,ensure_ascii=False)}" if edit_design else "preserve the approved editorial cuts and shot timing", "single attention subject per internal shot; preserve continuity across cuts; no generated text", "explicitly render hard cuts, action/shape/color/sound match cuts and shot-size changes where listed", "one primary camera move per internal shot, not per whole generation container", "never show: readable text, logo, watermark, extra characters, sudden unexplained transformation", "continuity lock: preserve subject, product, light direction and screen direction", "only the final film container requires a stable hold; middle containers may exit on a declared cut action"])
            shot["sound"]=audio
    project["story_source"]={"package":str(args.package),"diagnostics":"pass","user_script_review":approval}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(project,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"EXPORTED SCRIPT PROJECT: {args.output}")
    return 0
if __name__=="__main__": raise SystemExit(main())
