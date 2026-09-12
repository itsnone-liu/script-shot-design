# Learnings

Corrections, insights, and knowledge gaps captured during development.

**Categories**: correction | insight | knowledge_gap | best_practice

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
