# 资产覆盖矩阵 ASSET COVERAGE MATRIX v1 — 2026-10-28

回答"人物各种镜头照片、场景各种照片的体系有没有"：**此前只有身份链（canonical_v6 = 身份锚，不是镜头覆盖库）与文字锁。本文定义覆盖矩阵；关键帧生产同时长出照片库（关键帧=资产）。**

## 1. 现状盘点（诚实）

| 资产 | 已有 | 缺 |
|---|---|---|
| 人物身份 | couple30 canonical_v6 参考链（woman/man，带姿态相似度分；woman "down"姿态 CHECK 0.747） | 多景别×多角度的正脸/侧脸/手部照片库 |
| 场景 | scene_bedroom 卡：环境/光/调色板文字锁 | 各机位（床头柜位/床边位/门口位/窗口位）实拍或生成图 |
| 道具 | 3张道具卡（phone/cup/note）：形状/材质/状态时间线文字 | 各状态实物图（满杯/第一口后/便签在杯沿下/手中） |

## 2. 覆盖矩阵（关键帧生产按此出图，出图即入库）

### 人物（每个角色）

| 维度 | 取值 | 《未发送》需求 |
|---|---|---|
| 景别 | ECU/CU/MCU/M/ML | woman: ECU(手) CU(N2/N7/N8) MCU(N3/N6)；man: M(N1背影) |
| 角度 | eye_level / high_angle / low_angle / dutch / overhead | woman: eye_level×4 + high_angle(N3)；man: eye_level |
| 机位关系 | objective / over_the_shoulder / pov / mirror_reflection | OTS(N4/N6) + objective |
| 姿态 | 躺/半坐/坐直 | woman: 躺(N2)→半坐(N3-N9)；**低头姿态(CHECK风险)：N5/N6/N7/N9 四镜加严** |

### 场景

| 机位 | 内容 | 光态 |
|---|---|---|
| 床头柜位 | 杯+便签+床头柜面 | 晨光右上（唯一光源，全片恒定） |
| 床边位 | 床+空床位+门口方向 | 同上 |
| 特写工作位 | 手与物交互平面 | 同上 |
| 产品位 | 杯+便签无人物 | 同上+蒸汽金边 |

### 道具状态（每状态一图，直接用 prop 卡 state_timeline）

phone×3状态、cup×3状态、note×3状态（=道具卡状态时间线，关键帧覆盖时勾选）。

## 3. 沉淀规则（关键帧=资产）

1. 每张已批关键帧自动成为资产库成员：标注 `{角色/场景/道具} × 景别 × 角度 × 机位关系 × 光态`，进 keyframes registry 的 scope 字段。
2. 资产库目录 = `output/creative_v2/<piece>/keyframes/` + registry 索引；跨片复用时 reference manifest 记 sha256（同 pay-gate 哈希）。
3. 覆盖检查：新片开拍前对照矩阵找空格，只补缺口不重造；couple30→coffee30 v2 复用的正是这套（卡不动，图按需补）。
4. 空格填充优先级：会出镜的组合 > 情绪重拍 > 备用角度。

## 4. 消费点

- 关键帧生产清单（13张 = 10首帧 + 3容器尾帧，每张标矩阵坐标）
- 身份链QA（低头风险镜用 woman 多角度库比对，不只对 canonical 单图）
- 后续片种的资产预检（A8：无消费者的资产不生成）
