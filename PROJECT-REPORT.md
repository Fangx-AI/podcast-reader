# Podcast Reader v2.0 项目交付报告

## 交付结论

Podcast Reader 已从“能读取播客”升级为可发布的长内容研究 Skill：用户只需提供 Bilibili、YouTube、RSS、节目页、媒体直链或本地文件，当前 Agent 即可完成来源解析、字幕优先获取、零 Key 本地转写、时间戳索引、证据约束分析、持续追问、翻译/说话人回填、可点击阅读器及安全导出。

v2 的核心原则是：**不伪装成功、不伪造证据、不静默漏内容、不把 API Key 变成核心前置条件。**

## v2 关键升级

1. **端到端闭环**：统一入口在转录后生成分析交接契约；Skill 要求当前 Agent 继续写入 `analysis.md`、`evidence.json`，严格校验后才可报告 `analyzed`。
2. **可恢复长任务**：来源 SHA-256、参数指纹、切块连续性、总时长覆盖和逐块缓存全部校验；损坏缓存自动隔离并重建。
3. **真实进度**：持久化阶段、百分比、已完成块数、耗时、ETA 和 partial transcript；中断后可继续。
4. **严格证据**：短引必须逐字存在于被引用 segment；章节、时间戳、枚举、主张和 segment 引用均有机器校验。
5. **多语言与说话人**：任意目标语言使用 100% segment 覆盖契约；供应商中立的说话人时间段适配器按重叠回填。
6. **零配置优先**：公开字幕优先，随后才获取音频；本地 `faster-whisper` 为零 Key 兜底；已配置云能力只是可选加速器。
7. **平台韧性**：字幕按“首选人工轨 → 源语言人工轨 → 自动轨”逐条回退，单轨 429 不再拖垮整个来源；Bilibili 可用公开 API 合法降级。
8. **安全分享**：分享包默认排除完整逐字稿，净化本机路径与敏感 URL 参数；完整 transcript 只能显式加入。
9. **无障碍阅读**：自动生成单文件 `reader.html`，支持全文搜索、键盘焦点、移动端、屏幕阅读器状态及 YouTube/Bilibili 时间跳转。
10. **工程化发布**：单一版本源、固定依赖、固定 GitHub Action SHA、CycloneDX SBOM、确定性 ZIP、SHA-256、安装备份/回滚和防降级。

## 当前质量指标

| 指标 | v2.0.0 结果 |
|---|---:|
| Skill Python CLI | 31 |
| 离线自动测试 | 55 / 55 通过 |
| `SKILL.md` | 159 个物理行，低于 500 行门槛 |
| Skill 内部链接 | 10 / 10 有效 |
| 发布版本源 | `podcast-reader/VERSION` = `2.0.0` |
| CI | Windows / Linux × Python 3.11 / 3.12 / 3.14 |
| 核心 API Key | 0 |
| 未处理 TODO/FIXME | 0（验证器检测字面量和受控异常分支除外） |

## 真实前向验证

- **YouTube**：TED 844 秒公开视频，无 Key、无音视频下载，取得发布者 `zh-CN` VTT，生成 316 个时间戳片段；转录质量 100 分、零警告，状态 `ready_for_analysis`。
- **Bilibili**：用户提供的 `BV1a5ECzqEVB` 成功读取 11,778.687 秒公开元数据；当前页面不公开字幕时返回合法 `partial`、明确下一步且不使用 Cookie。v1 长链路证据已验证同一来源的 2 个分 P、12,139.015 秒公开音频、8 个可恢复块及 1,897 个本地转录片段。
- **RSS**：NPR Planet Money 公开 Feed 解析 355 期，`--latest` 精确选择最新一期，只保存元数据、不下载音频，bundle 校验通过。
- **本地完整闭环**：固定 SRT 生成 transcript、索引、质量报告、分析契约；黄金分析和证据经严格校验后生成可点击 reader，最终 `analyzed`。
- **隐私导出**：默认分享 ZIP 不含完整逐字稿和绝对本机路径；独立校验通过并输出 SHA-256。
- **恢复性**：删除一个已缓存音频块后重跑，系统识别缺块并事务式重建，而非静默复用不完整结果。

详细命令与结果见 [docs/smoke-results.md](docs/smoke-results.md)、[docs/ux-acceptance.md](docs/ux-acceptance.md) 和 [docs/quality-and-acceptance.md](docs/quality-and-acceptance.md)。

## 交付结构

- `podcast-reader/`：可直接安装的 Skill 本体。
- `podcast-reader/scripts/`：解析、获取、转写、分析契约、验证、导出、安装和发布 CLI。
- `podcast-reader/references/`：Agent 运行时按需读取的流程与格式规范。
- `README.md` / `README.en.md`：中英文用户入口。
- `docs/`：架构、竞品、验收、真实测试和发布说明。
- `.github/`：CI、Release、Dependabot、Issue 与 PR 模板。

## 明确边界

- 不绕过 DRM、付费墙、登录、地区限制、私人 Feed 或平台访问控制。
- 没有公开字幕时，完整语义分析仍需要公开/授权媒体或用户提供的 transcript。
- 本地首次转写可能需要联网下载隔离依赖和模型，并消耗本机 CPU/GPU。
- 说话人分离质量取决于宿主或用户提供的 diarization 时间段；项目不会把猜测包装成可靠身份。
- 完整受版权保护逐字稿默认不进入分享包；分析、导航、短引与证据出处优先。
