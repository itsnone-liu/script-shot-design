# 编剧知识库方案：让系统先学会写故事，再写镜头

## 目标

821 的编剧能力不应来自一条“写一个广告脚本”的提示词，而应来自：

```text
案例采集 → 剧本解析 → 结构化标注 → 经验归纳 → 检索增强创作 → 多角色审稿 → 复盘入库
```

知识库帮助系统回答：这个创意适合什么故事结构？人物的目标、阻碍和选择能否在时长内看懂？产品为什么必须出现？每个场景和镜头承担什么叙事功能？

## 一、知识来源分层

### A. 原始案例

保存可追溯的原文或用户提供的截图/文本，不直接把模型总结当作事实来源：优秀广告脚本、分镜脚本、短剧剧本、公开案例拆解、编剧教材和 821 自己的生成结果。每条来源记录 `source_id`、标题、URL、访问日期、版权/使用限制、原文文件路径和采集状态。网页受验证码、登录或版权限制时记录 `blocked`，不能伪造正文。

### B. 结构化案例卡

由模型在原文基础上生成，并保留原文段落引用：`logline`、主题、受众、平台、时长；人物目标、外部阻碍、内部缺陷、关键选择；节拍顺序和状态变化；产品/品牌在因果链中的角色；场景功能、信息揭示顺序、情绪曲线；结尾承诺、记忆点和 CTA；使用的视听手段。

### C. 经验规则

至少 3 个相似案例出现同一模式，才提升为一般规则；单案例只作为案例偏好。规则必须带适用条件、反例、证据案例和置信度。示例：30 秒产品短片应在前 5 秒给出可识别目标，中段出现可见阻碍，最后 5 秒给出由人物选择造成的结果；产品至少改变一次观察、决策或行动。

### D. 失败经验

把 821 自己的失败片段也作为知识：错误类型、原因、修复方式、修复后评分。例如“连续饮用咖啡但没有状态变化”归类为 `product_action_without_story_function`，作为生成时的负面约束。

## 二、案例解析数据结构

每个案例保存为 `knowledge/cases/<source_id>.json`，最小字段如下：

```json
{
  "source_id": "case_001",
  "title": "案例标题",
  "source": {"url": "", "accessed_at": "", "status": "ok"},
  "format": {"type": "advertisement", "duration_sec": 30, "platform": "vertical"},
  "story": {"logline": "", "theme": "", "character_goal": "", "obstacle": "", "turning_choice": "", "result": "", "brand_role": "tool|trigger|proof|companion|symbol"},
  "beats": [{"id": "B1", "time": "0-4", "function": "goal", "visible_action": "", "state_in": "", "state_out": "", "evidence": ""}],
  "scene_functions": [], "visual_motifs": [], "dialogue_strategy": "none|dialogue|voiceover|text",
  "rules_observed": [], "anti_patterns": [], "quality_notes": [], "confidence": 0.0
}
```

`state_in` / `state_out` 是关键字段：没有状态变化的节拍不能被当成故事节拍，只能标记为展示镜头或冗余镜头。

## 三、从案例到可用经验

1. 采集原文；网页无法访问时保留失败记录。
2. 按场景、节拍、动作和台词切块，不按固定字数盲切。
3. 双遍标注：第一遍只标注事实，第二遍才归纳意图和技巧。
4. 跨案例归纳，给每条规则附证据与反例。
5. 生成时按题材、时长、产品角色、冲突类型和平台检索案例。
6. 经过 StoryEditor、AudienceAdvocate、BrandStrategist、AdversarialReviewer 审稿。
7. 成片复盘结果回写案例库。

## 四、优秀编剧生成闸门

- 一句话说清人物、目标、阻碍、选择和结果；
- 只有一个主线，人物和场景服从时长；
- 产品能解释它改变了什么，不是装饰；
- 每个 beat 有 `state_in → visible_event → choice → state_out`；
- 转折由前面埋下的线索或产品特征造成；
- 结局由人物行动造成，不是“喝完/拿到产品就突然成功”；
- 产品展示动作最多两次，每次承担不同叙事功能；
- 每个镜头注明叙事功能，删除后无损则合并或删除；
- 运镜服务于揭示、跟随、强调或转场；
- Logo、字幕、参数后期叠加，不交给视频模型生成。

## 五、受限网页的真实浏览器流程

系统支持用户上传/粘贴，或使用用户明确启动的 Chrome 调试实例读取可见正文；不读取或转换 OAuth/Cookie。当前机器的 Chrome 未开放 CDP 端口，不能安全接管已登录窗口。可由用户启动专用实例：

```powershell
& 'C:\Program Files\Google\Chrome\Application\chrome.exe' `
  --remote-debugging-port=9222 `
  --user-data-dir='D:\qjcNetDiskDownload\deepseek-harness\project\821\.browser-profile'
```

首次由用户完成登录/验证码；采集器只访问页面可见内容，并保存 HTML/截图和采集时间。生产环境不复用日常 Chrome Profile。

## 六、第一阶段

建立 `sources/`、`cases/`、`rules/` 和 manifest；先导入 5–10 个可访问广告/短剧脚本；用 DeepSeek 做结构化标注并保存证据片段；人工确认规则后接入 StoryPlanner；用咖啡广告作为回归题比较知识增强前后脚本。只有通过故事闸门和反方审稿才进入分镜和 RH 生成。

## 七、推荐资源来源

### 1. 公开英文剧本原文：学习故事结构

优先用于电影、短片和电视剧的节拍、场景功能、对白节奏学习：

- IMSDb（Internet Movie Script Database）：大量电影剧本，适合结构化解析；
- SimplyScripts：电影、短片、舞台剧和原创投稿；
- Script Slug：电影剧本、制作稿和行业资料；
- The Daily Script：电影/电视剧剧本归档；
- BBC Writersroom：部分剧本和编剧示例，来源相对正规；
- The Script Lab：剧本示例和编剧方法文章。

这些资源不能直接作为商业成片素材或逐字模仿对象，只用于抽取结构、节拍和写法，并记录版权与来源。

### 2. 广告和品牌案例：学习“产品如何进入故事”

- Ads of the World：广告成片、品牌、创意说明和制作信息；
- Campaign / Adweek：广告行业案例与创意分析；
- Lürzer's Archive：广告创意案例；
- Vimeo Staff Picks、Short of the Week：短片叙事和视觉表达案例；
- StudioBinder：分镜、镜头表、三幕结构和运镜方法；
- No Film School：独立短片、剧本和制作复盘。

广告案例应重点标注：品牌出现时间、产品角色、冲突来源、视觉记忆点和 CTA，而不是只保存广告文案。

### 3. 中文行业资源：学习本土广告表达

- 数英网（DIGITALING）：品牌广告案例、创意说明和传播策略；
- 广告门：广告案例、提案和行业分析；
- 影视工业网：剧本、导演、摄影和制作经验；
- 新片场：短片案例、导演阐述和幕后内容；
- 中国编剧网及公开编剧课程：中文剧本格式、人物和戏剧结构。

中文网站经常有登录、反爬或内容版权限制，应优先保存公开页面的标题、摘要、截图和用户合法提供的文件；不能把受限正文批量抓取作为系统依赖。

### 4. 可用于批量实验的数据集

- Kaggle/GitHub 上的公开 screenplay 数据集；
- Cornell Movie-Dialogs Corpus：对白和人物关系，不等于完整剧本；
- Script-based NLP 数据集：用于对白、场景和人物网络实验。

数据集只用于统计和结构实验，不能默认拥有商业再发布权。对于 821，完整案例数量不需要很大，先做 20–50 个高质量、来源明确的案例，比抓取数千篇低质量文本更有价值。

### 5. 821 自有案例库

最重要的长期来源是自己的生产记录：每个创意方案、被否决的剧本、分镜、RH 生成结果、失败原因和修改前后评分都要回写。这样知识库最终学习的是“哪些故事在本系统的视频工作流中真的可拍、可连续、可验收”。

### 推荐采集顺序

```text
StudioBinder/公开方法论
→ 10 个公开英文短片或电影剧本
→ 10 个广告案例（Ads of the World、数英网等）
→ 821 自己的咖啡广告迭代
→ 中文短剧/广告案例扩展
```
