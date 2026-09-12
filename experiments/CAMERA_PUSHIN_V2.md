# CAMERA_PUSHIN_V2 — 单一运镜配方三次重复

日期：2026-09-12 · 状态：done

## 动机

CAMERA_PROMPT_AB_V1 的 STRUCTURED 臂使用了复合运镜（跟随下降→弧线→拉远→降机位），实际基本未被执行；主体还回归成整颗咖啡豆。本轮验证假设：**单一、直接可观察的运镜指令能显著提高 MiniMax 的运镜服从率**。

## 配方

- 合同：`examples/director_contract/coffee_pushin_v2.json`
- 主运镜：`dolly_in`（沿光轴连续缓慢推近），`path_changes: 0`
- Camera lint：0 findings；编译提示词 3930 字符
- 主体负向锁定：never_show 含 `whole coffee beans`、`large splash crown`、`camera orbit/pullback`
- 时间线：0-2 悬滴 / 2-4 接触 / 4-7 毛细扩散 / 7-9 汇成小液池 / 9-10 减速停稳
- T2V workflow `2092847765977378817`，10秒，3次重复（R1-R3），提示词逐字相同

## 结果

| 臂 | Task | 咖啡粉 | 因果链 | 运镜 | 卫生 |
|---|---|---|---|---|---|
| R1 | 2098725439587831809 | ✓ | 完整 | 同轴推近执行 | 干净 |
| R2 | 2098727826376146946 | ✓ | 基本完整 | 漂移：轻微横移+微变焦 | 干净 |
| R3 | 2098729947788001281 | ✓ | 完整 | 同轴推近执行 | 干净 |

汇总：咖啡粉 3/3；干净单一推近 2/3；因果链 3/3；无文字/UI/方块 3/3。

对照 v1：复合运镜 0/1 执行且出现整豆回归 → 单一运镜 2/3 执行、整豆回归 0/3。

## 结论与规则更新

1. **单一主运镜规则升格**：每个 ≤10 秒 T2V 段的 Camera Plan 只允许一个直接可观察的主运镜（dolly-in / 跟随 / 小弧线 / 拉远之一），path_changes=0。已有离线测试 `test_single_pushin_recipe_has_clean_camera_lint` 固化该配方样本。
2. **主体负向锁定有效**：把观察到的回归模式（整豆、大飞溅皇冠）写进 never_show 后，3/3 未再出现。观察到的失败模式应回流成负向锁定词。
3. **重复方差仍存在**（R2 漂移），正式制作对镜头关键段预算 best-of-N 重抽。
4. dolly_in 词汇表扩充（push-in / move straight forward 等），CAM02 实例化检查保持通过。

## 产物

- 视频：`output/camera_pushin_v2/render/shots/PUSHIN_R{1,2,3}_00_vertical.mp4`
- 接触表：`output/camera_pushin_v2/qa/PUSHIN_R{1,2,3}_contact.jpg`
- 复盘：`output/camera_pushin_v2/experiment_review.json`
- 运行器：`experiments/run_pushin_repeats.py`（幂等，可续跑）
- 页面：http://100.84.28.40:8836/
