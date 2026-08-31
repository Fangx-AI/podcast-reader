<div align="center">

# Podcast Reader 文档中心

从产品体验、系统架构到质量验证与发布记录的完整导航。

[返回项目首页](../README.md) · [English README](../README.en.md) · [最新 Release](https://github.com/Fangx-AI/podcast-reader/releases/latest)

</div>

---

## 按角色阅读

| 你是谁 | 建议阅读顺序 | 你会得到什么 |
|---|---|---|
| 第一次使用 | [项目首页](../README.md) → [故障排查](../podcast-reader/references/troubleshooting.md) | 安装、运行和常见问题 |
| Agent / Skill 用户 | [工作流](../podcast-reader/references/analysis-workflows.md) → [输出规范](../podcast-reader/references/output-schema.md) | 分析档位、交付结构与问答方式 |
| 开发者 | [架构](architecture.md) → [质量门](quality-and-acceptance.md) → [贡献指南](../CONTRIBUTING.md) | 模块边界、测试要求与 PR 规范 |
| 产品经理 | [竞品基准](benchmark.md) → [体验验收](ux-acceptance.md) → [项目报告](../PROJECT-REPORT.md) | 定位、差异化和交付成熟度 |
| 安全审查者 | [安全策略](../SECURITY.md) → [证据与版权](../podcast-reader/references/evidence-and-copyright.md) | 信任边界、隐私和版权处理 |
| 发布维护者 | [当前发布说明](release-v2.0.1.md) → [真实冒烟](smoke-results.md) | 发布门、前向结果和已知边界 |

## 产品与体验

| 文档 | 内容 |
|---|---|
| [竞品与顶级 Skill 基准](benchmark.md) | 与同类工具、GitHub 顶级 Skill 的能力和体验对照 |
| [用户体验验收矩阵](ux-acceptance.md) | 从贴链接到持续追问、导出与失败恢复的体验检查 |
| [项目交付报告](../PROJECT-REPORT.md) | v2.0.1 的能力全景、质量指标和真实验证 |
| [产品审计历史](product-audit-v1.1.md) | 早期版本问题、优先级和演进依据 |

## 架构与数据

| 文档 | 内容 |
|---|---|
| [系统架构](architecture.md) | 来源解析、摄取、转写、索引、分析、导出的完整链路 |
| [来源解析](../podcast-reader/references/source-resolution.md) | URL、RSS、节目页与本地文件如何路由 |
| [摄取与平台降级](../podcast-reader/references/ingestion.md) | 字幕优先、Bilibili 公开 API、媒体完整性和安全限制 |
| [输出 Schema](../podcast-reader/references/output-schema.md) | bundle、transcript、chunks、evidence 和 reader 的契约 |
| [跨 Agent 可移植性](../podcast-reader/references/portability.md) | 宿主能力、本地兜底和供应商中立适配器 |

## 分析与证据

| 文档 | 内容 |
|---|---|
| [分析工作流](../podcast-reader/references/analysis-workflows.md) | quick、standard、deep 以及持续问答 |
| [证据、核验与版权](../podcast-reader/references/evidence-and-copyright.md) | 引文、主张、外部核验和分享边界 |
| [画面分析](../podcast-reader/references/visual-analysis.md) | 何时抽帧、如何把画面与口头内容对应 |
| [多语言转写](../podcast-reader/references/transcription-languages.md) | 语言识别、翻译映射和专有名词处理 |
| [分析报告模板](../podcast-reader/assets/analysis-template.md) | 最终 Markdown 报告的推荐结构 |

## 质量与发布

| 文档 | 内容 |
|---|---|
| [质量与验收](quality-and-acceptance.md) | 自动测试、严格验证和完成定义 |
| [公开来源冒烟报告](smoke-results.md) | YouTube、Bilibili、RSS 与本地完整闭环 |
| [v2.0.1 发布说明](release-v2.0.1.md) | 当前稳定版本与真链接驱动修复 |
| [Changelog](../CHANGELOG.md) | 全部版本变化 |
| [贡献指南](../CONTRIBUTING.md) | 开发、测试、Commit 与 PR 要求 |

## 需要帮助？

- 安装或运行失败：先看 [故障排查](../podcast-reader/references/troubleshooting.md)。
- 发现可复现缺陷：提交 [Bug report](https://github.com/Fangx-AI/podcast-reader/issues/new?template=bug_report.yml)。
- 希望增加来源或能力：提交 [Feature request](https://github.com/Fangx-AI/podcast-reader/issues/new?template=feature_request.yml)。
- 安全漏洞：按 [Security Policy](../SECURITY.md) 私密报告，不要公开可利用细节。

---

<div align="center">

[返回项目首页](../README.md) · [下载最新版本](https://github.com/Fangx-AI/podcast-reader/releases/latest)

</div>
