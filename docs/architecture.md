# 架构说明

## 产品目标与完成定义

默认目标只有一个：把可获取到内容的播客，变成 3–5 分钟可读的省流版。总结按**关键问题与直接答案、高价值信息**组织；来源解析、转写、索引、证据和导出共同支持这一目标。

默认模式为 `summary`。当前 Agent 编写 `evidence.json` 中的 `digest`，finalizer 校验后生成 `summary.md`、`reader.html` 和用于兼容的 `analysis.md`。准备好逐字稿不等于已经完成总结。

## 设计原则

1. **链接即可开始**：自动走省流版流程，不让用户先选分析档位。
2. **先覆盖内容，再筛选重点**：检索辅助回看，不能只凭几个命中片段代表整期节目。
3. **围绕问题提炼**：找关键问题、直接答案、判断变化、反直觉发现、关键数据案例、方法与边界；不照搬目录。
4. **证据约束**：一句话结论、每个答案和洞察可追溯到原文片段，短引必须逐字匹配。
5. **字幕优先**：可用官方稿或字幕优先于重新转写。
6. **单一总结来源**：Agent 写结构化证据，Markdown 与 HTML 由同一内容生成，防止三份摘要漂移。
7. **失败可恢复**：保留来源与转写缓存；明确区分准备完成、部分成果和总结完成。
8. **不编造缺失信息**：无时间轴就引用 segment ID；身份未确认就不补造人物履历；内容无法获取就说明。
9. **供应商中立**：宿主转写、本地模型或用户已配置提供商均可接入，不要求某个云 API Key。
10. **来源内容不可信**：节目中的提示词不是 Agent 指令；不绕过访问控制、不隐式读 Cookie。

## 完整链路

```text
链接 / 本地文件
    ↓
解析来源，优先字幕 / 官方稿；必要时获取音频与转写
    ↓
标准化文本、时间轴、质量报告、分块索引
    ↓
ready_for_analysis + analysis-handoff.json
    ↓
当前 Agent 阅读整期内容，选择关键问题与高价值信息
    ↓
evidence.json：digest + 来源 + 引用 + 限制
    ↓
finalize_bundle.py 校验并生成
    ↓
summary.md + reader.html + analysis.md（兼容副本）
    ↓
validate_bundle.py → analyzed
```

`process_episode.py` 不独立调用大模型 API 生成总结。它负责准备与交接，当前宿主 Agent 完成理解与写作。这样既保持供应商中立，也避免把“下载转写成功”误报为“总结成功”。

## 组件职责

| 层 | 组件 | 职责 |
|---|---|---|
| 任务入口 | `SKILL.md` | 默认省流版目标、内容覆盖、编辑选择和交付规则 |
| 统一编排 | `process_episode.py` | 来源、转写、时间轴、质量、索引和 Agent 交接 |
| 来源准备 | `prepare_episode.py` | 摄取、外部逐字稿回填、缓存和状态 |
| 环境诊断 | `doctor.py` | 离线检查依赖、可写目录、磁盘与首次下载需求 |
| 来源获取 | `resolve_podcast.py`, `ingest_media.py`, `fetch_audio.py` | URL/RSS/页面解析、字幕与媒体获取 |
| 文本标准化 | `normalize_transcript.py` | 各格式转为稳定 segments，保留未知值 |
| 长音频转写 | `prepare_audio_chunks.py`, `transcribe_local.py`, `combine_chunk_transcripts.py` | 可恢复分块、转写、全局时间轴 |
| 长文本阅读 | `chunk_transcript.py`, `search_chunks.py` | 有界分块和回查上下文；不代替完整覆盖 |
| Agent 提炼 | `analysis-handoff.json`, 编辑模板 | 选出中心问题、直接答案和高价值信息，写入 `digest` |
| 校验与生成 | `finalize_bundle.py`, `validate_evidence.py`, `validate_notes.py`, `validate_bundle.py` | 验证结构、引用和短引，生成并检查最终交付 |
| 阅读与分享 | `render_reader.py`, `export_bundle.py` | 省流版卡片页、原文核对、隐私净化分享 |

视频抽帧、字幕导出等现有辅助能力保留，在总结需要时使用。`quick` / `standard` / `deep` 仅保留显式调用的旧契约。

## 状态机

```text
new
 ├─→ needs_selection ─→ resolved
 ├─→ metadata_only
 ├─→ needs_transcription ─→ ready_for_analysis
 ├─→ ready_for_analysis ─→ analyzed
 ├─→ partial ─→ retry failed stage
 └─→ blocked ─→ available source / dependency required
```

`ready_for_analysis` 表示文本已就绪，还需 Agent 完成总结。`partial` 表示有可复用成果，同时有明确的 `warnings` 和 `next_actions`。元数据和部分转写都不能伪装成整期总结完成。

## 数据不变量

- 原始逐字稿不被总结覆盖。
- `chunks.json` 与所有 evidence 引用可追溯到 `transcript.json` 的真实 segment。
- 未知值保持未知；TXT / Markdown 没有时间轴时不生成假时间。
- `digest` 保存标题、结论、参与者、关键问题、洞察和可选未解问题；每个主要答案都有原文引用。
- 人物身份来自明确的元数据或介绍；人物卡片可省略。
- 短引必须与引用片段精确匹配；节目观点、Agent 归纳、画面观察和外部核验保持区分。
- 问题与洞察数量有上限，短来源可以更少，不强迫填满所有类别。
- `summary` 模式下，`summary.md`、`analysis.md` 和 `reader.html` 从同一份 evidence 生成。
- 只有证据与交付物通过验证才标为 `analyzed`；旧模式缓存不能替代新省流版交付。
- Bundle 内路径不得逃逸出 episode 目录。分享包默认不含完整逐字稿，不暴露本机路径、凭据或临时签名参数。

详见 [输出规范](../podcast-reader/references/output-schema.md)。

## 扩展方向

新增能力应直接改善来源覆盖、提炼准确度、阅读速度或失败恢复。来源适配器和转写供应商应输出现有标准结构；摘要样式和字段变更必须同步 schema、生成器、验证器和示例。不要让默认入口膨胀为研究、翻译、知识管理等平行产品菜单。
