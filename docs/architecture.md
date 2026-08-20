# 架构说明

## 设计原则

1. **用户意图优先**：链接本身足以开始，技术参数是高级选项。
2. **证据优先**：先建立可追溯文本，再分析；重要判断必须能回到时间戳。
3. **字幕优先**：公开稿件/字幕通常比重新转写更快、更便宜、更准确。
4. **持久任务包**：一次处理，多次问答；失败阶段可以单独恢复。
5. **渐进披露**：`SKILL.md` 负责路由，参考文档负责复杂策略，脚本负责确定性操作。
6. **优雅降级**：元数据、字幕、音频、转写、画面任一可用时都保留成果。
7. **最小权限**：不自动读取 Cookie，不绕过访问控制，不持久化临时签名 URL。
8. **供应商中立**：转写依次使用宿主原生能力、无 Key 本地模型、用户已配置提供商；不把任一 API 设为硬依赖。

## 层次

| 层 | 组件 | 责任 |
|---|---|---|
| 交互路由 | `SKILL.md` | 判断来源、模式、分析意图、何时加载参考文档 |
| 统一编排 | `process_episode.py` | 一条命令完成解析、字幕优先、必要时本地转写、全局时间线与索引 |
| Bundle 编排 | `prepare_episode.py` | 来源摄取、外部转录回填、缓存和状态管理 |
| 环境诊断 | `doctor.py` | 无网络检查 Python、FFmpeg、uv、yt-dlp、本地转写与输出权限 |
| 来源 | `resolve_podcast.py`, `ingest_media.py`, `fetch_audio.py` | URL 分类、RSS/页面解析、字幕/媒体获取 |
| 文本 | `normalize_transcript.py` | SRT/VTT/JSON/TXT/MD 统一为稳定 segment 模型 |
| 转写 | `prepare_audio_chunks.py`, `transcribe_local.py`, `combine_chunk_transcripts.py` | 长音频切分、无 Key 本地转写、全局时间轴恢复 |
| 检索 | `chunk_transcript.py`, `search_chunks.py` | 长文本分块、跨中英文关键词检索、邻近上下文 |
| 视觉 | `extract_keyframes.py` | 有界关键帧、联系表、时间戳 manifest |
| 导出 | `export_evidence.py`, 模板 | Markdown、JSON、SRT、VTT、CSV |
| 质量 | `validate_bundle.py`, `validate_notes.py`, tests | 结构、证据、占位符、接口和回归检查 |

`process_episode.py` 将阶段事件同时输出到终端并持久化为 `progress.json`。长音频按块恢复；重复运行已完成来源时，不重新下载或转写。

## 状态机

```text
new
 ├─→ needs_selection ─→ resolved
 ├─→ metadata_only
 ├─→ needs_transcription ─→ ready_for_analysis
 ├─→ ready_for_analysis ─→ analyzed
 ├─→ partial ─→ retry failed stage
 └─→ blocked ─→ different lawful source/authorization/dependency required
```

`partial` 不是异常退出的同义词。它表示任务包中存在可复用成果，同时有明确的 `warnings` 与 `next_actions`。

## 数据不变量

- `transcript-raw.*` 不被覆盖。
- 未知值使用 `null` 或明确的“未知”，不生成看似合理的值。
- `chunks.json` 的文本可追溯至 `transcript.json` 的 segment。
- 画面观察与口头陈述分开存储和引用。
- 外部事实核验与节目证据分开引用。
- 任务包中的路径不得逃逸出 episode 目录。

## 多语言检索

检索器不依赖大型向量数据库，默认采用可解释的词项排名：英文/数字/技术符号词项 + 中文二元字符片段 + 精确短语加权。它适合作为 Agent 的第一阶段召回；Agent 再读取相邻块并进行语义判断。这样离线可测试，也避免强制外部服务。

## 扩展点

- 新平台适配器应输出与 `ingest_media.py` 相同的结果结构。
- 新转录供应商只需将结果映射为标准 segments；核心流程不得要求特定厂商密钥。
- 新分析模式应复用 evidence labels 与时间戳契约。
- OCR 或向量检索可以作为可选增强，不能让核心链路失去离线可用性。
