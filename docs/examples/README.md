# 省流版示例

[打开卡片阅读页](summary-preview.html) · [查看页面截图](../assets/summary-preview.png)

这是一段项目原创的虚构演示对话，人物、时间轴和计算案例均为演示内容，不代表真实播客、采访或调查数据。示例展示关键问题、直接答案、高价值信息、原文依据与未解问题。

在仓库根目录重建：

```bash
python podcast-reader/scripts/process_episode.py podcast-reader/tests/fixtures/summary-demo.srt --output-dir outputs/summary-demo --output-language zh-CN
```

将 `podcast-reader/tests/fixtures/summary-demo-evidence.json` 复制到 `outputs/summary-demo/evidence.json`，然后执行：

```bash
python podcast-reader/scripts/finalize_bundle.py outputs/summary-demo
python podcast-reader/scripts/validate_bundle.py outputs/summary-demo
```

生成的 `outputs/summary-demo/reader.html` 与 `summary.md` 可以直接打开。真实播客需由当前 Agent 阅读其完整文本并编写对应 `evidence.json`，不要套用演示内容。
