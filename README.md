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

### 创意审批与导演提示词

短片生产采用“创意先审批，再编译生产”：LLM脚本即使通过结构验证，也必须存在明确的 `user_script_review`（`status=approved`、`script_version`、`reviewed_by`）才能通过项目验证或导出镜头。修改脚本后应重新审批。

镜内导演合同将 Prompt Bible、3–6个连续时间节拍、Camera Plan、首尾帧和稳定尾帧拆成结构化字段，再确定性编译为MiniMax提示词：

```powershell
python -m shortfilm.cli.compile_director_prompt examples/director_contract/coffee_camera_v1.json output/director_prompt.txt
```

合同和运镜lint会拦截：缺少用户审批、时间线间隙、超过15秒、多于一次路径变化、无动机运镜、静止/运动冲突、没有稳定尾帧以及超过7000字符。

### 创意与电影化质量闸门

脚本管线不再只检查因果完整性。概念候选必须显式声明观众预期、预期偏离、互不相同的创意机制、世界规则、视觉母题、三级升级、信息隐瞒/线索/揭示、结尾重释和拒绝的俗套版本。镜头设计必须声明叙事任务、观众信息差、构图逻辑、调度地图、表演微动作、物理光源和并发事件预算；同一瞬间最多安排3个视觉事件。这些字段会继续编译进入 MiniMax 导演提示词，而不是停留在分析文档。详见 [knowledge/CREATIVE_CINEMATIC_SYSTEM_V2.md](knowledge/CREATIVE_CINEMATIC_SYSTEM_V2.md)。

### 每镜头参考图与串行生成

I2V 可通过 JSON 为不同镜头指定独立参考图；相对路径以映射文件所在目录解析，同一图片在一次运行中只上传一次：

```powershell
python -m shortfilm.cli.render_shots examples/ad30/project.json output/ad30 --workflow i2v --reference-map examples/ad30/reference_map.json --dry-run
```

映射可使用单图 `{"S03":"assets/first_frames/S03.png"}`，也可为动作镜头使用独立首尾帧 `{"S04":{"first":"assets/first_frames/S04.png","last":"assets/first_frames/S04_end.png"}}`。相对路径以映射文件所在目录解析；未映射镜头可用 `--reference-image` 指定全局回退图。生产始终逐镜头串行执行。
