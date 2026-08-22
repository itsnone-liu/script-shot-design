# 进度快照 —— 2026-08-22（P1–P8 全部完成，端到端验证通过）

## 结论

OpenTutor 的“教案/课件文字 + PPT 模板 → 可编辑 PPTX”模块已抽成独立项目 821，
本地双服务可跑，真实 38 页模板端到端验证通过（含单页修订与下载）。**未上线**（按要求只完成代码）。

## 验证证据（2026-08-22）

- 模板导入：38 页 → lab 目录（并列卡片 11 / 通用内容 8 / 章节过渡 6 / 图文 5…）
- 风格卡：色板 `#44546A/#4472C4/#ED7D31…`；字体 思源黑体/微软雅黑/思源宋体 CN Heavy；
  LLM 综合描述正常
- 教案（二次函数复习课，约 400 字）→ 7 页课件文字（封面/学习目标/图象特征/配方法/辨析/练习/小结）
- build 43–62s：映射合理（封面→#1、目标→#31 卡片、结束→#38），全部页有内容，无空页
- 占位清理：收紧提示词后 Lorem ipsum/示例汇报人 **0 残留**（封面改写为“课程名：数学复习课/主讲教师：数学组”）
- 单页修订：意见+换参考页 → revision 2 正常
- 下载：264KB 有效 PPTX（7 页，zip 结构完整，课件文字在 slide XML 中可检索）

## 运行

```powershell
# 1) lab（模板识别，:8127）——注意必须清 PYTHONPATH（见 .learnings）
$env:PYTHONPATH=''
& "D:\AI-Teaching-Assistant\PPT-Template-Lab\.venv-lab\Scripts\python.exe" -m uvicorn service.app:app --port 8127
#   （workdir = D:\AI-Teaching-Assistant\PPT-Template-Lab）

# 2) 821（:8840）
$env:PYTHONPATH=''
& "D:\AI-Teaching-Assistant\OpenTutor\apps\api\.venv\Scripts\python.exe" -m uvicorn app.main:app --port 8840
#   （workdir = 821 根目录；LLM key 取自 820 的 .qwen_key 或 .env）

# 浏览器 http://localhost:8840
```

## 已知边界（v1）

- 结构性模板标签（如内容页的“后续工作计划”“第一步”）可能保留——语义上中性，逐页修订可改
- fit-text 只缩字号不换参考页；文字严重超槽时应在 UI 换参考页
- 视觉生图通道关闭（schema 保留；lab 图片替换 API 已在客户端就绪）
- 任务无队列：并发 build 会同时打满 lab 的 CLI 子进程；单用户场景可接受
- 项目存储为文件 JSON，无锁并发写可能丢更新（单用户可接受）
