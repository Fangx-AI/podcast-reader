# Podcast Reader v2.0.1

<div align="center">

<img src="podcast-reader/assets/icon-small.svg" width="88" alt="Podcast Reader 图标">

## 🎧 快速看懂长播客，直接问内容，随时找回关键片段

**给一个链接就行。** 没时间听完，就先看重点；有具体问题，就直接问；以后想起某个观点，还能回到它在原片中出现的时间点。

[![Release](https://img.shields.io/github/v/release/Fangx-AI/podcast-reader?style=flat-square&color=2563eb)](https://github.com/Fangx-AI/podcast-reader/releases/latest)
[![CI](https://img.shields.io/github/actions/workflow/status/Fangx-AI/podcast-reader/ci.yml?branch=main&style=flat-square&label=CI)](https://github.com/Fangx-AI/podcast-reader/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/github/license/Fangx-AI/podcast-reader?style=flat-square)](LICENSE)
![API Key](https://img.shields.io/badge/Cloud_API_Key-optional-16a34a?style=flat-square)

[开始使用](#30-秒开始) · [可以怎么问](#你可以直接这样问) · [能得到什么](#你会得到什么) · [中文](README.md) · [English](README.en.md) · [文档中心](docs/README.md)

</div>

> [!TIP]
> 大多数情况下不需要配置云转写 API Key。公开字幕可直接处理；没有字幕时，可以使用宿主 Agent 的转写能力或在本机转写。

---

## 它能帮你做什么

| 当你遇到这种情况 | Podcast Reader 会怎么帮你 | 你省下什么 |
|---|---|---|
| 刚发现一期两三个小时的节目 | 先给出主题、章节、核心观点和关键片段 | 不必从头听完，几分钟判断是否值得深入 |
| 只关心其中一个问题 | 检索整期内容后直接回答，并附对应时间戳 | 不必拖动进度条反复试听 |
| 记得一个观点，却忘了哪期、哪一分钟 | 按关键词或自然语言找回相关段落 | 不必重听整期或翻遍旧笔记 |
| 想听外语播客，但理解成本太高 | 翻译、解释术语，并保留原始时间轴 | 更快理解，同时还能核对原文 |
| 想整理笔记、研究材料或分享内容 | 导出 Markdown、字幕、JSON、CSV 和阅读页面 | 不必手动复制、整理和重新排版 |

它不会要求你先建立一套复杂的知识管理系统。它做的事情很直接：**让原本只能顺序播放的长内容，变得可以快速理解、随时询问和重新找到。**

## 你可以直接这样问

不需要学习命令，也不需要先决定复杂参数。像平时聊天一样说出目的即可。

| 你的目的 | 可以直接复制的说法 |
|---|---|
| 快速了解 | `帮我用 5 分钟读懂这期播客：<链接>` |
| 判断是否值得听 | `这期主要讲什么？最值得听的三个片段在哪里？` |
| 询问具体内容 | `嘉宾如何回答“人生有没有意义”？请结合上下文说明。` |
| 找回以前听过的观点 | `我记得他谈过“个人视角和宇宙视角”，帮我找到原话和时间点。` |
| 梳理分歧 | `主持人和嘉宾在哪些问题上意见不同？每一点附时间戳。` |
| 听懂外语内容 | `翻译成中文，保留重要英文原句、专有名词和时间戳。` |
| 做笔记或分享 | `整理成适合 Notion 的 Markdown，保留章节和来源链接。` |
| 深入研究 | `检查关键主张，区分节目原话、你的分析和外部事实核验。` |

处理完成后，你可以继续追问，不需要重新发送链接或重新转写整期节目。

## 30 秒开始

### 1. 安装一次

~~~bash
git clone https://github.com/Fangx-AI/podcast-reader.git
cd podcast-reader
python podcast-reader/scripts/install_skill.py --json
~~~

更新已有安装时，显式使用 <code>--force</code>；安装器会先保留时间戳备份：

~~~bash
python podcast-reader/scripts/install_skill.py --force --json
~~~

也可以从 [最新 Release](https://github.com/Fangx-AI/podcast-reader/releases/latest) 下载 ZIP，把其中的 <code>podcast-reader/</code> 复制到 Agent 能发现的 Skills 目录。需要安装到自定义目录时使用 <code>--target</code>。

| 客户端 | 常见目录 |
|---|---|
| Codex | <code>~/.codex/skills/podcast-reader/</code> |
| Agent Skills 兼容客户端 | <code>.agents/skills/podcast-reader/</code> |

### 2. 发一个链接

~~~text
用 $podcast-reader 帮我快速了解这期播客：https://...
~~~

这已经足够。Skill 会自动选择公开字幕或可用音频，并使用与你相同的语言回答。你也可以把“快速了解”换成“完整拆解”“回答这个问题”或“帮我找回一个观点”。

### 3. 可选：检查当前机器

~~~bash
python podcast-reader/scripts/doctor.py --json
~~~

Doctor 不访问网络，会明确区分“已经离线就绪”和“首次运行可自动引导”，也会告诉你缺少的是 FFmpeg、yt-dlp、本地转写环境，还是磁盘写入能力。

> [!NOTE]
> 第一次在没有字幕的节目上启用本地转写时，可能需要下载 FFmpeg、隔离依赖或语音模型。Doctor 会明确告诉你当前机器缺少什么，不会要求你把 API Key 粘贴到聊天里。

## 一次处理，以后随时回来问

Podcast Reader 会为每期节目保留带时间戳的本地内容包。它不是一次性摘要：今天可以先快速了解，明天继续追问，几个月后还能搜索曾经听过的观点。

~~~mermaid
flowchart LR
    A[一个链接或本地文件] --> B[读取并整理整期内容]
    B --> C[快速了解重点]
    B --> D[询问具体问题]
    B --> E[找回旧观点]
    B --> F[翻译或导出]
    C --> G[时间戳回到原片]
    D --> G
    E --> G
~~~

再次提问时，Skill 会优先复用已有内容，不会无故重新下载或转写。

## 你会得到什么

| 结果 | 对你有什么用 |
|---|---|
| **几分钟可读的内容概览** | 快速知道主题、结论和这期是否值得继续听 |
| **带时间戳的章节地图** | 直接跳到真正关心的部分，不必盲目拖动进度条 |
| **可以持续追问的节目记忆** | 围绕人物、观点、例子和分歧继续提问 |
| **可搜索的全文阅读器** | 用关键词找回一句话，并返回对应原片位置 |
| **多语言版本** | 翻译内容，同时保留原文、术语和时间轴对应关系 |
| **Markdown 等导出文件** | 保存到 Notion、Obsidian，或继续用于研究与写作 |

回答默认先给结论，再提供足够小的时间范围。节目没有讲过的内容会明确说明，不会为了回答而编造节目观点。

### 它和普通摘要或转录工具有什么不同？

| 能力 | 一次性摘要 | 普通转录工具 | Podcast Reader |
|---|:---:|:---:|:---:|
| 快速了解整期内容 | ✓ | — | ✓ |
| 查看完整文字 | — | ✓ | ✓ |
| 针对节目持续提问 | — | — | ✓ |
| 用自然语言找回旧观点 | — | 依赖手动搜索 | ✓ |
| 回到原片时间点核对 | 少见 | 视产品而定 | ✓ |
| 章节、论证与分歧拆解 | 简单概括 | — | ✓ |
| 多语言翻译并保留时间轴 | 少见 | 视产品而定 | ✓ |
| Markdown / JSON / 字幕等导出 | 少见 | 视产品而定 | ✓ |

## 内部工作方式

~~~mermaid
flowchart LR
    A[链接或本地文件] --> B[解析来源]
    B --> C{存在公开字幕?}
    C -->|是| D[标准化转录]
    C -->|否| E[获取公开或授权音频]
    E --> F[转写与质量评估]
    F --> D
    D --> G[时间戳分块索引]
    G --> H[快速 / 标准 / 深度分析]
    H --> I[持续问答]
    H --> J[Markdown / JSON / 字幕 / CSV]
    B --> K{画面包含关键信息?}
    K -->|是| L[关键帧与画面证据]
    L --> H
~~~

每个阶段都会留下状态和可恢复产物。只有分析、证据、时间戳与阅读器全部通过验证后，bundle 才会标记为 <code>analyzed</code>。

## 三种分析档位

| 档位 | 适合 | 默认交付 |
|---|---|---|
| <code>quick</code> | 判断是否值得听、快速预览 | 节目卡片、短总结、关键时刻、限制 |
| <code>standard</code> | 普通“分析 / 拆解”请求 | 章节、核心观点、主张、分歧、行动建议、证据 |
| <code>deep</code> | 研究、事实核查、跨节目比较 | 论证地图、主张账本、画面证据、核验队列、开放问题 |

## 支持的来源

| 来源 | 处理策略 | 说明 |
|---|---|---|
| YouTube | 公开字幕优先，音频转写兜底 | 保留可跳转时间戳 |
| Bilibili | 字幕优先；412 时使用公开 API 合法降级 | 支持多分 P、Range 恢复与时长校验 |
| RSS / Atom | Podcasting 2.0 transcript 优先 | 可按日期或明确选择节目 |
| 播客节目页 | JSON-LD、官方 transcript、RSS discovery、<code>og:audio</code> | 不依赖固定网站模板 |
| 媒体直链 | 限制大小、原子下载、来源指纹 | 防止静默截断 |
| 本地音视频 | 直接处理 | 不重复复制大型文件 |
| SRT / VTT / ASS / TTML / LRC / JSON3 / JSON / TXT / MD | 标准化后直接分析 | 保留原始稿 |

> [!IMPORTANT]
> Spotify、付费墙、登录内容、私人 Feed、DRM 和地区限制只处理公开可得信息。项目不会绕过访问控制，也不会默认读取浏览器 Cookie。

## 文件与数据结构

<details open>
<summary><strong>核心交付物</strong></summary>

~~~text
episode/
├── bundle.json                   # 状态、来源、文件清单、警告与下一步
├── source.json                   # 稳定来源信息
├── transcript-raw.*              # 原始字幕或生成式转写
├── transcript.json               # 标准化逐段文本
├── transcript.md                 # 可读时间戳全文
├── transcript.srt / .vtt         # 字幕导出
├── chunks.json                   # 持续问答检索索引
├── transcript-quality.json       # 转写质量与抽查建议
├── analysis.md                   # 深度分析报告
├── summary.md                    # 可独立分享的摘要
├── evidence.json                 # 章节、主张、短引、行动和实体
├── reader.html                   # 搜索、键盘操作、时间戳跳转
├── *.csv                         # 可选表格导出
└── frames/                       # 可选视频画面证据
~~~

</details>

分析报告不止包含“摘要 + 金句”，还可以包括章节地图、中心问题、论据与反例、主张账本、说话人分歧、概念解释、行动启示、强弱点评估、未回答问题、外部核验队列和限制说明。

## 为什么回答更可信

- **回答有出处：** 每个关键结论尽量绑定到最小可用时间范围。
- **原话可核对：** 短引文必须能在对应转录片段中逐字找到。
- **事实不混在一起：** 节目原话、Agent 分析、画面观察和外部核验会明确区分。
- **不知道就说明：** 来源不完整、转写质量不足或节目没有回答时，会直接标注限制。

下面这些工程机制负责守住上述体验：

| 风险 | Podcast Reader 的处理 |
|---|---|
| 长音频中途断开 | Range 可恢复下载，核对远端字节数和平台时长 |
| 缓存只完成一半 | 校验来源指纹、参数、块序号和总时长覆盖 |
| 转写出现重复幻觉 | 检测精确重复、token 重复和 CJK 段内模式重复 |
| Agent 编造引文 | 短引必须逐字存在于引用 segment |
| 分析完成但状态假成功 | 严格验证 analysis、evidence、reader 和 bundle |
| 分享泄露本机信息 | 净化绝对路径和敏感 URL 参数 |
| 版权边界不清 | 分享包默认不携带完整逐字稿 |
| 平台内容提示注入 | 页面、字幕、转写和画面一律视为不可信内容 |

## 已验证的真实效果

最新的 98 分钟 Bilibili 前向测试在**无浏览器 Cookie、无云转写 API Key**的环境下完成：

| 完整媒体 | 时间戳片段 | 深度章节 | 证据化主张 | 自动测试 |
|---:|---:|---:|---:|---:|
| 5,899.52 秒 | 202 | 9 | 11 | 58 / 58 |

- 完成公开音频获取、4 块可恢复本地转写、分析、阅读器与安全分享包。
- 自动识别并标记中文 ASR 的段内重复幻觉，没有把异常文本包装成可靠引文。
- Markdown、结构化证据、bundle 与可点击阅读器均通过严格校验。

查看完整测试记录：[公开来源冒烟报告](docs/smoke-results.md) · [项目交付报告](PROJECT-REPORT.md)

## 高级命令

通常不需要手动编排这些脚本；Skill 会根据用户意图自动调用。

<details>
<summary><strong>展开 CLI 示例</strong></summary>

~~~bash
# 一键处理
python podcast-reader/scripts/process_episode.py <url-or-file> --output-root outputs/podcast-reader

# 只准备来源与字幕 / 媒体
python podcast-reader/scripts/prepare_episode.py <url-or-file> --output-root outputs/podcast-reader

# 只测试元数据和字幕，不下载音频
python podcast-reader/scripts/prepare_episode.py <url> --mode subtitles

# 零 Key 本地转写
python podcast-reader/scripts/transcribe_local.py episode/audio-chunks/*.ogg --output-dir episode/chunk-transcripts --bootstrap --model small --language auto

# 建立索引并查询
python podcast-reader/scripts/chunk_transcript.py episode/transcript.json -o episode/chunks.json
python podcast-reader/scripts/search_chunks.py episode/chunks.json "AI Agent 的风险" --top-k 8

# 关键帧、翻译与说话人回填
python podcast-reader/scripts/extract_keyframes.py video.mp4 --output-dir episode/frames
python podcast-reader/scripts/translate_transcript.py episode/transcript.json --target-language zh-CN
python podcast-reader/scripts/apply_diarization.py episode/transcript.json speaker-turns.json

# 验证、阅读与安全分享
python podcast-reader/scripts/finalize_bundle.py episode
python podcast-reader/scripts/validate_bundle.py episode
python podcast-reader/scripts/render_reader.py episode
python podcast-reader/scripts/export_bundle.py episode --profile share
~~~

</details>

## 运行要求

- Python 3.10+
- FFmpeg / ffprobe：媒体处理与关键帧
- yt-dlp：平台公开来源；装有 <code>uv</code> 时可临时运行固定版本
- 无公开字幕时：宿主原生转写，或 <code>uv</code> + 本地 <code>faster-whisper</code>

标准化、索引、检索、RSS/网页解析、验证和 CSV 导出只依赖 Python 标准库。首次本地转写需要联网下载隔离依赖和模型，长音频会消耗相应 CPU/GPU 与磁盘空间。

## 工程质量

- **58 / 58** 项离线单元、契约、安全、恢复与端到端测试。
- **31** 个可独立运行的 Python CLI。
- Windows / Linux × Python 3.11 / 3.12 / 3.14 CI。
- 所有 CLI 的帮助接口、Skill frontmatter、内部链接和发布不变量自动检查。
- 确定性发布 ZIP、SHA-256 sidecar 与 CycloneDX SBOM。
- YouTube、Bilibili、RSS、本地文件与视频关键帧真实前向测试。

~~~bash
python -m unittest discover -s podcast-reader/tests -v
python -m compileall -q podcast-reader/scripts
python podcast-reader/scripts/release_check.py
~~~

## 文档地图

| 想了解什么 | 文档 |
|---|---|
| 从哪里开始 | [文档中心](docs/README.md) |
| 系统如何工作 | [架构说明](docs/architecture.md) |
| 与同类产品相比如何 | [竞品与顶级 Skill 基准](docs/benchmark.md) |
| 什么才算交付完成 | [质量与验收](docs/quality-and-acceptance.md) |
| 真实来源跑得怎么样 | [公开来源冒烟报告](docs/smoke-results.md) |
| 用户体验是否完整 | [验收矩阵](docs/ux-acceptance.md) |
| 当前版本改了什么 | [v2.0.1 发布说明](docs/release-v2.0.1.md) |
| 如何贡献或报告安全问题 | [CONTRIBUTING](CONTRIBUTING.md) · [SECURITY](SECURITY.md) |

## 安全、隐私与版权

- 不保存临时签名媒体 URL，不输出 Cookie、Token 或 API Key。
- 不要求用户把密钥粘贴到聊天中。
- 医疗、法律、金融和安全主张会区分“节目怎么说”与“外部核验”。
- 默认提供分析、导航、短引和格式转换，不无条件传播完整受版权保护文本。

详见 [Security Policy](SECURITY.md)。

## 参与贡献

欢迎新增来源适配器、转录格式、语言测试、分析工作流和真实失败样例。提交前请阅读 [贡献指南](CONTRIBUTING.md)，确保离线测试不访问网络，公开冒烟测试不绕过平台访问控制。

## License

[MIT License](LICENSE) © 2026 Podcast Reader contributors

---

<div align="center">

如果 Podcast Reader 帮你更快听懂一期节目，或找回了那段一直想不起位置的内容，欢迎给项目一个 ⭐

[下载最新版本](https://github.com/Fangx-AI/podcast-reader/releases/latest) · [查看路线与问题](https://github.com/Fangx-AI/podcast-reader/issues) · [回到顶部](#podcast-reader-v201)

</div>
