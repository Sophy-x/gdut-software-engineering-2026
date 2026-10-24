# Windows 原生兼容验证

验证日期：2026-10-24。环境：Windows x64（系统版本 10.0.26200）、CPython 3.11.7、uv 0.13.5、ripgrep 15.2.0 MSVC。依赖来自项目 `.venv`，通过 `uv sync --frozen` 同步。

| 检查 | 结果 |
| --- | --- |
| 全量自动化测试 | 915 通过、0 失败、1 跳过，耗时 220.23 秒 |
| Linux Docker 容器集成 | 2 项通过：Windows 工作区挂载/读写，以及超时后清理容器 |
| 六项离线场景 | 6/6 通过 |
| 程序入口 | `uv run --frozen aria --help` 正常显示帮助 |
| 编译检查 | `uv run --frozen python -m compileall -q src/core evaluation tests` 通过 |
| 中文和空格路径 | ripgrep 搜索、Git worktree 创建与清理回归通过 |
| 容器调度 | Windows/POSIX 用户身份分流、子进程参数、超时和取消清理单元测试通过 |

全量测试命令与最终摘要：

```text
uv run --frozen pytest -q --tb=short -ra

SKIPPED [1] tests\test_big_task_single_goal.py:114: tsc not installed
915 passed, 1 skipped in 220.23s (0:03:40)
```

唯一跳过项需要可选的 TypeScript 编译器。未通过跳过来规避 Windows 失败；测试中的 POSIX 专属命令、文本编码、路径断言和过短的定时器假设已调整为可跨平台验证的写法。

界面测试通过 prompt-toolkit 的应用会话注入测试输入输出，实际执行布局、消息渲染、历史、快捷键处理等逻辑，不要求测试进程拥有物理 Win32 控制台。此结果不代表已完成真实终端键盘操作或真实模型服务的端到端验证。

## 运行边界

- 日常 Aria 功能在 Windows 原生环境验证，命令工具使用 `cmd.exe`；PowerShell 命令需要显式调用 PowerShell。
- SWE-bench 宿主侧的容器用户身份、进程创建与清理已适配 Windows，并通过 Alpine Linux 容器实测 Windows 工作区挂载、读写及超时清理。本次没有执行真实 SWE-bench 任务：当前环境未安装 `datasets` 与 `swebench` Python 包，也未下载任何 SWE-bench 官方实例镜像；没有发起真实模型请求。
- `evaluation.big_task_single_goal` 实验会挂载宿主 Linux Node 工具链，并使用 POSIX 用户身份，仍应在 Linux/WSL2 下运行。
- `evaluation.subagent_workflow_smoke` 的本地验证命令已按 Windows/Unix 分别转义；真实模型冒烟需要有效模型配置和显式 `--confirm`。

uv 和 ripgrep 安装后，旧进程可能尚未继承新的 `PATH`。本次通过 uv 完整路径启动，并仅为测试进程补充 ripgrep 所在目录；用户可重新打开终端后使用常规命令。
