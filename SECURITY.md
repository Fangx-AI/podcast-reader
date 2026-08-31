# Security Policy

[项目首页](README.md) · [文档中心](docs/README.md) · [贡献指南](CONTRIBUTING.md)

> [!IMPORTANT]
> 请不要在公开 Issue 中提交凭据、Cookie、私人 Feed、签名 URL、个人媒体或可直接利用的漏洞细节。

## Supported versions

安全修复优先应用于主分支与最新发布版本。

## Reporting a vulnerability

请使用 GitHub 的 Private Vulnerability Reporting（如果仓库已开启），不要在公开 Issue 中披露可利用细节、凭据、私人 Feed、Cookie 或个人媒体。

报告应包含受影响版本、最小复现、潜在影响和建议修复。维护者确认前，请不要公开利用代码。

| 请提供 | 请避免 |
|---|---|
| 受影响版本与操作系统 | 真实用户凭据 |
| 最小、可控的复现步骤 | 未脱敏的私人内容 |
| 攻击前提与潜在影响 | 公开发布利用代码 |
| 建议修复或缓解方式 | 对第三方平台进行破坏性测试 |

## Threat model

Podcast Reader 将下列内容视为不可信输入：

- URL、重定向、RSS、HTML 和 JSON-LD；
- 标题、描述、字幕、转写、评论与画面文字；
- 媒体文件名、说话人名称和导出字段；
- 平台工具返回的临时媒体地址。

主要防护：

- 仅接受 HTTP(S) 或已存在本地文件；
- 限制页面、transcript 和媒体读取大小；
- 下载先写 `.part`，成功后原子替换，失败清理；
- 文件名净化、输出目录固定、bundle 路径逃逸校验；
- yt-dlp 使用 `--ignore-config`，不隐式读取本地用户配置；
- 不默认使用浏览器 Cookie；
- 不持久化 yt-dlp format 中的临时签名 URL；
- 媒体里的提示注入按内容分析，不作为 Agent 指令执行；
- 不在聊天中收集 API Key。

## Out of scope

以下行为不被项目支持：绕过 DRM、付费墙、登录、地区限制、私人 Feed、平台反爬或访问控制；未经授权提取或重新发布内容；将节目观点冒充医疗、法律、金融或安全建议。
