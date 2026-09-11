# Errors

Command failures and integration errors.

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
