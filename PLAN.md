# PLAN —— 项目 821：课件生成独立服务（从 OpenTutor 抽取）

## 0. 定位

把 OpenTutor 中"教案/课件文字 + 上传 PPT 模板 → 可编辑 PPTX"的模块抽成独立项目：

- **输入**：教案内容（仍需 AI 生成课件文字）**或** 课件文字内容（直接可用）
- **模板**：用户上传 .pptx；识别布局/风格/色彩/字体
- **输出**：套用模板参考页的可编辑 PPTX + 网页预览 + 单页修订
- **形态**：独立 FastAPI 服务 + 单页前端；模板识别复用 PPT-Template-Lab（HTTP :8127）
- **范围**：只完成代码，本地可跑，不上线

## 1. 从 OpenTutor 抽取的对应关系

| 821 模块 | OpenTutor 来源 | 调整 |
|---|---|---|
| `app/lab_client.py` | `services/ppt_template_lab_client.py` | 同构改同步 httpx；配置进 `.env` |
| `app/mapper.py` | `services/native_presentation_bridge.py` | choose_reference_slide/映射提示词/校验逐条保留；单页修订不再自动重选参考页，改由用户指定 |
| `app/deckgen.py` | `routers/teacher.py` `_parse_deck_json`/`_deck_from_markdown` | 逐条移植（容错链：剥代码栏→正则捞 JSON→wrapper/pages 兼容→Markdown 分页回退）；新增教案→课件 JSON 生成提示词 |
| `app/stylecard.py` | 无（新增） | OOXML theme + run 级字体/字号/颜色统计 + LLM 综合成"风格卡" |
| `app/llm.py` | `services/llm`（多 provider 路由） | 单一 OpenAI 兼容客户端（默认 dashscope compatible-mode / qwen-plus） |
| `app/store.py` | DB `GeneratedAsset` 体系 | 免 DB，文件 JSON（`data/projects/<id>/project.json`） |
| `static/index.html` | `routers/ui.py` 内嵌 UI | 重写为三步式单页（输入→模板分析→课件生成/修订/下载） |

## 2. 数据流

```
教案 Markdown ──LLM──> deck JSON（语义页：type/title/bullets/…）
课件文字    ──解析──> deck JSON（JSON 直读 / Markdown 分页回退）
                              │
用户 .pptx ──lab import──> slide catalog（page_type/slots/geometry/SVG 预览）
          └─python-pptx──> theme 字体+色板 + run 级统计 ──LLM──> 风格卡
                              │
deck × catalog ──choose_reference_slide + LLM 槽位映射──> lab DeckCreate
                              │
lab create_deck（OOXML 原生填充 + fit-text + PNG 预览）
                              │
前端逐页预览 ──单页 instruction──> LLM 重排槽位 → lab revise（新 revision）
                              │
GET /download → PPTX
```

## 3. 里程碑

| # | 内容 | 状态 |
|---|---|---|
| P1 | 项目骨架 + PLAN/README/依赖 | ✅ |
| P2 | lab_client / llm / stylecard | ✅ |
| P3 | deckgen（教案→课件文字 + 容错解析） | ✅ |
| P4 | mapper（参考页选择/槽位映射/单页修订） | ✅ |
| P5 | FastAPI 服务 + store | ✅ |
| P6 | 前端单页 | ✅ |
| P7 | 本地端到端验证（真实模板 + 教案文字，含单页修订） | ✅ |
| P8 | git + 文档 | ✅ |

## 4. 关键决策

1. **lab 以 HTTP 依赖，不复制**：lab（含 112MB vendor/node 运行时）已是独立仓库，821 只持客户端；启动顺序 = 先 lab 后 821，`/api/health` 显式上报 lab 状态。
2. **同步端点**：lab 导入/生成是分钟级 CLI 子进程，FastAPI `def` 端点走线程池即可，不必 async 化。
3. **风格卡三源合一**：布局=lab classification；色彩/字体=OOXML theme+run 统计（确定性）；风格描述=LLM 对前两者的综合（不虚构）。
4. **映射不猜内容**：沿用 lab 单页修订契约——LLM 只做槽位替换，slot_id/source_slide 必须来自给定清单，服务端二次校验丢弃伪造。
5. **视觉素材 v1 关闭**：schema 保留 visual 字段，lab 图片替换 API 已在客户端就绪，但生图通道（wan）不在 v1 打开。
