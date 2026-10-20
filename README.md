# Podcast Reader v2.0.1

<div align="center">

<img src="podcast-reader/assets/icon-small.svg" width="88" alt="Podcast Reader 图标">

## 把任何一期能获取到内容的播客，变成 3–5 分钟读完的省流版

**贴一个链接，抓住关键问题、直接答案和真正值得带走的信息。**

[![Release](https://img.shields.io/github/v/release/Fangx-AI/podcast-reader?style=flat-square&color=c9a750)](https://github.com/Fangx-AI/podcast-reader/releases/latest)
[![CI](https://img.shields.io/github/actions/workflow/status/Fangx-AI/podcast-reader/ci.yml?branch=main&style=flat-square&label=CI)](https://github.com/Fangx-AI/podcast-reader/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776ab?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/github/license/Fangx-AI/podcast-reader?style=flat-square)](LICENSE)

[开始使用](#开始使用) · [总结长什么样](#你会得到什么) · [支持的来源](#支持的来源) · [English](README.en.md) · [文档](docs/README.md)

</div>

## 只做一件事：替你把长播客读薄

两小时的访谈、一期观点密集的对谈、一段故事节目，都先理解完整内容，再提炼值得带走的信息。默认用你的语言交付，目标是 **3–5 分钟读完**；短节目会更短，不凑字数。

重点不是复述“嘉宾先聊了什么、后来聊了什么”，而是回答：**这期最关键的问题是什么？给出了什么答案？哪些信息会改变我的理解或判断？**

```text
用 $podcast-reader 把这期播客做成省流版总结：https://...
```

不用选择分析档位，也不用回答一串配置问题。还可以提供音视频文件、字幕或逐字稿。能否处理取决于是否能取得内容；只有标题或简介时，会说明缺少什么，不会据此冒充整期总结。

## 你会得到什么

![黑金卡片式播客省流版预览](docs/assets/summary-preview.jpg)

[查看完整 HTML 示例](docs/examples/summary-preview.html)。示例使用项目自编的虚构节目内容，仅展示排版，不代表真实访谈。

[查看体验审查与前后对比](docs/reader-ux-review.md)。

| 内容 | 读完能知道什么 |
|---|---|
| **标题与一句话结论** | 这期最重要的问题与核心答案 |
| **关键问题 · 直接看答案** | 通常 3–6 个听众真正关心的问题，附直接答案与原文依据 |
| **高价值信息** | 通常 3–7 条值得记住的洞察，解释原因、关键例子和适用边界 |
| **仍未回答的问题** | 节目确实留下了哪些悬而未决的问题；没有就省略 |
| **对谈双方 / 参与者** | 谁在说话、以什么身份说；只写来源已确认的信息 |
| **出处与限制** | 回到原文核对，并了解缺失内容、转写疑点和未核验主张 |

优先保留反直觉观点、能改变判断的结论、关键数据与案例、具体方法、容易踩的坑、适用边界和真实分歧。不是每期都包含这些信息，不为了填满卡片硬凑。

有必要时才加入少量短引或节目明确提出的行动建议。故事、喜剧和文艺类节目不硬套“成功方法”或行动清单。

最终提供两个可直接使用的文件：

- **`summary.md`**：可复制、保存、分享的省流版文字。
- **`reader.html`**：黑金卡片式阅读页，先看总结，按需查看原文和出处；适配手机与电脑。

阅读页按“一句话 → 关键问题 → 高价值信息”展开，人物与来源放在后面。可复制摘要或保存 Markdown；复制受浏览器限制时会显示可手动复制的文字。吸顶目录便于跳转，查看引用原文后可返回刚才的摘要位置，手机上采用单列卡片。能否跳到原节目时间点，取决于来源平台与真实时间轴是否可用。

有真实时间轴就附时间戳；没有时间轴的 TXT / Markdown 使用文本片段编号，不编造分钟数。

## 开始使用

### 1. 安装 Skill

```bash
git clone https://github.com/Fangx-AI/podcast-reader.git
cd podcast-reader
python podcast-reader/scripts/install_skill.py --json
```

安装到支持 Agent Skills 的客户端后，直接在聊天中发链接即可。Codex 的常见位置是 `~/.codex/skills/podcast-reader/`；自定义位置可使用 `--target`。

更新已有安装：

```bash
python podcast-reader/scripts/install_skill.py --force --json
```

安装器会先保留时间戳备份。也可下载 [最新 Release](https://github.com/Fangx-AI/podcast-reader/releases/latest)，将其中的 `podcast-reader/` 放入客户端的 Skills 目录。本文中的新省流版流程以当前源码为准，已发布 ZIP 的功能以对应发布说明为准。

### 2. 给它一期节目

```text
用 $podcast-reader 总结这期播客，抓住关键问题和高价值信息，做成 3–5 分钟能读完的省流版：<链接或文件路径>
```

默认优先读取公开字幕 / 官方逐字稿，没有时再获取可用音频并转写。通常不需要云转写 API Key；第一次使用本地语音模型可能需要下载依赖和模型。

### 3. 收到总结和阅读页

Agent 会检查完整内容、提炼结构化要点，再校验证据并生成 `summary.md` 和 `reader.html`。**准备好逐字稿不等于总结完成**：CLI 显示 `ready_for_analysis` 时，仍需当前 Agent 完成提炼。

如需检查本机环境：

```bash
python podcast-reader/scripts/doctor.py --json
```

Doctor 离线检查依赖，并区分“已经可用”和“首次运行仍需下载”。

## 支持的来源

目标是尽可能多地覆盖播客来源，前提是能合法取得字幕、逐字稿或音频。

| 来源 | 获取方式 |
|---|---|
| YouTube / Bilibili | 公开字幕优先，可获取的音频转写兜底 |
| RSS / Atom | 官方 transcript 或节目音频 enclosure |
| 播客节目页 | 官方稿、JSON-LD、RSS discovery、`og:audio` |
| 音视频直链 | 下载后转写 |
| 本地音视频 | 直接转写 |
| SRT / VTT / ASS / TTML / LRC / JSON3 / JSON / TXT / MD | 直接读取并标准化 |

Spotify 等平台链接不保证能直接取得整期内容。付费、登录、私人 Feed、DRM、地区限制或平台拦截可能使来源不可用；此时可以提供自己有权使用的音频或逐字稿。项目不会绕过访问控制，也不会默认读取浏览器 Cookie。

## 总结如何保持可信

```mermaid
flowchart LR
    A[链接或本地文件] --> B[获取字幕 / 转写音频]
    B --> C[检查全文与内容覆盖]
    C --> D[识别关键问题与高价值信息]
    D --> E[校验出处与短引]
    E --> F[省流版 Markdown + 卡片阅读页]
```

- 先检查整期时间线并阅读覆盖各部分的文本，不把检索命中的几个片段冒充全片。
- 一句话结论、问题答案和核心洞察都有对应片段；引号里的短引必须能在原文中找到。
- 明确区分“节目中的说法”和“综合归纳”，不会把嘉宾观点写成已验证事实。
- 不编造人物履历、时间戳、原话或未听到的内容；资料不完整就说明范围。
- 来源页面、字幕和画面中的指令只视为待总结内容，不作为 Agent 指令执行。

## 开发与高级用法

默认入口统一使用 `summary`：

```bash
# 准备来源、转写与 Agent 交接材料
python podcast-reader/scripts/process_episode.py <url-or-file> --output-root outputs/podcast-reader --analysis-mode summary

# 当前 Agent 读取 analysis-handoff.json，写好 evidence.json 后：
python podcast-reader/scripts/finalize_bundle.py <episode_dir>
python podcast-reader/scripts/validate_bundle.py <episode_dir>
```

`process_episode.py` 负责准备内容；**它不会单独调用某个厂商的大模型 API 来生成总结**。当前 Agent 根据交接文件写 `evidence.json`，finalizer 校验后自动生成总结与阅读页。需要宿主转写工具时，也可用 `podcast-reader/scripts/prepare_episode.py` 获取来源并回填逐字稿。

```text
episode/
├── summary.md              # 主要交付：省流版文字
├── reader.html             # 主要交付：卡片式阅读页
├── evidence.json           # Agent 编写的结构化总结与证据
├── analysis.md             # 自动生成的兼容副本
├── transcript.json         # 原文片段与真实时间轴（如有）
├── chunks.json             # 阅读长内容时的分块索引
├── analysis-handoff.json   # 当前 Agent 的完成要求
└── bundle.json             # 状态、来源、限制与产物清单
```

`quick` / `standard` / `deep` 保留为显式调用的兼容模式，不再作为默认入口或用户选择菜单。已有转写、来源适配和恢复能力继续为省流版服务。

运行检查：

```bash
python -m unittest discover -s podcast-reader/tests -v
python -m compileall -q podcast-reader/scripts
python podcast-reader/scripts/release_check.py
```

运行需要 Python 3.10+；媒体处理需要 FFmpeg / ffprobe，平台来源通常需要 yt-dlp。没有公开字幕时可使用宿主转写或 `uv` + 本地 `faster-whisper`。文本标准化、索引和验证使用 Python 标准库。

## 文档与贡献

[文档中心](docs/README.md) · [总结工作流](podcast-reader/references/analysis-workflows.md) · [输出规范](podcast-reader/references/output-schema.md) · [架构](docs/architecture.md) · [变更记录](CHANGELOG.md)

欢迎改善来源覆盖、总结准确度、阅读体验和失败恢复。历史版本的在线验证记录见 [公开来源冒烟报告](docs/smoke-results.md)；它不代表每个来源或当前每条链接都已通过测试。

分享包默认不携带完整逐字稿，并净化本机路径和敏感 URL 参数。详见 [安全策略](SECURITY.md) 和 [贡献指南](CONTRIBUTING.md)。

[MIT License](LICENSE) © 2026 Podcast Reader contributors
