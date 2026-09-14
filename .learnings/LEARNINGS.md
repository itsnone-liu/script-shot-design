# Learnings

Corrections, insights, and knowledge gaps captured during development.

**Categories**: correction | insight | knowledge_gap | best_practice

---

## [LRN-20260914-001] correction

**Logged**: 2026-09-14T18:36:00+08:00
**Priority**: critical
**Status**: in_progress
**Area**: docs

### Summary
Concert storytelling and dual-person identity require a different production grammar from the coffee-ad pipeline.

### Details
concert30 v1 reused calm, restrained pacing; this removed live singing, drums, lighting, crowd noise and arena tension. It also generated a lookalike girl and described Hua Chenyu symbolically instead of conditioning both identities from real references.

### Suggested Action
Let the live song drive every cut; compress audience-to-stage travel into rhythmic montage; keep performance running through the flower exchange and photo. Feed the girl's original photos directly. Build a single-era public Hua Chenyu reference pack and enforce two independent identity gates plus cross-ID separation.

### Metadata
- Source: user_feedback
- Related Files: examples/concert30_hcy_flowers/production_plan_v1.json, examples/concert30_hcy_flowers/production_plan_v2.json
- Tags: concert, screenplay, identity, qa

---

## [LRN-20260912-006] best_practice

**Logged**: 2026-09-12T09:42:00+08:00
**Priority**: critical
**Status**: resolved
**Area**: backend

### Summary
821 must treat user script approval and director-prompt compilation as separate hard stages.

### Details
Story causality improved in both people and product-only versions, but creative quality remains the root of output quality. Structural validation cannot replace user review. After approval, abstract story language must be compiled into a Prompt Bible, physical visible states, 3–6 in-shot beats, one motivated camera path, focus transitions and an editable final hold. New scripts must generate new shot structures instead of being fitted into inherited templates.

### Suggested Action
Require `user_script_review` before export/render; use structured director contracts and camera lint for all new MiniMax segments; run controlled A/B experiments before promoting camera recipes.

### Metadata
- Source: user_feedback
- Related Files: shortfilm/prompt_contract.py, shortfilm/camera_lint.py, shortfilm/model.py
- Tags: approval, prompting, camera, minimax

---

## [LRN-20260912-007] correction

**Logged**: 2026-09-12T23:38:00+08:00
**Priority**: critical
**Status**: in_progress
**Area**: backend

### Summary
Script and editorial rhythm must determine shot structure; MiniMax segment duration and single-move recipes are packaging constraints, not creative laws.

### Details
The EV30 implementation over-promoted two experimental findings into architecture: 3×10-second generation segments became the story skeleton, and one primary camera move was enforced over each whole segment. This improved camera compliance but made the film structurally rigid. MiniMax can generate internal cuts and shot-size changes inside a 5–15-second container; the screenplay should first choose shots and motivated cuts, then pack compatible adjacent shots into model calls. The single-move result remains valid only for one internal shot or continuous action, not a complete generation segment or film.

### Suggested Action
Refactor the contract to represent internal shots with explicit cut types and per-shot camera plans; make generation segments variable-duration containers chosen after script approval; modify or replace the RunningHub T2V card so duration is an exposed 5–15s parameter; use the high-variation drink advertisement as a validation target.

### Metadata
- Source: user_feedback
- Related Files: shortfilm/prompt_contract.py, shortfilm/camera_lint.py, shortfilm/knowledge/MINIMAX_SEGMENT_PROMPTING.md, examples/ev30/
- Tags: script-first, editing, internal-cuts, variable-duration, minimax
- See Also: LRN-20260912-006

---

## [LRN-20260912-001] best_practice

**Logged**: 2026-09-12T00:00:00Z
**Priority**: high
**Status**: resolved
**Area**: infra

### Summary
知乎访问研究必须连接用户已经打开且可访问的 Chrome 调试实例，不能新建匿名 Playwright 浏览器上下文。

### Details
新启动的 headless/有头 Chrome 和匿名 context 都返回知乎 40362；用户实际打开的调试版和非调试版可以正常访问。检查发现用户 Chrome 正在以 `--remote-debugging-port=9222 --user-data-dir=C:\\chrome-debug-profile` 运行，且已有知乎页面和登录/风控状态。改为 `connect_over_cdp('http://127.0.0.1:9222')` 并复用已有 context 后，两篇文章均成功读取。

### Suggested Action
以后遇到用户说“我浏览器能打开、自动化打不开”，优先检查现有 Chrome 进程和调试端口；复用现有页面/session，而不是新建 context。连接后只 disconnect，不关闭用户浏览器。

### Metadata
- Source: error
- Related Files: `_read_zhihu_articles.py`
- Tags: chrome, cdp, playwright, zhihu, real-browser
- Pattern-Key: browser.reuse-live-cdp-session
- Recurrence-Count: 1

---

## [LRN-20260912-002] correction

**Logged**: 2026-09-12T08:05:00Z
**Priority**: critical
**Status**: pending
**Area**: backend

### Summary
方块化视觉不能在生成后才发现，必须在产品视觉脚本和提示词阶段被质量闸门拦截。

### Details
用户指出：原剧本改写后仍然产生方块，说明问题不只在原故事，也在大模型要求和验收标准。产品广告需要具体材质、可执行的物理转化链和可识别的产品形态；“简单图形、抽象形状、视觉化答案”即使附带“不要方块”也会把视频模型推向几何占位符。当前确定性诊断只检查结构因果、时长和脚本存在，未检查产品级视觉设计。

### Suggested Action
新增产品视觉设计闸门：禁止抽象/几何占位词；要求每个视觉变化有具体物质、前状态、动作、后状态、因果和可验证的首尾帧；禁止“否定词补救”代替正向材质设计。对未通过的概念直接 block，不进入 RunningHub。

### Metadata
- Source: user_feedback
- Related Files: validators.py, visual_reset_pipeline.py, stages.py
- Tags: product-ad, visual-design, prompt-quality, minimax, quality-gate

---
