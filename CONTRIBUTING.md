<div align="center">

# 为 Podcast Reader 贡献

把播客做成更准确、更有信息量、更容易读完的省流版。

[项目首页](README.md) · [文档中心](docs/README.md) · [架构](docs/architecture.md) · [安全策略](SECURITY.md)

</div>

---

感谢你改进 Podcast Reader。项目的默认目标只有一个：让用户在 3–5 分钟内抓住一期播客的关键问题、直接答案和高价值信息。优先接受改善来源兼容性、提炼准确度、证据可靠性、阅读体验和失败恢复的改动。

## 开始之前

1. 先用 [Issue](https://github.com/Fangx-AI/podcast-reader/issues) 描述问题、来源类型、预期行为和实际行为。
2. 涉及平台适配时，只使用公开、合法、无需规避访问控制的接口。
3. 不要提交 Cookie、Feed Token、签名 URL、API Key、私人媒体或受版权保护的完整文本。
4. 新增依赖前说明为什么标准库或现有工具无法完成。

## 本地开发

```text
python -m compileall -q podcast-reader/scripts
python -m unittest discover -s podcast-reader/tests -v
```

核心离线测试必须在 Windows 与 Linux 上通过。测试夹具应短小、可再分发、确定性强，并且不访问网络。

> [!TIP]
> 最有价值的贡献通常来自真实失败：请尽量保留最小复现、公开来源类型、失败阶段和可安全分享的诊断信息。

## 改动要求

- 新来源：补充解析/摄取测试、错误降级、隐私与限制说明。
- 新转录格式：保留原始文本、时间戳、说话人和未知值。
- 新输出字段：同步 `references/output-schema.md`、模板、生成器、验证器和固定样例。
- 总结改动：保留关键条件与分歧，避免把检索命中片段冒充完整节目，验证主要结论的原文依据。
- 产品范围：默认入口维持 `summary`；旧模式仅作兼容，新增能力应服务省流版，不增加平行产品菜单。
- 文档改动：保持 `SKILL.md` 精简，将复杂内容放入单层 `references/`。

## Commit 与 PR

提交信息应说明结果，例如 `feat: add Podcasting 2.0 transcript discovery`。Pull Request 需要包含：

- 用户问题与解决方式；
- 兼容性或安全影响；
- 新增/修改测试；
- 手动冒烟结果（如涉及在线平台）；
- 文档与 schema 是否同步。

请保持 PR 聚焦，不在同一改动中混入无关格式化或重构。

## 可优先贡献的方向

| 方向 | 示例 |
|---|---|
| 来源兼容 | 新 RSS 变体、官方 transcript、公开平台降级 |
| 转写质量 | 新语言夹具、数字与专名、重复幻觉检测 |
| 证据可靠性 | 时间戳、短引、主张和画面证据校验 |
| 信息提炼 | 关键问题识别、直接答案、反直觉发现、关键案例与适用边界 |
| 用户体验 | 更快读懂的卡片与排版、更清楚的限制和恢复路径 |
| 可移植性 | 不绑定厂商的能力适配器和跨系统测试 |

感谢你让 Podcast Reader 更接近“贴一个链接就能放心使用”。
