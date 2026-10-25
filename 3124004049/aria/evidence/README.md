# 测试与功能验证记录

Windows 原生兼容的最新验证：921 项通过、3 项按环境条件跳过，六项离线场景通过。环境、复现命令与运行边界见 [Windows 验证记录](./windows-validation.md)。

验证日期：2026-10-21。环境：WSL Ubuntu 22.04、CPython 3.13.16、uv 0.13.4、ripgrep 14.1.1。

| 检查 | 结果 | 证据 |
| --- | --- | --- |
| 依赖安装 | `uv sync --frozen` 成功，依赖版本由 `uv.lock` 固定 | 版本见上述环境与锁文件 |
| 完整自动化测试 | 910 通过，1 跳过 | [pytest.txt](./pytest.txt) |
| 六项离线场景 | 6/6 通过 | [摘要](./offline-summary.txt)、[完整 JSONL](./offline-results.jsonl)、[HTML 报告](./offline-report.html) |
| 命令入口 | `aria --help` 正常退出并显示帮助 | [cli-help.txt](./cli-help.txt) |
| 打包与资源 | Wheel 构建成功；离开源码目录后验证命令入口、六个提示词资源与配置模板 | [package-smoke.txt](./package-smoke.txt) |
| 搜索工具 | 使用 Linux ripgrep 14.1.1 后搜索测试全部通过 | [ripgrep-version.txt](./ripgrep-version.txt) |

唯一跳过项是 `tests/test_big_task_single_goal.py` 中需要 `tsc` 的 TypeScript 外部项目验证测试：本验证环境没有安装 TypeScript 编译器。其他测试已执行。

Wheel 验证将生成的安装包放入独立虚拟环境，通过 `PYTHONPATH` 复用已按锁文件安装的第三方依赖；实际 `core` 包从 Wheel 安装位置导入，并检查其路径不属于源项目。没有重新从包索引解析一套依赖。

首次完整测试有四项搜索测试因缺少 `rg` 失败。补齐 ripgrep 后重新执行完整测试，得到以上结果；源码与测试未为此修改。课程 README 已明确列出 ripgrep 为运行依赖。

## 离线场景

1. `multi_turn_memory`：保存并恢复会话，验证下一轮携带历史。
2. `file_edit`：通过真实本地文件工具编辑文件并核对结果。
3. `tool_failure_recovery`：工具失败后根据返回错误继续执行。
4. `compaction_restore`：上下文压缩后的会话恢复。
5. `cancelled_tool_restore`：工具调用取消后的会话恢复。
6. `model_network_retry`：模拟网络错误并验证重试。

场景使用可控的模型替身和临时工作区，不需要 API Key，不产生真实模型调用。通过这些检查验证代码和本地工具链可运行；真实模型的自然语言交互效果须由小组配置有效服务后演示。

## 复现

先安装 Python 3.11+、Git、uv 与 ripgrep，再从 `3124004049/aria/` 执行：

```bash
uv sync --frozen
uv run --frozen pytest -q -rs
uv run --frozen python -m evaluation.runner
uv run --frozen aria --help
uv build --wheel
```

离线评测默认写入被忽略的 `evaluation-results/`。本目录保存的是本次运行结果，不应直接覆盖后将历史记录当作新一轮结果。
