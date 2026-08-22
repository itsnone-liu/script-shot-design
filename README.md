# 821 —— 课件生成独立服务

从 OpenTutor 抽取的"教案/课件文字 + PPT 模板 → 可编辑 PPTX"模块，独立成项目。
模板识别复用 [PPT-Template-Lab](../../../AI-Teaching-Assistant/PPT-Template-Lab)（本地 HTTP 服务）。

## 功能

- **内容来源二选一**
  - 教案内容：LLM 先转课件文字（每页标题 + 3-5 要点 + 讲稿提示）
  - 课件文字内容：直接解析（JSON `{"slides":[…]}` 或 Markdown 按标题分页，含容错链）
- **模板识别**（AI）
  - 布局：lab 逐页分类（封面/章节/目录/卡片/图文/数据/大图/结束）+ 槽位清单
  - 色彩/字体：OOXML theme 色板 + run 级字体/字号/颜色频次统计
  - 风格：LLM 综合上述机器信号生成风格卡（不虚构）
- **生成**：语义页 → 确定性参考页选择（版式族 + 使用均衡 + 槽位容量）→ LLM 槽位文字映射
  （服务端校验 slot_id/source_slide，伪造即丢弃，规则回退兜底）→ lab OOXML 原生填充
  → fit-text 自适应 → PNG 逐页预览
- **修订**：逐页自然语言意见 → LLM 重排槽位 / 换模板参考页 → 新 revision（旧版可回滚在 lab 侧）
- **下载**：可编辑 PPTX（保留模板设计、替换文字）

## 运行

```powershell
# 0) 依赖（本仓用 OpenTutor venv 已全部可用；独立环境则）
pip install -r requirements.txt

# 1) 先启动模板识别 lab（见其仓库 README；默认 :8127）
#    D:\AI-Teaching-Assistant\PPT-Template-Lab

# 2) 配置
copy .env.example .env      # 填 LLM_API_KEY（或放 .qwen_key 单行文件）

# 3) 启动本服务
$env:PYTHONPATH=''
& "D:\AI-Teaching-Assistant\OpenTutor\apps\api\.venv\Scripts\python.exe" -m uvicorn app.main:app --port 8840
# 浏览器打开 http://localhost:8840
```

## 结构

```
app/
  config.py    .env/密钥文件 解析
  llm.py       OpenAI 兼容 chat/json（默认 dashscope qwen-plus）
  lab_client.py  PPT-Template-Lab HTTP 客户端（自 OpenTutor 移植改同步）
  deckgen.py   教案→课件文字 + 容错解析链（自 OpenTutor teacher.py 移植）
  stylecard.py 模板风格/色彩/字体识别（OOXML + LLM 综合）
  mapper.py    参考页选择/槽位映射/单页修订（自 native_presentation_bridge 移植）
  store.py     data/projects/<id>/project.json（免 DB）
  main.py      FastAPI：模板/项目/生成/修订/下载 + 静态前端
static/index.html  单页前端
```

## 与 OpenTutor 的差异（有意）

- 免 DB/用户/课程体系：文件 JSON 存储
- 单页修订不自动重选参考页（由用户指定），映射失败走规则回退而非直接报错
- LLM 收敛为单一 OpenAI 兼容客户端；视觉生图通道 v1 关闭（schema 保留）
