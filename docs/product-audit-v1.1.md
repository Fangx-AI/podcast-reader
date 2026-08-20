# Podcast Reader v1.1 发布门禁与产品审计

审计日期：2026-08-19
审计角色：用户产品经理、Skill 设计负责人、发布负责人
结论：**达到 GitHub/Codex Skill 范畴的顶级梯队标准；综合评分 9.2/10。**

这个结论不等于“没有边界”。它表示：没有已知 P0/P1，链接首用、恢复、证据、跨语言、视觉、导出和安全形成完整闭环，且关键路径有可复现验证。它仍不等同于带托管转写、账号系统和平台授权合作的商业 SaaS。

## 发布门禁

| 门禁 | 要求 | 结果 |
|---|---|---|
| 致命/高优缺陷 | P0 = 0，P1 = 0 | 通过 |
| 关键用户场景 | 通过率 100% | 24/24 离线场景通过 |
| Skill 结构 | 官方 validator 通过 | 通过 |
| Python | 3.11、3.12、3.14 | 三个版本通过 |
| 平台 | YouTube ready；RSS metadata-only；Bilibili 可解释 partial | 通过 |
| 数据安全 | 不持久化凭据/签名媒体参数 | 通过 |
| 安装与交付 | 本机 Skill 与 GitHub 包哈希一致 | 通过（发布前复核） |
| 文档 | 无断链、无未完成 scaffold | 通过 |

## 评分卡

| 维度 | 权重 | 得分 | 证据 |
|---|---:|---:|---|
| 发现与触发 | 10% | 9.4 | 描述可区分、自然语言触发、默认 prompt、品牌图标与颜色 |
| 零配置首用 | 15% | 9.3 | 只贴链接走 standard；脚本使用真实 `{skill_dir}`，不依赖 cwd |
| 来源覆盖 | 12% | 8.8 | YouTube、Bilibili、RSS、网页、直链、本地；平台限制仍客观存在 |
| 转录与多语言 | 12% | 9.2 | SRT/VTT/ASS/TTML/LRC/JSON3/JSON/TXT/MD、说话人和术语规则 |
| 证据与持续问答 | 12% | 9.4 | 原始稿保留、标准 segments、时间戳 chunks、跨中英文检索 |
| 视频画面 | 8% | 8.6 | 有界 720p 获取、关键帧、联系表、视觉/口头证据分离 |
| 可靠性与恢复 | 10% | 9.4 | partial bundle、阶段错误、转写回填、模式感知缓存、超时与幂等 |
| 安全/隐私/版权 | 8% | 9.5 | access control、Cookie 审批、提示注入、URL 清理、短引规则 |
| 文档与易用性 | 6% | 9.5 | 中英 README、渐进披露、模板、架构、故障矩阵、治理文档 |
| 测试与发布工程 | 7% | 9.4 | 24 场景、黄金报告、CLI 契约、多 Python、Windows/Linux CI |
| **加权总分** | **100%** | **9.2** | 顶级梯队门槛：≥9.0 且无 P0/P1 |

## 本轮发现并修复的问题

### P1：真实首用会失败或主能力不闭环

1. **脚本路径依赖当前目录**：`python scripts/...` 在用户工作区可能找不到。改为解析 `{skill_dir}` 后绝对调用。
2. **RSS/网页模式语义错误**：`metadata`/`subtitles` 仍可能下载音频。现在这两个模式绝不回退到音频。
3. **转写后无法恢复同一 bundle**：新增 `--transcript` 回填，自动保留 raw、标准化、索引并切换状态。
4. **超长纯文本没有真正分块**：单一巨型 segment 现在按句子/长度拆成受限检索块。
5. **缓存阻断深度升级**：metadata preview 不再冒充 auto/deep 的完整结果；缓存按模式、语言和产物判断。
6. **远程视觉能力只存在于文档**：新增明确 `video` 模式，获取有界 720p 公共视频后进入关键帧 lane。
7. **临时/追踪媒体 URL 被持久化**：运行时地址与落盘 provenance 分离，凭据和查询参数被清理。

### P2：可靠性、兼容和精度问题

- RSS `--latest` 从“默认第一条”改为按可解析发布日期选择最新。
- 直链下载拒绝 HTML/JSON 错误页，并通过 URL 哈希避免同名缓存冲突。
- 新增 ASS、TTML、LRC、YouTube JSON3 兼容与滚动字幕去重。
- ready bundle 强制要求 `source.json`；报告中的普通 URL 不再冒充来源字段。
- YouTube/Bilibili 默认目录至少包含稳定视频 ID，不再生成含糊的 `watch-*`。
- 子进程超时转换为结构化阶段错误，不泄露 traceback。
- UI 增加小图标、大图标和品牌色。
- 核心安全规则明确把字幕、描述、幻灯片和屏幕文字视为不可信内容。

## 24 个可复现场景

1. 本地 SRT 一键 bundle。
2. 同源 bundle 缓存复用。
3. metadata → subtitles 模式升级不被旧缓存拦截。
4. 生成式 transcript 回填原媒体 bundle。
5. SRT 标准化。
6. VTT 重复/滚动 cue 去重。
7. ASS 标准化。
8. TTML 标准化。
9. YouTube JSON3 标准化。
10. 中英文混合检索。
11. 超长无时间戳文本分块上限。
12. RSS 精确标题选择。
13. 未排序 RSS 按日期选 latest。
14. RSS metadata 不下载音频。
15. RSS subtitles 无 transcript 时不下载音频。
16. 直链 metadata 不下载文件。
17. 直链拒绝 HTML 错误页。
18. 同名直链避免缓存碰撞。
19. 签名参数不落盘。
20. HTML metadata 属性顺序兼容与 URL 去重。
21. YouTube/Bilibili 离线分类。
22. bundle 来源强校验。
23. Markdown 来源、时间戳、短引与限制严格校验。
24. 所有 CLI `--help`、Skill 链接、UI 图标和 frontmatter 契约。

## 公开冒烟

- **YouTube**：TED 公开视频成功获取英文字幕、保存 `transcript-raw.vtt`、生成 JSON/Markdown/SRT/VTT/chunks，状态 `ready_for_analysis`。中文翻译轨 429 被记录为非阻塞警告。
- **Bilibili**：当前网络的 yt-dlp 请求被 HTTP 412 阻断；公共元数据兜底成功返回标题、UP 主、日期和 2890 秒时长，状态为结构合法的 `partial`，未使用 Cookie 或绕过限制。
- **RSS**：NPR Planet Money Feed 成功按日期选择最新一期；`metadata` 模式未下载音频，enclosure 查询参数未持久化。
- **远程视频**：YouTube 视频下载遇到平台 bot verification 时安全降级为 partial；本地/已授权视频关键帧 lane 已通过可再现 FFmpeg 测试。

## 残余边界（非发布阻断）

1. Bilibili/YouTube 的字幕和媒体访问会随地区、登录、反爬和 yt-dlp 版本变化。
2. 无公开字幕时仍依赖可用转写 Skill/供应商或用户提供媒体；本项目不内置托管 ASR 服务。
3. 关键帧是代表性采样，不能证明未采样时刻不存在某个视觉事件。
4. 依赖词项的本地检索强调可解释和零依赖；超大跨节目语料可选向量/混合检索仍属后续增强。
5. Linux 由 GitHub Actions 门禁覆盖，本次本地动态验证环境为 Windows。

## v1.2 建议

- 增加可选向量/混合检索，但保留零依赖 fallback。
- 增加正式的评测集：章节边界、claim recall、speaker attribution 和引用准确率。
- 增加可选 OCR adapter 与精确时间点补帧命令。
- 建立平台适配器健康监控与 yt-dlp 版本兼容矩阵。
- 若走商业产品，再增加托管转写队列、进度 UI、成本预估和团队知识库。
