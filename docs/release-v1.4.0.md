# Podcast Reader v1.4.0 发布说明

v1.4.0 的主题是：把完整底层能力变成真正链接即用、零 Key 默认、可恢复、可持续追问的用户体验。

## 用户可感知变化

- 一条命令处理链接或文件：`process_episode.py` 自动完成字幕优先、必要时本地转写、时间线恢复与索引。
- 一条命令安全安装：`install_skill.py` 默认拒绝覆盖，强制更新会保留旧版本备份。
- 无网络环境自检：`doctor.py` 明确显示哪些能力 ready、degraded 或 blocked。
- 长任务有反馈：终端显示阶段，`progress.json` 保存最近一次处理状态。
- 中文可追问英文节目：检索器利用双语术语表和结构化主张证据回到源 segment。
- 转录完成后本地回填不再依赖平台第二次联网。

## 发布证据

| 项目 | 结果 |
|---|---|
| 离线测试 | 38/38 通过 |
| Python 编译 | 全部脚本通过 |
| Skill 官方快速校验 | 通过（Windows 使用 Python UTF-8 模式） |
| CI 配置 | Windows/Linux × Python 3.11/3.12/3.14 |
| 产品验收矩阵 | 15 个场景，其中 12 个核心场景全部通过 |
| 独立前向测试 | 4 次：本地媒体、Bilibili 复用/追问、YouTube 冷启动、全新安装 |
| 安全扫描 | 无媒体、完整转录、pyc、大文件、真实凭据或签名 URL 进入 Git |

## 安装与开始

```text
python podcast-reader/scripts/install_skill.py --json
python ~/.codex/skills/podcast-reader/scripts/doctor.py --json
```

然后直接在支持 Agent Skills 的客户端中说：

```text
用 $podcast-reader 完整分析这个链接，保留时间戳并导出 Markdown：https://...
```

## 已知边界

- 本地 `faster-whisper` 不提供可靠说话人分离；需要 diarization 时应使用宿主原生或用户已配置的能力。
- 首次零 Key 转写需要联网下载隔离依赖和模型；多小时 CPU 转写仍然耗时。
- 纯跨语言检索依赖分析 bundle 中的双语 glossary 或结构化 evidence；尚未分析的原始 bundle 由 Agent 补充翻译查询词。
- 平台登录、付费墙、DRM、地区限制和私人 Feed 不会被绕过。
- 医疗、法律、金融等高风险陈述必须与节目原话分开，并按需进行外部权威核验。

## 发布操作

1. 从干净 Git `HEAD` 创建带目录前缀的 ZIP。
2. 记录 ZIP SHA-256，并确认不包含 `.git`、缓存、媒体或测试输出。
3. 解压到隔离目录，运行安装器、官方快速校验、编译和离线测试。
4. 如需公开 GitHub Release，必须由用户明确授权后再推送仓库和创建远程发布。
