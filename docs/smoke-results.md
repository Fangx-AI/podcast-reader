# v1.4.0 公开来源冒烟结果

测试日期：2026-08-19（Asia/Shanghai）

## YouTube：字幕到可检索任务包

- 来源：TED《Inside the Mind of a Master Procrastinator》
- URL：<https://www.youtube.com/watch?v=arj7oStGLkU>
- 模式：`subtitles`，语言顺序 `en,zh-Hans`
- 结果：成功读取标题、频道、发布日期、844 秒时长和英文 VTT；自动生成 `transcript.json`、`transcript.md`、SRT、VTT 与 `chunks.json`。
- 状态：`ready_for_analysis`
- 校验：`validate_bundle.py` 全部通过。
- 降级验证：中文自动翻译轨触发 HTTP 429 时，英文原始字幕仍然保留并继续完成，警告不影响已有结果。

## Bilibili：平台限制下的公共元数据兜底

- 来源：《【深度访谈】AI未来已来！李飞飞揭示人工智能的下一个前沿》
- URL：<https://www.bilibili.com/video/BV1hruCz2ESY/>
- 模式：`subtitles`，不下载音频。
- 结果：yt-dlp 在当前网络返回 HTTP 412；公共元数据兜底成功读取 BV 号、标题、UP 主、发布日期、2890 秒时长和规范链接。
- 状态：`partial`
- 校验：partial bundle 结构校验通过，并提供“公开 transcript 或授权本地媒体导出”的下一步。
- 安全：未使用 Cookie，未尝试绕过 412，未下载媒体。

## Bilibili：HTTP 412 后的多分 P 音频兜底

- 来源：《纳瓦尔25年最新博客：你只有一次人生（完整版）关于生活、工作和智慧的访谈》
- URL：<https://www.bilibili.com/video/BV1a5ECzqEVB/>
- 结果：yt-dlp 返回 HTTP 412 后，公开 API 识别 2 个分 P；公共字幕数为 0，随后无 Cookie 获取并规范化两段音频。
- 完整性：音频合计 12,139.015 秒，页面标称 12,140 秒，相差约 0.985 秒。
- 长音频准备：218.7 MB 音频生成 8 个 30 分钟内的 16 kHz Opus 块，最大约 5.47 MB，均低于 25 MB 上传限制。
- 全量转写：无需 Cookie 与 API Key，使用本地 `faster-whisper small` 完成 8 个音频块，合并为 1,897 个连续时间戳片段。
- 检索与分析：生成 82 个语义检索块、严格校验的 `analysis.md` / `summary.md` 和引用可解析的 `evidence.json`。
- 风险分层：将医疗、育儿、AI 与人口预测从可执行生活建议中分离，明确标注未做外部核验。
- 最终状态：`analyzed`；bundle、完整报告、独立摘要及结构化证据校验全部通过。

## RSS：公开 Feed 选择

- 来源：NPR Planet Money
- Feed：<https://feeds.npr.org/510289/podcast.xml>
- 模式：`--latest`
- 结果：成功解析节目名、355 个条目，并显式选择第一条最新节目，提取标题、GUID、发布日期、时长和 enclosure。
- 安全：只解析 Feed，不下载节目音频。

## 无 API Key 本地转写

- 来源：`BV1a5ECzqEVB` P1 的 30 秒真实音频样本。
- 命令：`transcribe_local.py ... --bootstrap --model tiny --language auto`。
- 引导：`uv` 自动创建隔离 Python 3.12 环境并安装固定版本 `faster-whisper==1.2.1`；未设置任何 API Key 或 Hugging Face Token。
- 结果：CPU int8 输出 11 个带起止时间的片段，自动识别英文，语言概率约 0.995。
- 结论：API Key 不是核心链路前置条件；首次本地运行仍需下载依赖/模型并消耗本机算力。

## 视频画面：关键帧与联系表

- 来源：FFmpeg 本地 6 秒可再现测试视频。
- 结果：成功生成 3 张有界采样帧、`manifest.json` 和 `contact-sheet.jpg`。
- 状态：`ready`

## 离线回归

- v1.4.0 当前 35 项测试通过；CI 配置覆盖 Windows/Linux × Python 3.11、3.12、3.14。
- 统一入口前向测试：从仓库外目录处理 30 秒真实 WAV，无 API Key 完成切分、tiny 转写、时间线恢复与索引；缓存复跑约 1.03 秒。
- Skill 官方快速结构校验通过。
- 所有 CLI 的 `--help` 成功。
- 本地 SRT 一键 bundle、缓存复用、字幕去重、中英文检索、黄金 Markdown 严格校验和 UTF-8 BOM CSV 导出均通过。
- RSS metadata 模式确认不会下载 enclosure，持久化 bundle 不包含媒体跟踪/签名查询参数。
- 新增 transcript 回填、metadata→subtitles 缓存升级、巨型纯文本分块、ASS/TTML/JSON3 和远程 video 模式回归。
