# Podcast Reader v1.4 项目交付报告

## 目标

打造一个达到成熟开源项目标准的 Codex Skill：用户只提供播客或长视频链接，即可完成公开来源摄取、字幕/转写、多语言处理、说话人区分、时间戳索引、深度拆解、持续问答、画面分析和多格式导出，同时具备清晰文档、错误恢复、安全边界、测试和 CI。

## 完成范围

1. 研究 Podwise、Armory YouTube Analysis、MCP Video Analyzer 和高质量 Skill 编写规范。
2. 完成原型架构、脚本、输出和用户体验审计。
3. 重写主 `SKILL.md`，建立 quick / standard / deep 档位与自然语言意图路由。
4. 实现 Bilibili、YouTube、RSS、网页、直链和本地文件来源链路。
5. 实现字幕优先、音频兜底、说话人/多语言规范和转录质量阶梯。
6. 实现统一 transcript schema、SRT/VTT/JSON/Markdown 转换、长文本分块与中英文检索。
7. 实现播客专用论证、主张、说话人、事实核查、学习、改写和跨节目工作流。
8. 实现视频关键帧、联系表与独立画面证据链。
9. 实现漂亮的中文分析模板、evidence schema 和 Excel 友好 CSV 导出。
10. 实现 bundle 状态、缓存复用、阶段性警告、恢复建议、隐私/版权/提示注入规则。
11. 建立 38 项离线场景、固定夹具、黄金报告、接口契约和跨平台 CI。
12. 增加统一零 Key 入口、无网络环境自检、持久进度与缓存恢复体验。
13. 增加默认不覆盖、强制更新保留备份的跨平台 Skill 安装器。
12. 完成 YouTube、Bilibili、RSS 和 FFmpeg 画面公开冒烟验证。
13. 真实验证 Bilibili HTTP 412 后的公开 API 多分 P 音频兜底，以及超 25 MB 音频的自动切分与全局时间轴恢复。
14. 完成无 API Key 的本地 `faster-whisper` 适配器、隔离自动引导、语言自动检测和跨 Agent 能力阶梯。

## 核心指标

| 指标 | 结果 |
|---|---:|
| 项目文件 | 55 |
| Skill Python CLI | 14 |
| 单层参考文档 | 8 |
| 离线自动测试 | 32 / 32 通过（当前 Python 3.14；核心 v1.1 矩阵已覆盖 3.11/3.12/3.14） |
| GitHub CI 组合 | Windows/Linux × Python 3.11/3.12/3.14 |
| 官方 Skill 快速校验 | 通过 |
| SKILL.md 行数 | 少于 500 |
| 未完成 TODO/FIXME/TBD | 0（验证器检测字符串除外） |
| Markdown 相对链接 | 全部存在 |

## 真实验证结论

- YouTube：TED 公开英文字幕成功进入 `ready_for_analysis`，转录、字幕、索引与 bundle 校验全部通过。
- Bilibili：以 `BV1a5ECzqEVB` 完成真实长视频验证。yt-dlp 遇到平台 412 后，公开 API 成功获取 2 个分 P、12,139.015 秒音频；未使用 Cookie。
- 长音频：218.7 MB 原始音频成功生成 8 个 API 安全 Opus 块，最大约 5.47 MB，并保留跨分 P 的全局时间偏移。
- 无 Key 转写：真实 30 秒样本通过 `uv` 自动安装隔离依赖、下载 tiny 模型并在 CPU int8 上输出 11 个带时间戳片段；语言自动识别为英文，概率约 0.995。
- RSS：NPR Planet Money 公开 Feed 成功解析并显式选择最新节目。
- 视频画面：本地可再现视频成功生成关键帧、manifest 和 contact sheet。

## 交付结构

- `podcast-reader/`：可安装 Skill 本体。
- `README.md` / `README.en.md`：项目介绍与使用指南。
- `docs/`：架构、竞品基准、验收标准和冒烟报告。
- `.github/`：CI、Issue 和 PR 模板。
- `CONTRIBUTING.md` / `SECURITY.md` / `CHANGELOG.md` / `LICENSE`：开源项目治理文件。

## 已知边界

- 平台字幕和媒体可用性会随地区、登录状态、反爬策略和 yt-dlp 版本变化。
- 没有公开字幕时，完整内容分析需要可用的转写能力或用户提供的媒体/字幕。
- 画面 lane 使用代表性采样，不能证明未采样时刻没有某个视觉事件。
- 完整受版权保护 transcript 默认不作为交付物；项目优先分析、导航和短引。

当前版本通过真实 Bilibili 长视频、统一入口和无 Key 本地转写前向测试，正在按 GitHub v1.4.0 发布门继续执行公开链接与持续追问验收。v1.1 的完整产品审计仍保留在 `docs/product-audit-v1.1.md`，当前用户体验证据见 `docs/ux-acceptance.md`，后续修复记录见 `CHANGELOG.md` 与 `docs/smoke-results.md`。
