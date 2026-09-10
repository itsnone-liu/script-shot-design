# 知乎文章：AI 视频开源项目源码级测评

来源：<https://zhuanlan.zhihu.com/p/2080742741798143245>

标题：`69 个 AI 视频开源项目源码级测评：我把它们全部 clone 下来，逐行读了代码`

访问日期：2026-09-11。通过独立 Chrome 实例读取页面正文。文章列举并比较了大量 AI 视频、短剧、剪辑、分镜和 Agent 项目。

## 对 821 最有价值的项目

### 1. drama-skills

仓库：<https://github.com/zenstory-ai/drama-skills>

它是一组面向短剧/漫剧的 Agent Skills，阶段包括：

```text
原著分析 → 故事开发 → 分集剧本 → 资产设定 → 图片提示词 → 分镜 → 视频提示词 → 生产 → 剪辑 → 审查
```

最值得借鉴的是：每个阶段都有独立产物；人物、场景、道具和连续性独立管理；生产前展示数量、参考、参数和输出，用户确认后才执行；供应商适配与项目知识分离。821 不应直接复制其漫剧流程，但可以吸收“故事通过闸门后才进入资产和生产”的原则。

### 2. video-shotcraft

仓库：<https://github.com/Vincentwei1021/video-shotcraft>

它提供产品视频镜头配方、运动预览和 Remotion 模板，强调镜头配方卡、相机运动、节拍同步、声音效果和可继续编辑的工程。

这对 821 的价值主要在“分镜到后期合成”层，而不是替代 MiniMax/RH 生视频。可借鉴其镜头卡字段和运动配方库，将 `Shot` 的运镜字段与可复用运动模板关联。

### 3. FireRed-OpenStoryline

仓库：<https://github.com/FireRedTeam/FireRed-OpenStoryline>

它是自然语言视频编辑 Agent，包含媒体搜索、素材组织、脚本生成、情绪和视觉理解、BGM/旁白/字体推荐、自然语言修改时间线和人机协同编辑。

对 821 的最大启发是“意图 → 时间线 → 可修改工程”。821 可以把它作为后期编辑层参考，不应因此放弃自己的故事闸门和镜头生产链路。

### 4. OpenMontage

仓库：<https://github.com/calesthio/OpenMontage>

它强调从创意、脚本、场景计划、素材检索到 Remotion 合成的完整流程，适合参考素材型视频和后期编辑。但仓库采用 AGPLv3，未来嵌入 821 或服务化前需要评估许可证义务。

### 5. MoneyPrinterTurbo、ShortGPT、NarratoAI

这些项目适合参考主题到文案、素材匹配、字幕配音和快速剪辑，但核心目标是快速生成短视频或解说视频，不足以解决 821 当前最关键的产品故事、人物目标、冲突和镜头因果问题，因此不作为编剧核心依赖。

## 项目取舍

| 项目 | 借鉴层 | 是否直接接入 821 |
|---|---|---|
| drama-skills | 编剧、资产、分镜、生产前确认 | 不直接接入，吸收阶段和文件契约 |
| video-shotcraft | 镜头配方、运镜、Remotion 后期 | 可作为镜头知识和后期模板参考 |
| FireRed-OpenStoryline | 媒体组织、自然语言剪辑、时间线 Agent | 后期阶段再评估 |
| OpenMontage | 素材检索、脚本到合成 | 许可证评估后再考虑 |
| MoneyPrinterTurbo | 一键短视频、字幕、配音 | 只作对照，不作核心方案 |
| ShortGPT/NarratoAI | Shorts/解说自动化 | 与 821 产品级广告目标不完全匹配 |

## 对 821 的具体改进

1. **Production Approval Gate**：故事、资产、分镜、提示词分别确认，未经确认不提交 RH；
2. **Shot Recipe Library**：把成功的运镜、构图、转场和后期合成保存为镜头配方卡；
3. **Editable Timeline Contract**：每次生产都输出可修改的结构化时间线，而不是只输出 MP4。

文章中的大量“一键生成”项目不能替代编剧层。对 821 来说，最值得吸收的是阶段化产物、镜头配方和人机确认机制。
