# 821 导演知识库：第一版可执行方法论

研究日期：2026-09-07。这里记录的是从成熟影视制作资料归纳出的可执行规则，不是把网页文章原文复制进提示词。

## 一、故事与广告脚本

### 30 秒广告的最小叙事

广告不是小型电视剧。30 秒只保留一条因果链：

```text
用户状态/痛点 → 产品介入 → 可见变化 → 产品证明 → 品牌承诺/行动号召
```

每个镜头必须回答“产品或品牌信息推进了什么”。人物动作只有在展示使用方式、情绪变化或结果证明时才保留。换装、与产品无关的职业行为、第二主角和复杂支线默认删除。

### 三段式压缩

- 开头 0–6 秒：迅速建立场景和需求，产品尽早出现；
- 中段 6–23 秒：展示产品动作、质感和效果，最多一个情绪转折；
- 结尾 23–30 秒：产品英雄镜头、品牌口号、Logo/CTA，文字后期叠加。

`Story Gate` 必须检查：产品出现时间、唯一冲突、结果是否由产品导致、结尾是否可记忆。

## 二、分镜表设计

分镜不是文学脚本的切片，而是拍摄/生成的执行合同。每行至少记录：

```text
shot_id / story_beat / duration / attention_subject
shot_size / angle / composition / start_framing / end_framing
camera_move / movement_intent / movement_speed / stabilization
subject_action / gaze / screen_direction / continuity_in / continuity_out
lighting / product_visibility / audio_policy / acceptance_tests
```

规则：

1. 每个镜头只有一个第一注意力对象；产品广告优先是产品或产品动作；
2. 每 2–3 个镜头至少有一次产品的清晰、可辨识展示；
3. 景别变化要有功能：远景交代空间，中景展示使用，近景证明质感/情绪，特写完成品牌记忆；
4. 相邻镜头记录屏幕方向、视线方向、动作起止状态，避免无动机跳轴；
5. 镜头时长按信息密度分配，动作镜头短，产品质感/品牌收束镜头可稍长；
6. 生成模型不可靠的文字、Logo、精确包装参数全部进入后期层。

## 三、运镜方法

运镜必须有叙事动机，不是提示词装饰：

| 运镜 | 适用目的 | 广告示例 | 风险 |
|---|---|---|---|
| 固定 | 建立秩序、产品收束、字幕承载 | 结尾产品英雄画面 | 过于平 |
| 推进 Dolly in | 揭示、强调、进入专注 | 从桌面推进到咖啡包装 | 主体漂移、过度变焦感 |
| 拉远 Dolly out | 结果揭示、空间关系 | 从产品拉到人物状态 | 叙事焦点丢失 |
| 跟拍 Tracking | 跟随手、人物或产品动作 | 跟随拿杯/饮用 | 方向不一致 |
| 摇摄 Pan/Tilt | 信息发现、空间关联 | 从工作状态摇到咖啡 | 乱摇、无终点 |
| 环绕 Orbit | 产品英雄、状态转折 | 围绕产品慢环绕 | 形体变形 |
| 手持 Handheld | 紧张、真实、纪实感 | 只在需要时使用 | AI 抖动和画面漂移 |

每个运动镜头都要定义：起始构图、结束构图、速度、稳定方式、屏幕方向和下一镜头的动势。复杂运动优先拆成稳定首帧 + 单一运动 + 后期剪辑。

## 四、剪辑与声音

- 先按动作匹配、视线匹配、方向连续和声音桥接组织镜头，再添加装饰性转场；
- 产品广告默认硬切、动作切和声音桥接，少用花哨转场；
- 视频模型生成的对白/旁白不进入交付链路，统一静音，音乐、拟音和旁白后期制作；
- Logo、字幕和产品文字使用后期叠加，保证可读性和品牌一致性。

## 五、来源

以下资料用于交叉归纳镜头表、故事结构、运镜、连续性和剪辑规则：

1. StudioBinder — [Shot List Templates for Any Creative Project](https://www.studiobinder.com/blog/shot-list/)：镜头表字段和按项目类型组织镜头；
2. StudioBinder — [The Best Storyboard Animatic Template](https://www.studiobinder.com/blog/storyboard/)：分镜/预演和镜头执行关系；
3. StudioBinder — [Camera Movements in Film](https://www.studiobinder.com/blog/camera-movements/)：运镜类型、动机和视觉效果；
4. StudioBinder — [Three Act Structure in Film](https://www.studiobinder.com/blog/three-act-structure/)：三段式故事结构；
5. StudioBinder — [The Rule of Thirds in Film](https://www.studiobinder.com/blog/rule-of-thirds/)：主体位置、留白和视线；
6. StudioBinder — [Match Cuts and Creative Transitions](https://www.studiobinder.com/blog/match-cut/)：动作匹配、图形匹配和声音桥接；
7. StudioBinder — [Shot Reverse Shot](https://www.studiobinder.com/blog/shot-reverse-shot/)：视线连续和反应镜头；

这些来源提供通用影视语言，咖啡广告中的具体取舍由 `coffee_ads.json` 的品类卡约束，并通过实际 RH 生成结果回测。

