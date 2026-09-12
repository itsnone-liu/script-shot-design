# T2V 可变时长工作流诊断与改造计划

日期：2026-09-12 · 状态：工作流副本/烤入待执行

## 已验证事实

- 现有工作流 `2092847765977378817` 的 node 132 是 `PrimitiveFloat`，默认值10，但并非固定常量。
- node 132 连接 node 131 `ComfyMathExpression`，动态秒数转帧公式：
  `max(5, round(a * 24)) + (5 - (max(5, round(a * 24)) % 17)) % 17`
- node 131 的 INT 输出连接 MiniMaxH3ReferenceToVideo node 136 的 `length`。
- 因而 5/10/12/15 秒在结构上都能转为合法17k+5帧数；此前“该卡只支持10秒”结论过强。
- 当前卡不是纯单采样：第一采样后 node 218 `H3LatentUpscaleByJingchen573` 做1.2x latent upscale，再由 node 189 `SamplerCustomAdvanced` 二次采样。
- 820 `_h3lora_taskjson.json` 已记录 `SamplerCustomAdvanced` 的 `torch.OutOfMemoryError`，证明805可由双采样/放大分支显存失败折叠而来。

## 正确分档

1. `t2v_quality`（现有卡）：4–10秒，双采样+1.2x放大，适合已验证短段。
2. `t2v_variable`（新副本）：5–15秒，保留同一prompt/duration入口和动态帧公式，移除/旁路latent upscale+第二采样，直接把第一采样解码输出；优先确保长时长稳定。
3. 不再把工作流档位写入脚本。脚本审批后由packager按镜头复杂度、时长和预算选择profile。

## RunningHub改造步骤

1. 复制现有工作流，不在生产卡上直接试错；
2. 在编辑器中断开 node 156→218→189→191 的二采样视频路径，将第一采样 node 125/156 的视频latent直接送至现有解码/输出链；音频保持第一采样输出；
3. node132保留为唯一秒数入口，UI默认可设8秒但API允许5–15；node131公式不改；
4. 编辑器Run一次短探针使 apiFormat 缓存烤入；记录新workflowId；
5. 串行探针：5秒→12秒→15秒，极短脚本优先，不在探针阶段使用复杂创意；检查任务状态、实际帧数/时长、峰值显存错误和输出污染；
6. 三档均通过后填写821 `T2V_VARIABLE_WORKFLOW`，把adapter的本地未烤入保护解除；任一长档OOM则进一步降低width/height或禁用音频采样，而不是把剧本重新锁死为10秒。

## 当前安全状态

821已新增`t2v_variable` profile目标范围5–15秒，但在新RH副本被实跑验证前，`T2V_VARIABLE_WORKFLOW`保持空字符串。调用该profile会在本地明确报`not baked`，不会静默路由到旧卡或浪费任务额度。
