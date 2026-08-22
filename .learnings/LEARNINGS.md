# Learnings —— 821

## LRN-001：后台服务启动必须清 PYTHONPATH（跨 venv 劫持）

- **症状**：`.venv-lab\Scripts\python.exe -m uvicorn service.app:app` 报
  `No module named 'pydantic_core._pydantic_core'`，traceback 落在
  `C:\Users\pc\AppData\Local\hermes\hermes-agent\venv\Lib\site-packages`。
- **原因**：harness 注入的 `PYTHONPATH` 指向 hermes venv 的 site-packages；
  `-m uvicorn` 先从 PYTHONPATH 解析到 hermes 的 uvicorn/pydantic，其二进制
  与目标 venv 的 Python 版本不匹配。
- **修复**：启动任何后台服务前先 `$env:PYTHONPATH=''`（820 既有惯例，适用于
  所有 venv python 调用）。

## LRN-002：中文文件名下载头必须 URL 编码

- FastAPI/Starlette 的 header 只接受 latin-1；
  `Content-Disposition: filename*=UTF-8''二次函数.pptx` 直接 500。
- **修复**：`urllib.parse.quote(filename)` 后再拼 `filename*=UTF-8''...`。

## LRN-003：模板占位文字要在映射提示词里点名处理

- 首版映射沿用了 OpenTutor 的"装饰文字可跳过"措辞，结果封面的 Lorem ipsum
  段与"汇报人：第一PPT"原样保留。
- **修复**：提示词显式列出"Lorem ipsum、示例汇报人等不得原样保留"，并给出
  改写方向（汇报人→主讲教师、汇报部门→课程名，纯占位→副标题/日期）。
  重建后占位残留 0。
