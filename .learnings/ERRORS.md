# Errors

Command failures and integration errors.

---

## [ERR-20260911-005] RunningHub polling read timeout

**Logged**: 2026-09-11T10:05:00+08:00
**Priority**: high
**Status**: resolved
**Area**: backend

### Summary
S05 image-to-video submission reached RunningHub, but status polling raised a network read timeout before the task result was persisted.

### Suggested Fix
Persist `task_id` immediately after task creation and treat transient status timeouts as retryable polling events rather than replacing the shot record with a generic failure.

### Metadata
- Reproducible: unknown
- Related Files: `shortfilm/rh_adapter.py`, `shortfilm/cli/render_shots.py`, `../820/experiments/rh_task.py`

### Resolution
- **Resolved**: 2026-09-11T10:08:00+08:00
- **Notes**: Two history checks confirmed no task was created; a single controlled retry succeeded. Persisting task IDs before polling remains a future hardening item.

---

## [ERR-20260911-004] Combined background-server command rejected

**Logged**: 2026-09-11T09:40:00+08:00
**Priority**: low
**Status**: resolved
**Area**: infra

### Summary
A single PowerShell command combining dynamic paths, `Start-Process`, delay, and HTTP checks was rejected by the execution policy.

### Suggested Fix
Resolve and verify paths first, then run the hidden background process and health checks as separate commands with fixed absolute paths.

### Metadata
- Reproducible: unknown
- Related Files: `output/ad30_coffee/index.html`

### Resolution
- **Resolved**: 2026-09-11T09:41:00+08:00
- **Notes**: Deployment was split into fixed-path steps.

---

## [ERR-20260911-003] Portrait output passed to landscape crop

**Logged**: 2026-09-11T09:01:00+08:00
**Priority**: high
**Status**: resolved
**Area**: backend

### Summary
The normalizer assumed every RH output was landscape and attempted an invalid crop on a native 9:16 I2V result.

### Error
FFmpeg failed while normalizing a 480x864 source.

### Suggested Fix
Probe source dimensions and branch between focus-aware landscape crop and full-frame portrait scale/pad.

### Metadata
- Reproducible: yes
- Related Files: `shortfilm/cli/normalize_video.py`

### Resolution
- **Resolved**: 2026-09-11T09:02:00+08:00
- **Notes**: Added ffprobe-based aspect handling.

---

## [ERR-20260911-002] I2V reference image omitted

**Logged**: 2026-09-11T08:55:00+08:00
**Priority**: critical
**Status**: resolved
**Area**: backend

### Summary
The I2V adapter accepted and uploaded a reference image but omitted it from `nodeInfoList`, allowing cached workflow images to produce unrelated anime footage.

### Error
S03 rendered as an anime woman instead of the locked contemporary male designer first frame.

### Context
- Workflow: `2092512701252022274`
- The verified 820 workflow contract uses image nodes 137 and 143.

### Suggested Fix
Always override both cached first-frame and last-frame image nodes when an I2V reference is supplied, and assert them in dry-run QA.

### Metadata
- Reproducible: yes
- Related Files: `shortfilm/rh_adapter.py`, `shortfilm/cli/render_shots.py`

### Resolution
- **Resolved**: 2026-09-11T08:56:00+08:00
- **Notes**: I2V now emits nodes 137 and 143 for every supplied per-shot reference.

---

## [ERR-20260911-001] Python CLI import path

**Logged**: 2026-09-11T08:30:00+08:00
**Priority**: low
**Status**: resolved
**Area**: tests

### Summary
The bundled Python executable does not automatically include the repository root when running project CLI scripts.

### Error
`ModuleNotFoundError: No module named 'shortfilm'`

### Context
- Direct script execution and `python -m` both failed from the repository root.
- The environment uses an embedded Python distribution.

### Suggested Fix
Insert the repository root into `sys.path` before invoking `shortfilm` CLI modules with the embedded interpreter, or use a standard Python installation.

### Metadata
- Reproducible: yes
- Related Files: `shortfilm/cli/validate_project.py`, `shortfilm/cli/qa_report.py`

### Resolution
- **Resolved**: 2026-09-11T08:31:00+08:00
- **Notes**: The embedded interpreter ignored `PYTHONPATH`; validation succeeded by inserting the repository root into `sys.path` inside the process and invoking the module through `runpy`.

---

## [ERR-20260911-002] MiniMax final-hold validator rejected valid durations

**Logged**: 2026-09-11T15:30:00+08:00
**Priority**: medium
**Status**: resolved
**Area**: tests

### Summary
The prompt gate only recognized final holds beginning with `0.` or `1.` and incorrectly rejected a deliberate 2.5-second advertising end card.

### Error
`LIGHT03: generation_prompt must define a final hold/interface state`

### Context
- Reproduced while validating `examples/ad30_light/project.json`.
- The prompt explicitly said `final 2.5 seconds`, but the gate used two hard-coded substring checks.

### Suggested Fix
Recognize any positive numeric duration in the phrase `final N seconds`.

### Metadata
- Reproducible: yes
- Related Files: `shortfilm/model.py`, `examples/ad30_light/project.json`

### Resolution
- **Resolved**: 2026-09-11T15:32:00+08:00
- **Notes**: Replaced hard-coded duration prefixes with a numeric regular expression.

---

## [ERR-20260911-003] Successful RH task returned a corrupt MP4 download

**Logged**: 2026-09-11T18:34:00+08:00
**Priority**: medium
**Status**: pending
**Area**: backend

### Summary
`LIGHT01` reached RH success but its downloaded MP4 lacked a `moov` atom, so normalization failed; later serial tasks were unaffected.

### Error
`moov atom not found` / `Invalid data found when processing input`

### Context
- Raw file existed but was only about 1 MB and was not a valid MP4.
- Renderer currently records only the normalization exception and loses the successful task id/output URL in the failed manifest item.

### Suggested Fix
Validate downloaded media before normalization, retry the download, and preserve task id/raw URL in failure manifests.

### Metadata
- Reproducible: unknown
- Related Files: `shortfilm/cli/render_shots.py`, `shortfilm/cli/normalize_video.py`

---
