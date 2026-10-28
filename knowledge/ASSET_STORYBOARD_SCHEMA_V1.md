# 821 资产卡与分镜 schema V1：从 inline lock 到一等公民资产

来源：2026-09-21 用户批准起草。外部输入 = YoLuster Shorts（釉光影）产品设计挖掘
（820 kb `capability_notes #29`，domain=product-frontier，文档归档 `kb-mining\YoLuster-shorts\`）；
内部整合 = [AI_CREATIVE_ROLE_BOUNDARY_V1](AI_CREATIVE_ROLE_BOUNDARY_V1.md) ·
[IDENTITY_HYBRID_PIPELINE_V1](IDENTITY_HYBRID_PIPELINE_V1.md) ·
[CREATIVE_CINEMATIC_SYSTEM_V2](CREATIVE_CINEMATIC_SYSTEM_V2.md)。
配套 schema：[assets.schema.json](../schema/assets.schema.json) · [shot_extensions.schema.json](../schema/shot_extensions.schema.json)。
示例：[asset_cards_couple30_v1.json](../examples/creative_v2/asset_cards_couple30_v1.json)。

## 0. 一句话

**把 couple30/concert30 里手工维护的 prompt_bible lock 拆成可复用的角色/场景/道具卡，
卡片是唯一事实源，seg 的 lock 文本由卡合成；分镜补齐 YoLuster 六字段的缺项
（出镜人物/关键场景/镜头级对白/首帧预览），并把首帧预览挂上既有的 5-keyframe 审批门。**

## 1. 为什么要拆卡（现状痛点）

现状（couple30 seg JSON）：`prompt_bible.subject_lock / environment_lock / lighting_lock / palette_lock`
是**每 seg 手写的整段文本**。后果：

1. **重复漂移**：同部片多个 seg 各写一份"她穿奶白睡衣"，改一处漏一处。
2. **复用靠复制粘贴**：新片要用同一角色，得回旧 seg 里捞文本，没有反向索引。
3. **审批粒度错**：用户批过的是"这个角色长这样"，但这个批准行为没有落成对象——
   每次合成都重新信任一遍手写文本。
4. YoLuster 的解法（#29）：资产=**锚点**（"资产持续参与→内容持续延展"），
   角色/场景/道具沉淀为**结构化提示词**而非一句描述。

## 2. 三张资产卡（字段表）

### 2.1 角色卡 `type=character`

| 字段 | 内容 | 821 对应物 |
|---|---|---|
| `identity_points[]` | 识别点：脸型/发/肤等不可漂移特征 | subject_lock 里的人物描述句 |
| `wardrobe` | 服饰 lock（跨镜不变项） | subject_lock 服饰从句 |
| `demeanor` | 气质：年龄感/体态/神态基调 | subject_lock 气质从句 |
| `refs.canonical_chain_version` | canonical 身份链版本 | canonical_v6（IDENTITY_HYBRID_PIPELINE §2-3） |
| `refs.reactor_calibration` | ReActor 逐位标定档 | per-index calibration（couple30 管线） |
| `voice_anchor` | TTS 音色/真声克隆 ref + 表演注记 | INDEXTTS2 / couple30 v2.8 直出 take 策略 |
| `approved_performance_range[]` | 用户已批准的表演/情绪范围 | 情绪主张单的执行边界 |
| `continuity_rules[]` | 该角色专属 never/always | never_show 中角色相关项 |
| `used_by[]` | 反向索引：引用处 | （新增：复用证据） |

边界：`approved_performance_range` 只是**记录**用户批过的范围，不是授权 AI 自行扩展——
新情绪/新表演意图仍回人审批（ROLE_BOUNDARY §3 审批门不变）。

### 2.2 场景卡 `type=scene`

| 字段 | 内容 | 821 对应物 |
|---|---|---|
| `spatial_structure` | 空间结构：布局/方位/家具位置关系 | environment_lock 空间从句 |
| `visual_anchors[]` | 视觉锚点：跨镜可指认的固定物 | environment_lock 里的物件罗列 |
| `light_plan` | 光源/方向/色温 | lighting_lock（seg 级恒光假设的源头） |
| `palette` | 色板 | palette_lock |
| `continuity_rules[]` | 场景专属规则（"不引入新人物/新物件"） | never_show 场景相关项 |

### 2.3 道具卡 `type=prop`（《逆流》教训的固化）

| 字段 | 内容 |
|---|---|
| `shape / material / ratio / style_lock` | 形状/材质/比例/风格锁定（YoLuster 原字段） |
| `state_timeline[]` | **状态时间线**：`{state, beat_id, emotion_intent, motivation}` |

`state_timeline` 是本设计对 YoLuster 的增量：道具状态变化=**情绪事件**
（《逆流》复盘：被踩扁的花持续输出感伤、举花微笑输出喜悦，两信号打架）。
规则：**一个状态一个情绪意图；换状态必须写 motivation（谁/为何）；无动机的状态变化标红上报人**。

## 3. 分镜六字段：YoLuster ↔ 821 对照与增量

| YoLuster 字段 | 821 现状 | 动作 |
|---|---|---|
| 画面描述 | `visual_state` ✅ | 不动 |
| 动作提示 | `subject_action` ✅ | 不动 |
| 对白旁白 | 仅 seg 级 `audio_policy` ⚠️ | **新增镜头级 `dialogue`**（speaker=卡 id、line 原文、voice_take_ref；H3 口型稳定法=台词入 prompt 引号+音频 reference） |
| 出镜人物 | 无显式字段 ❌ | **新增 `cast[]`**（卡 id 列表；生成前校验 cast ⊆ seg 合成卡集合，防串场） |
| 关键场景 | 无显式字段 ❌ | **新增 `scene_ref`**（同场同 ref；换 ref=转场，须与 transition_in 一致） |
| 首帧预览 | `end_state`（只有出点）⚠️ | **新增 `first_frame`**（keyframe_id + approval + continuity_from 上一镜 end_state） |

`first_frame` 与既有制度的挂钩：**5-keyframe 用户审批 pay-gate 的帧全集=各镜首帧**
（couple30 管线本就在做，本字段把它变成 schema 强制项：`approval != approved` 不得进视频生成）。

## 4. 组装规则（卡 → prompt_bible 的合成公式）

```
seg.prompt_bible.subject_lock     = Σ(角色卡.subject_lock_text) + 本 seg 附加姿态约束
seg.prompt_bible.environment_lock = 场景卡.environment_lock_text
seg.prompt_bible.lighting_lock    = 场景卡.lighting_lock_text
seg.prompt_bible.palette_lock     = 场景卡.palette_lock_text
seg.prompt_bible.material_lock    = Σ(道具卡.material_lock_text) + 角色卡材质从句
seg.prompt_bible.never_show       = 全局 never ∪ Σ(卡.continuity_rules)
```

- 合成是**纯函数**：同卡+同 seg 附加项 → 同 lock 文本（可 diff、可回归测试）。
- seg 里的 lock 保留为**缓存**：卡是源，lock 是产物；手改 lock 不回写卡=违规，以脚本重合成覆盖。
- `cast`/`scene_ref` 是合成的**输入校验器**：shot 声明了谁，lock 就必须包含谁的卡。

## 5. 迁移示范（couple30_segA → 资产卡）

见 `examples/creative_v2/asset_cards_couple30_v1.json`：从 segA 的 prompt_bible 拆出
`char_woman` / `char_man` / `scene_bedroom` 三卡（couple30 无独立道具，双人床上游戏的
"duvet/pillow"归场景卡锚点）。迁移步骤：

1. 从最成熟的 seg 的 lock 文本拆卡（人审一遍拆分结果）。
2. `used_by` 回填全片 seg/shot。
3. 写合成脚本（input: 卡+seg 附加项 → output: lock），对旧 seg 跑 diff，
   差异=拆卡时的语义损失，逐条修到零 diff。
   **已实现（2026-10-28）**：`shortfilm/assets.py` + `shortfilm/cli/synth_bible.py`
   （本公式纯函数实现；couple30 segA 回归：env/light/palette/subject 零 diff，
   material 同片段集不同序，never_show 剩 1 条文案级差异待卡片复审；
   测试 `tests/test_assets.py`）。refs 内容哈希清单：
   `couple30_refs_manifest_v1.json`（审批门输入）。
4. 此后新 seg 只写"引用+增量"，不写整段 lock。

## 6. 反模式（本设计的）

1. 卡里写**镜头级**信息（景别/角度/动作）——卡是跨镜恒量，镜头变量属于 shot。
2. 用卡的数量当资产库 KPI——`used_by` 为空的卡是死卡，删或并。
3. 拆卡后删原始 lock 文本——provenance 要能追溯到"从哪个 seg 的哪段 lock 拆出、谁批的"。
4. AI 自行扩展 `approved_performance_range`（同 ROLE_BOUNDARY 反模式 5 的变体）。
5. 把 `state_timeline` 当剧情大纲写——它只记道具的**物理状态**与情绪含义，叙事归 beats/story。

## 7. 边界

- 本 V1 只覆盖 character/scene/prop 三类。声音（BGM/环境音床）与"镜头资产"（recurring 机位）
  暂不建卡，等第二次真实需求出现再议。
- 与 820 kb 的关系：本文件是**执行层 schema**；YoLuster 的产品层观察（History 复用观、
  批量任务/失败重试刚需）属 820 `product-frontier` 域，不在本文件范围。
- 情绪裁决权仍 100% 在人：本 schema 所有 `emotion_intent` 字段都是**记录人已批的主张**，
  不是 AI 的创作依据。
