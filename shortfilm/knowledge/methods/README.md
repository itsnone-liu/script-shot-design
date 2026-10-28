# 方法卡（candidate）v0 — 2026-10-28

四张候选方法卡，来源=LibTV 18集课程审读（用户附件）+ 821 既有知识 + coffee30 v1 复盘。
状态全部是 `candidate`：coffee30 v2 验证只登记使用与结果，不自动升格
（升格规则见 STORY_PIPELINE_UPGRADE.md visual_recipe 沉淀规则）。

## 字段

`id/version/kind/lifecycle/title/problem/intended_effect/applicability[]/exclusions[]/procedure[]/acceptance_tests[]/failure_modes[]/provenance[{source_id,locator}]/relations[]/consumers[]`

`consumers` 是强制项（方案§8.3：每个知识对象必须声明消费点，答不出即砍）。

## 卡与消费点对照

| 卡 | 消费点（代码/流程） |
|---|---|
| method.expression-chain | `performance_detail.emotion+trigger+micro_action+reaction_order`（`shortfilm/prompt_contract.py` 校验+编译进 Performance 行） |
| method.attention-reveal | 增强法执行工具（节拍-可见行为单）；镜头设计字段 composition_logic/focus/camera_plan |
| method.action-three-stage | 增强法执行工具（镜间连续性登记表终止状态列）；subject_action 写作规范 |
| method.keyframe-readiness | `shortfilm/keyframe_gate.py` + `shortfilm/cli/check_seg.py`（代码消费） |

## 既有方法（不重复建卡）

容器≠内部镜头/单运镜仅限内部镜头 → `knowledge/CREATIVE_CINEMATIC_SYSTEM_V2.md` §5；
一拍一情绪/情绪须有动机 → `knowledge/AI_CREATIVE_ROLE_BOUNDARY_V1.md` §5（emotion+trigger 字段已落地）；
资产卡=事实源 → `knowledge/ASSET_STORYBOARD_SCHEMA_V1.md`（合成已实现 ef46b9d）。
