# 质量与验收

## 完成定义

一个版本只有同时满足以下条件才可发布：

- Skill frontmatter 合法，名称与目录一致；
- `SKILL.md` 少于 500 行，所有相对链接有效；
- 所有 Python CLI 可编译且 `--help` 返回成功；
- 离线测试不访问网络并全部通过；
- 本地字幕可以一键生成 bundle、标准转录、字幕和索引；
- 统一入口可以从任意工作目录处理本地字幕和媒体，并记录 `progress.json`；
- 环境自检不联网、不下载、不要求 API Key，并能区分 ready/degraded/blocked；
- 黄金 Markdown 通过严格结构/证据校验；
- JSON 证据可导出 Excel 友好的 UTF-8 BOM CSV；
- YouTube 公开字幕链路形成 `ready_for_analysis` bundle；
- Bilibili 在 yt-dlp 遇到 412 时，仍可通过公开 API 形成元数据、字幕或多分 P 音频 bundle，且不使用浏览器 Cookie；
- 没有宿主原生转写工具或 API Key 时，可通过隔离的本地模型输出带时间戳 JSON；
- Skill 核心指令不绑定任一厂商密钥，并明确不同 Agent 的能力降级路径；
- 公开 RSS 可以精确匹配或显式选择最新一期；
- 本地视频可以生成关键帧 manifest 与 contact sheet；
- 无未处理 TODO、FIXME 或程序占位实现。
- [用户体验验收矩阵](ux-acceptance.md)中的 12 个核心场景具有自动化或前向测试证据。

## 测试分层

| 层 | 内容 | 是否联网 |
|---|---|---|
| 单元 | RSS、HTML、时间解析、字幕去重、检索 | 否 |
| 契约 | frontmatter、文档链接、CLI help、代理元数据 | 否 |
| 端到端 | 本地 SRT → bundle → transcript → chunks → validate | 否 |
| 黄金输出 | 完整 Markdown 严格验证、CSV 编码 | 否 |
| 冒烟 | YouTube、Bilibili、公开 RSS、FFmpeg 关键帧 | 是（长媒体下载仅做显式发布验收） |

## 命令

```text
python -m compileall -q podcast-reader/scripts
python -m unittest discover -s podcast-reader/tests -v
```

公开冒烟测试应使用 `--mode subtitles`，避免为了 CI 或开发验证下载长音频。平台网络错误必须被记录为可解释结果，不应通过 Cookie 或规避机制强行绕过。

## 性能边界

- 页面解析读取有大小上限。
- 直接媒体默认限制为 2 GB，可显式调整。
- 自动音频提取默认拒绝超过 8 小时的内容，需确认后放宽。
- 关键帧默认最多 16 张，硬上限 60 张。
- 文本索引按字符与时间双阈值分块，并保留少量重叠。

## 发布检查

1. 运行全部离线测试与编译。
2. 检查 `CHANGELOG.md`。
3. 用至少一个公开视频链接运行字幕模式。
4. 验证错误路径不会泄露 Cookie、签名 URL 或本地密钥。
5. 确认报告模板、结构化 schema 和验证器同步。
6. 更新版本标签并创建发布说明。
