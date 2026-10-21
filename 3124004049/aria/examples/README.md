# 配置与演示样例

`settings.example.json` 用于展示配置结构，其中的模型服务、模型名和密钥都是占位内容。请复制到被忽略的 `.aria/settings.json`，填写实际值后运行 `uv run aria --config .aria/settings.json`。

`demo-workspace/meeting-notes.txt` 是文件整理演示输入，内容为演示用的任务安排。真实输出由 Agent 运行后创建，不能将样例输入视为已完成记录。

## 可选 stdio MCP

在实际配置 JSON 顶层添加 `mcp_stdio`，与 `model` 并列：

```json
{
  "mcp_stdio": {
    "command": "python",
    "arguments": ["/absolute/path/to/your_mcp_server.py"],
    "provider_id": "course-demo",
    "trusted_read_tools": []
  }
}
```

需要自行提供支持 stdio 通信的 MCP Server，并将 `command`、`arguments` 改为实际启动命令。该片段须合并到已有模型配置中，不能单独作为完整配置使用。

默认保持 `trusted_read_tools` 为空，由用户审批远程工具。确认可信且只读的工具后，才按 Server 返回的原始工具名加入此列表。`/mcp` 可以查看接入状态。

项目已有 MCP 握手、工具发现、调用和错误处理测试：`uv run --frozen pytest -q tests/test_mcp.py tests/test_mcp_stdio.py`。这些测试启动测试用 Server，不代表已连接某个真实业务服务。
