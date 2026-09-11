# Errors

Command failures and integration errors.

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
