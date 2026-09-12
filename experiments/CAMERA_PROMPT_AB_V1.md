# MiniMax镜内分镜与运镜提示词 A/B 实验 v1

## 目的
比较“只写发生什么”的模糊提示词与821结构化导演提示词，在15秒产品镜头中的运镜执行、镜内分镜实现和内容卫生。

## 冻结实验
- A：`examples/director_contract/coffee_camera_baseline.txt`
- B：`examples/director_contract/coffee_camera_v1.json` 经确定性编译生成
- 项目：`examples/director_contract/experiment_project.json`
- 两臂原计划15秒；诊断发现该T2V卡时长节点132的已验证范围为1–10秒，15秒会触发平台805，因此冻结内容按比例压缩为10秒、9:16，RunningHub T2V workflow `2092847765977378817`。
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
- 初次真实提交：两臂均返回 `[805] APIKEY_TASK_STATUS_ERROR`。
- 根因：T2V卡只支持1–10秒，但实验误传15秒；不是API权限问题。同一Key查询历史任务正常，改为10秒后BASELINE任务 `2098715125739769858` SUCCESS。
- 已在 `rh_adapter.build_node_info` 加入工作流级时长闸门：T2V≤10秒，I2V≤15秒，超限在投币前本地拒绝。

## 当前结论
805已解决。BASELINE已生成，STRUCTURED正在串行续跑；提示内容不变，仅按工作流能力将节拍时间轴等比例压缩到10秒。
