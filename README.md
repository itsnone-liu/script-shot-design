# 821 成片短视频制作系统

> 注意：821 原本已经包含一个可运行的教案/课件（PPTX）生成模块。本方案不删除或重写该模块，而是在同一项目中新增“短片制作”能力线；两者共享项目状态、素材资产和 820 工作流知识库。

821 不是单个视频生成工作流，而是一个从创意到成片的短视频制作系统：

```text
创意
  ↓
故事/脚本
  ↓
视觉开发与角色设定
  ↓
分镜表
  ↓
镜头提示词与生成任务
  ↓
素材筛选/连续性检查
  ↓
剪辑、配音、音乐、字幕
  ↓
成片质检与交付
```

项目复用 820 的工作流知识库和 RunningHub/ComfyUI 研究，但上层以“影片项目、镜头和资产”为核心对象。

详细设计见 [PLAN.md](PLAN.md)。

当前两条能力线：

- `courseware`：教案、课件文字和可编辑 PPTX（已有能力，保持兼容）。
- `shortfilm`：创意到成片的故事、分镜、镜头生成、剪辑和质量检查（本方案）。

## 已有课件能力（保持兼容）

原有 `app/` 服务仍负责：教案/课件文字解析、PPT 模板识别、风格卡生成、槽位映射、单页修订和可编辑 PPTX 下载。模板识别依赖本地 `PPT-Template-Lab`（默认 `8127`），821 API 默认运行在 `8840`。短视频模块不得改变这些接口。

## 运行约定

```powershell
pip install -r requirements.txt
$env:PYTHONPATH=''
python -m uvicorn app.main:app --port 8840
```

短视频模块的第一版建议作为独立 CLI/服务（例如 `shortfilm/`），完成稳定后再挂到现有前端；这样不会把尚未稳定的镜头生成流程混入课件生产链路。

### 每镜头参考图与串行生成

I2V 可通过 JSON 为不同镜头指定独立参考图；相对路径以映射文件所在目录解析，同一图片在一次运行中只上传一次：

```powershell
python -m shortfilm.cli.render_shots examples/ad30/project.json output/ad30 --workflow i2v --reference-map examples/ad30/reference_map.json --dry-run
```

映射可使用单图 `{"S03":"assets/first_frames/S03.png"}`，也可为动作镜头使用独立首尾帧 `{"S04":{"first":"assets/first_frames/S04.png","last":"assets/first_frames/S04_end.png"}}`。相对路径以映射文件所在目录解析；未映射镜头可用 `--reference-image` 指定全局回退图。生产始终逐镜头串行执行。
