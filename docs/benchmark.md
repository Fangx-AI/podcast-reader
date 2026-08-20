# 同类产品与顶级 Skill 基准

本项目在实现前对同类 Agent Skill、CLI 和 MCP 视频分析项目做了对照。研究重点不是复制功能列表，而是提炼高质量 Skill 的共同结构：链接入口、渐进披露、确定性工具、证据约束、优雅降级、可测试性和持久产物。

## 代表项目

### Podwise CLI / Skill

- 项目：[hardhackerlabs/podwise-cli](https://github.com/hardhackerlabs/podwise-cli)
- 优点：播客搜索、处理、转录、摘要、章节、问答、思维导图、高亮，以及周报、主题研究、辩论和语言学习等丰富工作流。
- 边界：主要依赖 Podwise 服务、CLI 与 API Key；并非以任意公开 Bilibili/视频链接的本地开放摄取为核心。
- 本项目吸收：面向用户任务设计工作流，而不是只暴露底层转录命令。

### Armory YouTube Analysis

- Skill：[youtube-analysis/SKILL.md](https://github.com/Mathews-Tom/armory/blob/main/skills/youtube-analysis/SKILL.md)
- 优点：明确依赖检查、主备字幕路径、quick/standard/deep 档位、视频类型分析模式、报告模板和错误矩阵。
- 边界：中心场景是 YouTube transcript 分析；跨 RSS/Bilibili、任务包持续问答、结构化证据和视觉证据不是主要范围。
- 本项目吸收：分析档位、模板化输出、依赖与错误行为显式化。

### MCP Video Analyzer

- Skill：[video/SKILL.md](https://github.com/guimatheus92/mcp-video-analyzer/blob/main/skills/video/SKILL.md)
- 优点：转录、OCR、关键帧和时间线结合；MCP 优先、CLI 兜底；部分结果与警告设计清楚。
- 边界：更偏通用视频处理工具，不以播客论证、说话人、主张账本、连续研究为主要产品形态。
- 本项目吸收：长视频不能只读音频，以及 partial result 不应被当作失败丢弃。

### OpenAI / Superpowers Skill 编写基准

- 文档：[Anthropic skill best practices](https://github.com/openai/plugins/blob/main/plugins/superpowers/skills/writing-skills/anthropic-best-practices.md)
- 关键标准：渐进披露、`SKILL.md` 控制体积、单层参考资料、具体工作流、确定性脚本、明确依赖、错误处理和至少三类评估。
- 本项目应用：主 Skill 只负责路由；8 个单层参考文档；10 个可独立调用脚本；24 项离线场景；黄金 Markdown、多 Python 版本和在线冒烟验收。

## 能力对照

| 能力 | Podwise | Armory YouTube | MCP Video Analyzer | Podcast Reader |
|---|---:|---:|---:|---:|
| 只贴链接开始 | 是 | 是 | 是 | 是 |
| Bilibili | 非核心 | 否 | 取决于输入 | 是，含公共元数据兜底 |
| YouTube | 是 | 是 | 是 | 是 |
| RSS / Episode Page | 是 | 否 | 否 | 是 |
| 本地音视频/字幕 | 部分 | 部分 | 是 | 是 |
| 多语言与术语表 | 是 | 部分 | 部分 | 是 |
| 说话人与分歧分析 | 部分 | 是 | 部分 | 是 |
| 论证地图与主张账本 | 部分 | 是 | 否 | 是 |
| 时间戳持续问答 | 是 | 单次分析为主 | 部分 | 是，本地持久索引 |
| 视频画面证据 | 否 | 通常否 | 是 | 是，可选关键帧 lane |
| Markdown / JSON / 字幕 / CSV | 部分 | Markdown | 结构化结果 | 全部 |
| 可恢复 bundle/cache | 服务端 | 部分 | 部分结果 | 是 |
| 离线标准库核心 | 否 | 部分 | 否 | 是 |

## 最终定位

Podcast Reader 的差异化不是某一个摘要提示词，而是完整闭环：

```text
多来源公开摄取
→ 原始证据保留
→ 多语言/说话人标准转录
→ 可检索时间戳索引
→ 播客专用深度分析
→ 持续追问与跨节目研究
→ 人类可读和机器可读导出
→ 可测试、可恢复、安全边界明确
```

这使它更接近“长内容研究基础设施”，而不只是“视频总结器”。
