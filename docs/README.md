# Podcast Reader 文档中心

项目只有一个默认目标：**把能获取到内容的播客做成 3–5 分钟读完的省流版，识别关键问题和高价值信息。**

[项目首页](../README.md) · [English](../README.en.md) · [完整阅读页示例](examples/summary-preview.html)

## 从哪里开始

| 需要什么 | 文档 |
|---|---|
| 安装、发链接、拿到总结 | [项目首页](../README.md) |
| 看最终结果长什么样 | [黑金卡片式 HTML 示例](examples/summary-preview.html)，内容为项目自编虚构节目 |
| Agent 怎样完成省流版 | [Skill 入口](../podcast-reader/SKILL.md) → [总结工作流](../podcast-reader/references/analysis-workflows.md) |
| 怎样识别关键问题与高价值信息 | [总结工作流](../podcast-reader/references/analysis-workflows.md) → [编辑模板](../podcast-reader/assets/analysis-template.md) |
| 结构化总结怎么写、怎样验收 | [输出规范](../podcast-reader/references/output-schema.md) |
| 来源不可用或处理失败 | [故障排查](../podcast-reader/references/troubleshooting.md) |

默认交付是 `summary.md` 和 `reader.html`。当前 Agent 从完整来源中提炼 `evidence.json`，校验后自动生成两份交付物；`ready_for_analysis` 只代表准备完成。

## 实现与来源

| 文档 | 内容 |
|---|---|
| [系统架构](architecture.md) | 来源准备 → 全文理解 → 结构化提炼 → 校验生成 |
| [来源解析](../podcast-reader/references/source-resolution.md) | URL、RSS、节目页和本地文件 |
| [摄取与平台降级](../podcast-reader/references/ingestion.md) | 字幕优先、公开音频、完整性与访问限制 |
| [跨 Agent 可移植性](../podcast-reader/references/portability.md) | 宿主转写、本地兜底和供应商中立接口 |
| [多语言转写](../podcast-reader/references/transcription-languages.md) | 原始语言、专有名词、转写质量 |
| [画面证据](../podcast-reader/references/visual-analysis.md) | 仅当画面影响总结中的重要结论时使用 |
| [证据与版权](../podcast-reader/references/evidence-and-copyright.md) | 原话、观点、综合归纳和分享边界 |

## 开发与维护

| 文档 | 内容 |
|---|---|
| [贡献指南](../CONTRIBUTING.md) | 围绕总结质量、来源覆盖和阅读体验贡献 |
| [安全策略](../SECURITY.md) | 信任边界、隐私和漏洞报告 |
| [Changelog](../CHANGELOG.md) | 未发布改动及版本历史 |
| [质量与验收](quality-and-acceptance.md) | 工程质量门；省流版字段与交付以当前输出规范为准 |

## 历史记录

以下文档记录旧版功能范围、发布和测试结果。旧版 `quick` / `standard` / `deep` 模式仍可显式调用，但不再作为默认产品入口；当前定位以项目首页和 Skill 为准。

- [v2.0.1 发布说明](release-v2.0.1.md)
- [公开来源冒烟报告](smoke-results.md)
- [历史体验验收](ux-acceptance.md)
- [历史竞品基准](benchmark.md)
- [历史交付报告](../PROJECT-REPORT.md)
- [早期产品审计](product-audit-v1.1.md)

遇到问题可提交 [Bug report](https://github.com/Fangx-AI/podcast-reader/issues/new?template=bug_report.yml)。建议新增来源或改善总结时，说明它如何帮助用户更快抓住一期节目的重要信息。
