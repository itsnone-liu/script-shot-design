# 咖啡广告 V2：3 × 10 秒段内分镜实验

本版不修补第一版的 10 个独立碎镜头。MiniMax 每次生成一个 10 秒连续叙事段，每段内部含 3–4 个有明确时间轴、动作接续和摄影机指令的镜头，最终只拼接三段。

## 三段接口状态

- `SEG01` 末帧：人物仍坐在工位，已看向右侧咖啡杯，手将要伸出。
- `SEG02` 首帧：从看杯状态开始伸手；末帧：人物在窗边持杯向左转身看回工位。
- `SEG03` 首帧：持杯向左返回；末帧：咖啡杯英雄画面稳定至少 0.8 秒。

精确倒计时、设计稿文字、提交成功提示、Logo 和广告语只在后期合成，不要求视频模型生成。

## 运行前检查

```powershell
python -m shortfilm.cli.validate_project examples/ad30_v2/project.json
python -m shortfilm.cli.render_shots examples/ad30_v2/project.json output/ad30_coffee_v2 --workflow i2v --reference-map examples/ad30_v2/reference_map.json --dry-run
```

首尾参考帧尚未通过人工/自动闸门前，不提交正式生成任务。
