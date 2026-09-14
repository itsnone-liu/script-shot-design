# Feature Requests

Capabilities requested by the user.

---

## [FEAT-20260914-001] dual-real-person-identity-gate

**Logged**: 2026-09-14T18:36:00+08:00
**Priority**: high
**Status**: in_progress
**Area**: backend

### Requested Capability
Preserve one private person's identity from original photos and one public figure's identity from a public reference set in the same video.

### User Context
The concert fan video must preserve both the girl's real appearance and Hua Chenyu's recognizable identity across keyframes and video frames.

### Complexity Estimate
complex

### Suggested Implementation
Use direct H3 Ref2VA multi-reference conditioning, role-separated face tracking and sequential identity repair, per-role FaceComparator thresholds, and cross-ID checks.

### Metadata
- Frequency: first_time
- Related Features: Ref2VA, PuLID, InstantID, VACE video face swap

---
