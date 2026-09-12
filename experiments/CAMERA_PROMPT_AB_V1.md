# MiniMax镜内分镜与运镜提示词 A/B 实验 v1

## 目的
比较“只写发生什么”的模糊提示词与821结构化导演提示词，在15秒产品镜头中的运镜执行、镜内分镜实现和内容卫生。

## 冻结实验
- A：`examples/director_contract/coffee_camera_baseline.txt`
- B：`examples/director_contract/coffee_camera_v1.json` 经确定性编译生成
- 项目：`examples/director_contract/experiment_project.json`
- 两臂均为15秒、9:16、RunningHub T2V workflow `2092847765977378817`。
- B包含 Prompt Bible、5个连续时间节拍、单主运镜路径、焦点转移、首尾帧和2秒稳定尾帧。

## 评分（每项0–2）
### 运镜（0–8）
1. 指定主运镜是否发生；2. 是否保持单一主路径；3. 是否平滑无跳变；4. 首尾景别是否实现。

### 镜内分镜（0–8）
1. 5个节拍覆盖率；2. 因果顺序；3. 时间窗准确性；4. 尾帧稳定保持。

### 卫生硬失败
人物、文字/Logo、UI/水印、方块/几何占位、物体替换、动漫/塑料CG风。

## 已完成
- 离线contract验证：通过。
- camera lint：通过（另有“运动族过多”warning，保留作实验观察点）。
- 项目验证：`VALID (2 shots, 30.0s)`。
- T2V dry-run：通过；两臂节点均只有138(prompt)与132(duration)，无图像节点污染。
- 真实提交：两臂均在生成前返回 `[805] APIKEY_TASK_STATUS_ERROR`。

## 当前结论
真实实验未产生视频，不能比较创意效果。因两臂同一基础设施错误，冻结提示词不应修改；RunningHub API凭证/权限恢复后从该项目原样续跑，避免事后改实验条件。
