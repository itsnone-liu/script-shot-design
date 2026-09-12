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
