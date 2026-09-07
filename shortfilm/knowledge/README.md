# 821 短片制作知识库

知识库不是提示词收藏，而是把“目标—镜头设计—工作流—失败模式—验收标准”绑定起来。

每张卡至少包含：

- `scenario`：适用的广告/短剧场景；
- `attention_priority`：观众此刻应该看什么；
- `visual_rules`：风格和构图限制；
- `shot_grammar`：推荐景别、运镜和剪辑节奏；
- `prompt_constraints`：应写入提示词的正向/负向约束；
- `audio_policy`：对白、旁白、环境声和后期处理策略；
- `failure_modes`：常见失败与修正方式；
- `acceptance_tests`：镜头是否可用的检查项。

第一批卡片针对 30 秒咖啡广告，后续再扩展到美妆、课程、建筑和短剧。

## 编剧知识库

- `SCREENWRITING_KNOWLEDGE_PLAN.md`：剧本案例采集、结构化解析、经验归纳和编剧闸门；
- `script_case.schema.json`：剧本案例卡的数据格式；
- `SCREENWRITER_SYSTEM.md`：从创意到故事、脚本和分镜的流程。

剧本学习必须保留原始来源和证据片段。模型的归纳不能替代原文；网页被验证码拦截时只记录 `blocked`，不把猜测写入知识库。
