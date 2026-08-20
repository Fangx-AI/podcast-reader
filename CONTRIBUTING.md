# Contributing

感谢你改进 Podcast Reader。项目优先接受能够提高来源兼容性、证据可靠性、长内容体验、多语言质量和可恢复性的改动。

## 开始之前

1. 先用 Issue 描述问题、来源类型、预期行为和实际行为。
2. 涉及平台适配时，只使用公开、合法、无需规避访问控制的接口。
3. 不要提交 Cookie、Feed Token、签名 URL、API Key、私人媒体或受版权保护的完整文本。
4. 新增依赖前说明为什么标准库或现有工具无法完成。

## 本地开发

```text
python -m compileall -q podcast-reader/scripts
python -m unittest discover -s podcast-reader/tests -v
```

核心离线测试必须在 Windows 与 Linux 上通过。测试夹具应短小、可再分发、确定性强，并且不访问网络。

## 改动要求

- 新来源：补充解析/摄取测试、错误降级、隐私与限制说明。
- 新转录格式：保留原始文本、时间戳、说话人和未知值。
- 新输出字段：同步 `references/output-schema.md`、模板、验证器和固定样例。
- 新分析模式：明确何时触发、证据要求、失败边界和导出结构。
- 文档改动：保持 `SKILL.md` 精简，将复杂内容放入单层 `references/`。

## Commit 与 PR

提交信息应说明结果，例如 `feat: add Podcasting 2.0 transcript discovery`。Pull Request 需要包含：

- 用户问题与解决方式；
- 兼容性或安全影响；
- 新增/修改测试；
- 手动冒烟结果（如涉及在线平台）；
- 文档与 schema 是否同步。

请保持 PR 聚焦，不在同一改动中混入无关格式化或重构。
