# Podcast Reader v2.0.1

<div align="center">

## 🎧 把数小时播客与长视频，变成可检索、可追问、可核验的长期知识资产

只需一个链接。自动完成来源解析、字幕优先获取、零 Key 本地转写、章节拆解、证据索引、持续问答与多格式导出。

[![Release](https://img.shields.io/github/v/release/Fangx-AI/podcast-reader?style=flat-square&color=2563eb)](https://github.com/Fangx-AI/podcast-reader/releases/latest)
[![CI](https://img.shields.io/github/actions/workflow/status/Fangx-AI/podcast-reader/ci.yml?branch=main&style=flat-square&label=CI)](https://github.com/Fangx-AI/podcast-reader/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/github/license/Fangx-AI/podcast-reader?style=flat-square)](LICENSE)
![API Key](https://img.shields.io/badge/Cloud_API_Key-optional-16a34a?style=flat-square)

[中文](README.md) · [English](README.en.md) · [最新版本](https://github.com/Fangx-AI/podcast-reader/releases/latest) · [文档中心](docs/README.md) · [问题反馈](https://github.com/Fangx-AI/podcast-reader/issues)

</div>

> [!NOTE]
> Podcast Reader 不是“再生成一篇摘要”。它为每期节目建立可复用的文本记忆、时间戳证据和结构化研究档案，让你之后可以继续提问、比较、翻译和导出，而不必重复下载或转写。

---

## 一眼看懂

| 你提供 | Podcast Reader 自动完成 | 你最终得到 |
|---|---|---|
| Bilibili / YouTube 链接 | 解析来源、寻找公开字幕、必要时获取音频 | 可搜索的完整转录 |
| RSS / 播客节目页 | 精确选择节目、发现 transcript 或 enclosure | 章节与时间线 |
| 本地音视频 / 字幕 | 本地转写、格式标准化、质量评估 | 主张、短引与证据 |
| 一个自然语言问题 | 检索相关片段、回到原始时间戳 | 有出处的回答 |
| 导出要求 | 隐私净化、版权友好的内容裁剪 | Markdown / JSON / SRT / VTT / CSV / HTML |

### 它和普通转录工具有什么不同？

| 能力 | 普通转录工具 | Podcast Reader |
|---|:---:|:---:|
| 获取文字 | ✓ | ✓ |
| 长内容断点恢复 | 视产品而定 | ✓ |
| 章节、论证与分歧拆解 | — | ✓ |
| 主张与原文时间戳绑定 | — | ✓ |
| 处理一次，持续追问 | — | ✓ |
| 视频画面证据 | — | ✓ |
| 多语言翻译且保留 segment 映射 | — | ✓ |
| 隐私安全分享包 | — | ✓ |
| 不绑定云厂商 | — | ✓ |

## 已验证的真实效果

最新的 98 分钟 Bilibili 前向测试在**无浏览器 Cookie、无云转写 API Key**的环境下完成：

| 完整媒体 | 时间戳片段 | 深度章节 | 证据化主张 | 自动测试 |
|---:|---:|---:|---:|---:|
| 5,899.52 秒 | 202 | 9 | 11 | 58 / 58 |

- 完成公开音频获取、4 块可恢复本地转写、分析、阅读器与安全分享包。
- 自动识别并标记中文 ASR 的段内重复幻觉，没有把异常文本包装成可靠引文。
- Markdown、结构化证据、bundle 与可点击阅读器均通过严格校验。

查看完整测试记录：[公开来源冒烟报告](docs/smoke-results.md) · [项目交付报告](PROJECT-REPORT.md)

---

<a id="quick-start"></a>

## 30 秒开始

### 1. 获取并安装

~~~bash
git clone https://github.com/Fangx-AI/podcast-reader.git
cd podcast-reader
python podcast-reader/scripts/install_skill.py --json
~~~

更新已有安装时，显式使用 <code>--force</code>；安装器会先保留时间戳备份：

~~~bash
python podcast-reader/scripts/install_skill.py --force --json
~~~

也可以从 [最新 Release](https://github.com/Fangx-AI/podcast-reader/releases/latest) 下载 ZIP，把其中的 <code>podcast-reader/</code> 复制到 Agent 能发现的 Skills 目录。

| 客户端 | 常见目录 |
|---|---|
| Codex | <code>~/.codex/skills/podcast-reader/</code> |
| Agent Skills 兼容客户端 | <code>.agents/skills/podcast-reader/</code> |

### 2. 直接对 Agent 说

~~~text
用 $podcast-reader 完整分析这个链接：https://...
~~~

这已经足够。默认 <code>standard</code> 模式会自动选择合理流程，不会先让用户填写一长串技术参数。

### 3. 可选：检查当前机器

~~~bash
python podcast-reader/scripts/doctor.py --json
~~~

Doctor 不访问网络，会明确区分“已经离线就绪”和“首次运行可自动引导”，也会告诉你缺少的是 FFmpeg、yt-dlp、本地转写环境，还是磁盘写入能力。

> [!TIP]
> 核心流程不要求云 API Key。存在公开字幕时直接处理；没有字幕时，优先使用宿主 Agent 的原生能力，否则可以通过 <code>uv</code> 引导隔离的本地 <code>faster-whisper</code>。

## 你可以这样用

~~~text
把这期 B 站访谈完整拆解，重点看嘉宾对 AI Agent 的判断。

只根据节目回答：主持人和嘉宾在哪里有分歧？每一点给时间戳。

翻译成中文，保留重要英文原句、专有名词和原始时间戳。

导出一份适合 Notion 的 Markdown，再把所有主张导出为 CSV。

比较这三期播客对“长期记忆”的定义，区分共识、冲突和未回答问题。

抽取视频里的图表和幻灯片，把画面证据与口头论述对应起来。
~~~

处理过的节目会复用本地 bundle。后续追问检索 <code>chunks.json</code> 和 <code>evidence.json</code>，不会重新下载整期内容。

## 工作方式

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

## 你会得到什么

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

## 可靠性设计

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

如果 Podcast Reader 帮你真正读完了一期长内容，欢迎给项目一个 ⭐

[下载最新版本](https://github.com/Fangx-AI/podcast-reader/releases/latest) · [查看路线与问题](https://github.com/Fangx-AI/podcast-reader/issues) · [回到顶部](#podcast-reader-v201)

</div>
