# IndexTTS2 真人干声克隆收官卡

**项目**：821 / couple30《再睡五分钟》
**日期**：2026-09-19
**状态**：收官，真人声线克隆试听通过用户验收（“有点象”）。

## 输入与处理

- 输入视频：`experiments/飞书20260919-203153.mp4`
- 从视频音轨提取女声参考，转为单声道 24 kHz，并清理首尾静音。
- 参考文件：`experiments/orpheus_test_output/indextts2_real_feishu/ref_feishu_w.wav`
- 清理后参考时长约 5.37 秒。
- 云端工作流：RunningHub IndexTTS2，webapp `2093959907870511105`。
  - node 11：情感提示
  - node 4：台词文本
  - node 10：参考音频
- 产物试听页：`http://100.84.28.40:8791/`

## 女方台词结果

| 台词 | 时长 | CER | 结论 |
|---|---:|---:|---|
| L01 醒醒，太阳晒屁股了 | 3.17s | 0.625 | ASR 未通过，但人耳试听保留，必要时单句重掷 |
| L03 起来嘛，说好的那家 brunch，去晚了排队 | 3.67s | 0.316 | ASR 未通过，英文借词增加风险 |
| L05 你五分钟之前也是这么说的 | 2.51s | 0.000 | 通过 |
| L08 你根本就是装的 | 1.87s | 0.000 | 通过 |
| L10 那……现在几点了 | 2.23s | 0.000 | 通过 |

批量平均 CER=0.188，ASR 闸门 3/5；这次 CER 只用于可懂度诊断，最终声线保真以用户人耳验收为准。用户反馈“有点象”，本轮收官，不继续为边界台词消耗任务。

## 工程结论

1. 5 秒级清理后干声即可驱动 IndexTTS2 真人音色克隆；不必强求 10 秒以上才能验证链路。
2. IndexTTS2 音色相似度不能由 CER 证明，必须单独人耳验收；本轮用户已确认“有点象”。
3. 中文台词中的英文借词（如 brunch）会增加 ASR/发音不稳定，应在正式剧本中改为中文或拼音；低 CER 不是唯一验收标准。
4. 情感提示中“闷/含糊/嘟囔”等声学劣化词应配“吐字清楚”约束；否则可懂度下降。
5. L01/L03 的 ASR 失败不否定声线克隆链路，只说明单句内容/提示词需要定向重掷；本轮按用户意见收官。
6. 下一次换声线只需替换参考 wav，复用 `experiments/indextts2_feishu_clone.py` 和同一 webapp；生成后用 `asr_feishu_clone_gate.py` 做诊断。

## 产物

- `experiments/indextts2_feishu_clone.py`
- `experiments/asr_feishu_clone_gate.py`
- `experiments/orpheus_test_output/indextts2_real_feishu/ref_feishu_w.wav`
- `experiments/orpheus_test_output/indextts2_real_feishu/L01.wav`、`L03.wav`、`L05.wav`、`L08.wav`、`L10.wav`
- `experiments/orpheus_test_output/indextts2_real_feishu/asr_results.json`
- `output/creative_v2/couple30_v1/audio/indextts2_real_feishu/`（归档副本）
