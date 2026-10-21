# Aria 迁移说明

## 来源与位置

- 迁移日期：2026-10-21。
- 来源：本地工作区 `F:\code\aria-main` 的现有项目快照。该目录没有 `.git` 历史，无法声明其对应的上游提交。
- 来源 README 引用的上游地址：<https://github.com/KevinBarrus/aria>。本次复用的是本地快照，未将其假定为上游最新版本。
- 目标：`gdut-software-engineering-2026/3124004049/aria/`。
- 课程作业：[构建一个能说会做的智能体](https://edu.cnblogs.com/campus/gdgy/Class56-Grade2024-CS/homework/16760)。

## 复用范围

完整复制 `src/`、`tests/`、`evaluation/`、`design/`、`problems/`、`todo/`、`pyproject.toml` 和 `uv.lock`。原 README 按原内容保存为 `README.upstream.md`。测试依赖 `evaluation` 模块，因此将评测代码与测试一同保留。

原有源码、测试、评测脚本、提示词和依赖文件保持原内容。本次新增课程 README、配置示例、演示输入和迁移证据，并更新两级作业索引。`.gitignore` 增加演示输出忽略项；项目内 `.gitattributes` 固定使用 LF 换行，便于 Windows / WSL 复现。

不复制用户配置、API Key、会话、虚拟环境、缓存和构建产物。运行时产生的 `.aria/` 和 `evaluation-results/` 保持忽略。

## 复用与本次成果的边界

模型调用、Agent 循环、工具审批、文件与命令工具、上下文管理、终端界面、会话恢复、MCP 与子 Agent 能力均属于既有实现。本次成果是迁移集成、课程场景和说明整理，以及在目标位置重新安装和执行验证。

`design/`、`problems/`、`todo/` 保留原有历史资料，可能包含旧机器路径、当时的改进计划和未附带的外部实验结果。它们不是本次作业已完成事项的声明；以课程 README 和 `evidence/` 中本次实际记录为准。

原快照未包含独立 LICENSE 文件。本次保留来源，不为已有代码另行声明许可证或虚构原创归属。

## 复现与证据

在目标项目目录运行 `uv sync --frozen`、`uv run --frozen pytest -q` 和 `uv run --frozen python -m evaluation.runner`。完整自动化验证使用 WSL Ubuntu；配置示例仅包含占位信息。

源码逐文件 SHA-256 比较、测试结果与离线评测记录见 [evidence/](./evidence/)。真实模型演示未包含在离线验证中。
